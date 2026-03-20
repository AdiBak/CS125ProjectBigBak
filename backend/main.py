import json
import os
import time
from typing import List, Optional

import requests
from fastapi import Depends, FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from location_service import BusinessLocationService
from pydantic import BaseModel, Field
from recc.prototype import SmartShoppingAssistant

# ==========================================
# 1. PYDANTIC SCHEMAS (Data Models)
# ==========================================


class ProductSuggestion(BaseModel):
    name: str
    price: str
    relevance: str


class RecommendationItem(BaseModel):
    item: str
    urgency: float = Field(..., description="Urgency score from 0.0 to 1.0")
    reason: str
    suggested_products: List[ProductSuggestion]
    nearest_store_name: Optional[str] = Field(
        None, description="Name of the nearest Trader Joe's (if location available)"
    )
    nearest_store_address: Optional[str] = Field(
        None, description="Address of the nearest Trader Joe's (if available)"
    )
    nearest_store_distance_mi: Optional[float] = Field(
        None, description="Distance to nearest store in miles (if available)"
    )


class RecommendationResponse(BaseModel):
    user_id: str
    context: str
    recommendations: List[RecommendationItem]
    low_stock_items: List[str] = Field(
        default_factory=list,
        description="Item names with stock below threshold (for local notifications when low_stock_warnings on)",
    )


class Business(BaseModel):
    name: str
    type: str
    lat: float
    lon: float
    address: str
    osm_id: Optional[int] = None


class NearbyBusinessesResponse(BaseModel):
    location: dict
    radius: int
    count: int
    businesses: List[Business]


class InventoryItem(BaseModel):
    item_name: str
    stock_percentage: float
    last_bought_days_ago: int
    category: str


class InventoryUpdate(BaseModel):
    item_name: str
    stock: float = Field(..., ge=0.0, le=1.0, description="Stock level 0.0–1.0")
    last_buy: int = Field(..., ge=0, description="Days since last purchase")


class UserSettings(BaseModel):
    user_name: str
    email: str
    preferred_brands: List[str]
    price_sensitivity: str
    location_alerts: bool
    low_stock_warnings: bool
    push_token: Optional[str] = None


class UserSettingsUpdate(BaseModel):
    """Partial update for settings; all fields optional."""
    user_name: Optional[str] = None
    email: Optional[str] = None
    preferred_brands: Optional[List[str]] = None
    price_sensitivity: Optional[str] = None
    location_alerts: Optional[bool] = None
    low_stock_warnings: Optional[bool] = None
    push_token: Optional[str] = None


# ==========================================
# 2. APP INITIALIZATION & DEPENDENCIES
# ==========================================

