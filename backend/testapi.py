import pytest
from fastapi.testclient import TestClient
from main import app  # Imports your FastAPI app

# Initialize the test client
client = TestClient(app)

def test_health_check():
    """Test if the API is up and running."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "Big Bak API"}

def test_nearby_trader_joes():
    """Test the location service encapsulation using UCI coordinates."""
    # Act: Send a request to the endpoint
    response = client.get(
        "/api/v1/locations/nearby-trader-joes",
        params={"lat": 33.6405, "lon": -117.8443, "radius": 10000}
    )
    
    # Assert: Check status and payload structure
    assert response.status_code == 200
    data = response.json()
    
    assert "location" in data
    assert "businesses" in data
    assert isinstance(data["businesses"], list)
    
    # If the Overpass API finds stores, verify they are formatted correctly
    if data["count"] > 0:
        first_store = data["businesses"][0]
        assert "Trader Joe's" in first_store["name"]
        assert "lat" in first_store
        assert "lon" in first_store

def test_get_user_inventory():
    """Test that the inventory endpoint returns a list for a mock user."""
    # Using a dummy user_id "test_user"
    response = client.get("/api/v1/users/test_user/inventory")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # If the user has items, check the schema matches our InventoryItem model
    if len(data) > 0:
        first_item = data[0]
        assert "item_name" in first_item
        assert "stock_percentage" in first_item
        assert "last_bought_days_ago" in first_item
    else:
        print("Nothing found")

def test_missing_parameters_error():
    """Test that FastAPI automatically handles missing required parameters."""
    # Missing 'lon' parameter
    response = client.get("/api/v1/locations/nearby-trader-joes?lat=33.6405")
    
    # FastAPI should automatically return a 422 Unprocessable Entity
    assert response.status_code == 422
    assert "detail" in response.json()