#!/usr/bin/env python3
"""Permit Radar — subscriber digests. Builds an HTML email digest per profile
in profiles.json (city + trades + min project value). Output: out/digests/.
Sends via Resend when RESEND_API_KEY is set.
"""
import html, json, sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config.json").read_text())
PROFILES = json.loads((ROOT / "profiles.json").read_text())
OUT = ROOT / "out" / "digests"; OUT.mkdir(parents=True, exist_ok=True)

def fmt_value(v):
    return f"${v:,.0f}" if v else "n/a"

def matches(p, prof):
    if p["city"] != prof["city"]: return False
    if prof.get("min_value") and (p["value"] or 0) < prof["min_value"] and p["value"] is not None:
        pass  # keep null-value permits; drop only confirmed-low
    if prof.get("min_value") and p["value"] is not None and p["value"] < prof["min_value"]:
        return False
    trades = set(json.loads(p["trades"] or "[]"))
    return bool(trades & set(prof["trades"])) if prof.get("trades") else True

def build(prof, permits):
    label = CFG["cities"][prof["city"]]["label"]
    rows = ""
    for p in permits[:25]:
        trades = ", ".join(json.loads(p["trades"] or "[]"))
        rows += f"""
        <tr>
          <td style="padding:10px;border-bottom:1px solid #e5e7eb;text-align:center;">
            <span style="background:{'#16a34a' if p['lead_score']>=60 else '#d97706'};color:#fff;border-radius:12px;padding:3px 10px;font-weight:bold;">{p['lead_score']}</span></td>
          <td style="padding:10px;border-bottom:1px solid #e5e7eb;">
            <strong>{html.escape(p['summary'] or p['permit_type'] or '')}</strong><br>
            <span style="color:#6b7280;font-size:13px;">{html.escape(p['address'] or '')} · issued {p['issued_date']}</span><br>
            <span style="font-size:12px;color:#374151;">Trades: {html.escape(trades)}{(' · Contractor of record: ' + html.escape(p['contractor'])) if p['contractor'] else ''}</span></td>
          <td style="padding:10px;border-bottom:1px solid #e5e7eb;white-space:nowrap;font-weight:600;">{fmt_value(p['value'])}</td>
        </tr>"""
    if not rows:
        rows = '<tr><td colspan="3" style="padding:20px;color:#6b7280;">No new matching permits in this period.</td></tr>'
    return f"""<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;background:#f9fafb;margin:0;padding:24px;">
  <div style="max-width:720px;margin:auto;background:#fff;border-radius:8px;padding:24px;border:1px solid #e5e7eb;">
    <h1 style="margin:0 0 4px;font-size:20px;">JustPermitted — {html.escape(label)}</h1>
    <p style="color:#6b7280;margin:0 0 16px;">{datetime.now().strftime('%B %d, %Y')} · {len(permits)} new matching permits for {html.escape(prof['name'])}</p>
    <table style="border-collapse:collapse;width:100%;">
      <tr style="text-align:left;color:#6b7280;font-size:12px;text-transform:uppercase;">
        <th style="padding:10px;">Score</th><th style="padding:10px;">Project</th><th style="padding:10px;">Value</th></tr>
      {rows}
    </table>
    <p style="color:#9ca3af;font-size:11px;margin-top:16px;">Source: public municipal permit records. Verify details before bidding.
    JustPermitted · justpermitted.com</p>
  </div></body></html>"""

def send_email(prof, html_body, n_hits):
    """Send the digest via Resend. Skips demo profiles and runs without a key."""
    import os
    key = os.environ.get("RESEND_API_KEY")
    if not key or prof["email"].endswith("@example.com"):
        return False
    import requests
    label = CFG["cities"][prof["city"]]["label"]
    r = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {key}"},
        json={"from": "JustPermitted <alerts@justpermitted.com>",
              "to": prof["email"],
              "subject": f"{n_hits} new {label} permits in your trades — JustPermitted",
              "html": html_body},
        timeout=30)
    if r.status_code >= 300:
        print(f"[{prof['name']}] SEND FAILED: {r.status_code} {r.text[:200]}")
        return False
    return True

def main():
    conn = sqlite3.connect(ROOT / CFG["db_path"]); conn.row_factory = sqlite3.Row
    permits = [dict(r) for r in conn.execute(
        "SELECT * FROM permits WHERE enriched=1 ORDER BY lead_score DESC, issued_date DESC")]
    for prof in PROFILES:
        hits = [p for p in permits if matches(p, prof)]
        body = build(prof, hits)
        path = OUT / f"{prof['name'].lower().replace(' ', '_')}.html"
        path.write_text(body, encoding="utf-8")
        sent = send_email(prof, body, len(hits))
        print(f"[{prof['name']}] {len(hits)} matches -> {path.name}{' · EMAILED' if sent else ''}")

if __name__ == "__main__":
    main()
