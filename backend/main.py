import os
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from location_service import BusinessLocationService
from pydantic import BaseModel, Field

# Import existing logic
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


class RecommendationResponse(BaseModel):
    user_id: str
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


class ContextualAlertResponse(BaseModel):
    alert: bool
    message: str
    store: Optional[Business] = None
    item: Optional[dict] = None


# ==========================================
# 2. APP INITIALIZATION & DEPENDENCIES
# ==========================================

app = FastAPI(
    title="Big Bak API",
    version="1.0.0",
    description="Context-aware recommendation system for daily essentials.",
)

# Add CORS middleware if a frontend (like your UI mockup) needs to call this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services (In a real app, these might be injected via Depends)
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


@app.get(
    "/api/v1/users/{user_id}/recommendations",
    response_model=RecommendationResponse,
    tags=["Recommendations"],
)
def get_user_recommendations(
    user_id: str = Path(..., description="The unique identifier of the user"),
    recc_engine: SmartShoppingAssistant = Depends(get_assistant),
):
    """
    Analyzes a specific user's inventory and returns a prioritized list of needed items,
    along with product matches from the database.
    """
    try:
        # In a real app, you would fetch the user's specific inventory from a DB here using user_id.
        # For now, we use the engine's current state.
        # NEW
        priorities = recc_engine.prioritize_needs(user_id)

        results = []
        for p in priorities:
            products = recc_engine.get_products_for_need(p["query"])
            results.append(
                RecommendationItem(
                    item=p["query"],
                    urgency=round(p["urgency_score"], 2),
                    reason=p["reason"],
                    suggested_products=[ProductSuggestion(**prod) for prod in products],
                )
            )

        return RecommendationResponse(user_id=user_id, recommendations=results)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate recommendations: {str(e)}"
        )


@app.get(
    "/api/v1/locations/nearby-businesses",
    response_model=NearbyBusinessesResponse,
    tags=["Location Services"],
)
def get_nearby_businesses(
    lat: float = Query(..., description="Latitude of user"),
    lon: float = Query(..., description="Longitude of user"),
    radius: int = Query(2000, ge=100, le=10000, description="Search radius in meters"),
    categories: Optional[List[str]] = Query(
        None, description="Categories to search (e.g., grocery, pharmacy)"
    ),
    loc_service: BusinessLocationService = Depends(get_location_service),
):
    """
    Finds adjacent businesses based on user coordinates using the Overpass API.
    """
    try:
        businesses = loc_service.get_nearby_businesses(
            lat=lat, lon=lon, radius=radius, categories=categories
        )

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


@app.get(
    "/api/v1/users/{user_id}/alerts/contextual",
    response_model=ContextualAlertResponse,
    tags=["Alerts"],
)
def get_contextual_alert(
    user_id: str = Path(..., description="The unique identifier of the user"),
    lat: float = Query(..., description="Current latitude"),
    lon: float = Query(..., description="Current longitude"),
    urgency_threshold: float = Query(
        0.6, description="Minimum urgency score to trigger an alert"
    ),
    recc_engine: SmartShoppingAssistant = Depends(get_assistant),
    loc_service: BusinessLocationService = Depends(get_location_service),
):
    """
    Evaluates if a user is near a relevant store while having urgent inventory needs.
    """
    # 1. Fetch user inventory and filter by urgency threshold
    # NEW: Just pass the user_id from the URL path directly to the engine!
    priorities = recc_engine.prioritize_needs(user_id)
    urgent_items = [p for p in priorities if p["urgency_score"] > urgency_threshold]

    if not urgent_items:
        return ContextualAlertResponse(alert=False, message="No urgent needs detected.")

    # 2. Check for nearby grocery stores
    try:
        stores = loc_service.get_nearby_businesses(
            lat, lon, radius=1000, categories=["grocery"]
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail="Failed to fetch nearby stores.")

    if stores:
        top_store = stores[0]
        top_need = urgent_items[0]

        return ContextualAlertResponse(
            alert=True,
            message=f"Hey! You're near {top_store['name']}. You are running low on {top_need['query']} ({top_need['reason']}).",
            store=Business(**top_store),
            item=top_need,
        )

    return ContextualAlertResponse(
        alert=False, message="Urgent items found, but no stores nearby."
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
