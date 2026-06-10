#!/usr/bin/env python3
"""JustPermitted — pSEO static site generator (with live Stripe checkout)."""
import html, json, sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config.json").read_text())
SITE = ROOT / "docs"

STRIPE_49 = "https://buy.stripe.com/28E4gy3XF9h80Ded8IfMA00"   # 1 Metro, 1 Trade
STRIPE_99 = "https://buy.stripe.com/cNi6oGbq71OGadO5GgfMA01"   # 1 Metro, All Trades

TRADE_LABELS = {
    "roofing": "Roofing", "hvac": "HVAC & Mechanical", "electrical": "Electrical",
    "plumbing": "Plumbing", "demolition": "Demolition", "general_renovation": "Renovation & New Construction",
    "concrete_masonry": "Concrete & Masonry", "signage": "Signage", "fire_protection": "Fire Protection",
    "windows_doors": "Windows, Doors & Glazing", "elevator": "Elevator", "fencing": "Fencing", "other": "Other",
}

CSS = """body{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;max-width:880px;margin:0 auto;padding:24px;color:#111827;line-height:1.6}
h1{font-size:28px;letter-spacing:-.02em}h2{font-size:20px}a{color:#1d4ed8}
table{border-collapse:collapse;width:100%;margin:18px 0}th,td{padding:9px 10px;border-bottom:1px solid #e5e7eb;text-align:left;font-size:14.5px}
th{font-size:12px;text-transform:uppercase;color:#6b7280}.pill{background:#eff6ff;color:#1d4ed8;border-radius:10px;padding:2px 9px;font-size:12px;font-weight:600}
.stat{display:inline-block;background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:12px 18px;margin:0 10px 10px 0}
.stat b{display:block;font-size:22px}footer{margin-top:40px;color:#9ca3af;font-size:12px;border-top:1px solid #e5e7eb;padding-top:14px}
nav{font-size:13px;color:#6b7280;margin-bottom:18px}
.plans{display:flex;gap:16px;flex-wrap:wrap;margin:18px 0}
.plan{flex:1;min-width:250px;border:1px solid #e5e7eb;border-radius:14px;padding:22px;background:#fff}
.plan h3{margin:0 0 6px;font-size:17px}.plan .price{font-size:30px;font-weight:800}.plan .per{color:#6b7280;font-size:14px}
.plan ul{padding-left:18px;color:#374151;font-size:14.5px}
.buy{display:inline-block;background:#1d4ed8;color:#fff !important;padding:12px 26px;border-radius:9px;text-decoration:none;font-weight:700;margin-top:8px}
.buy:hover{background:#1741b8}"""

def page(title, desc, body, home):
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<style>{CSS}</style></head><body>
<nav><a href="{home}">JustPermitted</a></nav>
{body}
<footer>Data: public municipal permit records, updated nightly. Generated {datetime.now().strftime('%B %d, %Y')}.
Verify permit details with the issuing authority before acting. © JustPermitted · justpermitted.com</footer>
</body></html>"""

def fmt(v): return f"${v:,.0f}" if v else "—"

def permit_table(permits, limit=50):
    rows = "".join(f"""<tr><td>{p['issued_date']}</td>
<td>{html.escape((p['summary'] or p['permit_type'] or '')[:140])}<br>
<span style="color:#6b7280;font-size:12.5px">{html.escape(p['address'] or '')}</span></td>
<td>{fmt(p['value'])}</td><td><span class="pill">{p['lead_score']}</span></td></tr>""" for p in permits[:limit])
    return f"<table><tr><th>Issued</th><th>Project</th><th>Value</th><th>Score</th></tr>{rows}</table>"

PLANS_HTML = f"""<h2 id="subscribe">Get tomorrow's permits at 7am</h2>
<div class="plans">
  <div class="plan">
    <h3>Single Trade</h3>
    <div class="price">$49<span class="per">/month</span></div>
    <ul><li>Daily email digest for your metro</li><li>Your trade only (e.g. roofing)</li><li>Project values, addresses &amp; lead scores</li><li>Cancel anytime</li></ul>
    <a class="buy" href="{STRIPE_49}">Subscribe — $49/mo</a>
  </div>
  <div class="plan">
    <h3>All Trades</h3>
    <div class="price">$99<span class="per">/month</span></div>
    <ul><li>Daily email digest for your metro</li><li>Every trade category included</li><li>Project values, addresses &amp; lead scores</li><li>Cancel anytime</li></ul>
    <a class="buy" href="{STRIPE_99}">Subscribe — $99/mo</a>
  </div>
