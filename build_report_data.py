#!/usr/bin/env python3
"""Reads data.json and computes the KPIs/tables the dashboard reports.

This does NOT touch cliente.html / interno.html — those carry narrative and
qualitative lead-quality judgment that comes from manual review of the leads
sheet (see README). This script only regenerates the numbers that ARE fully
derivable from the Meta Ads API, as a source of truth for the next manual
update of the HTML.
"""
import json
from pathlib import Path

LEAD_ACTION = "lead"


def num(x):
    return float(x) if x is not None else 0.0


def action_value(actions, action_type):
    for a in actions or []:
        if a.get("action_type") == action_type:
            return num(a["value"])
    return 0.0


def main():
    data = json.loads(Path("data.json").read_text())

    account = data["account"]
    life = data["lifetime"]["data"][0] if data["lifetime"]["data"] else {}
    spend = num(life.get("spend"))
    leads = action_value(life.get("actions"), LEAD_ACTION)
    cpl = spend / leads if leads else 0.0

    lines = []
    lines.append(f"# Oppolia · Resumen Meta Ads (auto-generado)\n")
    lines.append(f"_Cuenta: {account['name']} ({account['id']}) · Moneda {account['currency']}_\n")
    lines.append("## KPIs de vida de campaña\n")
    lines.append(f"- **Inversión total:** ${spend:,.0f}")
    lines.append(f"- **Leads:** {leads:.0f}")
    lines.append(f"- **Costo por lead:** ${cpl:,.0f}")
    lines.append(f"- **CTR:** {num(life.get('ctr')):.2f}%")
    lines.append(f"- **CPC:** ${num(life.get('cpc')):.2f}")
    lines.append(f"- **CPM:** ${num(life.get('cpm')):.2f}")
    lines.append("")

    lines.append("## Por campaña\n")
    lines.append("| Campaña | Gasto | Leads | CPL | CTR |")
    lines.append("|---|---:|---:|---:|---:|")
    campaign_insights = data["campaign_insights"]
    if isinstance(campaign_insights, dict):
        campaign_insights = campaign_insights.get("data", [])
    for c in campaign_insights:
        c_spend = num(c.get("spend"))
        c_leads = action_value(c.get("actions"), LEAD_ACTION)
        c_cpl = c_spend / c_leads if c_leads else 0
        lines.append(f"| {c.get('campaign_name','—')} | ${c_spend:,.0f} | {c_leads:.0f} | ${c_cpl:,.0f} | {num(c.get('ctr')):.2f}% |")
    lines.append("")

    lines.append("## Por anuncio (creativo)\n")
    lines.append("| Anuncio | Gasto | Impr. | CTR | Leads | CPL |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    ad_insights = data["ad_insights"]
    ad_insights = ad_insights.get("data", ad_insights) if isinstance(ad_insights, dict) else ad_insights
    for a in sorted(ad_insights, key=lambda r: -num(r.get("spend"))):
        a_spend = num(a.get("spend"))
        a_leads = action_value(a.get("actions"), LEAD_ACTION)
        a_cpl = a_spend / a_leads if a_leads else 0
        lines.append(f"| {a.get('ad_name','—')} | ${a_spend:,.0f} | {int(num(a.get('impressions'))):,} | {num(a.get('ctr')):.2f}% | {a_leads:.0f} | {'$' + format(a_cpl, ',.0f') if a_leads else '—'} |")
    lines.append("")

    lines.append("## Edad y género\n")
    lines.append("| Edad | Género | Gasto | Leads |")
    lines.append("|---|---|---:|---:|")
    by_ag = data["by_age_gender"]
    by_ag = by_ag.get("data", by_ag) if isinstance(by_ag, dict) else by_ag
    for r in by_ag:
        r_leads = action_value(r.get("actions"), LEAD_ACTION)
        lines.append(f"| {r.get('age','—')} | {r.get('gender','—')} | ${num(r.get('spend')):,.0f} | {r_leads:.0f} |")
    lines.append("")

    lines.append("## Región\n")
    lines.append("| Región | Gasto | Leads |")
    lines.append("|---|---:|---:|")
    by_region = data["by_region"]
    by_region = by_region.get("data", by_region) if isinstance(by_region, dict) else by_region
    for r in sorted(by_region, key=lambda r: -num(r.get("spend"))):
        r_leads = action_value(r.get("actions"), LEAD_ACTION)
        lines.append(f"| {r.get('region','—')} | ${num(r.get('spend')):,.0f} | {r_leads:.0f} |")
    lines.append("")

    lines.append("## Facebook vs Instagram\n")
    lines.append("| Plataforma | Gasto | Leads |")
    lines.append("|---|---:|---:|")
    by_platform = data["by_platform"]
    by_platform = by_platform.get("data", by_platform) if isinstance(by_platform, dict) else by_platform
    for r in by_platform:
        r_leads = action_value(r.get("actions"), LEAD_ACTION)
        lines.append(f"| {r.get('publisher_platform','—')} | ${num(r.get('spend')):,.0f} | {r_leads:.0f} |")

    out = Path("data") / "meta-ads-resumen.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print(f"✓ wrote {out}")


if __name__ == "__main__":
    main()
