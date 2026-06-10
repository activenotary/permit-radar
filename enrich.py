#!/usr/bin/env python3
"""Permit Radar — enrichment. Tags each permit with trades, a plain-English
summary, and a lead score (0-100).

Uses the Claude API when ANTHROPIC_API_KEY is set; otherwise falls back to a
rule-based keyword classifier so the pipeline always runs.
"""
import json, os, re, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config.json").read_text())

TRADE_KEYWORDS = {
    "roofing": ["roof", "re-roof", "reroof", "shingle"],
    "hvac": ["hvac", "mechanical", "furnace", "air cond", "a/c", "rtu", "ventilation", "duct", "heat pump", "boiler"],
    "electrical": ["electric", "wiring", "panel", "low voltage", "lighting", "ev charg", "solar", "photovoltaic"],
    "plumbing": ["plumb", "sewer", "water heater", "water service", "piping", "irrigation", "backflow"],
    "demolition": ["demolit", "wreck", "raze", "tear down"],
    "general_renovation": ["renovat", "remodel", "build-out", "buildout", "build out", "interior alter", "tenant improvement", "rehab", "addition", "new construction", "erect"],
    "concrete_masonry": ["concrete", "masonry", "foundation", "tuckpoint", "porch", "paving", "sidewalk"],
    "signage": ["sign", "awning", "canopy"],
    "fire_protection": ["sprinkler", "fire alarm", "fire suppression", "fire pump"],
    "windows_doors": ["window", "door", "glazing", "storefront"],
    "elevator": ["elevator", "escalator", "lift"],
    "fencing": ["fence", "fencing"],
}

def rule_based(p):
    text = f"{p['permit_type']} {p['description']}".lower()
    trades = [t for t, kws in TRADE_KEYWORDS.items() if any(k in text for k in kws)]
    if not trades:
        trades = ["general_renovation"] if p.get("value") else ["other"]
    v = p.get("value") or 0
    score = 30
    if v >= 50_000: score += 15
    if v >= 250_000: score += 20
    if v >= 1_000_000: score += 20
    if p.get("contractor"): score += 5
    if len(trades) >= 2: score += 5
    desc = re.sub(r"\s+", " ", (p["description"] or p["permit_type"] or "")).strip()
    summary = desc[:180].capitalize() if desc else "No description provided."
    return {"trades": trades, "summary": summary, "lead_score": min(score, 100)}

def claude_batch(permits, model):
    """Batch-classify via Claude API. Returns {permit_id: result} or None on failure."""
    import requests
    items = [{"id": p["id"], "type": p["permit_type"], "desc": p["description"][:400],
              "value": p["value"]} for p in permits]
    prompt = (
        "Classify each building permit for a contractor lead-gen service. "
        f"Valid trades: {', '.join(TRADE_KEYWORDS)}. For EACH permit return: id, "
        "trades (array, the trades that could win work from this project), "
        "summary (one plain-English sentence a contractor instantly understands), "
        "lead_score (0-100: project value, trade-work clarity, recency; commercial scores higher). "
        "Respond with ONLY a JSON array.\n\n" + json.dumps(items)
    )
    r = requests.post("https://api.anthropic.com/v1/messages",
        headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                 "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": model, "max_tokens": 4000,
              "messages": [{"role": "user", "content": prompt}]}, timeout=120)
    r.raise_for_status()
    text = r.json()["content"][0]["text"]
    m = re.search(r"\[.*\]", text, re.S)
    return {x["id"]: x for x in json.loads(m.group(0))} if m else None

def main():
    conn = sqlite3.connect(ROOT / CFG["db_path"])
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM permits WHERE enriched=0 LIMIT ?",
        (CFG["enrich"]["max_permits_per_run"],))]
    if not rows:
        print("Nothing to enrich."); return

    use_api = bool(os.environ.get("ANTHROPIC_API_KEY"))
    mode = "claude" if use_api else "rule-based fallback"
    print(f"Enriching {len(rows)} permits ({mode})")

    bs = CFG["enrich"]["batch_size"]
    for i in range(0, len(rows), bs):
        batch = rows[i:i+bs]
        results = None
        if use_api:
            try:
                results = claude_batch(batch, CFG["enrich"]["model"])
            except Exception as e:
                print(f"[warn] Claude API failed ({e}); falling back", file=sys.stderr)
        for p in batch:
            res = (results or {}).get(p["id"]) or rule_based(p)
            conn.execute(
                "UPDATE permits SET enriched=1, trades=?, summary=?, lead_score=? WHERE id=?",
                (json.dumps(res.get("trades", ["other"])), res.get("summary", "")[:300],
                 int(res.get("lead_score", 30)), p["id"]))
        conn.commit()
        print(f"  batch {i//bs + 1}: {len(batch)} done")
    print("Enrichment complete.")

if __name__ == "__main__":
    main()
