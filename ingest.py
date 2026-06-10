#!/usr/bin/env python3
"""Permit Radar — ingestion. Pulls recent permits from city open-data APIs
(Socrata SODA + ArcGIS REST + custom city portals), normalizes to a common
schema, upserts into SQLite.

Usage:
  python3 ingest.py                              # live pull, all cities
  python3 ingest.py --city chicago               # one city
  python3 ingest.py --fixture fixtures/chicago_sample.json --city chicago
"""
import argparse, json, sqlite3, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config.json").read_text())

SCHEMA = """
CREATE TABLE IF NOT EXISTS permits (
  id TEXT PRIMARY KEY,            -- city:permit_id
  city TEXT, permit_id TEXT, permit_type TEXT, description TEXT,
  issued_date TEXT, value REAL, address TEXT, contractor TEXT,
  lat REAL, lon REAL, raw_json TEXT,
  ingested_at TEXT,
  enriched INTEGER DEFAULT 0,
  trades TEXT, summary TEXT, lead_score INTEGER
);
CREATE INDEX IF NOT EXISTS idx_city_date ON permits(city, issued_date);
CREATE INDEX IF NOT EXISTS idx_enriched ON permits(enriched);
"""

def db():
    conn = sqlite3.connect(ROOT / CFG["db_path"])
    conn.executescript(SCHEMA)
    return conn

def to_float(v):
    try:
        return float(str(v).replace("$", "").replace(",", ""))
    except (TypeError, ValueError):
        return None

