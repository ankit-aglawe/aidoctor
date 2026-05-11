import pandas as pd
import os


def format_currency(amount):
    return f"${amount:.2f}"


def parse_csv(path):
    df = pd.read_csv(path)
    items = []
    for i in range(len(df)):
        items.append(df.iloc[i].to_dict())
    return items


def _legacy_normalizer(text):
    # used in v0.0.0, kept for compat
    return text.strip().lower()
