import sqlite3
import pandas as pd
import numpy as np
import os

# Connect to the existing database
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'olist.sqlite')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print(f"🔌 Connected to: {DB_PATH}")

# 1. Create a NEW Table (that didn't exist before)
table_name = "silver_marketing_campaigns"
print(f"🔨 Creating table: {table_name}...")

# Generate dummy data
data = {
    'campaign_date': pd.date_range(start='2023-01-01', periods=10, freq='D').astype(str),
    'campaign_name': ['Email_Blast', 'Social_Ad', 'TV_Spot', 'Email_Blast', 'Social_Ad'] * 2,
    'clicks': np.random.randint(100, 5000, size=10),
    'cost_usd': np.random.uniform(50.0, 1000.0, size=10).round(2)
}
df = pd.DataFrame(data)

# 2. Write to SQLite
df.to_sql(table_name, conn, if_exists='replace', index=False)

print(f"✅ Success! Injected 10 rows into '{table_name}'.")
print("👉 Now go to your running Streamlit app and ask: 'Visualize silver_marketing_campaigns'")

conn.close()