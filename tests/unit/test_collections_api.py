import os
from fastapi.testclient import TestClient
import uuid

from bharatrag.main import app


def _db_enabled() -> bool:
    return os.getenv("BHARATRAG_RUN_DB_TESTS", "1") == "1"


def test_create_and_get_collection():
    if not _db_enabled():
        return

    client = TestClient(app)

    # Create
    name = f"weekend-1-{uuid.uuid4()}"
    r = client.post("/collections", json={"name": name})
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["name"] == name
    assert "id" in created

    # Fetch
    cid = created["id"]
    r2 = client.get(f"/collections/{cid}")
    assert r2.status_code == 200, r2.text
    fetched = r2.json()
    assert fetched["id"] == cid
    assert fetched["name"] == name
