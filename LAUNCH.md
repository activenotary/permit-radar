# Permit Radar — Launch Checklist

The pipeline is built and tested. Going live is ~30 minutes of account work that
only you can do. In order:

## 1. Local setup (5 min)
- [ ] Copy the `Permit Radar Code` folder to a LOCAL path, e.g. `C:\dev\permit-radar`
      (NOT OneDrive — SQLite + cloud sync corrupts databases)
- [ ] Install Python 3.11+ and `pip install requests`
- [ ] Sanity run: `python ingest.py` (live pull) then `enrich.py`, `digest.py`, `pseo.py`

## 2. GitHub (10 min) — this is the autopilot
- [ ] Create a private repo `permit-radar`, push the folder
- [ ] Repo Settings → Secrets and variables → Actions → add:
      - `ANTHROPIC_API_KEY` (console.anthropic.com — enables real AI tagging)
      - `SODA_APP_TOKEN` (free at evergreen.data.socrata.com — higher rate limits; optional day 1)
- [ ] Actions tab → enable workflows → run `nightly-pipeline` manually once to verify
- [ ] Settings → Pages → deploy from branch, folder `/docs` → your pSEO site is live

## 3. Domain (5 min)
- [ ] Buy the domain (e.g. permitradar.io or similar — check availability)
- [ ] Point it at GitHub Pages (or import the repo into Vercel for nicer DNS handling)
- [ ] Set `base = "https://yourdomain.com"` in pseo.py and re-run

## 4. Stripe (10 min) — money pipe, zero code
- [ ] Stripe account under the LLC (or personal now, migrate at LLC formation)
- [ ] Create 2 Payment Links: "$49/mo — 1 metro, 1 trade" and "$99/mo — 1 metro, all trades"
- [ ] Paste the links into the site index (pseo.py, the #subscribe section)
- [ ] When a payment lands: add a row to profiles.json with the buyer's metro/trades.
      (Manual for the first 10 customers is FINE. Automate with webhooks at ~20.)

## 5. Email alerts (when first subscriber lands)
- [ ] resend.com account, verify your domain, add `RESEND_API_KEY` secret
- [ ] Uncomment the Resend block in digest.py

## First-customers playbook (no SEO wait required)
The pSEO traffic takes months. Don't wait for it:
1. Post the live trade-page link in 2-3 contractor Facebook groups / subreddits per metro
   ("free list of every commercial permit pulled in Chicago this week")
2. DM 20 roofing/HVAC companies per metro on the free tier
3. R. Dugan Construction (Wendy/Brandon) — your warm contact IS the target customer
   for a Riverside/SoCal metro. Add their county, give them 3 months free, get feedback
   + a testimonial.

## Weekly 3 hours
30 min: check Actions runs + parse QA · 30 min: Stripe/churn · 2 hrs: add 1 city
or post free content in contractor communities.
