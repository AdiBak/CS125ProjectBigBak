# save as init_db.py and run: python init_db.py
import sqlite3

conn = sqlite3.connect("backend/bigbak.db")
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

# Insert some test data for demo_user_123
test_data = [
    ("demo_user_123", "Cheese", 0.1, 45),
    ("demo_user_123", "Milk", 0.9, 2),
    ("demo_user_123", "For the Love of Chocolate Mousse Cake", 0.0, 365),
]

cursor.executemany("INSERT INTO inventory VALUES (?, ?, ?, ?)", test_data)
conn.commit()
conn.close()

print("Database initialized with test inventory!")
