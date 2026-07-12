# 🏛️ RAST Studios — Lead Generation System

A simple, self-hosted MVP for scraping business leads and managing outreach — built with Google Places API, SQLite, and Streamlit.

---

## Folder Structure

```
rast_leads/
├── scraper.py        # Fetches leads from Google Places API
├── database.py       # SQLite CRUD helpers
├── app.py            # Streamlit dashboard
├── outreach.py       # AI cold-DM generator (Anthropic API)
├── load_env.py       # Loads .env file automatically
├── requirements.txt
├── .env.example      # Copy → .env and add your keys
├── leads.csv         # ← auto-created after first scrape
└── leads.db          # ← auto-created SQLite database
```

---

## Step 1 — Get API Keys

### Google Places API
1. Go to https://console.cloud.google.com/
2. Create a new project (or use an existing one)
3. Navigate to **APIs & Services → Library**
4. Enable both:
   - **Places API**
   - **Geocoding API**
5. Go to **APIs & Services → Credentials → Create Credentials → API Key**
6. Copy the key

> **Billing note:** Google gives $200 free credit/month. Each "Nearby Search" call = $0.032, each "Place Details" call = $0.017. A full scrape of ~200 leads costs roughly $5–8.

### Anthropic API (for cold DM generation only — optional)
1. Go to https://console.anthropic.com/
2. Create an account and add a payment method
3. Navigate to **API Keys → Create Key**
4. Copy the key

---

## Step 2 — Setup

```bash
# 1. Clone / download the project
cd rast_leads

# 2. Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate          # Mac/Linux
venv\Scripts\activate             # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your API keys
cp .env.example .env
# Open .env in any text editor and paste your keys:
#   GOOGLE_API_KEY=AIza...
#   ANTHROPIC_API_KEY=sk-ant-...
```

---

## Step 3 — Run the Scraper

```bash
python scraper.py
```

You'll see live progress in the terminal:

```
📍 Geocoding 'Bangalore, India' …
   → 12.9716, 77.5946

🔍 Searching: Interior Designer (interior designer) …
   Found 38 raw results
   ✓ Studio 7 Interiors
   ✓ The Design Studio
   ...

✅ Done! 143 unique leads saved → leads.csv + leads.db
```

### Change location or categories
Edit the top of `scraper.py`:

```python
DEFAULT_LOCATION = "Mumbai, India"   # any city
DEFAULT_RADIUS   = 20000             # metres

CATEGORIES = {
    "Interior Designer": "interior designer",
    "Real Estate Agent": "real estate agency",
    "Builder":           "construction company",
    "Architect":         "architect",
}
```

---

## Step 4 — Launch the Dashboard

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

### Dashboard features
| Feature | How to use |
|---|---|
| Search | Type a name or area in the sidebar search box |
| Filter by category | Use the "Category" dropdown |
| Filter by status | Use the "Status" dropdown |
| Update contact status | Select a lead → click Not Contacted / Contacted → Save Status |
| Add notes | Select a lead → type in Notes box → Save Notes |
| Generate cold DM | Select a lead → click "Generate personalised DM" |
| Delete a lead | Select a lead → expand "Delete this lead" → confirm |

---

## Step 5 — Generate a Cold DM (optional)

From the dashboard, select any lead and click **✨ Generate personalised DM**.

Or run it from the terminal:

```bash
python outreach.py
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `REQUEST_DENIED` from Places API | Check that Places API and Geocoding API are both enabled in Google Console |
| `0 results` for a category | Try a broader keyword or increase `DEFAULT_RADIUS` |
| `ModuleNotFoundError` | Make sure your venv is activated and `pip install -r requirements.txt` ran successfully |
| DM generation fails | Check that `ANTHROPIC_API_KEY` is set correctly in `.env` |

---

## Cost Estimate (Google Places API)

| Action | Cost |
|---|---|
| 1 Nearby Search page (~20 results) | $0.032 |
| 1 Place Details call (phone + website) | $0.017 |
| Full scrape (4 categories × 3 pages + 200 detail calls) | ~$7–10 |

Run the scraper once, then work from the database — no repeated API costs.