app = FastAPI(
    title="Big Bak API",
    version="1.0.0",
    description="Context-aware recommendation system for daily essentials.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(os.path.dirname(__file__), "bigbak.db")
LOW_STOCK_THRESHOLD = 0.3
assistant = SmartShoppingAssistant(db_path=DB_PATH)
location_service = BusinessLocationService()


def get_assistant():
    return assistant


def get_location_service():
    return location_service


# ==========================================
# 3. RESTFUL ENDPOINTS
# ==========================================


@app.get("/api/v1/health", tags=["System"])
def health_check():
    """Health check endpoint to verify the API is running."""
    return {"status": "healthy", "service": "Big Bak API"}


# --- HOME / DASHBOARD ---
@app.get(
    "/api/v1/users/{user_id}/home",
    response_model=RecommendationResponse,
    tags=["Home/Dashboard"],
)
def get_home_dashboard(
    user_id: str = Path(..., description="The unique identifier of the user"),
    lat: float = Query(None, description="Current latitude"),
    lon: float = Query(None, description="Current longitude"),
    recc_engine: SmartShoppingAssistant = Depends(get_assistant),
    loc_service: BusinessLocationService = Depends(get_location_service),
):
    """
    Populates the main dashboard with contextual info and high-priority recommendations.
    Returns low_stock_items so the app can show a local notification (no push needed).
    """
    priorities = recc_engine.prioritize_needs(user_id)

    # Compute low-stock items for local notifications (only if user has setting on)
    low_stock_items: List[str] = []
    _ensure_settings_table()
    settings_obj = _get_settings_from_db(user_id)
    if settings_obj and settings_obj.low_stock_warnings:
        inv = assistant.get_user_inventory(user_id)
        low_stock_items = [name for name, data in inv.items() if float(data.get("stock", 1)) < LOW_STOCK_THRESHOLD]

    context_str = "At home"
    nearest_store = None
    if lat is not None and lon is not None:
        print(f"Home dashboard: using device location lat={lat}, lon={lon}")
        stores = loc_service.get_nearby_businesses(lat, lon, radius=8000)
        if stores:
            nearest_store = stores[0]
            sname = nearest_store.get("name") or "Store"
            dist = nearest_store.get("distance_mi")
            if dist is not None:
                context_str = f"Near {sname} • {float(dist):.1f} mi"
            else:
                context_str = f"Near {sname}"
        else:
            print("Home dashboard: no stores found for this location (Overpass may have returned empty or failed)")
            context_str = "No Trader Joe's found nearby"
    else:
        print("Home dashboard: no lat/lon provided — request location permission on device and ensure API is called with ?lat=...&lon=...")

    results = []
    for p in priorities:
        # Only show high/medium priority on home screen
        if p["urgency_score"] > 0.4:
            products = recc_engine.get_products_for_need(p["query"])
            results.append(
                RecommendationItem(
                    item=p["query"],
                    urgency=round(p["urgency_score"], 2),
                    reason=p["reason"],
                    suggested_products=[ProductSuggestion(**prod) for prod in products],
                    nearest_store_name=nearest_store["name"] if nearest_store else None,
                    nearest_store_address=nearest_store.get("address") if nearest_store else None,
                    nearest_store_distance_mi=nearest_store.get("distance_mi") if nearest_store else None,
                )
            )

    return RecommendationResponse(
        user_id=user_id,
        context=context_str,
        recommendations=results,
        low_stock_items=low_stock_items,
    )


# --- INVENTORY ---
@app.get(
    "/api/v1/users/{user_id}/inventory",
    response_model=List[InventoryItem],
    tags=["Inventory"],
)
def get_user_inventory(
    user_id: str = Path(...),
    recc_engine: SmartShoppingAssistant = Depends(get_assistant),
):
    """
    Retrieves the user's current inventory.
    """
    inv_data = recc_engine.get_user_inventory(user_id)
    result = []
    for item_name, data in inv_data.items():
        result.append(
            InventoryItem(
                item_name=item_name,
                stock_percentage=data["stock"] * 100,
                last_bought_days_ago=data["last_buy"],
                category="General",  # You can extend the DB to track categories
            )
        )
    return result


@app.post("/api/v1/users/{user_id}/inventory/restock", tags=["Inventory"])
def restock_inventory_item(
    user_id: str = Path(...),
    item_name: str = Query(...),
    recc_engine: SmartShoppingAssistant = Depends(get_assistant),
):
    """
    Marks an item as restocked (100% stock, 0 days ago). Persists to the database.
    """
    ok = recc_engine.restock_item(user_id, item_name)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to update inventory.")
    return {"status": "success", "message": f"{item_name} restocked for {user_id}."}


@app.patch(
    "/api/v1/users/{user_id}/inventory",
    tags=["Inventory"],
)
def update_inventory_item(
    user_id: str = Path(...),
    body: InventoryUpdate = ...,
    recc_engine: SmartShoppingAssistant = Depends(get_assistant),
):
    """
    Set an item's stock (0.0–1.0) and days since last buy. Creates the item if it doesn't exist.
    Use this to add items with custom level or to lower stock so they show on Home again.
    """
    ok = recc_engine.set_inventory_item(user_id, body.item_name, body.stock, body.last_buy)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to update inventory.")
    return {"status": "success", "message": f"{body.item_name} updated."}


# --- LOCATION SERVICES ---
@app.get(
    "/api/v1/locations/nearby-trader-joes",
    response_model=NearbyBusinessesResponse,
    tags=["Location Services"],
)
def get_nearby_tj(
    lat: float = Query(..., description="Latitude of user"),
    lon: float = Query(..., description="Longitude of user"),
    radius: int = Query(5000, description="Search radius in meters"),
    loc_service: BusinessLocationService = Depends(get_location_service),
):
    """
    Finds adjacent Trader Joe's stores based on user coordinates.
    """
    try:
        businesses = loc_service.get_nearby_businesses(lat=lat, lon=lon, radius=radius)
        return NearbyBusinessesResponse(
            location={"lat": lat, "lon": lon},
            radius=radius,
            count=len(businesses),
            businesses=[Business(**b) for b in businesses],
        )
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=f"External location API error: {str(e)}"
        )


