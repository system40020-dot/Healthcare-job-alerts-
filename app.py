import streamlit as st
import pandas as pd
import logging
import subprocess
import sys
from jobspy import scrape_jobs
from playwright.sync_api import sync_playwright

# jobspy apne internal errors khud print/log karta hai - abhi tak woh chup ho rahe the.
# Isse enable karne se Streamlit Cloud ke "Manage app" -> Logs mein asli reason dikhega
# jab Glassdoor/Google/Indeed fail ho.
logging.basicConfig(level=logging.INFO)

# Streamlit Cloud pe koi custom "build command" nahi chalta (Render jaisa) jo
# `playwright install chromium` chala sake - isliye yeh startup pe khud karna padta hai.
# @st.cache_resource isse sirf EK BAAR chalata hai (poore app-session ke liye), baar-baar
# button-click pe repeat nahi hota.
@st.cache_resource
def ensure_playwright_browser_installed():
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True, capture_output=True, text=True
        )
        return "installed"
    except subprocess.CalledProcessError as e:
        return f"failed: {e.stderr}"

_playwright_install_status = ensure_playwright_browser_installed()

st.set_page_config(
    page_title="India Healthcare Job Automator & Broadcaster",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 India Healthcare Job Aggregator & WhatsApp Broadcaster")
st.markdown("Automate job discovery across **Indeed, Glassdoor, Naukri, Google, and Official Hospital Portals** with precise regional and freshness controls.")

# Comprehensive Healthcare Department and Sub-Role Keyword Mapping
HEALTHCARE_JOB_CATEGORIES = {
    "Radiology & Imaging": [
        "radiology", "imaging", "radiographer", "x-ray technician", "xray technician",
        "ct technician", "computed tomography", "mri technician", "ultrasound technician",
        "sonographer", "cath lab technician", "nuclear medicine technologist",
        "radiology assistant", "imaging assistant", "radiology in-charge", "radiology supervisor",
        "x-ray assistant", "ct in-charge", "mri in-charge"
    ],
    "Laboratory & Pathology": [
        "lab technician", "laboratory technician", "mlt", "medical laboratory technologist",
        "pathology technician", "phlebotomist", "biochemistry technician",
        "microbiology technician", "blood bank technician",
        "lab assistant", "laboratory assistant", "lab in-charge", "pathology assistant",
        "lab supervisor", "blood bank in-charge"
    ],
    "Operation Theatre & Critical Care": [
        "ot technician", "operation theatre technician", "icu technician",
        "critical care technician", "anesthesia technician",
        "ot assistant", "operation theatre assistant", "ot in-charge",
        "icu assistant", "icu in-charge", "critical care assistant"
    ],
    "Dialysis Technician": [
        "dialysis technician", "dialysis assistant", "dialysis technologist",
        "hemodialysis technician", "dialysis nurse", "dialysis in-charge", "dialysis supervisor"
    ],
    "Dietician & Nutritionist": [
        "dietician", "dietitian", "nutritionist", "clinical nutritionist",
        "dietetics in-charge", "chief dietician", "food and nutrition supervisor",
        "dietary assistant"
    ],
    "Optometrist": [
        "optometrist", "ophthalmic assistant", "eye care technician",
        "optometry technician", "optometrist in-charge", "ophthalmic technician"
    ],
    "Nursing & Emergency": [
        "staff nurse", "nursing officer", "emergency medical technician",
        "emt", "paramedic", "ward nurse", "nursing in-charge", "nursing supervisor"
    ],
    "Pharmacy & Biomedical Engineering": [
        "pharmacist", "pharmacy technician", "dispenser",
        "biomedical engineer", "biomedical technician", "pharmacy in-charge"
    ],
    "Assistant Professor - Radiology & Imaging": [
        "assistant professor radiology", "assistant professor imaging", "assistant professor radiodiagnosis"
    ],
    "Assistant Professor - Laboratory & Pathology": [
        "assistant professor pathology", "assistant professor laboratory medicine", "assistant professor microbiology", "assistant professor biochemistry"
    ],
    "Assistant Professor - Operation Theatre & Surgery": [
        "assistant professor surgery", "assistant professor operation theatre", "assistant professor anesthesiology"
    ],
    "Assistant Professor - Dialysis & Nephrology": [
        "assistant professor nephrology", "assistant professor dialysis"
    ],
    "Assistant Professor - Nursing": [
        "assistant professor nursing"
    ],
    "Assistant Professor - Optometry & Ophthalmology": [
        "assistant professor ophthalmology", "assistant professor optometry"
    ],
    "Assistant Professor - General Medical / Clinical": [
        "assistant professor medical", "assistant professor clinical", "assistant professor anatomy", "assistant professor physiology"
    ]
}

location_options = {
    "Pan-India / State-Wide": [
        "India", "Uttar Pradesh, India", "Gujarat, India", "Delhi, India",
        "Maharashtra, India", "Bihar, India", "Jharkhand, India", "Karnataka, India", "Tamil Nadu, India"
    ],
    "Tier 1 Cities (Metros)": [
        "Delhi NCR, India", "Mumbai, Maharashtra", "Bengaluru, Karnataka",
        "Chennai, Tamil Nadu", "Kolkata, West Bengal", "Hyderabad, Telangana", "Ahmedabad, Gujarat", "Pune, Maharashtra"
    ],
    "Tier 2 & Healthcare Hubs": [
        "Lucknow, Uttar Pradesh", "Surat, Gujarat", "Kanpur, Uttar Pradesh",
        "Varanasi, Uttar Pradesh", "Agra, Uttar Pradesh", "Meerut, Uttar Pradesh",
        "Vadodara, Gujarat", "Rajkot, Gujarat", "Indore, Madhya Pradesh", "Bhopal, Madhya Pradesh",
        "Patna, Bihar", "Ranchi, Jharkhand", "Jamshedpur, Jharkhand", "Jaipur, Rajasthan"
    ],
    "Tier 3 Districts & Regional Centers": [
        "Gorakhpur, Uttar Pradesh", "Bareilly, Uttar Pradesh", "Aligarh, Uttar Pradesh",
        "Moradabad, Uttar Pradesh", "Saharanpur, Uttar Pradesh", "Jhansi, Uttar Pradesh",
        "Bhavnagar, Gujarat", "Jamnagar, Gujarat", "Anand, Gujarat", "Dhanbad, Jharkhand", "Bokaro, Jharkhand"
    ]
}

st.sidebar.header("🔍 Search Filters")

if _playwright_install_status != "installed":
    st.sidebar.error(f"⚠️ Playwright browser install issue: {_playwright_install_status[:200]}")
else:
    st.sidebar.caption("✅ Playwright browser ready")

selected_category_name = st.sidebar.selectbox("Select Healthcare Category", list(HEALTHCARE_JOB_CATEGORIES.keys()))
loc_group = st.sidebar.selectbox("Location Scope", list(location_options.keys()))
selected_location = st.sidebar.selectbox("Select City / Region / State", location_options[loc_group])

custom_location = st.sidebar.text_input("Or Type Custom City/District/State", "")
target_location = custom_location if custom_location.strip() else selected_location

freshness_label = st.sidebar.selectbox("Freshness / Time Filter", ["Past 24 Hours (Today)", "Past 3 Days", "Past 7 Days", "Past 30 Days"])
freshness_hours_map = {
    "Past 24 Hours (Today)": 24,
    "Past 3 Days": 72,
    "Past 7 Days": 168,
    "Past 30 Days": 720
}
freshness_hours = freshness_hours_map[freshness_label]

results_count = st.sidebar.slider("Results Limit per Job Board", min_value=5, max_value=25, value=10)
selected_boards = st.sidebar.multiselect("Select Resources & Job Boards", ["indeed", "glassdoor", "naukri", "google"], default=["indeed", "glassdoor", "naukri", "google"])
include_official_portals = st.sidebar.checkbox("Include Official Hospital & Institutional Career Pages", value=True)
whatsapp_channel_link = st.sidebar.text_input("Channel Invite URL", "https://whatsapp.com/channel/0029VbCCDBbDzt8flpKPh2o")

# Custom Stealth Scraper function for Naukri to bypass reCAPTCHA
def scrape_naukri_stealth(keyword, location, results_wanted=10):
    jobs_list = []
    kw = keyword.replace(" ", "-").lower()
    loc = location.split(",")[0].strip().replace(" ", "-").lower()
    url = f"https://www.naukri.com/{kw}-jobs-in-{loc}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            # Manual stealth-script - external playwright-stealth library ki jagah, kyunki
            # wo purani library naye Python versions (3.14) ke saath crash kar rahi thi
            # (pkg_resources/setuptools issue). Yahi technique relay-deals-bot mein bhi
            # kaam kar rahi hai - koi extra dependency nahi chahiye isko.
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                window.chrome = { runtime: {} };
            """)
            page = context.new_page()

            page.goto(url, timeout=30000)
            page.wait_for_timeout(3000)

            html_snapshot = page.content()
            job_cards = page.locator(".srp-jobtuple-wrapper").all()

            if len(job_cards) == 0:
                # Kuch bhi nahi mila - is baar chup nahi honge, exact wajah record karenge
                short_snapshot = html_snapshot[:800]
                st.session_state.setdefault("naukri_debug", []).append(
                    f"'{keyword}' @ {location}: 0 job-cards mile. URL={url}\nHTML sample: {short_snapshot}"
                )

            for card in job_cards[:results_wanted]:
                try:
                    title_elem = card.locator(".title")
                    comp_elem = card.locator(".comp-name")

                    title = title_elem.inner_text() if title_elem.count() > 0 else keyword
                    company = comp_elem.inner_text() if comp_elem.count() > 0 else "Leading Healthcare Facility"
                    link = title_elem.get_attribute("href") if title_elem.count() > 0 else "#"

                    jobs_list.append({
                        "site": "naukri",
                        "title": title,
                        "company": company,
                        "location": location,
                        "date_posted": "Recent",
                        "job_url": link
                    })
                except Exception as card_err:
                    st.session_state.setdefault("naukri_debug", []).append(f"Card parse error: {card_err}")
                    continue
            browser.close()
    except Exception as e:
        # Pehle yahan chup-chaap 'pass' ho jaata tha - ab exact error record karenge
        st.session_state.setdefault("naukri_debug", []).append(f"'{keyword}' @ {location}: CRASH -> {type(e).__name__}: {e}")

    return pd.DataFrame(jobs_list)

if st.button("🚀 Run Multi-Source Scraper & Generate Broadcasts", type="primary"):
    expanded_titles = HEALTHCARE_JOB_CATEGORIES[selected_category_name]

    st.info(f"🔎 Category: **{selected_category_name}** | Target Location: **{target_location}** | Freshness: **{freshness_label}**")

    all_jobs = []
    progress_bar = st.progress(0)
    total_titles = len(expanded_titles)
    st.session_state["naukri_debug"] = []
    jobspy_errors = []

    # Exclude naukri from jobspy to prevent 406 recaptcha crash, handle it via stealth scraper
    jobspy_boards = [b for b in selected_boards if b != "naukri"]

    with st.spinner("Scraping Indeed, Glassdoor, Google, and Naukri (via Playwright-Stealth) concurrently..."):
        for i, title in enumerate(expanded_titles):
            # 1. Fetch via JobSpy for Indeed, Glassdoor, Google - HAR SITE ALAG SE call karo,
            # taaki ek site fail ho toh baaki bhi na rukein, aur exact site ka error mile
            if jobspy_boards:
                google_query_param = f"{title} jobs hiring in {target_location}"
                if include_official_portals:
                    google_query_param = f"{title} (hospital OR medical center OR nursing home OR career portal) hiring in {target_location}"

                for board in jobspy_boards:
                    try:
                        jobs = scrape_jobs(
                            site_name=[board],
                            search_term=title,
                            google_search_term=google_query_param,
                            location=target_location,
                            results_wanted=results_count,
                            hours_old=freshness_hours,
                            country_indeed="India"
                        )
                        if not jobs.empty:
                            all_jobs.append(jobs)
                        else:
                            jobspy_errors.append(f"[{board}] '{title}': 0 results returned (no exception, empty response)")
                    except Exception as e:
                        jobspy_errors.append(f"[{board}] '{title}': CRASH -> {type(e).__name__}: {e}")

            # 2. Fetch via Playwright-Stealth for Naukri if selected (aapka original custom scraper)
            if "naukri" in selected_boards:
                naukri_df = scrape_naukri_stealth(title, target_location, results_count)
                if not naukri_df.empty:
                    all_jobs.append(naukri_df)

            # 3. EXPERIMENTAL: jobspy ka apna built-in Naukri scraper bhi try karo (alag approach -
            # internal API-based ho sakta hai, custom Playwright-stealth se alag). Dono chalenge,
            # jo kaam kare uska result milega, results "naukri_jobspy_native" tag se alag dikhenge.
            if "naukri" in selected_boards:
                try:
                    naukri_native = scrape_jobs(
                        site_name=["naukri"],
                        search_term=title,
                        location=target_location,
                        results_wanted=results_count,
                        country_indeed="India"
                    )
                    if not naukri_native.empty:
                        naukri_native["site"] = "naukri_jobspy_native"
                        all_jobs.append(naukri_native)
                    else:
                        jobspy_errors.append(f"[naukri_jobspy_native] '{title}': 0 results returned (no exception, empty response)")
                except Exception as e:
                    jobspy_errors.append(f"[naukri_jobspy_native] '{title}': CRASH -> {type(e).__name__}: {e}")

            progress_bar.progress((i + 1) / total_titles)

    # Debug panel - ab har site ka exact error/status dikhega, chup nahi hoga
    with st.expander("🔧 Debug Log (per-site errors - agar koi site 0 results de rahi hai, yahan wajah dekho)"):
        if jobspy_errors:
            st.write("**JobSpy (Indeed/Glassdoor/Google) issues:**")
            for err in jobspy_errors[:30]:
                st.text(err)
        if st.session_state.get("naukri_debug"):
            st.write("**Naukri issues:**")
            for err in st.session_state["naukri_debug"][:30]:
                st.text(err)
        if not jobspy_errors and not st.session_state.get("naukri_debug"):
            st.write("Koi error record nahi hua is run mein.")

    if all_jobs:
        master_df = pd.concat(all_jobs, ignore_index=True)
        if 'job_url' in master_df.columns:
            master_df = master_df.drop_duplicates(subset=['job_url'], keep='first')

        st.success(f"✅ Successfully gathered {len(master_df)} unique verified listings!")
        st.subheader("📊 Live Data Preview")
        st.dataframe(master_df[['site', 'title', 'company', 'location', 'date_posted']])

        st.subheader("💬 Ready-to-Post WhatsApp Channel Formats")
        for _, row in master_df.iterrows():
            job_title = str(row.get('title', 'Healthcare Professional')).upper()
            company_name = row.get('company', 'Hospital / Healthcare Facility')
            if pd.isna(company_name) or company_name == '':
                company_name = "Leading Healthcare Provider"

            location_val = row.get('location', target_location)
            job_link = row.get('job_url', '#')
            site_source = str(row.get('site', 'Official Portal')).capitalize()

            whatsapp_template = (
                f"HIRING | {job_title}\n\n"
                f"🏥 {company_name}\n\n"
                f"📍 {location_val}\n\n"
                f"🎓 *Qualification:* Diploma / B.Sc. / Relevant Degree\n"
                f"💼 *Experience:* As per industry standards ({site_source})\n"
                f"💰 *Salary:* Best in industry / Disclosed on application\n\n"
                f"🌐 *Apply through website:*\n{job_link}\n\n"
                f"📢 *Healthcare Job Updates | Join & Share with Colleagues 👆*\n"
                f"{whatsapp_channel_link}"
            )
            st.text_area(f"📱 Format for: {job_title} at {company_name}", whatsapp_template, height=220)
            st.markdown("---")

        csv_data = master_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Master Job Spreadsheet (CSV)",
            data=csv_data,
            file_name=f"healthcare_jobs_{selected_category_name.lower().replace(' ', '_')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("⚠️ No active listings found matching this exact filter combination. Try expanding your freshness timeframe or location scope.")
        
