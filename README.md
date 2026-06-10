# Permit Radar — Phase 1

**"Your next job, every morning at 7am."** Nightly pipeline that pulls commercial
building permits from city open-data APIs, AI-tags them by trade, scores them as
leads, and outputs (a) subscriber email digests and (b) a static pSEO site.

## Architecture

```
city open-data APIs (Socrata)        ANTHROPIC_API_KEY (optional)
        │                                     │
   ingest.py ──► permits.db (SQLite) ──► enrich.py (Claude tag/score,
        │                                     rule-based fallback)
        │                                     │
        ├──────────► digest.py ──► out/digests/*.html   (subscriber emails)
        └──────────► pseo.py   ──► site/                (static pSEO pages)
```

## Quickstart (5 minutes)

```bash
pip install requests
python3 ingest.py                 # live pull: Chicago + Austin, last 7 days
python3 enrich.py                 # uses Claude if ANTHROPIC_API_KEY set, else keyword fallback
python3 digest.py                 # builds digests from profiles.json
python3 pseo.py                   # builds static site into site/
```

Offline test (no network needed):
```bash
python3 ingest.py --fixture fixtures/chicago_sample.json --city chicago
python3 enrich.py && python3 digest.py && python3 pseo.py
```

## Adding a city (~10 minutes)

1. Find the city's permit dataset on its open-data portal (search "issued building permits site:data.CITY.gov").
2. Hit `https://DOMAIN/resource/DATASET.json?$limit=1` to see field names.
3. Add an entry to `config.json` mapping those fields. Done — every script picks it up.

Good candidates with Socrata permit data: NYC (ipu4-2q9a), Seattle, San Francisco,
Los Angeles, Mesa, Cambridge, Nashville, plus ~300 more cities on Socrata/ArcGIS.

## Production deployment

- **Cron:** GitHub Actions (`.github/workflows/nightly.yml` included) — runs the
  pipeline nightly, commits `docs/`, GitHub Pages/Vercel auto-deploys. Secrets
  needed: `ANTHROPIC_API_KEY`. Optional: `SODA_APP_TOKEN` (free; raises Socrata
  rate limits), `RESEND_API_KEY` (uncomment the send block in digest.py).
- **DB:** SQLite is fine to ~50 cities. Swap connection for Supabase Postgres when
  you add user accounts.
- **Phase 2 (monetization):** Stripe Payment Links per metro+trade tier (no code
  needed for v1 — paste links into the site), then webhook → profiles.json row.
  Phase 3: Next.js dashboard with auth + self-serve filter builder.

## Costs at current scope
~$0 hosting (GitHub Pages) + Claude API ~$2-6/month for 2 cities (Haiku batching).

## Compliance notes
- Municipal permit data is public record; check each portal's terms (nearly all are
  open licenses). Attribution footers are included on pSEO pages.
- Contractor names shown are from the public permit record.
- If you email digests commercially: CAN-SPAM (working unsubscribe, physical address).
