"""
load_env.py — Auto-loads .env before any module is imported.

Add this one-liner at the top of scraper.py or app.py if you prefer
managing keys via a .env file instead of shell exports:

    import load_env  # noqa: F401  (must be first import)
"""
from dotenv import load_dotenv
load_dotenv()