</div>
<p style="color:#6b7280;font-size:13.5px">After subscribing, reply to your receipt email with your metro and trade — your daily digest starts the next morning.</p>"""

def main():
    conn = sqlite3.connect(ROOT / CFG["db_path"]); conn.row_factory = sqlite3.Row
    permits = [dict(r) for r in conn.execute(
        "SELECT * FROM permits WHERE enriched=1 ORDER BY issued_date DESC, lead_score DESC")]
    month = datetime.now().strftime("%B %Y")
    city_links = []

    for ck, ccfg in CFG["cities"].items():
        cps = [p for p in permits if p["city"] == ck]
        if not cps: continue
        label = ccfg["label"]
        trade_links = []

        by_trade = {}
        for p in cps:
            for t in json.loads(p["trades"] or "[]"):
                by_trade.setdefault(t, []).append(p)
        for t, plist in sorted(by_trade.items()):
            tl = TRADE_LABELS.get(t, t.title())
            d = SITE / ck / t; d.mkdir(parents=True, exist_ok=True)
            total = sum(p["value"] or 0 for p in plist)
            biggest = max(plist, key=lambda p: p["value"] or 0)
            body = f"""<h1>New {tl} Permits in {label} — {month}</h1>
<p>{len(plist)} commercial building permits relevant to {tl.lower()} contractors were issued recently in {label},
representing {fmt(total)} in reported project value. The largest: {html.escape((biggest['summary'] or '')[:140])}
({fmt(biggest['value'])}). Every project below was just permitted — meaning trade packages are being awarded now.</p>
<div><span class="stat"><b>{len(plist)}</b>new permits</span>
<span class="stat"><b>{fmt(total)}</b>total reported value</span>
<span class="stat"><b>{fmt(biggest['value'])}</b>largest project</span></div>
{permit_table(plist)}
<p><strong>Want tomorrow's list at 7am?</strong> <a class="buy" href="{STRIPE_49}">Get {tl} alerts for {label} — $49/mo</a></p>"""
            (d / "index.html").write_text(page(
                f"New {tl} Permits in {label} ({month}) | JustPermitted",
                f"{len(plist)} new {tl.lower()} building permits in {label}, updated nightly with project values and addresses.",
                body, "../../"), encoding="utf-8")
            trade_links.append(f'<li><a href="{t}/">{tl} — {len(plist)} new permits</a></li>')

        (SITE / ck).mkdir(parents=True, exist_ok=True)
        cbody = f"""<h1>New Commercial Building Permits in {label} — {month}</h1>
<p>{len(cps)} recent permits, {fmt(sum(p['value'] or 0 for p in cps))} in reported value. Browse by trade:</p>
<ul>{''.join(trade_links)}</ul>{permit_table(cps, 30)}
{PLANS_HTML}"""
        (SITE / ck / "index.html").write_text(page(
            f"New Commercial Building Permits in {label} ({month}) | JustPermitted",
            f"Live tracker of commercial building permits in {label}: values, addresses, contractors. Updated nightly.",
            cbody, "../"), encoding="utf-8")
        city_links.append(f'<li><a href="{ck}/">{label} — {len(cps)} recent permits</a></li>')
        print(f"[{ck}] {len(by_trade)} trade pages + city index")

    SITE.mkdir(exist_ok=True)
    (SITE / "index.html").write_text(page(
        "JustPermitted — Your Next Job, Every Morning at 7am",
        "Daily commercial building permit alerts for contractors and suppliers. Know who pulled permits before your competitors do.",
        f"""<h1>JustPermitted</h1>
<p><strong>Your next job, every morning at 7am.</strong> We track every commercial building permit
in your metro, tag it by trade, and send you the ones worth calling about — the week they're filed.</p>
<h2>Coverage</h2><ul>{''.join(city_links)}</ul>
{PLANS_HTML}""",
        "./"), encoding="utf-8")
    print("Root index written. Total pages:", sum(1 for _ in SITE.rglob("index.html")))

if __name__ == "__main__":
    main()
