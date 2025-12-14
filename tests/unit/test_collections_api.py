import os
from fastapi.testclient import TestClient

from bharatrag.main import app


def _db_enabled() -> bool:
    return os.getenv("BHARATRAG_RUN_DB_TESTS", "1") == "1"


def test_create_and_get_collection():
    if not _db_enabled():
        return

    client = TestClient(app)

    # Create
    r = client.post("/collections", json={"name": "weekend-1"})
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["name"] == "weekend-1"
    assert "id" in created

    # Fetch
    cid = created["id"]
    r2 = client.get(f"/collections/{cid}")
    assert r2.status_code == 200, r2.text
    fetched = r2.json()
    assert fetched["id"] == cid
    assert fetched["name"] == "weekend-1"
