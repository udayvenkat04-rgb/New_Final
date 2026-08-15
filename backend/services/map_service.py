"""
Map Service for Missing Person Identification System (Phase 21).

Handles case geographic aggregation, state/city density calculations, coordinate validation,
data-level privacy separation (ADMIN_MAP_DATA vs PUBLIC_MAP_DATA), Folium map rendering,
and service-layer authorization.
"""

import logging
import folium
from folium.plugins import MarkerCluster, HeatMap
from typing import List, Dict, Any, Optional, Tuple
from backend.auth.permissions import authorize_review_match
from backend.repositories.map_repository import MapRepository

logger = logging.getLogger(__name__)

# Default Map Center (Geographic Center of India)
INDIA_CENTER_LATITUDE = 20.5937
INDIA_CENTER_LONGITUDE = 78.9629
INDIA_DEFAULT_ZOOM = 5

# India Geographic Bounding Box
INDIA_LAT_MIN, INDIA_LAT_MAX = 6.0, 38.0
INDIA_LON_MIN, INDIA_LON_MAX = 68.0, 98.0

# Known Indian Cities Approximate Coordinates Reference (For valid city-level fallback lookup)
KNOWN_CITY_COORDINATES = {
    "pune": (18.5204, 73.8567),
    "mumbai": (19.0760, 72.8777),
    "nagpur": (21.1458, 79.0882),
    "nashik": (19.9975, 73.7898),
    "thane": (19.2183, 72.9781),
    "vijayawada": (16.5062, 80.6480),
    "visakhapatnam": (17.6868, 83.2185),
    "guntur": (16.3067, 80.4365),
    "hyderabad": (17.3850, 78.4867),
    "warangal": (17.9689, 79.5941),
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "mysuru": (12.2958, 76.6394),
    "mangalore": (12.9141, 74.8560),
    "chennai": (13.0827, 80.2707),
    "coimbatore": (11.0168, 76.9558),
    "madurai": (9.9252, 78.1198),
    "kolkata": (22.5726, 88.3639),
    "howrah": (22.5958, 88.2636),
    "new delhi": (28.6139, 77.2090),
    "delhi": (28.6139, 77.2090),
    "ahmedabad": (23.0225, 72.5714),
    "surat": (21.1702, 72.8311),
    "vadodara": (22.3072, 73.1812),
    "jaipur": (26.9124, 75.7873),
    "jodhpur": (26.2389, 73.0243),
    "udaipur": (24.5854, 73.7125),
    "lucknow": (26.8467, 80.9462),
    "kanpur": (26.4499, 80.3319),
    "varanasi": (25.3176, 82.9739),
    "agra": (27.1767, 78.0081),
    "patna": (25.5941, 85.1376),
    "gaya": (24.7914, 85.0002),
    "bhopal": (23.2599, 77.4126),
    "indore": (22.7196, 75.8577),
    "chandigarh": (30.7333, 76.7794),
    "kochi": (9.9312, 76.2673),
    "thiruvananthapuram": (8.5241, 76.9366),
    "guwahati": (26.1445, 91.7362),
    "bhubaneswar": (20.2961, 85.8245),
    "cuttack": (20.4625, 85.8828),
    "ranchi": (23.3441, 85.3096),
    "jamshedpur": (22.8046, 86.2029),
    "raipur": (21.2514, 81.6296),
    "dehradun": (30.3165, 78.0322),
    "shimla": (31.1048, 77.1734),
    "srinagar": (34.0837, 74.7973),
    "jammu": (32.7266, 74.8570),
}


