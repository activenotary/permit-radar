#!/usr/bin/env python3
"""Permit Radar — ingestion. Pulls recent permits from city open-data APIs
(Socrata SODA), normalizes them to a common schema, upserts into SQLite.

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
        "issued_date": (rec.get(ccfg["issued_field"]) or "")[:10],
        "value": to_float(rec.get(f.get("value"))),
        "address": address,
        "contractor": rec.get(f.get("contractor")) or "",
        "lat": to_float(rec.get(f.get("lat"))),
        "lon": to_float(rec.get(f.get("lon"))),
        "raw_json": json.dumps(rec)[:8000],
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }

def fetch_live(city_key, ccfg, days):
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
            print(f
