"""
Prompt builder for RAG (Retrieval-Augmented Generation).

Builds prompts optimized for local LLMs with context chunks.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def build_rag_prompt(
    question: str,
    context_chunks: list[str],
    max_context_tokens: int = 400,
    use_instruction_format: bool = False,
) -> str:
    """
    Build a RAG prompt optimized for local LLMs.
    
    Args:
        question: User's question
        context_chunks: List of context chunks from retrieval
        max_context_tokens: Maximum tokens to use for context (approximate)
        use_instruction_format: Whether to use instruction-tuned model format
        
    Returns:
        Formatted prompt string
    """
    if not context_chunks:
        logger.warning("No context chunks provided for RAG prompt")
        return f"Question: {question}\n\nAnswer:"
    
    # Estimate tokens per chunk (rough approximation: 1 token ≈ 4 characters)
    # Truncate context if needed
    available_length = max_context_tokens * 4  # Rough character limit
    total_context = "\n---\n".join(context_chunks)
    
    if len(total_context) > available_length:
        # Truncate chunks, keeping most relevant (first ones)
        truncated_chunks = []
        current_length = 0
        for chunk in context_chunks:
            chunk_length = len(chunk) + 5  # +5 for separator
            if current_length + chunk_length <= available_length:
                truncated_chunks.append(chunk)
                current_length += chunk_length
            else:
                # Add partial chunk if space allows
                remaining = available_length - current_length - 5
                if remaining > 100:  # Only if meaningful space
                    truncated_chunks.append(chunk[:remaining] + "...")
                break
        
        context_text = "\n---\n".join(truncated_chunks)
        logger.debug(
            "Truncated context for prompt",
            extra={
                "original_chunks": len(context_chunks),
                "truncated_chunks": len(truncated_chunks),
            },
        )
    else:
        context_text = total_context
    
    if use_instruction_format:
        # Format for instruction-tuned models (e.g., TinyLlama-Chat, etc.)
        prompt = (
            "You are a helpful assistant that answers questions based on provided context.\n\n"
            f"Context:\n{context_text}\n\n"
            f"Question: {question}\n\n"
            "Answer based only on the context provided above:"
        )
    else:
        # Improved format for base models (e.g., GPT-2, DialoGPT)
        # Use more explicit instructions and better structure
        # For base models, we need to be very explicit and provide examples
        prompt = (
            f"Context: {context_text}\n\n"
            f"Question: {question}\n\n"
            "Answer based on the context:"
        )
    
    logger.debug(
        "RAG prompt built",
        extra={
            "question_length": len(question),
            "context_chunks": len(context_chunks),
            "prompt_length": len(prompt),
            "instruction_format": use_instruction_format,
            "context_length": len(context_text),
        },
    )
    
    return prompt

