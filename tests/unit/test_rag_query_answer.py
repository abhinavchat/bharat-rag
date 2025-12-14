import os
import uuid
from fastapi.testclient import TestClient
from bharatrag.main import app


def _db_enabled() -> bool:
    return os.getenv("BHARATRAG_TEST_DB", "0") == "1"


def test_weekend3_rag_flow_query_and_answer():
    """End-to-end test for Weekend 3: ingestion → query → answer with citations."""
    if not _db_enabled():
        return

    client = TestClient(app)

    # 1) Create collection (unique name)
    cname = f"w3-{uuid.uuid4()}"
    r = client.post("/collections", json={"name": cname})
    assert r.status_code == 201, r.text
    collection_id = r.json()["id"]

    # 2) Ingest a small text (uri treated as raw content)
    payload = {
        "collection_id": collection_id,
        "source_type": "text",
        "format": "txt",
        "uri": "India stack includes Aadhaar, UPI, DigiLocker. Bharat-RAG is a protocol-first RAG system.",
    }
    r = client.post("/ingestion-jobs", json=payload)
    assert r.status_code == 201, r.text
    job = r.json()
    assert job["status"] in ("COMPLETED", "FAILED", "RUNNING", "PENDING")
    
    # Verify job completes successfully
    if job["status"] == "RUNNING":
        # Poll for completion (simple test, no async wait)
        job_id = job["id"]
        r = client.get(f"/ingestion-jobs/{job_id}")
        assert r.status_code == 200
        job = r.json()
    
    assert job["status"] == "COMPLETED", f"Job should complete, got: {job.get('error_summary')}"
    assert "progress" in job
    # Verify progress stages were tracked
    progress = job.get("progress", {})
    assert "stage" in progress
    assert progress["stage"] in ("persisted", "completed")

    # 3) Query - verify retrieval works
    r = client.post("/query", json={"collection_id": collection_id, "query": "What is India Stack?", "top_k": 3})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "results" in data
    assert len(data["results"]) > 0, "Query should return at least one result"
    assert len(data["results"]) <= 3, "Should respect top_k limit"
    
    # Verify result structure
    for result in data["results"]:
        assert "chunk" in result, "Result should contain chunk"
        assert "score" in result, "Result should contain score"
        chunk = result["chunk"]
        assert "id" in chunk, "Chunk should have id"
        assert "document_id" in chunk, "Chunk should have document_id"
        assert "text" in chunk, "Chunk should have text"
        assert chunk["text"], "Chunk text should not be empty"
        assert isinstance(result["score"], (int, float)), "Score should be numeric"

    # 4) Answer - verify RAG with citations
    r = client.post("/answer", json={"collection_id": collection_id, "question": "Explain Bharat-RAG", "top_k": 3})
    assert r.status_code == 200, r.text
    ans = r.json()
    assert "answer" in ans
    assert ans["answer"], "Answer should not be empty"
    assert "citations" in ans, "Answer should include citations"
    assert "context" in ans, "Answer should include context"
    
    # Verify citations structure
    assert len(ans["citations"]) > 0, "Should have at least one citation"
    for citation in ans["citations"]:
        assert "document_id" in citation, "Citation should have document_id"
        assert "chunk_id" in citation, "Citation should have chunk_id"
        assert "chunk_index" in citation, "Citation should have chunk_index"
        assert isinstance(citation["chunk_index"], int), "chunk_index should be integer"
    
    # Verify context matches citations
    assert len(ans["context"]) > 0, "Context should not be empty"
    assert len(ans["context"]) == len(ans["citations"]), "Context length should match citations"
    
    # Verify citations reference chunks from query results
    query_chunk_ids = {result["chunk"]["id"] for result in data["results"]}
    answer_chunk_ids = {citation["chunk_id"] for citation in ans["citations"]}
    # At least some citations should match query results (they may not all match due to ordering)
    assert len(query_chunk_ids & answer_chunk_ids) > 0, "Citations should reference chunks from query"
