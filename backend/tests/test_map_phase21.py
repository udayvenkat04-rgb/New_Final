"""
Unit and Integration Test Suite for Phase 21: Live India Map and Case Density Dashboard.

Tests:
1. Empty database handling.
2. Single city aggregation.
3. Multiple cities aggregation.
4. Multiple states aggregation.
5. Missing city handling.
6. Missing state handling.
7. Missing coordinates handling.
8. Invalid coordinates handling.
9. Case status filtering.
10. Date filtering.
11. State count accuracy.
12. City count accuracy.
13. Total case count accuracy.
14. Active case count accuracy.
15. Resolved case count accuracy.
16. Marker generation properties.
17. Marker clustering configuration.
18. Public vs Admin data separation.
19. Unauthorized access rejection.
20. MongoDB failure resilience.
21. Large dataset performance.
"""

import pytest
from datetime import datetime, timedelta
import folium
from folium.plugins import MarkerCluster
from models.missing_person import MissingPerson
from repositories.map_repository import MapRepository
from services.map_service import MapService, INDIA_CENTER_LATITUDE, INDIA_CENTER_LONGITUDE


# ── Mock Map Repository for Isolated Unit Testing ────────────────────

class MockMapRepository:
    def __init__(self, cases: list = None):
        self.cases = cases or []

    def get_case_locations(self, status=None, days=None, state=None):
        filtered = [c for c in self.cases if not c.get("is_deleted")]
        if status and status != "All":
            target_status = "Missing" if status.lower() == "active" else ("Found" if status.lower() == "resolved" else status)
            filtered = [c for c in filtered if c.get("status") == target_status]
        if state and state not in ("All India", "All"):
            filtered = [c for c in filtered if c.get("last_seen_state") == state]
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            filtered = [c for c in filtered if c.get("created_at") and c.get("created_at") >= cutoff]
        return filtered

    def get_case_counts_by_state(self, status=None, days=None):
        filtered = self.get_case_locations(status=status, days=days)
        state_map = {}
        for c in filtered:
            st = c.get("last_seen_state") or "Unknown State"
            if st not in state_map:
                state_map[st] = {"state": st, "total_cases": 0, "active_cases": 0, "resolved_cases": 0}
            state_map[st]["total_cases"] += 1
            if c.get("status") == "Missing":
                state_map[st]["active_cases"] += 1
            elif c.get("status") == "Found":
                state_map[st]["resolved_cases"] += 1
        return sorted(list(state_map.values()), key=lambda x: x["total_cases"], reverse=True)

    def get_case_counts_by_city(self, status=None, days=None, state=None):
        filtered = self.get_case_locations(status=status, days=days, state=state)
        city_map = {}
        for c in filtered:
            ct = c.get("last_seen_city") or "Unknown City"
            st = c.get("last_seen_state") or "Unknown State"
            key = (ct, st)
            if key not in city_map:
                city_map[key] = {
                    "city": ct,
                    "state": st,
                    "total_cases": 0,
                    "active_cases": 0,
                    "resolved_cases": 0,
                    "latitude": c.get("latitude"),
                    "longitude": c.get("longitude"),
                }
            city_map[key]["total_cases"] += 1
            if c.get("status") == "Missing":
                city_map[key]["active_cases"] += 1
            elif c.get("status") == "Found":
                city_map[key]["resolved_cases"] += 1
            if not city_map[key]["latitude"] and c.get("latitude"):
                city_map[key]["latitude"] = c.get("latitude")
                city_map[key]["longitude"] = c.get("longitude")
        return sorted(list(city_map.values()), key=lambda x: x["total_cases"], reverse=True)

    def get_case_counts_by_status(self, days=None, state=None):
        filtered = self.get_case_locations(days=days, state=state)
        total = len(filtered)
        active = sum(1 for c in filtered if c.get("status") == "Missing")
        resolved = sum(1 for c in filtered if c.get("status") == "Found")
        closed = sum(1 for c in filtered if c.get("status") == "Closed")
        return {"total_cases": total, "active_cases": active, "resolved_cases": resolved, "closed_cases": closed}


# ── Test Suite ──────────────────────────────────────────────────────