# --- SETTINGS ---

def _default_settings() -> UserSettings:
    return UserSettings(
        user_name="Alex Student",
        email="alex@example.com",
        preferred_brands=["Trader Joe's", "365"],
        price_sensitivity="Medium",
        location_alerts=True,
        low_stock_warnings=True,
    )


def _ensure_settings_table():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id TEXT PRIMARY KEY,
            user_name TEXT,
            email TEXT,
            preferred_brands TEXT,
            price_sensitivity TEXT,
            location_alerts INTEGER,
            low_stock_warnings INTEGER,
            push_token TEXT,
            last_near_store_push_at REAL,
            last_low_stock_push_at REAL
        )
    """)
    # Migrate existing DBs: add columns if missing
    for col_sql in [
        "ALTER TABLE user_settings ADD COLUMN push_token TEXT",
        "ALTER TABLE user_settings ADD COLUMN last_near_store_push_at REAL",
        "ALTER TABLE user_settings ADD COLUMN last_low_stock_push_at REAL",
    ]:
        try:
            conn.execute(col_sql)
        except Exception:
            pass
    conn.commit()
    conn.close()


def _get_settings_from_db(user_id: str) -> Optional[UserSettings]:
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT user_name, email, preferred_brands, price_sensitivity, location_alerts, low_stock_warnings, push_token FROM user_settings WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return UserSettings(
        user_name=row[0] or "Alex Student",
        email=row[1] or "alex@example.com",
        preferred_brands=json.loads(row[2]) if row[2] else ["Trader Joe's", "365"],
        price_sensitivity=row[3] or "Medium",
        location_alerts=bool(row[4] if row[4] is not None else 1),
        low_stock_warnings=bool(row[5] if row[5] is not None else 1),
        push_token=row[6] if len(row) > 6 else None,
    )


def _save_settings_to_db(user_id: str, s: UserSettings):
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO user_settings (user_id, user_name, email, preferred_brands, price_sensitivity, location_alerts, low_stock_warnings, push_token)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
             user_name=excluded.user_name,
             email=excluded.email,
             preferred_brands=excluded.preferred_brands,
             price_sensitivity=excluded.price_sensitivity,
             location_alerts=excluded.location_alerts,
             low_stock_warnings=excluded.low_stock_warnings,
             push_token=excluded.push_token""",
        (
            user_id,
            s.user_name,
            s.email,
            json.dumps(s.preferred_brands),
            s.price_sensitivity,
            1 if s.location_alerts else 0,
            1 if s.low_stock_warnings else 0,
            s.push_token,
        ),
    )
    conn.commit()
    conn.close()


def _get_settings_row_raw(user_id: str) -> Optional[tuple]:
    """Get settings row including server-only fields (push_token, last_near_store_push_at)."""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT push_token, last_near_store_push_at FROM user_settings WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return row


