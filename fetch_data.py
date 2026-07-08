#!/usr/bin/env python3
"""Pulls everything we need from Meta Marketing API for the Oppolia dashboard."""
import json
import urllib.parse
import urllib.request
from pathlib import Path

API_VERSION = "v23.0"
BASE = f"https://graph.facebook.com/{API_VERSION}"

INSIGHT_FIELDS = (
    "spend,impressions,reach,clicks,ctr,cpc,cpm,frequency,actions,"
    "cost_per_action_type,inline_link_clicks"
)


def load_env():
    env = {}
    for line in Path(".env").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def fetch(path, params, token):
    params = {**params, "access_token": token}
    url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(urllib.request.Request(url), timeout=60) as resp:
        return json.loads(resp.read().decode())


def paginate(path, params, token, max_pages=20):
    out = []
    page = fetch(path, params, token)
    out.extend(page.get("data", []))
    pages = 1
    while pages < max_pages:
        nxt = page.get("paging", {}).get("next")
        if not nxt:
            break
        with urllib.request.urlopen(urllib.request.Request(nxt), timeout=60) as resp:
            page = json.loads(resp.read().decode())
        out.extend(page.get("data", []))
        pages += 1
    return out


def main():
    env = load_env()
    token = env["META_ACCESS_TOKEN"]
    act = env["META_OPPOLIA_AD_ACCOUNT_ID"]

    data = {}

    print("→ account info")
    data["account"] = fetch(
        act,
        {"fields": "name,account_status,currency,timezone_name,amount_spent,business_name"},
        token,
    )

    print("→ lifetime insights")
    data["lifetime"] = fetch(
        f"{act}/insights",
        {"fields": INSIGHT_FIELDS, "date_preset": "maximum"},
        token,
    )

    print("→ daily insights (for period-over-period comparisons)")
    data["daily"] = paginate(
        f"{act}/insights",
        {
            "fields": INSIGHT_FIELDS,
            "date_preset": "maximum",
            "time_increment": 1,
            "limit": 200,
        },
        token,
    )

    print("→ campaigns")
    data["campaigns"] = paginate(
        f"{act}/campaigns",
        {"fields": "id,name,status,effective_status,objective,daily_budget,lifetime_budget,start_time", "limit": 100},
        token,
    )

    print("→ campaign insights")
    data["campaign_insights"] = paginate(
        f"{act}/insights",
        {"fields": f"campaign_id,campaign_name,{INSIGHT_FIELDS}", "level": "campaign", "date_preset": "maximum", "limit": 100},
        token,
    )

    print("→ ads")
    data["ads"] = paginate(
        f"{act}/ads",
        {"fields": "id,name,status,effective_status,campaign_id,adset_id,created_time", "limit": 100},
        token,
    )

    print("→ ad insights (creative-level table)")
    data["ad_insights"] = paginate(
        f"{act}/insights",
        {"fields": f"ad_id,ad_name,adset_id,campaign_id,{INSIGHT_FIELDS}", "level": "ad", "date_preset": "maximum", "limit": 100},
        token,
    )

    print("→ ad insights × platform (FB vs IG)")
    data["ad_by_platform"] = paginate(
        f"{act}/insights",
        {
            "fields": "ad_id,ad_name,spend,impressions,reach,clicks,ctr,cpc,actions",
            "breakdowns": "publisher_platform",
            "level": "ad",
            "date_preset": "maximum",
            "limit": 500,
        },
        token,
    )

    breakdowns = {
        "by_age_gender": "age,gender",
        "by_region": "region",
        "by_platform": "publisher_platform",
    }
    for key, brk in breakdowns.items():
        print(f"→ breakdown {key}")
        try:
            data[key] = paginate(
                f"{act}/insights",
                {"fields": INSIGHT_FIELDS, "breakdowns": brk, "date_preset": "maximum", "limit": 500},
                token,
            )
        except Exception as e:
            print(f"  ! {key} failed: {e}")
            data[key] = []

    # Same breakdowns again, but day-by-day, so the dashboards' date-range
    # picker can recompute everything client-side for an arbitrary window
    # instead of only showing the lifetime totals above.
    print("→ campaign insights (daily)")
    data["campaign_insights_daily"] = paginate(
        f"{act}/insights",
        {
            "fields": f"campaign_id,campaign_name,{INSIGHT_FIELDS}",
            "level": "campaign",
            "date_preset": "maximum",
            "time_increment": 1,
            "limit": 500,
        },
        token,
        max_pages=60,
    )

    print("→ ad insights (daily)")
    data["ad_insights_daily"] = paginate(
        f"{act}/insights",
        {
            "fields": f"ad_id,ad_name,adset_id,campaign_id,{INSIGHT_FIELDS}",
            "level": "ad",
            "date_preset": "maximum",
            "time_increment": 1,
            "limit": 500,
        },
        token,
        max_pages=60,
    )

    daily_breakdowns = {
        "by_age_gender_daily": "age,gender",
        "by_region_daily": "region",
        "by_platform_daily": "publisher_platform",
    }
    for key, brk in daily_breakdowns.items():
        print(f"→ breakdown {key}")
        try:
            data[key] = paginate(
                f"{act}/insights",
                {
                    "fields": INSIGHT_FIELDS,
                    "breakdowns": brk,
                    "date_preset": "maximum",
                    "time_increment": 1,
                    "limit": 500,
                },
                token,
                max_pages=60,
            )
        except Exception as e:
            print(f"  ! {key} failed: {e}")
            data[key] = []

    out = Path("data.json")
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"\n✓ wrote {out} ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
