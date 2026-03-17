import sqlite3
import time

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


class SmartShoppingAssistant:
    def __init__(self, db_path="bigbak.db"):
        self.db_path = db_path

        # 1. LOAD PRODUCT CATALOG (The Store)
        try:
            conn = sqlite3.connect(self.db_path)
            self.df = pd.read_sql_query("SELECT * FROM products", conn)
            conn.close()
            self.df["name"] = self.df["name"].fillna("")
        except Exception as e:
            print(f"Warning: Could not load products. {e}")
            self.df = pd.DataFrame(columns=["name", "price", "category"])

        # 2. TRAIN TEXT ENGINE (For Product Matching)
        self.tfidf = TfidfVectorizer(stop_words="english")
        if not self.df.empty:
            self.tfidf_matrix = self.tfidf.fit_transform(self.df["name"])

    # Demo: 1 real hour = 1 "day"; stock decays 10% per hour (so after ~2.5h full becomes low).
    DECAY_PER_HOUR = 0.9  # multiplier per hour

    def get_user_inventory(self, user_id: str) -> dict:
        """
        Fetches the inventory for a specific user. Applies hourly decay: 1 real hour = 1 "day",
        and stock decreases by 10% per hour from last_updated_utc so the demo can show
        low-stock notifications without waiting real days.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            now = time.time()
            try:
                query = "SELECT item_name, stock, last_buy, last_updated_utc FROM inventory WHERE user_id = ?"
                df_inv = pd.read_sql_query(query, conn, params=(user_id,))
            except Exception:
                query = "SELECT item_name, stock, last_buy FROM inventory WHERE user_id = ?"
                df_inv = pd.read_sql_query(query, conn, params=(user_id,))
                df_inv["last_updated_utc"] = None
            conn.close()

            user_inventory = {}
            for _, row in df_inv.iterrows():
                stock = float(row["stock"])
                last_buy = int(row["last_buy"])
                last_utc = row.get("last_updated_utc")
                if last_utc is None or (isinstance(last_utc, float) and (last_utc != last_utc)):
                    last_utc = now - (last_buy * 24 * 3600) if last_buy else now
                last_utc = float(last_utc)
                hours_since = max(0, (now - last_utc) / 3600)
                # Effective stock after decay (10% per hour)
                effective_stock = max(0.0, min(1.0, stock * (self.DECAY_PER_HOUR ** hours_since)))
                # 1 real hour = 1 "day" for display and urgency
                effective_days_ago = hours_since / 24.0
                user_inventory[row["item_name"]] = {
                    "stock": effective_stock,
                    "last_buy": int(round(effective_days_ago)),
                }
            return user_inventory

        except Exception as e:
            print(
                f"Database error or missing inventory table: {e}. Using fallback mock data."
            )
            return {
                "Cheese": {"stock": 0.1, "last_buy": 45},
                "Milk": {"stock": 0.9, "last_buy": 2},
                "For the Love of Chocolate Mousse Cake": {
                    "stock": 0.0,
                    "last_buy": 365,
                },
            }

    def prioritize_needs(self, user_id: str, potential_needs: list = None):
        """
        Step 1: Rank the 'Queries' based on a specific User's Urgency.
        """
        # Fetch dynamic inventory for this user
        user_inventory = self.get_user_inventory(user_id)

        # If no specific list is passed in, check everything in the user's inventory
        if potential_needs is None:
            potential_needs = list(user_inventory.keys())

        ranked_needs = []

        for item in potential_needs:
            # Look up user data (Default to 'Unknown' stock logic if item isn't tracked)
            data = user_inventory.get(item, {"stock": 0.5, "last_buy": 15})

            # SCORING LOGIC (0.0 to 1.0)
            score_stock = 1.0 - data["stock"]
            score_time = min(
                data["last_buy"] / 30.0, 1.0
            )  # Cap at 30 days for max urgency
            final_urgency = (score_stock * 0.7) + (score_time * 0.3)

            ranked_needs.append(
                {
                    "query": item,
                    "urgency_score": final_urgency,
                    "reason": f"Stock: {data['stock'] * 100:.0f}%, Last Buy: {data['last_buy']}d",
                }
            )

        return sorted(ranked_needs, key=lambda x: x["urgency_score"], reverse=True)

    def restock_item(self, user_id: str, item_name: str) -> bool:
        """
        Marks an item as restocked (stock=1.0, last_buy=0).
        If the row doesn't exist, inserts it so new items can be added from the app.
        """
        return self.set_inventory_item(user_id, item_name, 1.0, 0)

    def set_inventory_item(
        self, user_id: str, item_name: str, stock: float, last_buy: int
    ) -> bool:
        """
        Sets an inventory item's stock (0.0-1.0) and last_buy (days ago).
        Resets last_updated_utc to now so hourly decay starts from this moment.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = time.time()
            cursor.execute(
                "UPDATE inventory SET stock = ?, last_buy = ?, last_updated_utc = ? WHERE user_id = ? AND item_name = ?",
                (stock, last_buy, now, user_id, item_name),
            )
            if cursor.rowcount == 0:
                cursor.execute(
                    "INSERT INTO inventory (user_id, item_name, stock, last_buy, last_updated_utc) VALUES (?, ?, ?, ?, ?)",
                    (user_id, item_name, stock, last_buy, now),
                )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            # Fallback if last_updated_utc column missing (old DB)
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE inventory SET stock = ?, last_buy = ? WHERE user_id = ? AND item_name = ?",
                    (stock, last_buy, user_id, item_name),
                )
                if cursor.rowcount == 0:
                    cursor.execute(
                        "INSERT INTO inventory (user_id, item_name, stock, last_buy) VALUES (?, ?, ?, ?)",
                        (user_id, item_name, stock, last_buy),
                    )
                conn.commit()
                conn.close()
                return True
            except Exception as e2:
                print(f"set_inventory_item error: {e2}")
                return False

    def get_products_for_need(self, query, top_n=3):
        """
        Step 2: Find the best products for the selected query.
        """
        if self.df.empty:
            return []

        query_vec = self.tfidf.transform([query])
        cosine_sim = linear_kernel(query_vec, self.tfidf_matrix).flatten()
        top_indices = cosine_sim.argsort()[::-1][:top_n]

        results = []
        for i in top_indices:
            if cosine_sim[i] < 0.1:  # Threshold to filter noise
                continue

            results.append(
                {
                    "name": self.df.iloc[i]["name"],
                    "price": self.df.iloc[i]["price"],
                    "relevance": f"{cosine_sim[i]:.2f}",
                }
            )

        return results


# --- DEMO SCENARIO ---
if __name__ == "__main__":
    assistant = SmartShoppingAssistant()
    test_user = "demo_user_123"

    print(f"\n>>> ANALYZING NEEDS FOR USER: {test_user}...")
    priorities = assistant.prioritize_needs(test_user)

    print("\n--- PRIORITY QUEUE ---")
    for p in priorities:
        print(
            f"Item: {p['query']:<10} | Urgency: {p['urgency_score']:.2f} | Context: {p['reason']}"
        )