def _set_last_near_store_push_at(user_id: str):
    import time
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE user_settings SET last_near_store_push_at = ? WHERE user_id = ?",
        (time.time(), user_id),
    )
    conn.commit()
    conn.close()


def _send_expo_push(to_token: str, title: str, body: str) -> bool:
    """Send one push via Expo Push API. Returns True if accepted. Logs ticket/receipt errors."""
    if not to_token or not to_token.strip():
        print("Expo push skipped: empty token")
        return False
    token = to_token.strip()
    try:
        r = requests.post(
            "https://exp.host/--/api/v2/push/send",
            json={"to": token, "title": title, "body": body, "sound": "default"},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=10,
        )
        if r.status_code != 200:
            print(f"Expo push rejected: status={r.status_code} body={r.text[:200]}")
            return False
        data = r.json()
        # Response can be {"data": {"status": "ok", "id": "..."}} or {"data": [{"status": "ok", "id": "..."}]}
        ticket_or_list = data.get("data")
        if isinstance(ticket_or_list, dict):
            ticket_or_list = [ticket_or_list]
        for ticket in (ticket_or_list or []):
            if isinstance(ticket, dict) and ticket.get("status") == "error":
                print(f"Expo push ticket error: {ticket.get('message')} details={ticket.get('details')}")
                return False
        ticket_ids = [t.get("id") for t in (ticket_or_list or []) if isinstance(t, dict) and t.get("id")]
        print(f"Expo push sent: title={title!r} token={token[:20]}... ticket_ids={ticket_ids}")
        # Optionally check receipts after a short delay to see delivery status (e.g. DeviceNotRegistered)
        if ticket_ids:
            _log_expo_receipts_after_delay(ticket_ids)
        return True
    except Exception as e:
        print(f"Expo push send failed: {e}")
        return False


def _log_expo_receipts_after_delay(ticket_ids: list):
    """After 5s, fetch push receipts and log any delivery errors (runs in background)."""
    import threading
    def _fetch():
        time.sleep(5)
        try:
            r = requests.post(
                "https://exp.host/--/api/v2/push/getReceipts",
                json={"ids": ticket_ids},
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=10,
            )
            if r.status_code != 200:
                return
            data = r.json()
            for rid, receipt in (data.get("data") or {}).items():
                if isinstance(receipt, dict) and receipt.get("status") == "error":
                    print(f"Expo push receipt error (delivery failed): {receipt.get('message')} details={receipt.get('details')}")
        except Exception:
            pass
    threading.Thread(target=_fetch, daemon=True).start()


def _set_last_low_stock_push_at(user_id: str):
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE user_settings SET last_low_stock_push_at = ? WHERE user_id = ?",
            (time.time(), user_id),
        )
        conn.commit()
    except Exception:
        pass
    conn.close()


def run_low_stock_pushes():
    """
    Send push notifications to users who have low_stock_warnings on and a push token,
    for items in their inventory with stock below LOW_STOCK_THRESHOLD.
    Throttled to at most once per 4 hours per user.
    """
    import sqlite3
    _ensure_settings_table()
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT user_id, push_token, last_low_stock_push_at FROM user_settings WHERE low_stock_warnings = 1 AND push_token IS NOT NULL AND push_token != ''"
        ).fetchall()
    except Exception as e:
        print(f"Low-stock push: settings query failed ({e}), trying without last_low_stock_push_at")
        rows = conn.execute(
            "SELECT user_id, push_token FROM user_settings WHERE low_stock_warnings = 1 AND push_token IS NOT NULL AND push_token != ''"
        ).fetchall()
        rows = [(r[0], r[1], None) for r in rows]
    conn.close()

    if not rows:
        print("Low-stock push: no users with push_token and low_stock_warnings on")
        return
    print(f"Low-stock push: checking {len(rows)} user(s)")

    for row in rows:
        user_id = row[0]
        push_token = row[1]
        last_at = row[2] if len(row) > 2 else None
        if last_at is not None and (time.time() - last_at) < 4 * 3600:
            print(f"Low-stock push: {user_id} throttled (last sent {int((time.time() - last_at) / 60)}m ago)")
            continue
        inv = assistant.get_user_inventory(user_id)
        low_items = [name for name, data in inv.items() if float(data.get("stock", 1)) < LOW_STOCK_THRESHOLD]
        if not low_items:
            print(f"Low-stock push: {user_id} has no items below {LOW_STOCK_THRESHOLD}")
            continue
        if len(low_items) == 1:
            body = f"'{low_items[0]}' is running low."
        else:
            body = f"Your {', '.join(low_items[:5])}{'…' if len(low_items) > 5 else ''} are running low."
        print(f"Low-stock push: sending to {user_id} for {low_items}")
        if _send_expo_push(push_token, "Low stock", body):
            _set_last_low_stock_push_at(user_id)


