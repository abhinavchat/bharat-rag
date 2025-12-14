from __future__ import annotations

import logging

from bharatrag.ports.llm import LLM

logger = logging.getLogger(__name__)


class ExtractiveLLM(LLM):
    """
    Deterministic fallback for Weekend-3:
    Extracts and summarizes context without requiring an external LLM.
    
    This is a simple stub that:
    - Extracts context chunks from the prompt
    - Provides a basic summary-style answer
    - Can be replaced with Ollama/OpenAI/etc. in future weekends
    """
    def generate(self, prompt: str) -> str:
        logger.debug("Generating answer with extractive LLM", extra={"prompt_length": len(prompt)})
        
        try:
            # Parse prompt structure: "QUESTION:\n{question}\n\nCONTEXT:\n{chunks}"
            if "CONTEXT:" not in prompt or "QUESTION:" not in prompt:
                logger.warning("Unexpected prompt structure, returning prompt as-is")
                return prompt
            
            # Extract question
            question_part = prompt.split("QUESTION:")[1].split("CONTEXT:")[0].strip()
            
            # Extract context chunks (separated by "\n---\n")
            context_part = prompt.split("CONTEXT:")[1].strip()
            chunks = [c.strip() for c in context_part.split("\n---\n") if c.strip()]
            
            logger.debug(
                "Parsed prompt",
                extra={
                    "question_length": len(question_part),
                    "chunk_count": len(chunks),
                },
            )
            
            if not chunks:
                logger.warning("No context chunks found for answer generation")
                return f"Based on the available information, I cannot find relevant context to answer: {question_part}"
            
            # Simple extractive answer: combine first few chunks with a summary
            # In a real LLM, this would be more sophisticated
            if len(chunks) == 1:
                answer = chunks[0]
            else:
                # Combine chunks with a simple connector
                answer = " ".join(chunks[:2])  # Use top 2 chunks
                if len(chunks) > 2:
                    answer += f" [Additional context available: {len(chunks) - 2} more chunks]"
            
            # Add a simple prefix to make it feel more like an answer
            result = f"Based on the provided context: {answer}"
            
            logger.info(
                "Answer generated successfully",
                extra={
                    "answer_length": len(result),
                    "chunks_used": min(2, len(chunks)),
                    "total_chunks": len(chunks),
                },
            )
            
            return result
        except Exception as e:
            logger.exception("Answer generation failed", extra={"error": str(e)})
            raise
