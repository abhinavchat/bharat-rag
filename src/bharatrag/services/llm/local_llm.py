"""
Local LLM implementation using Hugging Face transformers.

Runs models directly in Python without external runners or APIs.
Fully local and sovereign - no external dependencies.
"""
from __future__ import annotations

import logging
from typing import Any

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch
except ImportError:
    AutoModelForCausalLM = None  # type: ignore
    AutoTokenizer = None  # type: ignore
    torch = None  # type: ignore

from bharatrag.ports.llm import LLM

logger = logging.getLogger(__name__)


def _is_response_relevant(response: str, prompt: str) -> bool:
    """
    Check if the LLM response is relevant to the question in the prompt.
    
    Args:
        response: The LLM-generated response
        prompt: The full prompt containing the question
        
    Returns:
        True if response appears relevant, False otherwise
    """
    import re
    
    # Extract question from prompt
    question = ""
    if "Question:" in prompt:
        parts = prompt.split("Question:")
        if len(parts) > 1:
            question_part = parts[1]
            if "Answer" in question_part:
                question = question_part.split("Answer")[0].strip()
            else:
                question = question_part.strip()
    
    if not question:
        # Can't check relevance without question
        return True  # Assume relevant if we can't check
    
    # Extract keywords from question
    question_lower = question.lower()
    question_words = set(re.findall(r'\b\w+\b', question_lower))
    stop_words = {'what', 'is', 'are', 'the', 'a', 'an', 'this', 'that', 'these', 'those',
                  'how', 'why', 'when', 'where', 'who', 'which', 'do', 'does', 'did', 'can', 'could'}
    question_keywords = question_words - stop_words
    
    if not question_keywords:
        # No meaningful keywords to check
        return True
    
    # Check if response contains any question keywords
    response_lower = response.lower()
    matches = sum(1 for keyword in question_keywords if keyword in response_lower)
    
    # Response is relevant if it contains at least one keyword
    # For very short responses (<= 2 words), be more lenient (might be yes/no)
    # But for 3+ word responses, require keyword match (they should be substantive)
    word_count = len(response.split())
    if word_count <= 2:
        # Very short - might be yes/no or single word answer
        is_relevant = matches > 0 or word_count <= 1
    else:
        # 3+ word responses must contain at least one keyword to be considered relevant
        is_relevant = matches > 0
    
    logger.debug(
        "Relevance check",
        extra={
            "question_keywords": list(question_keywords),
            "matches": matches,
            "is_relevant": is_relevant,
            "response_preview": response[:50],
        },
    )
    
    return is_relevant