@app.get(
    "/api/v1/users/{user_id}/settings", response_model=UserSettings, tags=["Settings"]
)
def get_user_settings(user_id: str = Path(...)):
    """
    Get user settings. Returns stored settings or defaults (and persists defaults on first access).
    """
    _ensure_settings_table()
    settings = _get_settings_from_db(user_id)
    if settings is None:
        settings = _default_settings()
        _save_settings_to_db(user_id, settings)
    return settings


@app.patch(
    "/api/v1/users/{user_id}/settings", response_model=UserSettings, tags=["Settings"]
)
def update_user_settings(
    user_id: str = Path(...),
    body: UserSettingsUpdate = ...,
):
    """
    Update user settings (partial update). Returns full settings after update.
    """
    _ensure_settings_table()
    current = _get_settings_from_db(user_id)
    if current is None:
        current = _default_settings()
        _save_settings_to_db(user_id, current)
    update = body.model_dump(exclude_unset=True)
    new_settings = UserSettings(
        user_name=update.get("user_name", current.user_name),
        email=update.get("email", current.email),
        preferred_brands=update.get("preferred_brands", current.preferred_brands),
        price_sensitivity=update.get("price_sensitivity", current.price_sensitivity),
        location_alerts=update.get("location_alerts", current.location_alerts),
        low_stock_warnings=update.get("low_stock_warnings", current.low_stock_warnings),
        push_token=update.get("push_token", current.push_token),
    )
    _save_settings_to_db(user_id, new_settings)
    return new_settings


@app.post("/internal/send-low-stock-pushes", include_in_schema=False)
def trigger_low_stock_pushes():
    """
    Trigger low-stock push notifications for all users with the setting on.
    Intended for cron (e.g. daily). No auth for now; add if needed.
    """
    run_low_stock_pushes()
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def get_index():
    """
    Root index page serving as a landing page for API documentation.
    (include_in_schema=False hides this specific endpoint from the API docs)
    """
    html_content = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Big Bak API</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    background-color: #f4f4f9;
                    color: #333;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                }
                .container {
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    max-width: 500px;
                    text-align: center;
                }
                h1 { margin-top: 0; color: #2c3e50; }
                p { font-size: 16px; color: #555; margin-bottom: 30px; }
                .btn {
                    display: inline-block;
                    margin: 10px;
                    padding: 12px 24px;
                    color: white;
                    background-color: #007bff;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    transition: background-color 0.2s;
                }
                .btn:hover { background-color: #0056b3; }
                .btn-secondary { background-color: #6c757d; }
                .btn-secondary:hover { background-color: #5a6268; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Big Bak API 🛒</h1>
                <p>Welcome to the backend service for the Big Bak mobile app. The API provides context-aware recommendations and location services.</p>

                <a href="/docs" class="btn">Swagger UI (Interactive Docs)</a>
                <a href="/redoc" class="btn btn-secondary">ReDoc (Static Docs)</a>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
