import logging

from fastapi import APIRouter
from bharatrag.domain.answer import AnswerRequest, AnswerResponse, Citation
from bharatrag.services.retrieval_service import RetrievalService
from bharatrag.services.llm.llm_factory import create_llm
from bharatrag.services.llm.prompt_builder import build_rag_prompt
from bharatrag.core.context import set_collection_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/answer", tags=["rag"])
retriever = RetrievalService()
llm = create_llm()  # Use factory to create LLM based on configuration


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
        
        if not results:
            logger.warning(
                "No chunks retrieved for answer",
                extra={
                    "collection_id": str(payload.collection_id),
                    "question": payload.question,
                },
            )
            return AnswerResponse(
                answer="I could not find any relevant information to answer your question.",
                citations=[],
                context=[],
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
        
        # Log chunk details for debugging
        logger.debug(
            "Context chunks prepared",
            extra={
                "collection_id": str(payload.collection_id),
                "chunk_count": len(context),
                "total_context_length": sum(len(c) for c in context),
                "chunk_lengths": [len(c) for c in context],
                "chunk_previews": [c[:100] + "..." if len(c) > 100 else c for c in context],
            },
        )

        # Detect if LLM is instruction-tuned (for better prompts)
        use_instruction_format = False
        if hasattr(llm, "_is_instruction_tuned"):
            try:
                use_instruction_format = llm._is_instruction_tuned()
            except Exception:
                pass  # Fall back to base format
        
        # Build RAG prompt using prompt builder
        prompt = build_rag_prompt(
            question=payload.question,
            context_chunks=context,
            max_context_tokens=400,
            use_instruction_format=use_instruction_format,
        )
        
        logger.debug(
            "Generating answer with LLM",
            extra={
                "collection_id": str(payload.collection_id),
                "prompt_length": len(prompt),
                "context_chunks": len(context),
                "use_instruction_format": use_instruction_format,
                "llm_type": type(llm).__name__,
            },
        )
        
        # Log prompt for debugging (first 200 chars)
        logger.debug(
            "Prompt preview",
            extra={
                "prompt_preview": prompt[:200] + "..." if len(prompt) > 200 else prompt,
            },
        )
        
        out = llm.generate(prompt)
        
        logger.debug(
            "LLM response received",
            extra={
                "collection_id": str(payload.collection_id),
                "response_length": len(out),
                "response_preview": out[:200] + "..." if len(out) > 200 else out,
            },
        )
        
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
