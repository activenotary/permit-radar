#!/usr/bin/env python3
"""JustPermitted — pSEO static site generator (v2 design, Stripe checkout)."""
import html, json, re, sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config.json").read_text())
SITE = ROOT / "docs"
BASE = "https://justpermitted.com"

STRIPE_49 = "https://buy.stripe.com/28E4gy3XF9h80Ded8IfMA00"   # 1 Metro, 1 Trade
STRIPE_99 = "https://buy.stripe.com/cNi6oGbq71OGadO5GgfMA01"   # 1 Metro, All Trades

TRADE_LABELS = {
    "roofing": "Roofing", "hvac": "HVAC & Mechanical", "electrical": "Electrical",
    "plumbing": "Plumbing", "demolition": "Demolition", "general_renovation": "Renovation & New Construction",
    "concrete_masonry": "Concrete & Masonry", "signage": "Signage", "fire_protection": "Fire Protection",
    "windows_doors": "Windows, Doors & Glazing", "elevator": "Elevator", "fencing": "Fencing", "other": "Other",
}

CSS = """*{box-sizing:border-box}body{margin:0;font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif;color:#0f172a;line-height:1.6;background:#fff}
.bar{background:#0c1b33;padding:14px 0}
.bar .wrap{display:flex;justify-content:space-between;align-items:center}
.brand{color:#fff;text-decoration:none;font-weight:800;font-size:19px;letter-spacing:-.01em}
.brand em{color:#60a5fa;font-style:normal}
.cta{background:#2563eb;color:#fff;text-decoration:none;font-weight:700;padding:8px 18px;border-radius:8px;font-size:14px}
.wrap{max-width:960px;margin:0 auto;padding:0 20px}
.hero{padding:46px 0 10px}
.hero h1{font-size:38px;margin:0 0 10px;letter-spacing:-.02em;line-height:1.15}
.hero p{font-size:18px;color:#475569;max-width:660px;margin:0 0 8px}
main{padding-bottom:40px}
h1{font-size:29px;letter-spacing:-.02em}h2{font-size:21px;margin-top:36px}
a{color:#2563eb}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px;margin:18px 0}
.card{border:1px solid #e2e8f0;border-radius:14px;padding:20px;text-decoration:none;color:#0f172a;background:#fff;transition:box-shadow .15s}
.card:hover{box-shadow:0 8px 24px rgba(2,6,23,.09)}
.card b{font-size:17px;color:#2563eb}.card span{color:#64748b;font-size:14px;display:block;margin-top:4px}
table{border-collapse:collapse;width:100%;margin:18px 0;font-size:14.5px}
th,td{padding:10px;border-bottom:1px solid #e2e8f0;text-align:left;vertical-align:top}
th{font-size:12px;text-transform:uppercase;color:#64748b;letter-spacing:.04em}
tr:nth-child(even) td{background:#f8fafc}
.pill{background:#eff6ff;color:#1d4ed8;border-radius:10px;padding:2px 9px;font-size:12px;font-weight:700;white-space:nowrap}
.stat{display:inline-block;background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:12px 18px;margin:0 10px 10px 0}
.stat b{display:block;font-size:22px}
.plans{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin:18px 0}
.plan{border:1px solid #e2e8f0;border-radius:16px;padding:24px;background:#fff;position:relative}
.plan.popular{border:2px solid #2563eb}
.badge{position:absolute;top:-12px;right:18px;background:#2563eb;color:#fff;font-size:11px;font-weight:700;padding:3px 10px;border-radius:99px;letter-spacing:.05em}
.plan h3{margin:0 0 6px;font-size:14px;text-transform:uppercase;letter-spacing:.05em;color:#64748b}
.price{font-size:34px;font-weight:800}.per{color:#64748b;font-size:15px;font-weight:400}
.plan ul{padding-left:18px;color:#334155;font-size:14.5px}
.buy{display:inline-block;background:#2563eb;color:#fff !important;padding:12px 26px;border-radius:9px;text-decoration:none;font-weight:700;margin-top:8px}
.buy:hover{background:#1e40af}
footer{border-top:1px solid #e2e8f0;margin-top:48px;padding:20px 0;color:#94a3b8;font-size:12.5px}
@media(max-width:640px){.hero h1{font-size:29px}}"""

