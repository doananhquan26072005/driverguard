"""Web driving controls (M31): #/drive sends speed / turn signal under a pairing code, #/live reads them."""

from backend.drive_link import DriveLinks


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_the_remote_page_sets_and_live_reads_the_latest_reading(client):
    assert client.get("/api/v1/drive/AB12CD").status_code == 404  # nothing sent yet
    assert client.put("/api/v1/drive/AB12CD", json={"speed_kmh": 42.5, "turn_signal": "left"}).status_code == 204
    r = client.get("/api/v1/drive/AB12CD").json()
    assert r["speed_kmh"] == 42.5 and r["turn_signal"] == "left" and 0 <= r["age_s"] < 1
    client.put("/api/v1/drive/AB12CD", json={"speed_kmh": 0, "turn_signal": None})
    assert client.get("/api/v1/drive/AB12CD").json()["turn_signal"] is None
    assert client.get("/api/v1/drive/ZZZZZZ").status_code == 404  # another code is another car


def test_only_numbers_and_a_short_code_are_accepted(client):
    assert client.put("/api/v1/drive/ab12cd", json={"speed_kmh": 10}).status_code == 422  # lower case
    assert client.put("/api/v1/drive/AB12", json={"speed_kmh": 10}).status_code == 422
    assert client.put("/api/v1/drive/AB12CD", json={"speed_kmh": -1}).status_code == 422
    assert client.put("/api/v1/drive/AB12CD", json={"speed_kmh": 999}).status_code == 422
    assert client.put("/api/v1/drive/AB12CD", json={"speed_kmh": 10, "turn_signal": "up"}).status_code == 422
    assert client.put("/api/v1/drive/AB12CD", json={"speed_kmh": 10, "image": "x"}).status_code == 422


def test_codes_expire_and_are_capped():
    clock = FakeClock()
    links = DriveLinks(ttl_s=600, max_codes=2, clock=clock)
    links.put("AAAAAA", 30.0, None)
    clock.now = 5.0
    assert links.get("AAAAAA").age_s == 5.0
    clock.now = 700.0
    assert links.get("AAAAAA") is None  # expired
    links.put("AAAAAA", 1.0, None)
    links.put("BBBBBB", 2.0, None)
    links.put("CCCCCC", 3.0, None)  # over the cap: the oldest goes
    assert links.get("AAAAAA") is None and links.get("CCCCCC").speed_kmh == 3.0
