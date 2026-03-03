import time

import requests


class BusinessLocationService:
    """
    Service to find nearby businesses (grocery stores, pharmacies, etc.)
    using the Overpass API (OpenStreetMap).
    """

    OVERPASS_URL = "https://overpass-api.de/api/interpreter"

    def __init__(self):
        # Default radius in meters
        self.default_radius = 2000
        # Map our internal categories to OpenStreetMap tags
        self.category_map = {
            "grocery": ["shop=supermarket", "shop=convenience", "shop=grocery"],
            "pharmacy": ["amenity=pharmacy"],
            "bakery": ["shop=bakery"],
            "department_store": ["shop=department_store"],
            "mall": ["shop=mall"],
        }

    def get_nearby_businesses(self, lat, lon, radius=None, categories=None):
        """
        Finds businesses near a specific latitude and longitude.

        Args:
            lat (float): Latitude
            lon (float): Longitude
            radius (int): Search radius in meters (default 2000)
            categories (list): List of internal category keys (e.g., ['grocery'])

        Returns:
            list: List of dictionaries containing business details
        """
        if radius is None:
            radius = self.default_radius

        if categories is None:
            categories = list(self.category_map.keys())

        # Build the Overpass QL query
        # We look for nodes and ways (areas) that match our tags
        query_parts = []
        for cat in categories:
            tags = self.category_map.get(cat, [])
            for tag in tags:
                query_parts.append(f"node[{tag}](around:{radius},{lat},{lon});")
                query_parts.append(f"way[{tag}](around:{radius},{lat},{lon});")

        full_query = f"""
        [out:json][timeout:25];
        (
            {" ".join(query_parts)}
        );
        out center;
        """

        try:
            response = requests.post(
                self.OVERPASS_URL, data={"data": full_query}, timeout=10
            )
            response.raise_for_status()
            data = response.json()

            return self._parse_results(data.get("elements", []), lat, lon)
        except Exception as e:
            print(f"Error fetching data from Overpass: {e}. Using mock location data.")
            # Fallback mock store so your app doesn't break during testing
            return [
                {
                    "name": "Mock Trader Joe's (Fallback)",
                    "type": "supermarket",
                    "lat": lat + 0.005,  # Slightly offset from user
                    "lon": lon + 0.005,
                    "address": "123 Mockingbird Lane",
                    "osm_id": 999999999,
                }
            ]

    def _parse_results(self, elements, user_lat, user_lon):
        """
        Parses raw Overpass JSON elements into a clean list of businesses.
        """
        results = []
        for element in elements:
            # Overpass 'way' elements with 'out center' provide a 'center' lat/lon
            # 'node' elements provide 'lat'/'lon' directly
            lat = element.get("lat") or element.get("center", {}).get("lat")
            lon = element.get("lon") or element.get("center", {}).get("lon")

            tags = element.get("tags", {})
            name = tags.get("name", "Unknown Business")

            # Determine the type based on tags
            business_type = "store"
            if "shop" in tags:
                business_type = tags["shop"]
            elif "amenity" in tags:
                business_type = tags["amenity"]

            results.append(
                {
                    "name": name,
                    "type": business_type,
                    "lat": lat,
                    "lon": lon,
                    "address": self._format_address(tags),
                    "osm_id": element.get("id"),
                }
            )

        return results

    def _format_address(self, tags):
        """Extracts and formats address from OSM tags if available."""
        street = tags.get("addr:street", "")
        house_number = tags.get("addr:housenumber", "")
        city = tags.get("addr:city", "")

        if street or house_number:
            return f"{house_number} {street}, {city}".strip(", ")
        return "Address unavailable"


# --- DEMO ---
if __name__ == "__main__":
    # Example: UCI Campus (approx)
    test_lat = 33.6405
    test_lon = -117.8443

    service = BusinessLocationService()
    print(f"Searching for grocery stores near {test_lat}, {test_lon}...")

    stores = service.get_nearby_businesses(
        test_lat, test_lon, radius=3000, categories=["grocery"]
    )

    print(f"Found {len(stores)} locations:")
    for store in stores[:5]:  # Show first 5
        print(f"- {store['name']} ({store['type']})")
        print(f"  Address: {store['address']}")
        print(f"  Coords: {store['lat']}, {store['lon']}")
        print("-" * 20)
