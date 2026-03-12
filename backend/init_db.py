# save as init_db.py and run from repo root: python backend/init_db.py
# or from backend/: python init_db.py
import os
import sqlite3

db_path = os.path.join(os.path.dirname(__file__), "bigbak.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create the inventory table
cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    user_id TEXT,
    item_name TEXT,
    stock REAL,
    last_buy INTEGER
)
""")

# Insert some test data for demo_user_123 and test_user (used by the mobile app)
test_data = [
    ("demo_user_123", "Cheese", 0.1, 45),
    ("demo_user_123", "Milk", 0.9, 2),
    ("demo_user_123", "For the Love of Chocolate Mousse Cake", 0.0, 365),
    ("test_user", "Cheese", 0.1, 45),
    ("test_user", "Milk", 0.9, 2),
    ("test_user", "Eggs", 0.4, 10),
    ("test_user", "Snacks", 0.2, 35),
]

cursor.executemany("INSERT INTO inventory VALUES (?, ?, ?, ?)", test_data)
conn.commit()
conn.close()

print("Database initialized with test inventory!")