def page(title, desc, body, home):
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<style>{CSS}</style></head><body>
<div class="bar"><div class="wrap">
<a class="brand" href="{home}">Just<em>Permitted</em></a>
<a class="cta" href="{home}#subscribe">Get Daily Alerts</a>
</div></div>
<main><div class="wrap">
{body}
</div></main>
<footer><div class="wrap">Data: public municipal permit records, updated nightly. Generated {datetime.now().strftime('%B %d, %Y')}.
Verify permit details with the issuing authority before acting. © JustPermitted · justpermitted.com</div></footer>
<script data-goatcounter="https://justpermitted.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
</body></html>"""

def fmt(v): return f"${v:,.0f}" if v else "—"

JUNK_CONTRACTORS = {"OWNER", "SELF", "NONE", "N/A", "NA", "UNKNOWN", "HOMEOWNER",
                    "OWNER/BUILDER", "OWNER BUILDER", "PROPERTY OWNER", "TBD", "VARIOUS"}

def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60].strip("-")
    return s or None

def display_name(name):
    d = name.strip().title()
    d = re.sub(r"\b(Llc|Inc|Co|Corp|Ltd|Lp|Pc|Dba|Hvac|Usa|Ac|Jb|Rj|Tj)\b",
               lambda m: m.group(0).upper(), d)
    return re.sub(r"'S\b", "'s", d)

def fmt_phone(ph):
    d = re.sub(r"\D", "", str(ph or ""))
    if len(d) == 10:
        return f"({d[:3]}) {d[3:6]}-{d[6:]}"
    return str(ph or "").strip()

def permit_table(permits, limit=50):
    rows = "".join(f"""<tr><td style="white-space:nowrap">{p['issued_date']}</td>
<td>{html.escape((p['summary'] or p['permit_type'] or '')[:140])}<br>
<span style="color:#64748b;font-size:12.5px">{html.escape(p['address'] or '')}</span></td>
<td style="white-space:nowrap">{fmt(p['value'])}</td><td><span class="pill">{p['lead_score']}</span></td></tr>""" for p in permits[:limit])
    return f"<table><tr><th>Issued</th><th>Project</th><th>Value</th><th>Score</th></tr>{rows}</table>"

PLANS_HTML = f"""<h2 id="subscribe">Get tomorrow's permits in your inbox at 7am</h2>
<div class="plans">
  <div class="plan">
    <h3>Single Trade</h3>
    <div class="price">$49<span class="per">/month</span></div>
    <ul><li>Daily email digest for your metro</li><li>Your trade only (e.g. roofing)</li><li>Project values, addresses &amp; lead scores</li><li>Cancel anytime</li></ul>
    <a class="buy" href="{STRIPE_49}">Subscribe — $49/mo</a>
  </div>
  <div class="plan popular">
    <span class="badge">MOST POPULAR</span>
    <h3>All Trades</h3>
    <div class="price">$99<span class="per">/month</span></div>
    <ul><li>Daily email digest for your metro</li><li>Every trade category included</li><li>Project values, addresses &amp; lead scores</li><li>Cancel anytime</li></ul>
    <a class="buy" href="{STRIPE_99}">Subscribe — $99/mo</a>
  </div>
</div>
<p style="color:#64748b;font-size:13.5px">After subscribing, reply to your receipt email with your metro and trade — your daily digest starts the next morning.</p>"""

PLAYS_BODY = f"""<div class="hero">
<h1>The Commercial Permit Playbook</h1>
<p>A building permit isn't just a lead for the trade on the permit — it predicts the next five purchases
at that address. Six plays businesses run with permit data, with real permits from our live feeds.</p>
</div>

<div class="cards">

<div class="card"><b>Signage permit → Janitorial, security &amp; services</b>
<span><strong>The signal:</strong> A commercial signage permit means a new tenant is 4–8 weeks from opening day.
They need recurring cleaning, security, waste pickup, and a point-of-sale vendor — and most haven't chosen any of them yet.<br><br>
<strong>The pitch:</strong> "Saw your sign permit go up at [address] — congrats on the new location.
Can we quote weekly cleaning before your soft-open?"<br><br>
<em>From our feed: sign permits for a Chevron, a CVS, and two new cafes hit Riverside alone in one week.</em></span></div>

<div class="card"><b>New restaurant permit → Kitchen, grease &amp; food supply</b>
<span><strong>The signal:</strong> A new-restaurant or drive-thru build-out means someone is about to buy hood systems,
grease interceptors, refrigeration, smallwares — and sign recurring contracts for hood cleaning and grease-trap service.<br><br>
<strong>The pitch:</strong> "We service every drive-thru on that corridor — want a hood-cleaning quote before the fire marshal asks for one?"<br><br>
<em>From our feed: a $1.7M new drive-thru restaurant permitted in Los Angeles, grease interceptor permits in Riverside the same week.</em></span></div>

<div class="card"><b>Tenant improvement → Furniture, IT &amp; everything inside</b>
<span><strong>The signal:</strong> A TI permit means a business is moving or expanding. Desks, network cabling,
AV systems, access control, movers, interior signage — all unpurchased the day the permit is filed.<br><br>
<strong>The pitch:</strong> "Saw the build-out starting at [address]. We handle structured cabling — can we walk the space before drywall closes?"<br><br>
<em>From our feed: a $350,000 first-tenant dental office permitted in Riverside June 4 — equipment, IT, and signage vendors all unchosen.</em></span></div>

