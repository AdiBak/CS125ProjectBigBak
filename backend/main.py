import os
from typing import List, Optional

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
    """
    priorities = recc_engine.prioritize_needs(user_id)

    context_str = "At home"
    nearest_store = None
    if lat is not None and lon is not None:
        print(f"Home dashboard: using device location lat={lat}, lon={lon}")
        stores = loc_service.get_nearby_businesses(lat, lon, radius=8000)
        if stores:
            nearest_store = stores[0]
            dist = nearest_store.get("distance_mi")
            context_str = f"Near {nearest_store['name']}" + (f" ({dist} mi)" if dist is not None else "")
        else:
            print("Home dashboard: no stores found for this location (Overpass may have returned empty or failed)")
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
        user_id=user_id, context=context_str, recommendations=results
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
@app.get(
    "/api/v1/users/{user_id}/settings", response_model=UserSettings, tags=["Settings"]
)
def get_user_settings(user_id: str = Path(...)):
    """
    Mock endpoint to retrieve user settings.
    """
    return UserSettings(
        user_name="Alex Student",
        email="alex@example.com",
        preferred_brands=["Trader Joe's", "365"],
        price_sensitivity="Medium",
        location_alerts=True,
        low_stock_warnings=True,
    )


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
