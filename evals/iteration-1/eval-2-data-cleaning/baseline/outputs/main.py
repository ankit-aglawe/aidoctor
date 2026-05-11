from datetime import datetime, timedelta

import pandas as pd


def drop_stale_users(df):
    cutoff = datetime.now() - timedelta(days=90)
    indices_to_drop = []
    for i, row in df.iterrows():
        if row["last_seen"] < cutoff:
            indices_to_drop.append(i)
    df = df.drop(indices_to_drop)
    return df
