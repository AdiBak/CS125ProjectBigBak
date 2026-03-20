# Big Bak Final Demo Script (5 minutes)

## Goal

Show: (1) problem \+ user, (2) system overview, (3) 2-3 concrete scenarios in app, (4) evidence it works, (5) limitations/future work.

---

## 0:00-0:30 — Hook (Problem \+ User)

**Visual:** Short clip/background of gym/workout and going home context (Zoom background is fine). Voiceover maybe.

**Say:** "Imagine you just finished a workout, got home, and you realize you forgot to buy that pack of spinach or can of milk or bread or whatever it may be\! That happens a lot with groceries and day-to-day items. Our project, Big Bak, is a context-aware recommendation app that helps users remember what they need and act quickly based on urgency and nearby store context."

---

## 0:30-1:00 — What the system does

**Visual:** Show app icon/home screen \+ quick pan over tabs (Home, Inventory, Settings). Voiceover maybe.

**Say:** "Big Bak combines inventory state, time since last purchase, and location context to rank what you should buy next. The app gives ranked recommendations, explains why each one is urgent, and shows nearby Trader Joe's information so the user can act immediately."

---

## 1:00-2:10 — Scenario 1: Low-stock urgency at home

**Visual flow: someone at their House maybe.**

1. Open **Inventory** tab.  
2. Show an item with low stock / increase 'days since last purchase' in edit screen.  
3. Return to **Home**.  
4. Show recommendation card order and urgency reason.

**Say:** "Scenario one is at-home. The stock automatically lowers as the days since last purchase for an item increased. So in the Home tab, that item moves higher in ranking. The app explains why with a transparent reason like stock level and time since last buy."

**Optional callout:** "For demo purposes, inventory decay is accelerated: one real hour is treated as one day, so urgency changes are visible during the demo window."

---

## 2:10-3:10 — Scenario 2: Location-aware recommendations

**Visual flow: someone outside/at gym again maybe. After workout open the app.**

1. Home tab open   
2. Show context label (e.g., "Near Trader Joe's (... mi)").  
3. Open a product detail card.  
4. Point to nearby store name/address/distance.

**Say:** "The app is all about location too. With location, the app detects nearby Trader Joe's via Overpass and surfaces store context directly in the recommendation flow. On Home and product details, we show the nearest store name, address, and distance. So the app isn't just saying what to buy; it's also helping with where and when to buy."

---

## 3:10-4:00 — Scenario 3: Notification reminder loop (can integrate with above part maybe \- after opening the app post-workout)

**Visual flow:**

1. Go to **Home** and refresh/open.  
2. Show local low-stock notification appearing.

**Say:** "Last but not least, the reminder loop is there: With low-stock warnings enabled, the app sends a local notification when low-stock items are detected. This gives the user a timely nudge. It's practical for our current scope and still closes the loop from state detection to user action."

---

## 4:00-4:35 — How it works (technical summary)

**Visual:** Optional split view of app \+ logos \+ codebase images?

**Say:** "Under the hood, backend APIs manage inventory, settings, and home recommendations. Product candidates come from our Trader Joe's scraped catalog. Ranking uses TF-IDF similarity plus urgency weighting from stock and last-buy time. Location context comes from Overpass nearby-store lookup. The mobile client renders ranked results and supports add/edit/restock actions in real time."

---

## 4:35-5:00 — Results \+ limitations \+ next steps

**Visual:** Return to Home screen with ranked cards.

**Say:** "In our tests, changing inventory and context consistently changes ranking and explanations as expected, and nearby-store context appears correctly when location is available. Current limitations are small-scale evaluation and local-only notifications. Next steps are broader user testing, stronger semantic ranking, and production-grade notification and scheduling infrastructure."

---

## Quick recording checklist (before filming)

- Backend running (`python backend/main.py`)  
- Mobile app running on phone (`npm start` in `mobile/`)  
- Location permission enabled  
- Notifications allowed for app  
- At least one low-stock item ready for scenario 1/3  
- Keep one clean take per scenario; stitch in order

---
