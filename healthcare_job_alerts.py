"""
Healthcare Job Alerts Bot
=========================
Fetches healthcare job listings using the Adzuna API (free tier, legal
aggregator that pulls from Indeed, Naukri-type sources, and many more
boards) and formats them into a ready-to-paste WhatsApp message.

WHY ADZUNA AND NOT DIRECT SCRAPING OF NAUKRI/INDEED/GLASSDOOR:
Those sites explicitly forbid automated scraping in their Terms of
Service and use strong anti-bot protection. Scraping them risks IP
bans and account suspension, and breaks often since their page
structure changes. Adzuna is a legitimate aggregator with a free,
documented API that already includes listings sourced from many of
those boards.

SETUP (free, ~2 minutes):
1. Go to https://developer.adzuna.com/ and create a free account.
2. Copy your APP_ID and APP_KEY from the dashboard.
3. Set them as environment variables (recommended) OR paste them into
   config.json (see config_example.json in this folder).

    export ADZUNA_APP_ID="your_app_id"
    export ADZUNA_APP_KEY="your_app_key"

4. Run:
    pip install requests --break-system-packages
    python healthcare_job_alerts.py

Output:
- Prints a WhatsApp-ready formatted list to the terminal
- Saves the same text to jobs_output.txt so you can copy-paste
  straight into your WhatsApp channel
"""

import os
import json
import requests
from datetime import datetime

# ---------------------------------------------------------------------
# CONFIG — edit these to match what you post about
# ---------------------------------------------------------------------

APP_ID = os.environ.get("ADZUNA_APP_ID", "PASTE_YOUR_APP_ID_HERE")
APP_KEY = os.environ.get("ADZUNA_APP_KEY", "PASTE_YOUR_APP_KEY_HERE")

COUNTRY = "in"  # India

# Cities/locations to search. Leave a blank string "" to search all-India.
LOCATIONS = ["Delhi", "Mumbai", "Bangalore", "Lucknow", "Gorakhpur"]

# Keywords describing the healthcare roles you post about.
# Add/remove freely — these are OR'd together in the search query per city.
KEYWORDS = [
    "staff nurse",
    "pharmacist",
    "lab technician",
    "medical officer",
    "physiotherapist",
    "hospital receptionist",
    "radiographer",
]

RESULTS_PER_QUERY = 10   # how many jobs to fetch per keyword/city combo
MAX_JOBS_IN_OUTPUT = 25  # cap on final formatted list, to keep the post readable

OUTPUT_FILE = "jobs_output.txt"

# ---------------------------------------------------------------------
# CORE LOGIC
# ---------------------------------------------------------------------

def fetch_jobs(keyword, location):
    """Query Adzuna for a single keyword + location combo."""
    url = f"https://api.adzuna.com/v1/api/jobs/{COUNTRY}/search/1"
    params = {
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "what": keyword,
        "where": location,
        "results_per_page": RESULTS_PER_QUERY,
        "content-type": "application/json",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except requests.exceptions.RequestException as e:
        print(f"  [warn] failed for '{keyword}' in '{location}': {e}")
        return []


def dedupe(jobs):
    """Remove duplicate postings by (title, company) pair."""
    seen = set()
    unique = []
    for job in jobs:
        title = job.get("title", "").strip().lower()
        company = (job.get("company", {}) or {}).get("display_name", "").strip().lower()
        key = (title, company)
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


def format_job(job, index):
    title = job.get("title", "Untitled role").strip()
    company = (job.get("company", {}) or {}).get("display_name", "Not listed")
    location = (job.get("location", {}) or {}).get("display_name", "Location not listed")
    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")
    url = job.get("redirect_url", "")

    salary_line = ""
    if salary_min and salary_max:
        salary_line = f"\n💰 ₹{int(salary_min):,} - ₹{int(salary_max):,}"

    return (
        f"{index}. 🏥 *{title}*\n"
        f"🏢 {company}\n"
        f"📍 {location}"
        f"{salary_line}\n"
        f"🔗 {url}\n"
    )


def build_message(jobs):
    today = datetime.now().strftime("%d %b %Y")
    header = f"*Healthcare Job Alerts — {today}*\n\n"
    body = "\n".join(format_job(j, i + 1) for i, j in enumerate(jobs))
    footer = "\n\n_Forward to someone who needs a job today 🙏_"
    return header + body + footer


def main():
    if "PASTE_YOUR" in APP_ID or "PASTE_YOUR" in APP_KEY:
        print("ERROR: Add your free Adzuna APP_ID and APP_KEY first.")
        print("Sign up free at https://developer.adzuna.com/")
        print("Then set ADZUNA_APP_ID and ADZUNA_APP_KEY as environment variables.")
        return

    all_jobs = []
    print("Fetching jobs...")
    for location in LOCATIONS:
        for keyword in KEYWORDS:
            print(f"  searching '{keyword}' in '{location}'...")
            all_jobs.extend(fetch_jobs(keyword, location))

    unique_jobs = dedupe(all_jobs)[:MAX_JOBS_IN_OUTPUT]

    if not unique_jobs:
        print("No jobs found. Try widening KEYWORDS or LOCATIONS.")
        return

    message = build_message(unique_jobs)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(message)

    print("\n" + "=" * 60)
    print(message)
    print("=" * 60)
    print(f"\nSaved {len(unique_jobs)} jobs to {OUTPUT_FILE} — ready to paste into WhatsApp.")


if __name__ == "__main__":
    main()
