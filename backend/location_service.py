import requests



class BusinessLocationService:
    """
    Service to find nearby Trader Joe's locations
    using the Overpass API (OpenStreetMap).
    """

    OVERPASS_URL = "https://overpass-api.de/api/interpreter"

    def __init__(self):
        # Default radius in meters (increased since specific stores are less dense)
        self.default_radius = 10000

    def get_nearby_businesses(self, lat, lon, radius=None):
        """
        Finds Trader Joe's near a specific latitude and longitude.

        Args:
            lat (float): Latitude
            lon (float): Longitude
            radius (int): Search radius in meters (default 10000)

        Returns:
            list: List of dictionaries containing store details
        """
        if radius is None:
            radius = self.default_radius

        # Build the Overpass QL query specifically for Trader Joe's (case-insensitive)
        full_query = f"""
        [out:json][timeout:25];
        (
            node["name"~"Trader Joe's",i](around:{radius},{lat},{lon});
            way["name"~"Trader Joe's",i](around:{radius},{lat},{lon});
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
            # Fallback mock store
            return [
                {
                    "name": "Trader Joe's (Mock)",
                    "type": "supermarket",
                    "lat": lat + 0.005,
                    "lon": lon + 0.005,
                    "address": "123 Mockingbird Lane, Irvine",
                    "osm_id": 999999999,
                }
            ]

    def _parse_results(self, elements, user_lat, user_lon):
        """
        Parses raw Overpass JSON elements into a clean list of businesses.
        """
        results = []
        for element in elements:
            lat = element.get("lat") or element.get("center", {}).get("lat")
            lon = element.get("lon") or element.get("center", {}).get("lon")

            tags = element.get("tags", {})
            name = tags.get("name", "Trader Joe's")

            results.append(
                {
                    "name": name,
                    "type": "supermarket",
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
    print(f"Searching for Trader Joe's near {test_lat}, {test_lon}...")

    stores = service.get_nearby_businesses(test_lat, test_lon, radius=10000)

    print(f"Found {len(stores)} locations:")
    for store in stores:
        print(f"- {store['name']}")
        print(f"  Address: {store['address']}")
        print(f"  Coords: {store['lat']}, {store['lon']}")
        print("-" * 20)
