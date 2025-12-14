import os
import uuid
from uuid import UUID
from fastapi.testclient import TestClient

from bharatrag.main import app


def _db_enabled() -> bool:
    return os.getenv("BHARATRAG_RUN_DB_TESTS", "1") == "1"


def test_ingestion_job_lifecycle():
    if not _db_enabled():
        return

    client = TestClient(app)

    # 1) Create a collection (FK prerequisite)
    name = f"weekend2-ingest-{uuid.uuid4()}"
    r_col = client.post("/collections", json={"name": name})
    assert r_col.status_code == 201, r_col.text
    collection = r_col.json()

    collection_id = collection["id"]
    assert UUID(collection_id)

    # 2) Create ingestion job referencing that collection
    r_job = client.post(
        "/ingestion-jobs",
        json={
            "collection_id": collection_id,
            "source_type": "file",
            "format": "txt",
        },
    )
    assert r_job.status_code == 201, r_job.text
    job = r_job.json()

    assert UUID(job["id"])
    assert job["collection_id"] == collection_id
    assert job["status"] in ("COMPLETED", "FAILED")

    # 3) Fetch job
    job_id = job["id"]
    r_get = client.get(f"/ingestion-jobs/{job_id}")
    assert r_get.status_code == 200, r_get.text
    fetched = r_get.json()

    assert fetched["id"] == job_id
    assert fetched["collection_id"] == collection_id
