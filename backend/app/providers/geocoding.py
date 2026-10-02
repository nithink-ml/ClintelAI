"""Map and Geocoding Abstraction Layer for ClintelAI Provider Discovery."""

from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.logging import logger
from app.providers.schemas import GeocodeResult


class GeoProvider(ABC):
    """Abstract interface for location geocoding and reverse geocoding."""

    @abstractmethod
    async def geocode(self, query: str) -> GeocodeResult | None:
        """Translates an address or place name into geographic coordinates."""

    @abstractmethod
    async def reverse_geocode(self, latitude: float, longitude: float) -> GeocodeResult | None:
        """Translates latitude and longitude coordinates into a human-readable place description."""


class LocalPrecomputedGeoProvider(GeoProvider):
    """Deterministic, zero-latency local gazetteer for Indian healthcare regions and localities."""

    LOCAL_GAZETTEER: dict[str, dict[str, Any]] = {
        # Chennai & Localities
        "chennai": {
            "display_name": "Chennai, Tamil Nadu, India",
            "lat": 13.0827,
            "lon": 80.2707,
            "city": "Chennai",
            "state": "Tamil Nadu",
        },
        "thousand lights": {
            "display_name": "Thousand Lights, Chennai, Tamil Nadu, 600006, India",
            "lat": 13.0604,
            "lon": 80.2496,
            "city": "Chennai",
            "state": "Tamil Nadu",
        },
        "mylapore": {
            "display_name": "Mylapore, Chennai, Tamil Nadu, 600004, India",
            "lat": 13.0334,
            "lon": 80.2678,
            "city": "Chennai",
            "state": "Tamil Nadu",
        },
        "gopalapuram": {
            "display_name": "Gopalapuram, Chennai, Tamil Nadu, 600086, India",
            "lat": 13.0489,
            "lon": 80.2528,
            "city": "Chennai",
            "state": "Tamil Nadu",
        },
        "triplicane": {
            "display_name": "Triplicane, Chennai, Tamil Nadu, 600005, India",
            "lat": 13.0569,
            "lon": 80.2742,
            "city": "Chennai",
            "state": "Tamil Nadu",
        },
        "anna nagar": {
            "display_name": "Anna Nagar, Chennai, Tamil Nadu, 600040, India",
            "lat": 13.0850,
            "lon": 80.2100,
            "city": "Chennai",
            "state": "Tamil Nadu",
        },
        "t nagar": {
            "display_name": "T. Nagar, Chennai, Tamil Nadu, 600017, India",
            "lat": 13.0418,
            "lon": 80.2341,
            "city": "Chennai",
            "state": "Tamil Nadu",
        },

        # Bengaluru & Localities
        "bengaluru": {
            "display_name": "Bengaluru, Karnataka, India",
            "lat": 12.9716,
            "lon": 77.5946,
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        "bangalore": {
            "display_name": "Bengaluru, Karnataka, India",
            "lat": 12.9716,
            "lon": 77.5946,
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        "indiranagar": {
            "display_name": "Indiranagar, Bengaluru, Karnataka, 560038, India",
            "lat": 12.9784,
            "lon": 77.6408,
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        "bellandur": {
            "display_name": "Bellandur, Bengaluru, Karnataka, 560103, India",
            "lat": 12.9279,
            "lon": 77.6771,
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        "koramangala": {
            "display_name": "Koramangala, Bengaluru, Karnataka, 560034, India",
            "lat": 12.9352,
            "lon": 77.6245,
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        "whitefield": {
            "display_name": "Whitefield, Bengaluru, Karnataka, 560066, India",
            "lat": 12.9698,
            "lon": 77.7500,
            "city": "Bengaluru",
            "state": "Karnataka",
        },

        # Kochi & Localities
        "kochi": {
            "display_name": "Kochi, Kerala, India",
            "lat": 9.9312,
            "lon": 76.2673,
            "city": "Kochi",
            "state": "Kerala",
        },
        "ernakulam": {
            "display_name": "Ernakulam, Kochi, Kerala, 682016, India",
            "lat": 9.9816,
            "lon": 76.2999,
            "city": "Kochi",
            "state": "Kerala",
        },
        "cheranallur": {
            "display_name": "Cheranallur, Kochi, Kerala, 682027, India",
            "lat": 10.0526,
            "lon": 76.2691,
            "city": "Kochi",
            "state": "Kerala",
        },

        # Hyderabad & Localities
        "hyderabad": {
            "display_name": "Hyderabad, Telangana, India",
            "lat": 17.3850,
            "lon": 78.4867,
            "city": "Hyderabad",
            "state": "Telangana",
        },
        "banjara hills": {
            "display_name": "Banjara Hills, Hyderabad, Telangana, 500034, India",
            "lat": 17.4156,
            "lon": 78.4487,
            "city": "Hyderabad",
            "state": "Telangana",
        },
        "charminar": {
            "display_name": "Charminar, Hyderabad, Telangana, 500002, India",
            "lat": 17.3616,
            "lon": 78.4747,
            "city": "Hyderabad",
            "state": "Telangana",
        },

        # New Delhi & Localities
        "delhi": {
            "display_name": "New Delhi, Delhi, India",
            "lat": 28.6139,
            "lon": 77.2090,
            "city": "New Delhi",
            "state": "Delhi",
        },
        "new delhi": {
            "display_name": "New Delhi, Delhi, India",
            "lat": 28.6139,
            "lon": 77.2090,
            "city": "New Delhi",
            "state": "Delhi",
        },
        "ansari nagar": {
            "display_name": "Ansari Nagar, New Delhi, Delhi, 110029, India",
            "lat": 28.5672,
            "lon": 77.2100,
            "city": "New Delhi",
            "state": "Delhi",
        },

        # Mumbai & Localities
        "mumbai": {
            "display_name": "Mumbai, Maharashtra, India",
            "lat": 19.0760,
            "lon": 72.8777,
            "city": "Mumbai",
            "state": "Maharashtra",
        },
        "parel": {
            "display_name": "Parel, Mumbai, Maharashtra, 400012, India",
            "lat": 19.0028,
            "lon": 72.8427,
            "city": "Mumbai",
            "state": "Maharashtra",
        },
        "bandra": {
            "display_name": "Bandra West, Mumbai, Maharashtra, 400050, India",
            "lat": 19.0560,
            "lon": 72.8340,
            "city": "Mumbai",
            "state": "Maharashtra",
        },
        "bandra west": {
            "display_name": "Bandra West, Mumbai, Maharashtra, 400050, India",
            "lat": 19.0560,
            "lon": 72.8340,
            "city": "Mumbai",
            "state": "Maharashtra",
        },
    }

    async def geocode(self, query: str) -> GeocodeResult | None:
        q_norm = query.lower().strip()
        # Direct lookup or substring lookup
        for key, val in self.LOCAL_GAZETTEER.items():
            if key in q_norm or q_norm in key:
                return GeocodeResult(
                    query=query,
                    display_name=val["display_name"],
                    latitude=val["lat"],
                    longitude=val["lon"],
                    city=val["city"],
                    state=val["state"],
                    country="India",
                    provider="LocalGazetteer",
                    attribution="ClintelAI Internal Precomputed Gazetteer",
                )
        return None

    async def reverse_geocode(self, latitude: float, longitude: float) -> GeocodeResult | None:
        # Find nearest known locality
        best_match = None
        min_dist_sq = float("inf")
        for val in self.LOCAL_GAZETTEER.values():
            d2 = (val["lat"] - latitude) ** 2 + (val["lon"] - longitude) ** 2
            if d2 < min_dist_sq:
                min_dist_sq = d2
                best_match = val

        # If within ~15 km (approx 0.15 deg)
        if best_match and min_dist_sq < 0.02:
            return GeocodeResult(
                query=f"{latitude},{longitude}",
                display_name=best_match["display_name"],
                latitude=best_match["lat"],
                longitude=best_match["lon"],
                city=best_match["city"],
                state=best_match["state"],
                country="India",
                provider="LocalGazetteer",
                attribution="ClintelAI Internal Precomputed Gazetteer",
            )
        return None


class NominatimGeoProvider(GeoProvider):
    """OpenStreetMap Nominatim Geocoding provider with rate limiting and timeout guards."""

    NOMINATIM_URL = "https://nominatim.openstreetmap.org"
    USER_AGENT = "ClintelAI-Healthcare-Platform/0.1.0 (https://clintelai.local)"

    async def geocode(self, query: str) -> GeocodeResult | None:
        params = {
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": 1,
            "countrycodes": "in",
        }
        headers = {"User-Agent": self.USER_AGENT}
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.NOMINATIM_URL}/search", params=params, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    if data and len(data) > 0:
                        first = data[0]
                        addr = first.get("address", {})
                        city = addr.get("city") or addr.get("town") or addr.get("suburb")
                        state = addr.get("state")
                        return GeocodeResult(
                            query=query,
                            display_name=first.get("display_name", query),
                            latitude=float(first["lat"]),
                            longitude=float(first["lon"]),
                            city=city,
                            state=state,
                            country=addr.get("country", "India"),
                            provider="OpenStreetMap Nominatim",
                            attribution="Data © OpenStreetMap contributors, ODbL 1.0",
                        )
        except Exception as e:
            logger.warning(f"Nominatim geocode request failed: {e}. Falling back to local gazetteer.")
        return None

    async def reverse_geocode(self, latitude: float, longitude: float) -> GeocodeResult | None:
        params = {
            "lat": latitude,
            "lon": longitude,
            "format": "jsonv2",
            "addressdetails": 1,
        }
        headers = {"User-Agent": self.USER_AGENT}
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.NOMINATIM_URL}/reverse", params=params, headers=headers)
                if res.status_code == 200:
                    first = res.json()
                    addr = first.get("address", {})
                    city = addr.get("city") or addr.get("town") or addr.get("suburb")
                    state = addr.get("state")
                    return GeocodeResult(
                        query=f"{latitude},{longitude}",
                        display_name=first.get("display_name", f"{latitude}, {longitude}"),
                        latitude=latitude,
                        longitude=longitude,
                        city=city,
                        state=state,
                        country=addr.get("country", "India"),
                        provider="OpenStreetMap Nominatim",
                        attribution="Data © OpenStreetMap contributors, ODbL 1.0",
                    )
        except Exception as e:
            logger.warning(f"Nominatim reverse geocode request failed: {e}.")
        return None


class CompositeGeoProvider(GeoProvider):
    """Primary composite geocoding engine prioritizing fast local gazetteer before external networks."""

    def __init__(self, allow_network: bool = False):
        self.local = LocalPrecomputedGeoProvider()
        self.external = NominatimGeoProvider()
        self.allow_network = allow_network

    async def geocode(self, query: str) -> GeocodeResult | None:
        # 1. Always evaluate local precomputed gazetteer first
        local_res = await self.local.geocode(query)
        if local_res:
            return local_res

        # 2. Fall back to external Nominatim if network allowed
        if self.allow_network:
            ext_res = await self.external.geocode(query)
            if ext_res:
                return ext_res

        return None

    async def reverse_geocode(self, latitude: float, longitude: float) -> GeocodeResult | None:
        local_res = await self.local.reverse_geocode(latitude, longitude)
        if local_res:
            return local_res

        if self.allow_network:
            return await self.external.reverse_geocode(latitude, longitude)

        return None