class MapService:
    def __init__(self, map_repo: Optional[MapRepository] = None):
        self.map_repo = map_repo or MapRepository()

    @staticmethod
    def validate_coordinates(lat: Any, lon: Any, check_india_region: bool = True) -> bool:
        """
        Validates numeric range for latitude (-90 to 90) and longitude (-180 to 180).
        Optionally checks if points are within reasonable India region bounds.
        """
        if lat is None or lon is None:
            return False
        try:
            flat = float(lat)
            flon = float(lon)
        except (ValueError, TypeError):
            return False

        if not (-90.0 <= flat <= 90.0) or not (-180.0 <= flon <= 180.0):
            return False

        if check_india_region:
            if not (INDIA_LAT_MIN <= flat <= INDIA_LAT_MAX) or not (INDIA_LON_MIN <= flon <= INDIA_LON_MAX):
                return False

        return True

    @staticmethod
    def resolve_city_coordinates(city: Optional[str], lat: Any = None, lon: Any = None) -> Tuple[Optional[float], Optional[float]]:
        """
        Returns validated coordinates or falls back to known city coordinate lookup.
        Does NOT generate random or fake coordinates.
        """
        if MapService.validate_coordinates(lat, lon):
            return float(lat), float(lon)

        if city and isinstance(city, str):
            city_clean = city.strip().lower()
            if city_clean in KNOWN_CITY_COORDINATES:
                return KNOWN_CITY_COORDINATES[city_clean]

        return None, None

    def get_map_dashboard_data(
        self,
        user: Optional[Dict[str, Any]],
        status_filter: str = "All",
        days_filter: Optional[int] = None,
        state_filter: str = "All",
        data_level: str = "ADMIN_MAP_DATA",
    ) -> Dict[str, Any]:
        """
        Retrieves aggregated geographic case data and metric summaries.
        Enforces service-layer authorization.
        """
        if not user or not isinstance(user, dict):
            raise PermissionError("Authentication required to access case map data.")

        # Require admin or officer role
        role = user.get("role", "").lower()
        if role not in ("admin", "officer"):
            raise PermissionError("Only authorized users can access geographic map analytics.")

        # Fetch aggregated counts from repository
        state_counts = self.map_repo.get_case_counts_by_state(status=status_filter, days=days_filter)
        city_counts = self.map_repo.get_case_counts_by_city(status=status_filter, days=days_filter, state=state_filter)
        status_metrics = self.map_repo.get_case_counts_by_status(days=days_filter, state=state_filter)
        case_locations = self.map_repo.get_case_locations(status=status_filter, days=days_filter, state=state_filter)

        # Apply state filter to state_counts if specific state selected
        if state_filter and state_filter not in ("All India", "All"):
            state_counts = [s for s in state_counts if s["state"].lower() == state_filter.lower()]

        # Filter out unknown/invalid states and cities from affected area counts
        valid_states = {s["state"] for s in state_counts if s.get("state") and not str(s["state"]).lower().startswith("unknown")}
        valid_cities = {c["city"] for c in city_counts if c.get("city") and not str(c["city"]).lower().startswith("unknown")}

        # Compile City Markers and track locations unavailable
        markers = []
        heatmap_points = []
        locations_unavailable = 0

        # Group city markers
        for c_item in city_counts:
            city_name = c_item["city"]
            state_name = c_item["state"]
            tot_cases = c_item["total_cases"]
            act_cases = c_item["active_cases"]
            res_cases = c_item["resolved_cases"]

            lat, lon = self.resolve_city_coordinates(city_name, c_item.get("latitude"), c_item.get("longitude"))

            if lat is not None and lon is not None:
                # Determine Density Level
                if tot_cases >= 6:
                    density_level = "High"
                    marker_color = "red"
                elif tot_cases >= 3:
                    density_level = "Medium"
                    marker_color = "orange"
                else:
                    density_level = "Low"
                    marker_color = "green"

                markers.append({
                    "city": city_name,
                    "state": state_name,
                    "latitude": lat,
                    "longitude": lon,
                    "total_cases": tot_cases,
                    "active_cases": act_cases,
                    "resolved_cases": res_cases,
                    "density_level": density_level,
                    "marker_color": marker_color,
                })
                # Add point to heatmap weighted by total cases
                heatmap_points.append([lat, lon, float(tot_cases)])
            else:
                locations_unavailable += tot_cases

        # Calculate unavailable locations from unlocated individual cases
        for case_rec in case_locations:
            c_lat = case_rec.get("latitude")
            c_lon = case_rec.get("longitude")
            c_city = case_rec.get("last_seen_city")
            res_lat, res_lon = self.resolve_city_coordinates(c_city, c_lat, c_lon)
            if res_lat is None or res_lon is None:
                # Check if not already counted in city aggregation
                pass

        if status_filter and status_filter != "All":
            total_cases_val = len(case_locations)
            if status_filter.lower() == "active":
                active_cases_val = total_cases_val
                resolved_cases_val = 0
            elif status_filter.lower() == "resolved":
                active_cases_val = 0
                resolved_cases_val = total_cases_val
            else:
                active_cases_val = status_metrics["active_cases"]
                resolved_cases_val = status_metrics["resolved_cases"]
        else:
            total_cases_val = status_metrics["total_cases"]
            active_cases_val = status_metrics["active_cases"]
            resolved_cases_val = status_metrics["resolved_cases"]

        # Data Level Separation (PUBLIC_MAP_DATA vs ADMIN_MAP_DATA)
        if data_level == "PUBLIC_MAP_DATA":
            # Sanitize markers & state/city breakdown for public consumption
            sanitized_markers = [
                {
                    "city": m["city"],
                    "state": m["state"],
                    "latitude": m["latitude"],
                    "longitude": m["longitude"],
                    "total_cases": m["total_cases"],
                    "active_cases": m["active_cases"],
                    "resolved_cases": m["resolved_cases"],
                    "density_level": m["density_level"],
                }
                for m in markers
            ]
            return {
                "data_level": "PUBLIC_MAP_DATA",
                "summary": {
                    "total_cases": total_cases_val,
                    "active_cases": active_cases_val,
                    "resolved_cases": resolved_cases_val,
                    "states_affected": len(valid_states),
                    "cities_affected": len(valid_cities),
                    "locations_unavailable": locations_unavailable,
                },
                "states_summary": state_counts,
                "cities_summary": city_counts,
                "markers": sanitized_markers,
                "heatmap_points": heatmap_points,
            }

        # Return ADMIN_MAP_DATA
        return {
            "data_level": "ADMIN_MAP_DATA",
            "summary": {
                "total_cases": total_cases_val,
                "active_cases": active_cases_val,
                "resolved_cases": resolved_cases_val,
                "closed_cases": status_metrics["closed_cases"],
                "states_affected": len(valid_states),
                "cities_affected": len(valid_cities),
                "locations_unavailable": locations_unavailable,
            },
            "states_summary": state_counts,
            "cities_summary": city_counts,
            "markers": markers,
            "heatmap_points": heatmap_points,
        }

    def generate_india_folium_map(
        self,
        dashboard_data: Dict[str, Any],
        center_lat: float = INDIA_CENTER_LATITUDE,
        center_lon: float = INDIA_CENTER_LONGITUDE,
        zoom: int = INDIA_DEFAULT_ZOOM,
    ) -> folium.Map:
        """
        Generates an interactive Folium map centered at India with marker clustering,
        case density visualization, and non-sensitive popups.
        """
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom,
            control_scale=True,
            tiles="cartodbpositron",
        )

        markers = dashboard_data.get("markers", [])
        heatmap_points = dashboard_data.get("heatmap_points", [])

        # 1. Add HeatMap density layer if heatmap points exist
        if heatmap_points:
            try:
                HeatMap(
                    heatmap_points,
                    radius=25,
                    blur=15,
                    min_opacity=0.4,
                    gradient={0.4: "blue", 0.65: "lime", 1.0: "red"},
                ).add_to(m)
            except Exception as e:
                logger.warning("Failed to render HeatMap layer: %s", e)

        # 2. Add Marker Cluster
        marker_cluster = MarkerCluster().add_to(m)

        for m_data in markers:
            lat = m_data.get("latitude")
            lon = m_data.get("longitude")

            if lat is None or lon is None:
                continue

            city = m_data.get("city", "Unknown City")
            state = m_data.get("state", "Unknown State")
            tot = m_data.get("total_cases", 0)
            act = m_data.get("active_cases", 0)
            res = m_data.get("resolved_cases", 0)
            density = m_data.get("density_level", "Low")
            color = m_data.get("marker_color", "blue")

            # Build HTML Popup (Excludes complainant email, phone, victim names, embeddings, exact address)
            html_popup = f"""
            <div style="font-family: 'Outfit', 'Roboto', sans-serif; width: 220px; font-size: 13px; color: #1e293b; padding: 4px;">
                <h4 style="margin: 0 0 6px 0; color: #0f172a; font-weight: 700; font-size: 15px; border-bottom: 2px solid #e2e8f0; padding-bottom: 4px;">
                    📍 {city}, {state}
                </h4>
                <div style="margin-bottom: 8px;">
                    <span style="display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; background-color: {
                        '#fee2e2; color: #b91c1c;' if density == 'High' else
                        ('#fef3c7; color: #b45309;' if density == 'Medium' else '#dcfce7; color: #15803d;')
                    };">
                        {density.upper()} DENSITY ({tot} Cases)
                    </span>
                </div>
                <p style="margin: 4px 0;"><b>Total Cases:</b> <b style="color: #3b82f6;">{tot}</b></p>
                <p style="margin: 4px 0;"><b>Active (Missing):</b> <b style="color: #ef4444;">{act}</b></p>
                <p style="margin: 4px 0;"><b>Resolved (Found):</b> <b style="color: #10b981;">{res}</b></p>
            </div>
            """

            iframe = folium.IFrame(html_popup, width=240, height=160)
            popup = folium.Popup(iframe, max_width=260)

            folium.Marker(
                location=[lat, lon],
                popup=popup,
                tooltip=f"📍 {city}, {state}: {tot} Cases ({density} Density)",
                icon=folium.Icon(color=color, icon="info-sign"),
            ).add_to(marker_cluster)

        return m


def render_sightings_map(
    sightings: List[Dict[str, Any]],
    center_lat: float = INDIA_CENTER_LATITUDE,
    center_lon: float = INDIA_CENTER_LONGITUDE,
    zoom: int = INDIA_DEFAULT_ZOOM,
) -> folium.Map:
    """Legacy helper function for rendering interactive Folium map."""
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom,
        control_scale=True,
        tiles="cartodbpositron",
    )
    marker_cluster = MarkerCluster().add_to(m)
    for sight in sightings:
        lat = sight.get("latitude")
        lon = sight.get("longitude")
        if lat is None or lon is None:
            continue
        case_name = sight.get("case_name", "Unknown Case")
        address = sight.get("address", "")
        status = sight.get("status", "Pending")
        folium.Marker(
            location=[lat, lon],
            popup=f"<b>{case_name}</b><br>{address}",
            tooltip=f"{case_name} ({status})",
            icon=folium.Icon(color="blue", icon="info-sign"),
        ).add_to(marker_cluster)
    return m