def to_date(v):
    if isinstance(v, (int, float)):  # ArcGIS returns epoch milliseconds
        try:
            return datetime.fromtimestamp(v / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        except (ValueError, OSError, OverflowError):
            return ""
    return (str(v) if v else "")[:10]

def normalize(city_key, ccfg, rec):
    f = ccfg["fields"]
    pid = str(rec.get(f["permit_id"], "")).strip()
    if not pid:
        return None
    address = " ".join(str(rec.get(a, "") or "").strip() for a in ccfg.get("address_fields", [])).strip()
    return {
        "id": f"{city_key}:{pid}",
        "city": city_key,
        "permit_id": pid,
        "permit_type": rec.get(f.get("permit_type"), ""),
        "description": (rec.get(f.get("description")) or "")[:2000],
        "issued_date": to_date(rec.get(ccfg["issued_field"])),
        "value": to_float(rec.get(f.get("value"))),
        "address": address,
        "contractor": rec.get(f.get("contractor")) or "",
        "lat": to_float(rec.get(f.get("lat"))),
        "lon": to_float(rec.get(f.get("lon"))),
        "raw_json": json.dumps(rec)[:8000],
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }

def fetch_live_arcgis(city_key, ccfg, days):
    """ArcGIS REST feature-service feeds (Las Vegas, Tucson, ...)."""
    if requests is None:
        sys.exit("pip install requests")
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    where = f"{ccfg['issued_field']} >= DATE '{since}'"
    if ccfg.get("extra_where"):
        where += f" AND {ccfg['extra_where']}"
    params = {"where": where, "outFields": "*", "returnGeometry": "false",
              "orderByFields": f"{ccfg['issued_field']} DESC",
              "resultRecordCount": 1000, "f": "json"}
    r = requests.get(ccfg["endpoint"], params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"ArcGIS error: {str(data['error'])[:300]}")
    return [f["attributes"] for f in data.get("features", [])]

def fetch_live_riverside(city_key, ccfg, days):
    """City of Riverside Engage portal: paged JSON, no server-side filters.
    The portal 500s on large offsets, so we work in DESCENDING permit-number
    order where the newest blocks sit at small, servable offsets."""
    if requests is None:
        sys.exit("pip install requests")

    def get(params):
        r = requests.get(ccfg["endpoint"], params=params, timeout=60)
        if r.status_code >= 500:
            return None  # portal 500s on offsets past what it can serve
        r.raise_for_status()
        return r.json()

    def probe(offset):
        rows = get({"max": 1, "offset": offset, "sort": "Permit Number", "order": "desc"})
        if not rows:
            return None
        v = rows[0].get("Permit Number")
        return v if isinstance(v, str) else ""

    year = datetime.now(timezone.utc).year
    prefix = (ccfg.get("prefixes") or ["BP"])[0]
    block_top = f"{prefix}-9999"        # anything above this is a later prefix (EP/MP/PP...)
    this_year = f"{prefix}-{year}-"

    # binary search (desc): first offset inside the BP block
    lo, hi = 0, 25000
    while lo < hi:
        mid = (lo + hi) // 2
        pn = probe(mid)
        if pn is None or pn > block_top:
            lo = mid + 1
        else:
            hi = mid

    out = []
    off = lo
    extra = 0
    for _ in range(220):  # safety cap ~22k records
        rows = get({"max": 100, "offset": off, "sort": "Permit Number", "order": "desc"})
        if not rows:
            break
        for rec in rows:
            pn = rec.get("Permit Number")
            if not isinstance(pn, str) or pn > block_top:
                continue  # still in a later prefix block (overshoot)
            out.append(rec)
        last = rows[-1].get("Permit Number")
        if isinstance(last, str) and last < this_year:
            extra += 1   # into last year's numbers — sweep a tail, then stop
            if extra >= 40:
                break
        off += 100

    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    keep = []
    for rec in out:
        if rec.get("Permit Type") != "Commercial":
            continue
        d = str(rec.get("Issue Date") or "")
        if len(d) != 10 or d < since:
            continue
        keep.append(rec)
    return keep

def fetch_live(city_key, ccfg, days):
    if ccfg.get("api") == "arcgis":
        return fetch_live_arcgis(city_key, ccfg, days)
    if ccfg.get("api") == "riverside":
        return fetch_live_riverside(city_key, ccfg, days)
    if requests is None:
        sys.exit("pip install requests")
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00.000")
    where = f"{ccfg['issued_field']} > '{since}'"
    if ccfg.get("extra_where"):
        where += f" AND {ccfg['extra_where']}"
    url = f"https://{ccfg['domain']}/resource/{ccfg['dataset']}.json"
    params = {"$where": where, "$limit": 1000, "$order": f"{ccfg['issued_field']} DESC"}
    headers = {}
    import os
    if os.environ.get("SODA_APP_TOKEN"):
        headers["X-App-Token"] = os.environ["SODA_APP_TOKEN"]
    r = requests.get(url, params=params, headers=headers, timeout=60)
    r.raise_for_status()
    return r.json()

def upsert(conn, rows):
    n = 0
    for row in rows:
        if row is None:
            continue
        cur = conn.execute("SELECT 1 FROM permits WHERE id=?", (row["id"],))
        if cur.fetchone():
            continue
        conn.execute(
            """INSERT INTO permits (id,city,permit_id,permit_type,description,issued_date,
               value,address,contractor,lat,lon,raw_json,ingested_at)
               VALUES (:id,:city,:permit_id,:permit_type,:description,:issued_date,
               :value,:address,:contractor,:lat,:lon,:raw_json,:ingested_at)""", row)
        n += 1
    conn.commit()
    return n

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", help="single city key from config.json")
    ap.add_argument("--days", type=int, default=CFG["lookback_days"])
    ap.add_argument("--fixture", help="local JSON file instead of live API (testing)")
    args = ap.parse_args()

    conn = db()
    cities = [args.city] if args.city else list(CFG["cities"].keys())
    total = 0
    for ck in cities:
        ccfg = CFG["cities"][ck]
        if args.fixture:
            records = json.loads(Path(args.fixture).read_text())
            print(f"[{ck}] fixture: {len(records)} records")
        else:
            try:
                days = ccfg.get("lookback_days", args.days)
                records = fetch_live(ck, ccfg, days)
                print(f"[{ck}] live: {len(records)} records (last {days}d)")
            except Exception as e:
                print(f"[{ck}] FETCH FAILED: {e}", file=sys.stderr)
                continue
        n = upsert(conn, (normalize(ck, ccfg, r) for r in records))
        print(f"[{ck}] {n} new permits stored")
        total += n
    print(f"Done. {total} new permits.")

if __name__ == "__main__":
    main()
