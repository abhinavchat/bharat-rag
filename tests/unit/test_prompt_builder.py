"""
Tests for prompt builder.
"""
from __future__ import annotations

from bharatrag.services.llm.prompt_builder import build_rag_prompt


def test_build_rag_prompt_basic():
    """Test basic prompt building."""
    question = "What is the main topic?"
    context = ["Context chunk 1", "Context chunk 2"]
    
    prompt = build_rag_prompt(question, context)
    
    assert question in prompt
    assert "Context chunk 1" in prompt
    assert "Context chunk 2" in prompt
    assert "Answer" in prompt or "answer" in prompt.lower()


def test_build_rag_prompt_empty_context():
    """Test prompt building with empty context."""
    question = "What is the main topic?"
    context: list[str] = []
    
    prompt = build_rag_prompt(question, context)
    
    assert question in prompt
    assert "Answer:" in prompt


def test_build_rag_prompt_instruction_format():
    """Test prompt building with instruction format."""
    question = "What is the main topic?"
    context = ["Context chunk 1"]
    
    prompt = build_rag_prompt(question, context, use_instruction_format=True)
    
    assert question in prompt
    assert "Context chunk 1" in prompt
    assert "helpful assistant" in prompt.lower() or "assistant" in prompt.lower()


def test_build_rag_prompt_truncation():
    """Test that long context is truncated."""
    question = "What is the main topic?"
    # Create very long context
    context = ["A" * 1000] * 10  # 10 chunks of 1000 chars each = 10000 chars
    
    prompt = build_rag_prompt(question, context, max_context_tokens=100)
    
    assert question in prompt
    # Should be truncated (roughly 400 chars for context)
    assert len(prompt) < len(question) + 10000 + 100


def test_build_rag_prompt_multiple_chunks():
    """Test prompt building with multiple chunks."""
    question = "What are the key points?"
    context = [
        "First point: This is important.",
        "Second point: This is also important.",
        "Third point: This is crucial.",
    ]
    
    prompt = build_rag_prompt(question, context)
    
    assert question in prompt
    assert "First point" in prompt
    assert "Second point" in prompt
    assert "Third point" in prompt
    assert "---" in prompt  # Separator between chunks


def test_build_rag_prompt_preserves_question():
    """Test that question is preserved exactly."""
    question = "What is the capital of India?"
    context = ["New Delhi is the capital of India."]
    
    prompt = build_rag_prompt(question, context)
    
    # Question should appear exactly as provided
    assert question in prompt

