from fastapi import FastAPI

app = FastAPI(
    title="Bharat-RAG Reference Server",
    version="0.0.1-prealpha",
    description=(
        "Reference implementation for the Bharat-RAG Protocol (BRP)."
        "This is an early pre-alpha API skeleton."
    ),
)

@app.get("/healthz", tags=["meta"])
async def healthz() -> dict:
    """
    Lightweight health check endpoint.
    
    This will be used by CI/tests and also by Kubernetes/infra in the future.
    """
    return {"status": "ok"}