def _extract_answer_from_context(prompt: str) -> str:
    """
    Extract a relevant answer from the context in the prompt.
    
    Tries to find sentences that are most relevant to the question.
    
    Args:
        prompt: The full prompt containing context and question
        
    Returns:
        Extracted answer text, or empty string if nothing found
    """
    import re
    
    # Extract question and context from prompt
    question = ""
    context_text = ""
    
    # Try different prompt formats
    if "Question:" in prompt:
        parts = prompt.split("Question:")
        if len(parts) > 1:
            question_part = parts[1]
            # Extract question (before "Answer:" or end)
            if "Answer" in question_part:
                question = question_part.split("Answer")[0].strip()
            else:
                question = question_part.strip()
    
    if "Context:" in prompt:
        context_part = prompt.split("Context:")[1]
        # Remove question part if present
        if "Question:" in context_part:
            context_text = context_part.split("Question:")[0].strip()
        else:
            context_text = context_part.strip()
    
    if not context_text:
        logger.debug("No context found in prompt for extraction")
        return ""
    
    # Split context into sentences
    # Handle both chunk separators and sentence boundaries
    # First split by chunk separators
    chunks = context_text.split("\n---\n")
    all_sentences = []
    
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        
        # Split chunk into sentences
        # Use a more robust sentence splitting that handles abbreviations
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', chunk)
        # Also handle cases where sentences might be split by chunk boundaries
        for sentence in sentences:
            sentence = sentence.strip()
            # Skip very short fragments (likely split words)
            if len(sentence) < 15:
                continue
            # Skip sentences that start with lowercase (likely continuation from previous chunk)
            # But allow if it's a proper sentence (starts with capital after punctuation)
            if sentence and sentence[0].islower() and not sentence[0].isupper():
                # This might be a continuation - try to find the actual start
                # Look for sentence patterns
                if not re.search(r'^[A-Z]', sentence):
                    # Skip fragments that don't start properly
                    continue
            all_sentences.append(sentence)
    
    if not all_sentences:
        logger.debug("No sentences found in context")
        return ""
    
    # Score sentences by relevance to question
    # Extract keywords from question (simple approach)
    question_lower = question.lower()
    question_words = set(re.findall(r'\b\w+\b', question_lower))
    # Remove common stop words
    stop_words = {'what', 'is', 'are', 'the', 'a', 'an', 'this', 'that', 'these', 'those', 
                  'how', 'why', 'when', 'where', 'who', 'which', 'do', 'does', 'did'}
    question_keywords = question_words - stop_words
    
    scored_sentences = []
    for sentence in all_sentences:
        sentence_lower = sentence.lower()
        # Count keyword matches
        matches = sum(1 for keyword in question_keywords if keyword in sentence_lower)
        # Bonus if sentence contains key phrases from question
        if question_keywords:
            # Check if sentence contains multiple keywords (more relevant)
            keyword_density = matches / len(question_keywords) if question_keywords else 0
            scored_sentences.append((sentence, matches, keyword_density))
        else:
            scored_sentences.append((sentence, 0, 0))
    
    # Sort by relevance (matches, then density)
    scored_sentences.sort(key=lambda x: (x[1], x[2]), reverse=True)
    
    # Take top 1-2 most relevant sentences
    if scored_sentences:
        top_sentence = scored_sentences[0][0]
        top_score = scored_sentences[0][1]
        
        # If top sentence has good relevance (at least 1 keyword match), use it
        if top_score > 0:
            # If we have a second highly relevant sentence, include it
            if len(scored_sentences) > 1 and scored_sentences[1][1] > 0:
                # Combine if they're from different chunks or complement each other
                second_sentence = scored_sentences[1][0]
                # Limit total length
                combined = f"{top_sentence} {second_sentence}"
                if len(combined) < 400:
                    response = combined
                else:
                    response = top_sentence
            else:
                response = top_sentence
        else:
            # No keyword matches, but we have sentences - use the longest/most complete one
            # Prefer sentences that look complete (end with punctuation, reasonable length)
            complete_sentences = [s for s in all_sentences if s.endswith(('.', '!', '?')) and len(s) > 50]
            if complete_sentences:
                # Use the longest complete sentence
                response = max(complete_sentences, key=len)
            else:
                # Fallback to first reasonable sentence
                response = top_sentence if len(top_sentence) > 30 else ""
        
        if response:
            # Ensure proper punctuation
            if not response.endswith(('.', '!', '?')):
                response += '.'
            
            logger.info(
                "Extracted answer from context",
                extra={
                    "length": len(response),
                    "sentences_considered": len(all_sentences),
                    "top_score": top_score,
                    "method": "keyword_match" if top_score > 0 else "fallback",
                },
            )
            return response
    
    return ""


def _is_coherent_text(text: str) -> bool:
    """
    Check if text appears to be coherent (not gibberish).
    
    Args:
        text: Text to check
        
    Returns:
        True if text appears coherent, False otherwise
    """
    if not text or len(text.strip()) < 10:
        return False
    
    import re
    
    # Check for too many non-word characters
    word_chars = len(re.findall(r'\w', text))
    total_chars = len(text.replace(' ', ''))
    if total_chars > 0 and word_chars / total_chars < 0.5:
        return False
    
    # Check for reasonable word length distribution
    words = text.split()
    if len(words) < 2:
        return False
    
    # Check if words are mostly reasonable length (not all very short or very long)
    avg_word_length = sum(len(w) for w in words) / len(words)
    if avg_word_length < 2 or avg_word_length > 15:
        return False
    
    # Check for too many single-character "words" (often indicates gibberish)
    single_char_words = sum(1 for w in words if len(w) == 1)
    if len(words) > 0 and single_char_words / len(words) > 0.3:
        return False
    
    # Check for common English words (basic heuristic)
    common_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had',
                   'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can',
                   'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
                   'and', 'or', 'but', 'if', 'then', 'when', 'where', 'what', 'who', 'how', 'why',
                   'in', 'on', 'at', 'to', 'for', 'of', 'with', 'from', 'by', 'about', 'into'}
    text_lower = text.lower()
    found_common_words = sum(1 for word in common_words if word in text_lower)
    # If we have at least 2 words and found at least 1 common word, it's likely coherent
    if len(words) >= 3 and found_common_words == 0:
        return False
    
    return True


