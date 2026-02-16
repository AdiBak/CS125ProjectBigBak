import sqlite3

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


class SmartShoppingAssistant:
    def __init__(self, db_path="bigbak.db"):
        # 1. LOAD PRODUCT CATALOG (The Store)
        try:
            conn = sqlite3.connect(db_path)
            self.df = pd.read_sql_query("SELECT * FROM products", conn)
            conn.close()
            self.df["name"] = self.df["name"].fillna("")
        except:
            self.df = pd.DataFrame(columns=["name", "price", "category"])

        # 2. TRAIN TEXT ENGINE (For Product Matching)
        self.tfidf = TfidfVectorizer(stop_words="english")
        if not self.df.empty:
            self.tfidf_matrix = self.tfidf.fit_transform(self.df["name"])

        # 3. SIMULATE USER INVENTORY (The "Personal Model")
        # Instead of random numbers per product, we track CATEGORIES/TERMS.
        # Logic:
        # - Stock: 0.0 (Empty) to 1.0 (Full)
        # - Last_Buy: Days ago
        self.user_inventory = {
            "Cheese": {"stock": 0.1, "last_buy": 45},  # Urgent
            "Milk": {"stock": 0.9, "last_buy": 2},  # Fine
            "Eggs": {"stock": 0.4, "last_buy": 10},  # Medium
            "Snacks": {"stock": 0.2, "last_buy": 35},  # Urgent
            "Fruit": {"stock": 0.8, "last_buy": 5},  # Fine
            # NEW ITEM
            "For the Love of Chocolate Mousse Cake": {
                "stock": 0.0,  # Empty (You don't have it)
                "last_buy": 365,  # Bought 1 year ago (Seasonal/Valentine's tradition)
            },
        }
        print(f">>> User Profile Loaded: {self.user_inventory}")

    def prioritize_needs(self, potential_needs):
        """
        Step 1: Rank the 'Queries' based on User Urgency.
        Input: ['Cheese', 'Milk', 'Eggs']
        Output: Sorted list with scores.
        """
        ranked_needs = []

        for item in potential_needs:
            # Look up user data (Default to 'Unknown' if not in inventory)
            data = self.user_inventory.get(item, {"stock": 0.5, "last_buy": 15})

            # SCORING LOGIC (0.0 to 1.0)
            # A. Stock Urgency (Lower stock = Higher score)
            score_stock = 1.0 - data["stock"]

            # B. Recency Urgency (Older buy = Higher score)
            # Cap at 30 days for max urgency
            score_time = min(data["last_buy"] / 30.0, 1.0)

            # C. Weighted Average (70% Stock, 30% Time)
            final_urgency = (score_stock * 0.7) + (score_time * 0.3)

            ranked_needs.append(
                {
                    "query": item,
                    "urgency_score": final_urgency,
                    "reason": f"Stock: {data['stock'] * 100:.0f}%, Last Buy: {data['last_buy']}d",
                }
            )

        # Sort by urgency (descending)
        return sorted(ranked_needs, key=lambda x: x["urgency_score"], reverse=True)

    def get_products_for_need(self, query, top_n=3):
        """
        Step 2: Find the best products for the selected query.
        Pure Text Similarity (Relevance).
        """
        if self.df.empty:
            return []

        query_vec = self.tfidf.transform([query])
        cosine_sim = linear_kernel(query_vec, self.tfidf_matrix).flatten()

        # Get top indices
        top_indices = cosine_sim.argsort()[::-1][:top_n]

        results = []
        for i in top_indices:
            # Threshold to filter noise
            if cosine_sim[i] < 0.1:
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

    # 1. The "Wake Up" Scenario
    # The system checks a list of common staples to see what's needed.
    print("\n>>> ANALYZING USER NEEDS...")

    daily_staples = assistant.user_inventory.keys()
    priorities = assistant.prioritize_needs(daily_staples)

    # 2. Display the Decision Process
    print("\n--- PRIORITY QUEUE ---")
    for p in priorities:
        print(
            f"Item: {p['query']:<10} | Urgency: {p['urgency_score']:.2f} | Context: {p['reason']}"
        )

    # 3. Action the Top Priority
    top_pick = priorities[0]
    print(f"\n>>> WINNER: '{top_pick['query']}' is the most urgent need.")
    print(f">>> Fetching best products for '{top_pick['query']}'...")

    products = assistant.get_products_for_need(top_pick["query"])

    print("\n--- RECOMMENDED PRODUCTS TO BUY ---")
    for prod in products:
        print(f"Product: {prod['name']}")
        print(f"Price:   {prod['price']}")
        print(f"Match:   {prod['relevance']}")
        print("-" * 30)
