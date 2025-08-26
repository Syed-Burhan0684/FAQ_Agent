# File: src/ingest.py
# -------------------------
"""Ingest CSV into Chroma using the ingest_faq.py logic.
This wrapper is callable from the /ingest endpoint.
"""
import os
from dotenv import load_dotenv

load_dotenv()

from .ingest_faq import ingest as ingest_main  # always use the main ingest

FAQ_CSV = os.getenv("FAQ_CSV", os.path.join("data", "faq.csv"))

def ingest_faq_from_csv(csv_path: str = FAQ_CSV) -> int:
    """Ingest FAQ CSV into Chroma and return number of items ingested."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"{csv_path} not found")

    # call the real ingest function and capture the count
    count = ingest_main(csv_path)
    # ensure it always returns an integer
    return int(count) if count is not None else 0