def _post_process_response(response: str, original_prompt: str) -> str:
    """
    Post-process LLM response to improve quality.
    
    Args:
        response: Raw generated response
        original_prompt: Original prompt (for context)
        
    Returns:
        Cleaned and improved response
    """
    if not response:
        return "I cannot generate a response based on the provided context."
    
    # Remove common artifacts
    response = response.strip()
    
    # Quick coherence check - if the entire response is clearly gibberish, skip to fallback
    if not _is_coherent_text(response):
        logger.warning(
            "Response failed initial coherence check",
            extra={"response": response[:100]},
        )
        # Skip to context extraction fallback
        response = ""
    
    # Remove repeated question if model echoed it
    if "Question:" in response:
        parts = response.split("Question:")
        if len(parts) > 1:
            # Take the part after the last "Question:"
            response = parts[-1].strip()
            # Remove "Answer:" if present
            if response.startswith("Answer:"):
                response = response[7:].strip()
    
    # Remove leading/trailing quotes if present
    if response.startswith('"') and response.endswith('"'):
        response = response[1:-1].strip()
    if response.startswith("'") and response.endswith("'"):
        response = response[1:-1].strip()
    
    # Remove excessive whitespace
    import re
    response = re.sub(r'\s+', ' ', response).strip()
    
    # If response is empty after initial processing, skip to fallback
    if not response:
        pass  # Will be handled by fallback logic below
    else:
        # For base models like GPT-2, responses can be incoherent
        # Try to extract the first coherent sentence or paragraph
        # Look for sentence boundaries
        sentences = re.split(r'[.!?]\s+', response)
        
        # Filter out very short or nonsensical sentences
        valid_sentences = []
        for sent in sentences:
            sent = sent.strip()
            # Skip very short sentences (< 10 chars)
            if len(sent) < 10:
                continue
            # Use coherence check for each sentence
            if not _is_coherent_text(sent):
                logger.debug(f"Skipping sentence (failed coherence check): {sent[:50]}")
                continue
            # Additional checks
            special_char_ratio = len(re.findall(r'[^\w\s]', sent)) / len(sent) if sent else 0
            if special_char_ratio > 0.35:
                logger.debug(f"Skipping sentence (high special char ratio: {special_char_ratio:.2f}): {sent[:50]}")
                continue
            number_ratio = len(re.findall(r'\d', sent)) / len(sent) if sent else 0
            if number_ratio > 0.3:
                logger.debug(f"Skipping sentence (high number ratio: {number_ratio:.2f}): {sent[:50]}")
                continue
            words = sent.split()
            if len(words) < 2:
                continue
            valid_sentences.append(sent)
            # Stop after first 2-3 coherent sentences for base models
            if len(valid_sentences) >= 3:
                break
        
        if valid_sentences:
            response = '. '.join(valid_sentences)
            if not response.endswith(('.', '!', '?')):
                response += '.'
            logger.debug(
                "Extracted valid sentences",
                extra={
                    "sentence_count": len(valid_sentences),
                    "total_sentences": len(sentences),
                },
            )
        else:
            # No valid sentences found
            response = ""
    
    # If we still don't have a valid response, try context extraction
    if not response or len(response.strip()) < 20:
            logger.warning(
                "Could not extract meaningful response from model output, attempting context extraction",
                extra={
                    "original_length": len(response),
                    "original_preview": response[:100],
                },
            )
            # Try to extract a relevant answer from the original prompt's context
            # This is a last resort - find the most relevant sentence(s) from context
            response = _extract_answer_from_context(original_prompt)
            
            if not response or len(response.strip()) < 20:
                response = "I found relevant information in the context, but I'm having difficulty generating a coherent answer. Please refer to the provided context chunks for details."
    
    # Final length limit
    max_response_length = 500  # Shorter for base models
    if len(response) > max_response_length:
        # Cut at sentence boundary
        sentences = response[:max_response_length].rsplit('.', 1)
        if len(sentences) > 1 and len(sentences[0]) > max_response_length * 0.7:
            response = sentences[0] + "."
        else:
            response = response[:max_response_length] + "..."
        logger.debug("Response truncated", extra={"final_length": len(response)})
    
    return response


