"""
scraper.py — SerpApi Google Maps scraper for RAST Studios
Free tier: 100 searches/month — no credit card required.
Sign up at https://serpapi.com to get your API key.
"""

import os
import csv
import time
import requests
from database import init_db, insert_lead, lead_exists

# ── Configuration ─────────────────────────────────────────────────────────────

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "afd21843dbf82fcdcfb418f628dcb656c88079082a54d643ea493a7afb5b74ea")

DEFAULT_LOCATION = "Bangalore, India"
CSV_OUTPUT_PATH  = "leads.csv"

# Each entry becomes one SerpApi search query.
# Format: "<keyword> in <location>" — keep keywords specific for better results.
CATEGORIES = {
    "Interior Designer": "interior designers",
    "Real Estate Agent": "real estate agents",
    "Builder":           "building contractors",
    "Architect":         "architects",
}

# How many result pages to fetch per category (20 results/page).
# Free tier = 100 searches total, so keep this at 1–2 per category.
PAGES_PER_CATEGORY = 2

# ── SerpApi helpers ───────────────────────────────────────────────────────────

def search_google_maps(query: str, location: str, start: int = 0) -> list[dict]:
    """
    Call SerpApi's Google Maps engine and return raw result list.

    Parameters
    ----------
    query    : search term, e.g. "interior designers"
    location : e.g. "Bangalore, India"
    start    : pagination offset (0, 20, 40 …)
    """
    url = "https://serpapi.com/search"
    params = {
        "engine":   "google_maps",
        "q":        f"{query} in {location}",
        "type":     "search",
        "start":    start,
        "api_key":  SERPAPI_KEY,
    }

    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    # SerpApi surfaces errors inside the JSON body
    if "error" in data:
        raise RuntimeError(f"SerpApi error: {data['error']}")

    return data.get("local_results", [])


def parse_result(raw: dict, category: str) -> dict:
    """
    Normalise a single SerpApi local_result into our lead schema.

    SerpApi already returns phone + website in the top-level result —
    no second round-trip needed (unlike Google Places API).
    """
    address  = raw.get("address", "")
    phone    = raw.get("phone", "")
    website  = raw.get("website", "")
    rating   = raw.get("rating", "")

    # Unique identifier — use place_id when present, else data_id
    place_id = raw.get("place_id") or raw.get("data_id") or raw.get("position", "")

    return {
        "name":     raw.get("title", ""),
        "category": category,
        "address":  address,
        "phone":    phone,
        "website":  website,
        "rating":   rating,
        "place_id": str(place_id),
    }


# ── Main scraper ──────────────────────────────────────────────────────────────

def scrape_leads(
    location: str = DEFAULT_LOCATION,
    csv_path: str = CSV_OUTPUT_PATH,
) -> list[dict]:
    """
    Scrape leads for all CATEGORIES at the given location via SerpApi.
    Saves results to CSV and SQLite. Returns list of lead dicts.
    """
    print(f"\n🌏 Location : {location}")
    print(f"📋 Categories: {', '.join(CATEGORIES.keys())}")
    print(f"📄 Pages/category: {PAGES_PER_CATEGORY} (~{PAGES_PER_CATEGORY * 20} results each)\n")

    init_db()

    all_leads:      list[dict] = []
    seen_place_ids: set[str]   = set()

    csv_file   = open(csv_path, "w", newline="", encoding="utf-8")
    csv_writer = csv.DictWriter(csv_file, fieldnames=[
        "name", "category", "address", "phone", "website", "rating", "place_id"
    ])
    csv_writer.writeheader()

    try:
        for category, keyword in CATEGORIES.items():
            print(f"🔍 {category} — searching '{keyword} in {location}' …")
            category_count = 0

            for page in range(PAGES_PER_CATEGORY):
                start = page * 20
                try:
                    results = search_google_maps(keyword, location, start=start)
                except Exception as e:
                    print(f"   [!] Search failed (page {page + 1}): {e}")
                    break

                if not results:
                    print(f"   No more results on page {page + 1}, stopping.")
                    break

                for raw in results:
                    lead = parse_result(raw, category)

                    # Skip blanks or duplicates
                    if not lead["name"]:
                        continue
                    uid = lead["place_id"] or lead["name"]
                    if uid in seen_place_ids:
                        continue
                    seen_place_ids.add(uid)

                    # Persist
                    csv_writer.writerow(lead)
                    if not lead_exists(lead["place_id"]):
                        insert_lead(lead)

                    all_leads.append(lead)
                    category_count += 1
                    print(f"   ✓ {lead['name']}")

                # Polite delay between pages
                if page < PAGES_PER_CATEGORY - 1:
                    time.sleep(1)

            print(f"   → {category_count} leads added\n")

    finally:
        csv_file.close()

    print(f"✅ Done! {len(all_leads)} unique leads saved → {csv_path} + leads.db")
    return all_leads


# ── Run directly ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    scrape_leads()
