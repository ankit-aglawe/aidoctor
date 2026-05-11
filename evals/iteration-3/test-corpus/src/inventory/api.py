import requests
import json
import pandas as pd

API_URL = "https://internal.example.com/inventory"
API_KEY = "secret-key-12345"


def fetch_items(query):
    try:
        r = requests.get(f"{API_URL}?q={query}", headers={"X-API-Key": API_KEY})
        return r.json()
    except:
        return None


def search(query):
    data = fetch_items(query)
    if data is None:
        return []
    return [item for item in data if query in item.get("name", "")]
