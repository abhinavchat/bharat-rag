import logging

from fastapi import APIRouter
from bharatrag.domain.query import QueryRequest, QueryResponse
from bharatrag.services.retrieval_service import RetrievalService
from bharatrag.core.context import set_collection_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["rag"])
svc = RetrievalService()


@router.post("", response_model=QueryResponse)
def query(payload: QueryRequest) -> QueryResponse:
    set_collection_id(payload.collection_id)
    logger.info(
        "Query request received",
        extra={
            "collection_id": str(payload.collection_id),
            "query_length": len(payload.query),
            "top_k": payload.top_k,
        },
    )
    
    try:
        results = svc.query(
            collection_id=payload.collection_id,
            query=payload.query,
            top_k=payload.top_k,
        )
        logger.info(
            "Query completed successfully",
            extra={
                "collection_id": str(payload.collection_id),
                "result_count": len(results),
            },
        )
        return QueryResponse(results=results, debug={"top_k": payload.top_k})
    except Exception as e:
        logger.exception(
            "Query failed",
            extra={
                "collection_id": str(payload.collection_id),
                "error": str(e),
            },
        )
        raise
