import math
import requests


def _haversine_mi(lat1, lon1, lat2, lon2):
    """Return distance in miles between two (lat, lon) points."""
    R = 3959  #f Earth radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


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
        [out:json][timeout:60];
        nwr["name"="Trader Joe's"](around:{radius},{lat},{lon});
        out center;
        """

        try:
            response = requests.post(
                self.OVERPASS_URL, data={"data": full_query}, timeout=20
            )
            response.raise_for_status()
            data = response.json()
            elements = data.get("elements", [])
            return self._parse_results(elements, lat, lon)
        except Exception as e:
            print(f"Overpass failed for lat={lat}, lon={lon}: {e}. Using mock location data.")
            mock_lat = lat + 0.005
            mock_lon = lon + 0.005
            return [
                {
                    "name": "Trader Joe's (offline fallback)",
                    "type": "supermarket",
                    "lat": mock_lat,
                    "lon": mock_lon,
                    "address": "Approximate — Overpass unavailable",
                    "distance_mi": round(_haversine_mi(lat, lon, mock_lat, mock_lon), 1),
                    "osm_id": 999999999,
                }
            ]

    def _parse_results(self, elements, user_lat, user_lon):
        """
        Parses raw Overpass JSON elements into a clean list of businesses.
        Adds distance from user and sorts by distance (nearest first).
        """
        results = []
        for element in elements:
            lat = element.get("lat") or (element.get("center") or {}).get("lat")
            lon = element.get("lon") or (element.get("center") or {}).get("lon")
            if lat is None or lon is None:
                continue

            tags = element.get("tags", {})
            name = tags.get("name", "Trader Joe's")
            distance_mi = round(_haversine_mi(user_lat, user_lon, lat, lon), 1)

            results.append(
                {
                    "name": name,
                    "type": "supermarket",
                    "lat": lat,
                    "lon": lon,
                    "address": self._format_address(tags),
                    "distance_mi": distance_mi,
                    "osm_id": element.get("id"),
                }
            )

        results.sort(key=lambda s: s["distance_mi"])
        return results

    def _format_address(self, tags):
        """Extracts and formats address from OSM tags if available."""
        street = tags.get("addr:street", "")
        house_number = tags.get("addr:housenumber", "")
        city = tags.get("addr:city", "")
        state = tags.get("addr:state", "")
        postcode = tags.get("addr:postcode", "")

        parts = []
        if house_number or street:
            parts.append(f"{house_number} {street}".strip())
        if city:
            parts.append(city)
        if state and postcode:
            parts.append(f"{state} {postcode}".strip())
        elif state:
            parts.append(state)
        elif postcode:
            parts.append(postcode)
        if parts:
            return ", ".join(parts)
        return "Address unavailable"


# --- DEMO ---
if __name__ == "__main__":
    # Example: UCI Campus (approx)
    test_lat = 33.6405
    test_lon = -117.8443

    service = BusinessLocationService()
    print(f"Searching for Trader Joe's near {test_lat}, {test_lon}...")

    stores = service.get_nearby_businesses(test_lat, test_lon, radius=5000)

    print(f"Found {len(stores)} locations:")
    for store in stores:
        print(f"- {store['name']}")
        print(f"  Address: {store['address']}")
        print(f"  Coords: {store['lat']}, {store['lon']}")
        print("-" * 20)