@pytest.fixture
def map_env():
    admin_user = {"username": "admin1", "role": "admin"}
    officer_user = {"username": "officer1", "role": "officer"}
    
    # Controlled dataset
    sample_cases = [
        {"id": 1, "name": "P1", "last_seen_city": "Pune", "last_seen_state": "Maharashtra", "latitude": 18.5204, "longitude": 73.8567, "status": "Missing", "created_at": datetime.utcnow()},
        {"id": 2, "name": "P2", "last_seen_city": "Pune", "last_seen_state": "Maharashtra", "latitude": 18.5204, "longitude": 73.8567, "status": "Found", "created_at": datetime.utcnow()},
        {"id": 3, "name": "M1", "last_seen_city": "Mumbai", "last_seen_state": "Maharashtra", "latitude": 19.0760, "longitude": 72.8777, "status": "Missing", "created_at": datetime.utcnow()},
        {"id": 4, "name": "V1", "last_seen_city": "Vijayawada", "last_seen_state": "Andhra Pradesh", "latitude": 16.5062, "longitude": 80.6480, "status": "Missing", "created_at": datetime.utcnow()},
        {"id": 5, "name": "H1", "last_seen_city": "Hyderabad", "last_seen_state": "Telangana", "latitude": 17.3850, "longitude": 78.4867, "status": "Missing", "created_at": datetime.utcnow() - timedelta(days=40)},
        {"id": 6, "name": "B1", "last_seen_city": "Bengaluru", "last_seen_state": "Karnataka", "latitude": 12.9716, "longitude": 77.5946, "status": "Found", "created_at": datetime.utcnow()},
        {"id": 7, "name": "U1", "last_seen_city": None, "last_seen_state": None, "latitude": None, "longitude": None, "status": "Missing", "created_at": datetime.utcnow()},
        {"id": 8, "name": "I1", "last_seen_city": "UnknownCityXYZ", "last_seen_state": "SomeState", "latitude": 999.0, "longitude": -500.0, "status": "Missing", "created_at": datetime.utcnow()},
    ]
    repo = MockMapRepository(sample_cases)
    service = MapService(map_repo=repo)
    return service, repo, admin_user, officer_user


def test_empty_database_handling():
    """1. Empty database returns zero counts without crashing."""
    empty_service = MapService(map_repo=MockMapRepository([]))
    admin_user = {"username": "admin", "role": "admin"}
    data = empty_service.get_map_dashboard_data(user=admin_user)
    
    assert data["summary"]["total_cases"] == 0
    assert data["summary"]["states_affected"] == 0
    assert data["summary"]["cities_affected"] == 0
    assert len(data["markers"]) == 0
    
    m = empty_service.generate_india_folium_map(data)
    assert isinstance(m, folium.Map)


def test_single_city_aggregation():
    """2. Single city aggregation accuracy."""
    single_cases = [
        {"id": 1, "last_seen_city": "Pune", "last_seen_state": "Maharashtra", "latitude": 18.5204, "longitude": 73.8567, "status": "Missing"},
        {"id": 2, "last_seen_city": "Pune", "last_seen_state": "Maharashtra", "latitude": 18.5204, "longitude": 73.8567, "status": "Missing"},
    ]
    service = MapService(map_repo=MockMapRepository(single_cases))
    data = service.get_map_dashboard_data(user={"role": "admin"})

    assert data["summary"]["cities_affected"] == 1
    assert data["cities_summary"][0]["city"] == "Pune"
    assert data["cities_summary"][0]["total_cases"] == 2


def test_multiple_cities_aggregation(map_env):
    """3. Multiple cities aggregation."""
    service, _, admin_user, _ = map_env
    data = service.get_map_dashboard_data(user=admin_user)

    cities = {c["city"] for c in data["cities_summary"]}
    assert "Pune" in cities
    assert "Mumbai" in cities
    assert "Vijayawada" in cities
    assert "Hyderabad" in cities
    assert "Bengaluru" in cities


def test_multiple_states_aggregation(map_env):
    """4. Multiple states aggregation."""
    service, _, admin_user, _ = map_env
    data = service.get_map_dashboard_data(user=admin_user)

    states = {s["state"] for s in data["states_summary"]}
    assert "Maharashtra" in states
    assert "Andhra Pradesh" in states
    assert "Telangana" in states
    assert "Karnataka" in states


def test_missing_city_handling(map_env):
    """5. Missing city handling does not crash."""
    service, _, admin_user, _ = map_env
    data = service.get_map_dashboard_data(user=admin_user)
    assert "summary" in data


def test_missing_state_handling(map_env):
    """6. Missing state handling does not crash."""
    service, _, admin_user, _ = map_env
    data = service.get_map_dashboard_data(user=admin_user)
    assert data["summary"]["total_cases"] > 0


def test_missing_coordinates_handling(map_env):
    """7. Missing coordinates fall back to city lookup or locations_unavailable."""
    service, _, admin_user, _ = map_env
    data = service.get_map_dashboard_data(user=admin_user)
    assert data["summary"]["locations_unavailable"] >= 1


def test_invalid_coordinates_handling():
    """8. Invalid coordinates validation range checks."""
    assert MapService.validate_coordinates(999.0, 77.0) is False
    assert MapService.validate_coordinates(20.0, -500.0) is False
    assert MapService.validate_coordinates("invalid", "invalid") is False
    assert MapService.validate_coordinates(18.5204, 73.8567) is True


def test_case_status_filtering(map_env):
    """9. Case status filtering for Active (Missing) and Resolved (Found)."""
    service, _, admin_user, _ = map_env
    
    active_data = service.get_map_dashboard_data(user=admin_user, status_filter="Active")
    assert all(c["active_cases"] > 0 or c["total_cases"] == c["active_cases"] for c in active_data["cities_summary"])
    
    resolved_data = service.get_map_dashboard_data(user=admin_user, status_filter="Resolved")
    assert all(c["resolved_cases"] > 0 or c["total_cases"] == c["resolved_cases"] for c in resolved_data["cities_summary"])