<div class="card"><b>Commercial re-roof → Solar &amp; rooftop equipment</b>
<span><strong>The signal:</strong> A fresh commercial roof is the ideal — and sometimes only — window to install solar.
Panel installers who wait until the roof is old quote against a tear-off; the ones who call at the re-roof permit quote clean.<br><br>
<strong>The pitch:</strong> "Your new roof is the perfect foundation for solar — quote now and the racking goes on while the warranty's fresh."<br><br>
<em>From our feed: a 1,552-panel, $1M commercial solar install permitted in Riverside — on a recently re-covered roof.</em></span></div>

<div class="card"><b>Demolition permit → Everyone, 6–18 months early</b>
<span><strong>The signal:</strong> Nobody pays to demolish a commercial building without a plan for the lot.
A demo permit is the earliest public signal of new construction — months before trade packages go to bid.<br><br>
<strong>The pitch:</strong> "Saw the demo at [address]. When the new building bids, we'd like to be on the list — who's the GC?"<br><br>
<em>From our feed: demolition permits in Chicago, LA and Henderson this week — each one a future jobsite.</em></span></div>

<div class="card"><b>EV charger permit → Electrical, concrete &amp; striping</b>
<span><strong>The signal:</strong> EV charger installs come in waves across a property portfolio — one site this month
means sister sites next quarter. They also mean trenching, concrete pads, bollards, and lot re-striping.<br><br>
<strong>The pitch:</strong> "We did the striping after your charger install at [address] — want pricing for the other locations before the next phase?"<br><br>
<em>From our feed: a $320,000 17-charger installation permitted in Riverside, plus single-charger permits the same week.</em></span></div>

</div>