class LocalLLM(LLM):
    """
    Local LLM using Hugging Face transformers.
    
    Runs models directly in Python without external runners.
    Supports any model from Hugging Face Hub that uses AutoModelForCausalLM.
    
    Features:
    - Lazy model loading (loads on first use)
    - CPU and GPU support
    - Configurable model selection
    - Memory-efficient for small models
    """
    
    def __init__(
        self,
        model_name: str = "gpt2",
        device: str = "cpu",
        max_length: int = 512,
        temperature: float = 0.7,
    ):
        """
        Initialize local LLM.
        
        Args:
            model_name: Hugging Face model identifier (e.g., 'gpt2', 'microsoft/DialoGPT-small')
            device: Device to run on ('cpu' or 'cuda')
            max_length: Maximum generation length
            temperature: Temperature for generation (0.0 = deterministic, higher = more creative)
        """
        if AutoModelForCausalLM is None or AutoTokenizer is None:
            raise ValueError(
                "transformers library not installed. "
                "Install with: pip install transformers torch"
            )
        
        self.model_name = model_name
        self.device = device
        self.max_length = max_length
        self.temperature = temperature
        
        self._model: Any = None
        self._tokenizer: Any = None
        self._loaded = False
    
    def _is_instruction_tuned(self) -> bool:
        """Detect if model is instruction-tuned based on name."""
        instruction_indicators = ["chat", "instruct", "alpaca", "vicuna", "llama-2-chat"]
        model_lower = self.model_name.lower()
        return any(indicator in model_lower for indicator in instruction_indicators)
    
    def _load_model(self) -> None:
        """Lazy load model and tokenizer on first use."""
        if self._loaded:
            return
        
        logger.info(
            "Loading local LLM model",
            extra={
                "model_name": self.model_name,
                "device": self.device,
            },
        )
        
        try:
            # Load tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            # Set pad token if not present (some models need this)
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token
            
            # Load model
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float32 if self.device == "cpu" else torch.float16,
            )
            self._model.to(self.device)
            self._model.eval()  # Set to evaluation mode
            
            # Detect if instruction-tuned
            is_instruction = self._is_instruction_tuned()
            
            self._loaded = True
            
            logger.info(
                "Local LLM model loaded successfully",
                extra={
                    "model_name": self.model_name,
                    "device": self.device,
                    "is_instruction_tuned": is_instruction,
                    "max_position_embeddings": getattr(
                        self._model.config, "max_position_embeddings", "unknown"
                    ),
                },
            )
        except Exception as e:
            logger.exception(
                "Failed to load local LLM model",
                extra={
                    "model_name": self.model_name,
                    "error": str(e),
                },
            )
            raise ValueError(f"Failed to load model {self.model_name}: {e}")
    
    def generate(self, prompt: str) -> str:
        """
        Generate text from prompt.
        
        Args:
            prompt: Input prompt text
            
        Returns:
            Generated text response
        """
        if not self._loaded:
            self._load_model()
        
        logger.debug(
            "Generating text with local LLM",
            extra={
                "model_name": self.model_name,
                "prompt_length": len(prompt),
                "max_length": self.max_length,
                "temperature": self.temperature,
                "device": self.device,
            },
        )
        
        # Log prompt preview for debugging
        logger.debug(
            "Prompt preview for generation",
            extra={
                "prompt_preview": prompt[:300] + "..." if len(prompt) > 300 else prompt,
            },
        )
        
        try:
            # Tokenize input
            inputs = self._tokenizer.encode(prompt, return_tensors="pt")
            inputs = inputs.to(self.device)
            
            # Truncate if too long (keep last N tokens that fit)
            max_input_length = self._model.config.max_position_embeddings if hasattr(self._model.config, 'max_position_embeddings') else 1024
            if inputs.shape[1] > max_input_length - self.max_length:
                # Keep the last tokens that fit
                keep_length = max_input_length - self.max_length - 10  # Leave some buffer
                inputs = inputs[:, -keep_length:]
                logger.debug(
                    "Truncated input to fit model context",
                    extra={"truncated_length": keep_length},
                )
            
            # Generate with improved parameters
            with torch.no_grad():  # Disable gradient computation for inference
                # Build generation kwargs
                input_length = inputs.shape[1]
                gen_kwargs: dict[str, Any] = {
                    "temperature": self.temperature,
                    "do_sample": self.temperature > 0.0,
                    "pad_token_id": self._tokenizer.pad_token_id,
                    "eos_token_id": self._tokenizer.eos_token_id,
                    "repetition_penalty": 1.2,  # Stronger penalty to reduce repetition
                    "no_repeat_ngram_size": 3,  # Avoid repeating 3-grams
                    "min_new_tokens": 10,  # Ensure minimum output
                }
                
                # Use max_new_tokens (preferred) or max_length (fallback)
                # Limit to reasonable length for RAG answers
                max_new_tokens = min(self.max_length, 200)  # Cap at 200 tokens for better quality
                try:
                    gen_kwargs["max_new_tokens"] = max_new_tokens
                except Exception:
                    # Fallback for older transformers versions
                    gen_kwargs["max_length"] = input_length + max_new_tokens
                
                logger.debug(
                    "Generation parameters",
                    extra={
                        "input_length": input_length,
                        "max_new_tokens": max_new_tokens,
                        "temperature": self.temperature,
                    },
                )
                
                outputs = self._model.generate(inputs, **gen_kwargs)
            
            # Decode only the newly generated tokens (skip input tokens)
            input_length = inputs.shape[1]
            generated_tokens = outputs[0][input_length:]
            raw_response = self._tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
            
            logger.debug(
                "Raw response from model",
                extra={
                    "input_tokens": input_length,
                    "generated_tokens": len(generated_tokens),
                    "raw_response_length": len(raw_response),
                    "raw_response_preview": raw_response[:200] + "..." if len(raw_response) > 200 else raw_response,
                },
            )
            
            # Post-process response
            # Remove common artifacts and improve formatting
            response = _post_process_response(raw_response, prompt)
            
            logger.debug(
                "Response after post-processing",
                extra={
                    "response_length": len(response),
                    "response_preview": response[:200] + "..." if len(response) > 200 else response,
                },
            )
            
            # Check if response is relevant to the question
            # If not, fall back to context extraction
            # Always check relevance, even for short responses
            if response and len(response.strip()) > 0:
                if not _is_response_relevant(response, prompt):
                    logger.warning(
                        "LLM response is not relevant to question, falling back to context extraction",
                        extra={
                            "response": response[:100],
                            "response_length": len(response),
                        },
                    )
                    # Extract from context instead
                    llm_response_original = response  # Save original for logging
                    context_response = _extract_answer_from_context(prompt)
                    if context_response and len(context_response.strip()) >= 20:
                        response = context_response
                        logger.info(
                            "Using context-extracted answer instead of LLM output",
                            extra={
                                "llm_response_original": llm_response_original[:100],
                                "context_response_length": len(context_response),
                                "context_response_preview": context_response[:100] + "..." if len(context_response) > 100 else context_response,
                            },
                        )
                    elif context_response:
                        # Even if short, use context response if it's more relevant
                        response = context_response
                        logger.info(
                            "Using short context-extracted answer",
                            extra={
                                "llm_response_original": llm_response_original[:100],
                                "context_response": context_response,
                            },
                        )
            
            logger.info(
                "Text generated successfully",
                extra={
                    "model_name": self.model_name,
                    "response_length": len(response),
                },
            )
            
            return response
            
        except Exception as e:
            logger.exception(
                "Text generation failed",
                extra={
                    "model_name": self.model_name,
                    "error": str(e),
                },
            )
            raise ValueError(f"Failed to generate text: {e}")

