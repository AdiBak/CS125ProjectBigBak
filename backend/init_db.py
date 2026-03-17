# save as init_db.py and run from repo root: python backend/init_db.py
# or from backend/: python init_db.py
import os
import sqlite3

db_path = os.path.join(os.path.dirname(__file__), "bigbak.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create the inventory table (last_updated_utc = Unix time when stock was last set; used for hourly decay)
cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    user_id TEXT,
    item_name TEXT,
    stock REAL,
    last_buy INTEGER,
    last_updated_utc REAL
)
""")
# Add column for existing DBs
try:
    cursor.execute("ALTER TABLE inventory ADD COLUMN last_updated_utc REAL")
except Exception:
    pass
# Backfill: assume "last update" was last_buy days ago so decay is correct
cursor.execute(
    "UPDATE inventory SET last_updated_utc = strftime('%s','now') - (last_buy * 86400) WHERE last_updated_utc IS NULL"
)

# Create the user_settings table
cursor.execute("""
CREATE TABLE IF NOT EXISTS user_settings (
    user_id TEXT PRIMARY KEY,
    user_name TEXT,
    email TEXT,
    preferred_brands TEXT,
    price_sensitivity TEXT,
    location_alerts INTEGER,
    low_stock_warnings INTEGER,
    push_token TEXT,
    last_near_store_push_at REAL
)
""")

# Insert test data only if inventory is empty (so re-running init_db doesn't duplicate)
import time
row_count = cursor.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
if row_count == 0:
    now = time.time()
    test_data = [
        ("demo_user_123", "Cheese", 0.5, 0, now),
        ("demo_user_123", "Milk", 0.9, 2, now - 2 * 86400),
        ("demo_user_123", "For the Love of Chocolate Mousse Cake", 0.0, 365, now - 365 * 86400),
        ("test_user", "Cheese", 0.5, 0, now),
        ("test_user", "Milk", 0.9, 2, now - 2 * 86400),
        ("test_user", "Eggs", 0.4, 10, now - 10 * 86400),
        ("test_user", "Snacks", 0.2, 35, now - 35 * 86400),
    ]
    try:
        cursor.executemany(
            "INSERT INTO inventory (user_id, item_name, stock, last_buy, last_updated_utc) VALUES (?, ?, ?, ?, ?)",
            test_data,
        )
    except Exception:
        cursor.executemany(
            "INSERT INTO inventory (user_id, item_name, stock, last_buy) VALUES (?, ?, ?, ?)",
            [(u, i, s, b) for u, i, s, b, _ in test_data],
        )
conn.commit()
conn.close()

print("Database initialized with test inventory!")
