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

REGIONS = [
    ("Southern California", ["losangeles", "lacounty", "santamonica", "anaheim", "newportbeach", "riverside", "corona", "sandiego"]),
    ("Northern California", ["sanfrancisco", "sanjose", "sacramento"]),
    ("Nevada", ["lasvegas", "henderson"]),
    ("Arizona", ["tucson"]),
    ("Texas", ["austin"]),
    ("Pacific Northwest", ["seattle"]),
    ("Mountain West", ["denver"]),
    ("Midwest", ["chicago"]),
    ("South", ["nashville", "neworleans", "miami"]),
    ("Northeast", ["newyork", "philadelphia"]),
]

SALES_METROS = [
    ("greater-la", "Greater Los Angeles", "LA, Orange County & the Inland Empire", ["losangeles", "lacounty", "santamonica", "anaheim", "newportbeach", "riverside", "corona"]),
    ("san-diego", "San Diego County", "", ["sandiego"]),
    ("bay-area", "Bay Area", "San Francisco & San Jose", ["sanfrancisco", "sanjose"]),
    ("sacramento", "Sacramento / Central CA", "", ["sacramento"]),
    ("las-vegas", "Las Vegas Valley", "Las Vegas & Henderson", ["lasvegas", "henderson"]),
    ("tucson", "Tucson, AZ", "", ["tucson"]),
    ("austin", "Austin, TX", "", ["austin"]),
    ("seattle", "Seattle, WA", "", ["seattle"]),
    ("denver", "Denver, CO", "", ["denver"]),
    ("chicago", "Chicago, IL", "", ["chicago"]),
    ("nashville", "Nashville, TN", "", ["nashville"]),
    ("neworleans", "New Orleans, LA", "", ["neworleans"]),
    ("miami", "Miami-Dade, FL", "", ["miami"]),
    ("newyork", "New York City, NY", "", ["newyork"]),
    ("philadelphia", "Philadelphia, PA", "", ["philadelphia"]),
]

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
.navlink{color:#cbd5e1;text-decoration:none;font-size:14px;margin-right:18px}
.navlink:hover{color:#fff}
.faq{border:1px solid #e2e8f0;border-radius:12px;padding:18px 22px;margin:12px 0;background:#fff}
.faq b{font-size:16px}
.faq p{color:#475569;margin:8px 0 0}
footer a{color:#94a3b8}
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
<span><a class="navlink" href="{home}plays/">Playbook</a><a class="navlink" href="{home}faq/">FAQ</a><a class="cta" href="{home}subscribe/">Get Daily Alerts</a></span>
</div></div>
<main><div class="wrap">
{body}
</div></main>
<footer><div class="wrap">Data: public municipal permit records, updated nightly. Generated {datetime.now().strftime('%B %d, %Y')}.
Verify permit details with the issuing authority before acting. © JustPermitted · justpermitted.com<br>
<a href="{home}subscribe/">Subscribe</a> · <a href="{home}plays/">Playbook</a> · <a href="{home}equipment-rental/">Equipment Rental</a> · <a href="{home}faq/">FAQ</a> · <a href="{home}terms/">Terms</a> · <a href="{home}privacy/">Privacy</a> · <a href="mailto:support@justpermitted.com">support@justpermitted.com</a></div></footer>
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
    <a class="buy" href="{BASE}/subscribe/">Subscribe — $49/mo</a>
  </div>
  <div class="plan popular">
    <span class="badge">MOST POPULAR</span>
    <h3>All Trades</h3>
    <div class="price">$99<span class="per">/month</span></div>
    <ul><li>Daily email digest for your metro</li><li>Every trade category included</li><li>Project values, addresses &amp; lead scores</li><li>Cancel anytime</li></ul>
    <a class="buy" href="{BASE}/subscribe/">Subscribe — $99/mo</a>
  </div>
</div>
<p style="color:#64748b;font-size:13.5px">Pick your metro and trade on the next page — your daily digest starts the next morning.</p>"""

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

EQUIPMENT_BODY = f"""<div class="hero">
<h1>Heavy Equipment Rental Leads from New Commercial Permits</h1>
<p>Every commercial building permit is a rental order that hasn't been placed yet. The yard that knows about
the jobsite first gets the call for the iron — and the fencing, the power, and the sanitation that go with it.
JustPermitted reads every permit in your metro the night it's published and tells you what's about to be rented.</p>
</div>

<div class="cards">

<div class="card"><b>Demolition permits → Excavators &amp; hauling</b>
<span>Excavators, skid steers, breakers, dumpsters, water trucks for dust control. A demo permit means iron on
site within weeks — and a clean lot that needs more equipment right after.<br><br>
<em>From our feeds this week: demolition permits in Chicago, Los Angeles and Henderson.</em></span></div>

<div class="card"><b>New construction &amp; grading → The whole yard</b>
<span>Temporary fencing, office trailers, generators, light towers, portable sanitation, compaction equipment —
new builds rent for months, not days.<br><br>
<em>From our feeds: a $2.5M grading permit on Tropical Pkwy in Las Vegas and a $1.7M new drive-thru build in Los Angeles.</em></span></div>

<div class="card"><b>Tenant improvements → Lifts &amp; power</b>
<span>Scissor lifts, dumpsters, temporary power, air scrubbers. TI permits are short, dense rental windows —
and metros produce dozens of them every week.<br><br>
<em>From our feeds: a $350,000 first-tenant dental office build-out in Riverside, hotel floor finish-outs in Austin.</em></span></div>

<div class="card"><b>Commercial roofing → Reach &amp; hauling</b>
<span>Boom lifts, telehandlers, dump trailers, debris chutes, safety gear. Every re-roof permit is two to six
weeks of access equipment on rent.<br><br>
<em>From our feeds: 68 roofing permits worth $28M in Chicago alone, plus commercial tear-offs in Riverside and Tucson.</em></span></div>

<div class="card"><b>Concrete &amp; masonry → Mixers &amp; compaction</b>
<span>Mixers, saws, plate compactors, concrete pumps, forms. Pours are scheduled fast once the permit lands —
the yard that calls first is in the pour schedule.<br><br>
<em>From our feeds: 37 concrete &amp; masonry permits worth $10.2M in Chicago this period.</em></span></div>

<div class="card"><b>Signage &amp; electrical → Bucket trucks</b>
<span>Bucket trucks and boom lifts for sign installs and exterior electrical. Sign permits also mean a brand-new
tenant about to need everything else on this page.<br><br>
<em>From our feeds: 20 signage permits in one Riverside week — a Chevron, a CVS, two cafes.</em></span></div>

</div>

<h2>The math for a rental counter</h2>
<p>One scissor lift on a one-month TI rental covers the cost of this service many times over.
Your counter gets a list every morning of every jobsite in the metro that just got permission to start work —
with the project value, the address, and the contractor of record to call. Equipment rental businesses should
choose the <strong>All Trades</strong> plan: every permit type in your metro is a rental signal.</p>
{PLANS_HTML}"""

FAQ_BODY = f"""<div class="hero"><h1>Frequently asked questions</h1>
<p>If yours isn't here, email <a href="mailto:support@justpermitted.com">support@justpermitted.com</a> — a human reads every message.</p></div>

<div class="faq"><b>How fresh is the data?</b>
<p>Most of our cities publish daily — your digest typically shows permits issued one to two days ago.
A few cities (such as Las Vegas and Riverside) refresh their public records weekly, so for those metros
we're exactly as fast as the city itself. Either way, you see it the morning after it appears.</p></div>

<div class="faq"><b>Which metros do you cover?</b>
<p>Greater Los Angeles (LA, LA County, Santa Monica, Anaheim, Newport Beach, Riverside &amp; Corona),
the Bay Area (San Francisco &amp; San Jose), Sacramento, Las Vegas Valley (Las Vegas &amp; Henderson),
Tucson, Austin, Seattle, Denver, Chicago, Nashville, New Orleans, Miami-Dade, New York City and Philadelphia —
and growing. One subscription covers your whole metro, every city in it. Don't see yours?
Email us — if your city publishes permit records, we can usually add it within days.</p></div>

<div class="faq"><b>What's in each lead?</b>
<p>Project description, jobsite address, reported dollar value, issue date, the contractor of record,
and a lead score — plus the contractor's phone number in cities that publish it.</p></div>

<div class="faq"><b>Is this a pay-per-lead service?</b>
<p>No. One flat subscription gets you every commercial permit in your metro. We never sell leads individually,
so "your" lead is never resold to a list of competitors.</p></div>

<div class="faq"><b>How do I receive my leads?</b>
<p>One email every morning around 7am. No dashboard, no login, nothing to remember to check.</p></div>

<div class="faq"><b>Can I try it before paying?</b>
<p>Yes — email <a href="mailto:support@justpermitted.com">support@justpermitted.com</a> with your metro and trade,
and we'll send you tomorrow morning's digest free. No card required.</p></div>

<div class="faq"><b>How do I set my metro and trade?</b>
<p>You'll pick your metro, trade, and business type on our subscribe page — they travel with your checkout
automatically. Your daily digest starts the next morning. Need to change anything later? Email support anytime.</p></div>

<div class="faq"><b>Can I cancel?</b>
<p>Anytime, instantly, from the link in any Stripe receipt — or just email us. No contracts, no phone calls, no hard feelings.</p></div>

<div class="faq"><b>Where does the data come from?</b>
<p>Official city and county public records, collected nightly by our automated pipeline.
Always verify permit details with the issuing authority before bidding or acting.</p></div>
{PLANS_HTML}"""

TERMS_BODY = """<div class="hero"><h1>Terms of Service</h1></div>
<p><strong>The service.</strong> JustPermitted provides daily email digests and web pages summarizing
commercial building permit information drawn from public municipal and county records.</p>
<p><strong>Subscriptions.</strong> Plans are billed monthly through Stripe. You can cancel at any time via the
link in any Stripe receipt or by emailing <a href="mailto:support@justpermitted.com">support@justpermitted.com</a>;
cancellation stops future charges. </p>
<p><strong>Data accuracy.</strong> Permit information is republished from public records as-is. Cities sometimes
publish errors, delays, or incomplete records, and our automated categorization may occasionally mislabel a permit.
The service is provided without warranty of accuracy, completeness, or fitness for a particular purpose.
Always verify permit details with the issuing authority before bidding, contacting a party, or making business decisions.</p>
<p><strong>Acceptable use.</strong> Digests are licensed for use within your business. Reselling or republishing
the service's output as a competing data product is not permitted.</p>
<p><strong>Liability.</strong> To the maximum extent permitted by law, JustPermitted's total liability for any claim
related to the service is limited to the amount you paid in the month the claim arose.</p>
<p><strong>Changes.</strong> Coverage (cities, fields, formats) may change as public data sources change.
We may update these terms; continued use after an update constitutes acceptance.</p>
<p>Questions: <a href="mailto:support@justpermitted.com">support@justpermitted.com</a></p>"""

PRIVACY_BODY = """<div class="hero"><h1>Privacy Policy</h1></div>
<p><strong>What we collect.</strong> When you subscribe, we receive your email address and plan details from Stripe,
plus the metro/trade preferences you send us. That's what we need to deliver your digest — nothing more.</p>
<p><strong>Payments.</strong> All payments are processed by Stripe. Your card number never touches our systems.</p>
<p><strong>Analytics.</strong> We use GoatCounter, a privacy-respecting analytics tool that counts visits without
cookies, fingerprinting, or tracking you across the web.</p>
<p><strong>Contractor information.</strong> Names and phone numbers shown on this site come directly from public
municipal permit and licensing records. If information about your business appears here and you'd like it corrected
or removed, email us and we'll handle it promptly.</p>
<p><strong>What we never do.</strong> We don't sell your information, share your email with anyone,
or send you anything other than the digests you subscribed to.</p>
<p>Questions or requests: <a href="mailto:support@justpermitted.com">support@justpermitted.com</a></p>"""

def main():
    conn = sqlite3.connect(ROOT / CFG["db_path"]); conn.row_factory = sqlite3.Row
    permits = [dict(r) for r in conn.execute(
        "SELECT * FROM permits WHERE enriched=1 ORDER BY issued_date DESC, lead_score DESC")]
    for p in permits:  # drop junk valuations from city data feeds (e.g. $63B typos)
        if p["value"] and p["value"] > 500_000_000:
            p["value"] = None
    month = datetime.now().strftime("%B %Y")
    city_cards = {}
    city_stats = {}
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
<p><strong>Want tomorrow's list at 7am?</strong><br><a class="buy" href="{BASE}/subscribe/">Get {tl} alerts for {label} — $49/mo</a></p>"""
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
<a class="buy" href="{BASE}/subscribe/">Track all {label} permits — $99/mo</a></p>"""
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
        city_cards[ck] = f'<a class="card" href="{ck}/"><b>{label}</b><span>{len(cps)} recent permits · {fmt(city_total)} tracked</span></a>'
        city_stats[ck] = (label, len(cps), city_total)
        sitemap_urls.append(f"{ck}/")
        print(f"[{ck}] {len(by_trade)} trade pages + {len([u for u in sitemap_urls if u.startswith(ck + '/contractors/')])} contractor pages + city index")

    region_html = ""
    used = set()
    for rname, rcities in REGIONS:
        cards = [city_cards[ck] for ck in rcities if ck in city_cards]
        used.update(ck for ck in rcities if ck in city_cards)
        if not cards:
            continue
        region_html += f'<h3 style="margin:26px 0 0;color:#334155">{rname}</h3><div class="cards">{"".join(cards)}</div>'
    leftover = [v for k, v in city_cards.items() if k not in used]
    if leftover:
        region_html += f'<h3 style="margin:26px 0 0;color:#334155">More metros</h3><div class="cards">{"".join(leftover)}</div>'

    SITE.mkdir(exist_ok=True)
    (SITE / "index.html").write_text(page(
        "JustPermitted — Your Next Job, Every Morning at 7am",
        "Daily commercial building permit alerts for contractors and suppliers. Know who pulled permits before your competitors do.",
        f"""<div class="hero">
<h1>Your next job,<br>every morning at 7am.</h1>
<p>We track every commercial building permit in your metro, tag it by trade, and send you the ones
worth calling about — the week they're filed, before your competitors hear about them.</p>
<a class="buy" href="subscribe/">See plans →</a>
</div>
<h2>Live coverage</h2>
<p style="color:#64748b">One subscription covers your whole metro — Greater Los Angeles includes LA, LA County,
Santa Monica, Anaheim, Newport Beach, Riverside and Corona; Las Vegas Valley includes Henderson; the Bay Area
includes San Francisco and San Jose.</p>
{region_html}
<p><a href="plays/"><strong>The Commercial Permit Playbook →</strong></a> Six ways businesses turn permit data into contracts — with real permits from our live feeds.
<br><a href="equipment-rental/"><strong>For Equipment Rental companies →</strong></a> Every permit type is a rental signal.</p>
{PLANS_HTML}""",
        "./"), encoding="utf-8")

    # /subscribe picker page — sells SALES_METROS (true work markets), not individual cities
    metro_opts = '<option value="" selected>Choose your metro…</option>'
    for mkey, mlabel, msub, mcities in SALES_METROS:
        have = [ck for ck in mcities if ck in city_stats]
        if not have:
            continue  # metro hidden until its feed exists (e.g. San Diego)
        n = sum(city_stats[ck][1] for ck in have)
        tot = sum(city_stats[ck][2] for ck in have)
        sub = f" — {msub}" if msub else ""
        stats_txt = f"{n} recent permits · {fmt(tot)} tracked{sub}"
        metro_opts += (f'<option value="{mkey}" data-stats="{html.escape(stats_txt)}">'
                       f'{html.escape(mlabel)}</option>')
    trade_opts = '<option value="all" selected>All trades</option>' + "".join(
        f'<option value="{k}">{html.escape(v)}</option>' for k, v in TRADE_LABELS.items() if k != "other")
    sel_style = "width:100%;padding:11px;border:1px solid #cbd5e1;border-radius:9px;font-size:15px;margin:6px 0 16px;background:#fff"
    sub_body = f"""<div class="hero"><h1>Start your daily permit alerts</h1>
<p>Three picks, one checkout — your first digest arrives tomorrow morning at 7am.</p></div>
<div class="faq" style="max-width:560px">
<b>Your metro</b>
<select id="metro" style="{sel_style}">{metro_opts}</select>
<div id="stats" style="color:#16a34a;font-weight:600;font-size:14px;margin:-8px 0 14px"></div>
<b>Your trade</b>
<select id="trade" style="{sel_style}">{trade_opts}</select>
<b>Business type</b>
<select id="biz" style="{sel_style}">
<option value="contractor" selected>Contractor / Subcontractor</option>
<option value="rental">Equipment Rental</option>
<option value="supplier">Supplier / Distributor</option>
<option value="service">Service Provider</option>
<option value="other">Other</option>
</select>
</div>
<div class="plans" style="max-width:760px">
  <div class="plan">
    <h3>Single Trade</h3>
    <div class="price">$49<span class="per">/month</span></div>
    <ul><li>Your metro, your trade only</li><li>Values, addresses &amp; lead scores</li><li>Cancel anytime</li></ul>
    <a class="buy" id="buy49" href="#" style="opacity:.5">Continue to checkout — $49/mo</a>
  </div>
  <div class="plan popular">
    <span class="badge">MOST POPULAR</span>
    <h3>All Trades</h3>
    <div class="price">$99<span class="per">/month</span></div>
    <ul><li>Your metro, every trade category</li><li>Values, addresses &amp; lead scores</li><li>Cancel anytime</li></ul>
    <a class="buy" id="buy99" href="#" style="opacity:.5">Continue to checkout — $99/mo</a>
  </div>
</div>
<p id="hint" style="color:#64748b;font-size:13.5px">Choose your metro above to continue.</p>
<script>
(function() {{
  var m=document.getElementById('metro'),t=document.getElementById('trade'),b=document.getElementById('biz'),
      s=document.getElementById('stats'),h=document.getElementById('hint'),
      a49=document.getElementById('buy49'),a99=document.getElementById('buy99'),
      U49='{STRIPE_49}',U99='{STRIPE_99}';
  function upd() {{
    var ck=m.value;
    if(!ck) {{ s.textContent=''; a49.href=a99.href='#'; a49.style.opacity=a99.style.opacity=.5;
      h.textContent='Choose your metro above to continue.'; return; }}
    var o=m.options[m.selectedIndex];
    s.textContent='\\u2713 '+o.text+' \\u2014 '+o.getAttribute('data-stats');
    var ref=[ck,t.value,b.value].join('--').replace(/[^a-zA-Z0-9_-]/g,'');
    a49.href=U49+'?client_reference_id='+ref;
    a99.href=U99+'?client_reference_id='+ref;
    a49.style.opacity=a99.style.opacity=1;
    h.textContent='Your picks travel with your checkout automatically.';
  }}
  m.onchange=t.onchange=b.onchange=upd; upd();
}})();
</script>"""
    (SITE / "subscribe").mkdir(parents=True, exist_ok=True)
    (SITE / "subscribe" / "index.html").write_text(page(
        "Subscribe | JustPermitted",
        "Pick your metro and trade — daily commercial permit alerts in your inbox tomorrow at 7am.",
        sub_body, "../"), encoding="utf-8")
    sitemap_urls.append("subscribe/")

    (SITE / "plays").mkdir(parents=True, exist_ok=True)
    (SITE / "plays" / "index.html").write_text(page(
        "The Commercial Permit Playbook | JustPermitted",
        "Six plays businesses run with commercial permit data: signage permits, tenant improvements, re-roofs, demolitions and more — with real examples.",
        PLAYS_BODY, "../"), encoding="utf-8")
    sitemap_urls.append("plays/")

    for slug, title, desc, body in (
        ("faq", "FAQ | JustPermitted",
         "How fresh is the data, which cities are covered, pricing, cancellation — answers about JustPermitted's daily commercial permit alerts.",
         FAQ_BODY),
        ("equipment-rental", "Heavy Equipment Rental Leads from Commercial Permits | JustPermitted",
         "Daily permit alerts for equipment rental companies: demolition, grading, TI, roofing and concrete permits mean excavators, lifts, fencing and power about to be rented.",
         EQUIPMENT_BODY),
        ("terms", "Terms of Service | JustPermitted", "JustPermitted terms of service.", TERMS_BODY),
        ("privacy", "Privacy Policy | JustPermitted", "JustPermitted privacy policy.", PRIVACY_BODY),
    ):
        (SITE / slug).mkdir(parents=True, exist_ok=True)
        (SITE / slug / "index.html").write_text(page(title, desc, body, "../"), encoding="utf-8")
        sitemap_urls.append(f"{slug}/")

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
