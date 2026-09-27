#!/usr/bin/env python3
"""
JobsPipe fetch script template for a personal Job Search Watcher.

Fill in the placeholders below (TITLES, MIN_SALARY_USD, CURATED_COMPANIES,
EXCLUDED_COMPANIES, and the location section) from the Step 1 interview
before using this. Once filled in, this script's full text belongs
directly inside each scheduled task's own prompt (see the spec's Step 4) --
a scheduled task starts a fresh, empty environment every time it fires, so
nothing here can be left to "the file from last time."

Reads the API key from ~/.secrets/jobspipe_api_key. Never prints the key.
"""
import json
import os
import sys
import urllib.request
import urllib.error

API_URL = "https://api.jobspipe.dev/v1/jobs/search"
KEY_PATH = os.path.expanduser("~/.secrets/jobspipe_api_key")

# --- FILL IN: the exact titles/role families to search for ---
TITLES = [
    "REPLACE ME",
]

# --- FILL IN: employers to weight higher in scoring (optional; leave [] if none) ---
CURATED_COMPANIES = [
]

# --- FILL IN: employers to exclude outright (lowercase, substring-matched
# against each posting's company field) ---
EXCLUDED_COMPANIES = [
]

# --- FILL IN: the hard salary floor in USD ---
MIN_SALARY_USD = 0

# Excludes postings JobsPipe scores at or above this on its 0-100
# ghost-likelihood scale (see the spec's operational notes). Unscored
# postings always pass regardless of this value.
MAX_GHOST_SCORE = 50

# --- FILL IN: location rule. JobsPipe's region_or is state/region-level
# only (e.g. "US-DC", "US-VA", "US-MD") with no radius or distance filter.
# If any accepted state/region needs to be narrowed further than "the
# whole state" (e.g. only certain named areas within it), add its city or
# area names, lowercased, to LOCATION_TEXT_HINTS below and it will be
# applied as a free, no-credit-cost text check against each posting's
# location field for results from that region. A region with no narrowing
# needed doesn't need any entries here -- see fetch_pattern_set below for
# how remote, onsite, and hybrid are each queried.
ONSITE_HYBRID_REGIONS = []  # e.g. ["US-DC", "US-VA"]
LOCATION_TEXT_HINTS = []    # e.g. ["silver spring", "bethesda", "rockville"]


def load_key():
    try:
        with open(KEY_PATH) as f:
            return f.read().strip()
    except FileNotFoundError:
        print("ERROR: JobsPipe API key not found at " + KEY_PATH, file=sys.stderr)
        sys.exit(1)


def query(api_key, body):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        API_URL, data=data, method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode('utf-8')[:500]}", file=sys.stderr)
        raise


def base_filters(posted_at_max_age_days, company_list=None):
    body = {
        "job_title_or": TITLES,
        "min_salary_usd": MIN_SALARY_USD,
        "posted_at_max_age_days": posted_at_max_age_days,
        "max_ghost_score": MAX_GHOST_SCORE,
        "limit": 100,
        "include_total_results": True,
    }
    if company_list:
        body["company_name_partial_match_or"] = company_list
    return body


def fetch_pattern_set(api_key, company_list, posted_at_max_age_days, label):
    results = {}

    # Remote (location-agnostic).
    b = base_filters(posted_at_max_age_days, company_list)
    b["remote"] = True
    r = query(api_key, b)
    for j in r.get("data", []):
        results[j["id"]] = j

    # Onsite and hybrid, narrowed by LOCATION_TEXT_HINTS if any are set.
    if ONSITE_HYBRID_REGIONS:
        for arrangement in ("onsite", "hybrid"):
            b = base_filters(posted_at_max_age_days, company_list)
            b["work_arrangement_or"] = [arrangement]
            b["region_or"] = ONSITE_HYBRID_REGIONS
            r = query(api_key, b)
            for j in r.get("data", []):
                if not LOCATION_TEXT_HINTS:
                    results[j["id"]] = j
                    continue
                loc = (j.get("location") or j.get("long_location") or "").lower()
                if any(hint in loc for hint in LOCATION_TEXT_HINTS):
                    results[j["id"]] = j

    print(f"  [{label}] remote+onsite+hybrid merged: {len(results)} postings", file=sys.stderr)
    return results


def main():
    posted_at_max_age_days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    out_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/jobspipe_results.json"

    api_key = load_key()
    merged = {}

    if CURATED_COMPANIES:
        print("Fetching curated-employer query set...", file=sys.stderr)
        merged.update(fetch_pattern_set(api_key, CURATED_COMPANIES, posted_at_max_age_days, "curated"))

    print("Fetching broad-search query set...", file=sys.stderr)
    broad = fetch_pattern_set(api_key, None, min(posted_at_max_age_days, 7), "broad")
    merged.update(broad)

    # Safety-net exclusion filter.
    filtered = {}
    for jid, j in merged.items():
        company = (j.get("company") or "").lower()
        if any(x in company for x in EXCLUDED_COMPANIES):
            continue
        filtered[jid] = j

    out = list(filtered.values())
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

    print(f"Wrote {len(out)} unique qualifying postings to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
