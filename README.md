# Healthcare Job Alerts Bot (Free)

Fetches healthcare job listings and formats them into a ready-to-paste
WhatsApp message — no scraping, no paid tools.

## Why not scrape Naukri/Indeed/Glassdoor/WorkIndia directly?
Their Terms of Service forbid automated scraping, and they actively block
bots. This uses **Adzuna**, a free, legal job aggregator API that already
pulls listings from many boards (Indeed included).

## Setup (takes ~5 minutes, completely free)

### 1. Get a free Adzuna API key
- Go to https://developer.adzuna.com/
- Sign up (free) and grab your `APP_ID` and `APP_KEY` from the dashboard.

### 2. Run it locally
```bash
pip install requests
export ADZUNA_APP_ID="your_app_id"
export ADZUNA_APP_KEY="your_app_key"
python healthcare_job_alerts.py
```
This prints a formatted job list and saves it to `jobs_output.txt`.
Copy-paste that into your WhatsApp channel.

### 3. (Optional) Automate it daily for free with GitHub Actions
1. Create a free GitHub account and a new repository.
2. Upload all files from this folder (including the `.github/workflows/`
   folder — keep that exact path).
3. In your repo: **Settings → Secrets and variables → Actions → New
   repository secret**. Add:
   - `ADZUNA_APP_ID`
   - `ADZUNA_APP_KEY`
4. That's it — GitHub will run the script daily and update
   `jobs_output.txt` in your repo automatically. Open the file each
   morning and paste it into WhatsApp.

## Customizing what it searches for
Open `healthcare_job_alerts.py` and edit near the top:
- `LOCATIONS` — cities you post jobs for
- `KEYWORDS` — roles you cover (nurse, pharmacist, lab tech, etc.)
- `MAX_JOBS_IN_OUTPUT` — how many jobs appear in the final message

## About fully automatic WhatsApp posting
Sending messages automatically to a WhatsApp Channel requires WhatsApp's
Business API, which isn't free. This setup gets you 95% of the way there
for ₹0 — the script does all the searching, filtering, and formatting;
you just paste the result in (takes seconds).

## Files in this folder
- `healthcare_job_alerts.py` — the main script
- `config_example.json` — reference for API key format
- `.github/workflows/daily-job-fetch.yml` — free daily automation
- `jobs_output.txt` — generated each run, this is what you paste to WhatsApp