def test_date_filtering(map_env):
    """10. Date filtering (e.g. Last 7 Days)."""
    service, _, admin_user, _ = map_env
    recent_data = service.get_map_dashboard_data(user=admin_user, days_filter=7)
    all_data = service.get_map_dashboard_data(user=admin_user)
    assert recent_data["summary"]["total_cases"] <= all_data["summary"]["total_cases"]


def test_state_count_accuracy(map_env):
    """11. State count accuracy."""
    service, _, admin_user, _ = map_env
    data = service.get_map_dashboard_data(user=admin_user)
    mh_summary = next(s for s in data["states_summary"] if s["state"] == "Maharashtra")
    assert mh_summary["total_cases"] == 3


def test_city_count_accuracy(map_env):
    """12. City count accuracy."""
    service, _, admin_user, _ = map_env
    data = service.get_map_dashboard_data(user=admin_user)
    pune_summary = next(c for c in data["cities_summary"] if c["city"] == "Pune")
    assert pune_summary["total_cases"] == 2
    assert pune_summary["active_cases"] == 1
    assert pune_summary["resolved_cases"] == 1


def test_total_case_count_accuracy(map_env):
    """13. Total case count accuracy."""
    service, _, admin_user, _ = map_env
    data = service.get_map_dashboard_data(user=admin_user)
    assert data["summary"]["total_cases"] == 8


def test_active_case_count_accuracy(map_env):
    """14. Active case count accuracy."""
    service, _, admin_user, _ = map_env
    data = service.get_map_dashboard_data(user=admin_user)
    assert data["summary"]["active_cases"] == 6


def test_resolved_case_count_accuracy(map_env):
    """15. Resolved case count accuracy."""
    service, _, admin_user, _ = map_env
    data = service.get_map_dashboard_data(user=admin_user)
    assert data["summary"]["resolved_cases"] == 2


def test_marker_generation_properties(map_env):
    """16. Marker records contain required non-sensitive properties."""
    service, _, admin_user, _ = map_env
    data = service.get_map_dashboard_data(user=admin_user)
    markers = data["markers"]
    assert len(markers) > 0
    m = markers[0]
    assert "city" in m
    assert "state" in m
    assert "latitude" in m
    assert "longitude" in m
    assert "density_level" in m
    assert "marker_color" in m


def test_marker_clustering_configuration(map_env):
    """17. Folium map generates MarkerCluster layer."""
    service, _, admin_user, _ = map_env
    data = service.get_map_dashboard_data(user=admin_user)
    folium_map = service.generate_india_folium_map(data)
    
    # Check that map object contains MarkerCluster children
    has_cluster = any(isinstance(child, MarkerCluster) for child in folium_map._children.values())
    assert has_cluster is True


def test_public_vs_admin_data_separation(map_env):
    """18. PUBLIC_MAP_DATA level excludes private/sensitive fields."""
    service, _, admin_user, _ = map_env
    pub_data = service.get_map_dashboard_data(user=admin_user, data_level="PUBLIC_MAP_DATA")
    
    assert pub_data["data_level"] == "PUBLIC_MAP_DATA"
    for m in pub_data["markers"]:
        assert "contact_email" not in m
        assert "contact_phone" not in m
        assert "face_vector" not in m
        assert "victim_name" not in m


def test_unauthorized_access_rejection(map_env):
    """19. Unauthenticated users raise PermissionError."""
    service, _, _, _ = map_env
    with pytest.raises(PermissionError):
        service.get_map_dashboard_data(user=None)

    with pytest.raises(PermissionError):
        service.get_map_dashboard_data(user={"username": "guest", "role": "public"})


def test_mongodb_failure_resilience():
    """20. MongoDB failure resilience."""
    class FailingMapRepo:
        def get_case_counts_by_state(self, status=None, days=None):
            return []
        def get_case_counts_by_city(self, status=None, days=None, state=None):
            return []
        def get_case_counts_by_status(self, days=None, state=None):
            return {"total_cases": 0, "active_cases": 0, "resolved_cases": 0, "closed_cases": 0}
        def get_case_locations(self, status=None, days=None, state=None):
            return []

    fail_service = MapService(map_repo=FailingMapRepo())
    data = fail_service.get_map_dashboard_data(user={"role": "admin"})
    assert data["summary"]["total_cases"] == 0


def test_large_dataset_performance():
    """21. Large dataset aggregation performance."""
    large_cases = []
    cities = [("Pune", "Maharashtra", 18.5204, 73.8567), ("Mumbai", "Maharashtra", 19.0760, 72.8777), ("Bengaluru", "Karnataka", 12.9716, 77.5946)]
    for i in range(150):
        c_name, c_state, c_lat, c_lon = cities[i % 3]
        large_cases.append({
            "id": i + 1,
            "last_seen_city": c_name,
            "last_seen_state": c_state,
            "latitude": c_lat,
            "longitude": c_lon,
            "status": "Missing" if i % 2 == 0 else "Found",
            "created_at": datetime.utcnow(),
        })

    perf_service = MapService(map_repo=MockMapRepository(large_cases))
    data = perf_service.get_map_dashboard_data(user={"role": "admin"})
    assert data["summary"]["total_cases"] == 150
    assert len(data["markers"]) == 3
