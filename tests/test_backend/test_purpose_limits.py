"""Purpose limits of the product (docs/data-policy.md, M41): the API offers no ranking of drivers,
and a new endpoint cannot appear without this list being edited on purpose."""

from tests.test_backend.conftest import OTHER_DEVICE_KEY, login, make_event, post_events
from tests.test_backend.test_fleet import beat

# Every route of the backend. Adding one means deciding here that it is no leaderboard of drivers
# (no list of people ordered or scored by their alerts) and whether it belongs in the access log.
ROUTES = {
    ("GET", "/health"),
    ("PUT", "/api/v1/drive/{code}"),
    ("GET", "/api/v1/drive/{code}"),
    ("GET", "/api/v1/policy"),
    ("POST", "/auth/login"),
    ("GET", "/auth/me"),
    ("POST", "/api/v1/events"),
    ("POST", "/api/v1/web/events"),
    ("GET", "/api/v1/web/thresholds"),
    ("GET", "/api/v1/events"),
    ("GET", "/api/v1/trips"),
    ("GET", "/api/v1/timeline"),
    ("GET", "/api/v1/stats"),
    ("GET", "/api/v1/fleet"),
    ("GET", "/api/v1/trip-reports"),
    ("GET", "/api/v1/trip-reports/{device_id}/{trip_id}"),
    ("POST", "/api/v1/trip-reports/{device_id}/{trip_id}/review"),
    ("GET", "/api/v1/thresholds"),
    ("PUT", "/api/v1/thresholds"),
    ("GET", "/api/v1/device/thresholds"),
    # M47: versions with their alert / false-alarm totals and the devices running them. Per version,
    # not per driver; changes (PUT above, rollout) are logged.
    ("GET", "/api/v1/thresholds/versions"),
    ("POST", "/api/v1/thresholds/rollout"),
    # M48: a driver's own data and deletion request (their own only); an admin's decision is logged.
    ("GET", "/api/v1/me/data"),
    ("GET", "/api/v1/me/deletion-request"),
    ("POST", "/api/v1/me/deletion-request"),
    ("GET", "/api/v1/deletion-requests"),
    ("POST", "/api/v1/deletion-requests/{request_id}"),
    ("GET", "/api/v1/access-log"),
    ("GET", "/api/v1/access-log/mine"),
    ("GET", "/api/v1/users"),
    ("POST", "/api/v1/users"),
    ("POST", "/api/v1/devices"),
}
FRAMEWORK = ("/docs", "/redoc", "/openapi.json")  # FastAPI's own pages


def test_the_api_is_exactly_the_reviewed_list(client):
    found = {
        (method, route.path)
        for route in client.app.routes
        for method in getattr(route, "methods", ()) - {"HEAD", "OPTIONS"}
        if not route.path.startswith(FRAMEWORK)
    }
    assert found == ROUTES


def test_no_route_or_field_ranks_drivers(client):
    spec = client.get("/openapi.json").json()
    text = str(spec).lower()
    for word in ("rank", "leaderboard", "top_drivers", "worst_drivers", "score_by_driver"):
        assert word not in text


def test_stats_are_totals_not_a_list_of_people(client):
    post_events(client, [make_event(), make_event()])
    post_events(client, [make_event()], device_id="cam-002", key=OTHER_DEVICE_KEY)
    stats = client.get("/api/v1/stats", headers=login(client, "boss")).json()
    assert set(stats) == {"total", "false_alarms", "by_level", "by_reason"}  # nothing keyed by driver
    assert "drv-001" not in str(stats) and "drv-002" not in str(stats)


def test_the_fleet_list_is_ordered_by_device_not_by_alerts(client):
    beat(client)
    beat(client, device_id="cam-002", key=OTHER_DEVICE_KEY)
    post_events(client, [make_event() for _ in range(5)], device_id="cam-002", key=OTHER_DEVICE_KEY)  # most alerts
    devices = client.get("/api/v1/fleet", headers=login(client, "boss")).json()
    assert [d["device_id"] for d in devices] == ["cam-001", "cam-002"]