<h2>The pattern</h2>
<p><strong>Permit data is the earliest public signal that money is about to move at an address.</strong>
Whoever sees it first calls first, and whoever calls first usually wins. JustPermitted sends the signals
to your inbox every morning at 7am — no database to remember to search.</p>
{PLANS_HTML}"""

def main():
    conn = sqlite3.connect(ROOT / CFG["db_path"]); conn.row_factory = sqlite3.Row
    permits = [dict(r) for r in conn.execute(
        "SELECT * FROM permits WHERE enriched=1 ORDER BY issued_date DESC, lead_score DESC")]
    for p in permits:  # drop junk valuations from city data feeds (e.g. $63B typos)
        if p["value"] and p["value"] > 500_000_000:
            p["value"] = None
    month = datetime.now().strftime("%B %Y")
    city_cards = []
    sitemap_urls = [""]

    for ck, ccfg in CFG["cities"].items():
        cps = [p for p in permits if p["city"] == ck]
        if not cps: continue
        label = ccfg["label"]
        trade_links = []
        city_total = sum(p["value"] or 0 for p in cps)

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
representing {fmt(total)} in reported project value. Every project below was just permitted — meaning trade packages
are being awarded right now.</p>
<div><span class="stat"><b>{len(plist)}</b>new permits</span>
<span class="stat"><b>{fmt(total)}</b>total reported value</span>
<span class="stat"><b>{fmt(biggest['value'])}</b>largest project</span></div>
{permit_table(plist)}
<p><strong>Want tomorrow's list at 7am?</strong><br><a class="buy" href="{STRIPE_49}">Get {tl} alerts for {label} — $49/mo</a></p>"""
            (d / "index.html").write_text(page(
                f"New {tl} Permits in {label} ({month}) | JustPermitted",
                f"{len(plist)} new {tl.lower()} building permits in {label}, updated nightly with project values and addresses.",
                body, "../../"), encoding="utf-8")
            trade_links.append(f'<a class="card" href="{t}/"><b>{tl}</b><span>{len(plist)} new permits · {fmt(total)}</span></a>')
            sitemap_urls.append(f"{ck}/{t}/")

        # --- contractor profile pages ---
        by_contractor = {}
        for p in cps:
            nm = (p["contractor"] or "").strip()
            if len(nm) < 4 or nm.upper() in JUNK_CONTRACTORS:
                continue
            by_contractor.setdefault(nm.upper(), {"name": nm, "permits": []})["permits"].append(p)
        contractor_cards = []
        for ckey, c in sorted(by_contractor.items(), key=lambda kv: -len(kv[1]["permits"])):
            plist = c["permits"]
            ctotal = sum(p["value"] or 0 for p in plist)
            if len(plist) < 2 and ctotal < 100000:
                continue  # skip thin one-permit/low-value profiles
            slug = slugify(c["name"])
            if not slug:
                continue
            disp = display_name(c["name"])
            d = SITE / ck / "contractors" / slug; d.mkdir(parents=True, exist_ok=True)
            tset = sorted({t for p in plist for t in json.loads(p["trades"] or "[]")})
            tnames = ", ".join(TRADE_LABELS.get(t, t.title()) for t in tset) or "General"
            cphone = next((p.get("phone") for p in plist if p.get("phone")), "")
            phone_stat = f'<span class="stat"><b>{html.escape(fmt_phone(cphone))}</b>phone (public record)</span>' if cphone else ""
            cb = f"""<h1>{html.escape(disp)} — Recent Permit Activity in {label}</h1>
<p>{html.escape(disp)} pulled {len(plist)} commercial building permit{'s' if len(plist) != 1 else ''} in {label} recently,
totaling {fmt(ctotal)} in reported project value. Work spans: {html.escape(tnames)}.</p>
<div><span class="stat"><b>{len(plist)}</b>recent permits</span>
<span class="stat"><b>{fmt(ctotal)}</b>total reported value</span>{phone_stat}</div>
{permit_table(plist)}
<p><strong>Know every contractor's next jobsite — the morning after the permit is filed.</strong><br>
<a class="buy" href="{STRIPE_99}">Track all {label} permits — $99/mo</a></p>"""
            (d / "index.html").write_text(page(
                f"{disp} — Permits in {label} ({month}) | JustPermitted",
                f"{disp} pulled {len(plist)} recent commercial building permits in {label} worth {fmt(ctotal)}. See their projects and jobsite addresses.",
                cb, "../../../"), encoding="utf-8")
            sitemap_urls.append(f"{ck}/contractors/{slug}/")
            if len(contractor_cards) < 12:
                contractor_cards.append(f'<a class="card" href="contractors/{slug}/"><b>{html.escape(disp)}</b><span>{len(plist)} permits · {fmt(ctotal)}</span></a>')
        contractors_html = (f'<h2>Most active contractors</h2><div class="cards">{"".join(contractor_cards)}</div>'
                            if contractor_cards else "")

        (SITE / ck).mkdir(parents=True, exist_ok=True)
        cbody = f"""<h1>New Commercial Building Permits in {label} — {month}</h1>
<p>{len(cps)} recent permits worth {fmt(city_total)} in reported value, updated nightly. Browse by trade:</p>
<div class="cards">{''.join(trade_links)}</div>
{contractors_html}
<h2>Latest permits</h2>{permit_table(cps, 30)}
{PLANS_HTML}"""
        (SITE / ck / "index.html").write_text(page(
            f"New Commercial Building Permits in {label} ({month}) | JustPermitted",
            f"Live tracker of commercial building permits in {label}: values, addresses, contractors. Updated nightly.",
            cbody, "../"), encoding="utf-8")
        city_cards.append(f'<a class="card" href="{ck}/"><b>{label}</b><span>{len(cps)} recent permits · {fmt(city_total)} tracked</span></a>')
        sitemap_urls.append(f"{ck}/")
        print(f"[{ck}] {len(by_trade)} trade pages + {len([u for u in sitemap_urls if u.startswith(ck + '/contractors/')])} contractor pages + city index")

    SITE.mkdir(exist_ok=True)
    (SITE / "index.html").write_text(page(
        "JustPermitted — Your Next Job, Every Morning at 7am",
        "Daily commercial building permit alerts for contractors and suppliers. Know who pulled permits before your competitors do.",
        f"""<div class="hero">
<h1>Your next job,<br>every morning at 7am.</h1>
<p>We track every commercial building permit in your metro, tag it by trade, and send you the ones
worth calling about — the week they're filed, before your competitors hear about them.</p>
<a class="buy" href="#subscribe">See plans →</a>
</div>
<h2>Live coverage</h2>
<div class="cards">{''.join(city_cards)}</div>
<p><a href="plays/"><strong>The Commercial Permit Playbook →</strong></a> Six ways businesses turn permit data into contracts — with real permits from our live feeds.</p>
{PLANS_HTML}""",
        "./"), encoding="utf-8")

    (SITE / "plays").mkdir(parents=True, exist_ok=True)
    (SITE / "plays" / "index.html").write_text(page(
        "The Commercial Permit Playbook | JustPermitted",
        "Six plays businesses run with commercial permit data: signage permits, tenant improvements, re-roofs, demolitions and more — with real examples.",
        PLAYS_BODY, "../"), encoding="utf-8")
    sitemap_urls.append("plays/")

    today = datetime.now().strftime("%Y-%m-%d")
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"<url><loc>{BASE}/{u}</loc><lastmod>{today}</lastmod></url>" for u in sitemap_urls]
    sm.append("</urlset>")
    (SITE / "sitemap.xml").write_text("\n".join(sm), encoding="utf-8")
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n", encoding="utf-8")
    print("Root index + sitemap written. Total pages:", sum(1 for _ in SITE.rglob("index.html")))

if __name__ == "__main__":
    main()
