import logging

from fastapi import APIRouter
from bharatrag.domain.answer import AnswerRequest, AnswerResponse, Citation
from bharatrag.services.retrieval_service import RetrievalService
from bharatrag.services.llm.extractive_llm import ExtractiveLLM
from bharatrag.core.context import set_collection_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/answer", tags=["rag"])
retriever = RetrievalService()
llm = ExtractiveLLM()


@router.post("", response_model=AnswerResponse)
def answer(payload: AnswerRequest) -> AnswerResponse:
    set_collection_id(payload.collection_id)
    logger.info(
        "Answer request received",
        extra={
            "collection_id": str(payload.collection_id),
            "question_length": len(payload.question),
            "top_k": payload.top_k,
        },
    )
    
    try:
        results = retriever.query(
            collection_id=payload.collection_id,
            query=payload.question,
            top_k=payload.top_k,
        )
        
        logger.debug(
            "Retrieved chunks for answer",
            extra={
                "collection_id": str(payload.collection_id),
                "chunk_count": len(results),
            },
        )
        
        # Extract context text and citations
        context = [r.chunk.text for r in results]
        citations = [
            Citation(
                document_id=r.chunk.document_id,
                chunk_id=r.chunk.id,
                chunk_index=r.chunk.chunk_index,
            )
            for r in results
        ]

        prompt = (
            "You are Bharat-RAG (Weekend-3). Answer using ONLY the CONTEXT.\n\n"
            f"QUESTION:\n{payload.question}\n\n"
            "CONTEXT:\n" + "\n---\n".join(context)
        )
        
        logger.debug(
            "Generating answer with LLM",
            extra={
                "collection_id": str(payload.collection_id),
                "prompt_length": len(prompt),
                "context_chunks": len(context),
            },
        )
        
        out = llm.generate(prompt)
        
        logger.info(
            "Answer generated successfully",
            extra={
                "collection_id": str(payload.collection_id),
                "answer_length": len(out),
                "citation_count": len(citations),
            },
        )
        
        return AnswerResponse(answer=out, citations=citations, context=context)
    except Exception as e:
        logger.exception(
            "Answer generation failed",
            extra={
                "collection_id": str(payload.collection_id),
                "error": str(e),
            },
        )
        raise
