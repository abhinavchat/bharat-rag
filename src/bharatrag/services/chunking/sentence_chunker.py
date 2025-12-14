"""
Sentence-aware chunker that respects sentence and word boundaries.

Splits text into sentences first, then combines sentences into chunks
of appropriate size while preserving semantic units.
"""
from __future__ import annotations

import re
import logging

logger = logging.getLogger(__name__)


class SentenceChunker:
    """
    Chunker that respects sentence boundaries.
    
    Splits text into sentences first, then combines sentences into chunks
    of approximately the target size, preserving word and sentence boundaries.
    """
    
    def __init__(self, *, chunk_size: int = 800, overlap: int = 120):
        """
        Initialize sentence-aware chunker.
        
        Args:
            chunk_size: Target chunk size in characters (approximate)
            overlap: Overlap size in characters between chunks (approximate)
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be in [0, chunk_size)")
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk(self, text: str) -> list[tuple[int, str]]:
        """
        Chunk text into sentences, then combine into appropriately-sized chunks.
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of (chunk_index, chunk_text) tuples
        """
        t = (text or "").strip()
        if not t:
            return [(0, "")]
        
        # Step 1: Split into sentences
        sentences = self._split_into_sentences(t)
        
        if not sentences:
            return [(0, t)]
        
        logger.debug(
            "Text split into sentences",
            extra={
                "sentence_count": len(sentences),
                "text_length": len(t),
            },
        )
        
        # Step 2: Combine sentences into chunks
        chunks: list[tuple[int, str]] = []
        current_chunk: list[str] = []
        current_length = 0
        chunk_idx = 0
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_length = len(sentence) + 1  # +1 for space separator
            
            # Check if adding this sentence would exceed chunk size
            if current_length + sentence_length > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = " ".join(current_chunk)
                if chunk_text:
                    chunks.append((chunk_idx, chunk_text))
                    chunk_idx += 1
                
                # Calculate overlap: keep last N sentences from the chunk we just saved
                # that fit within overlap size
                overlap_sentences: list[str] = []
                overlap_length = 0
                
                # Work backwards from end of saved chunk
                for s in reversed(current_chunk):
                    s_len = len(s) + 1
                    if overlap_length + s_len <= self.overlap:
                        overlap_sentences.insert(0, s)
                        overlap_length += s_len
                    else:
                        break
                
                # Start new chunk with overlap (if any)
                if overlap_sentences:
                    current_chunk = overlap_sentences.copy()
                    current_length = overlap_length
                else:
                    # No overlap possible (sentence too long or overlap too small), start fresh
                    current_chunk = []
                    current_length = 0
            
            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # Add final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if chunk_text:
                chunks.append((chunk_idx, chunk_text))
        
        logger.debug(
            "Text chunked into sentences",
            extra={
                "chunk_count": len(chunks),
                "sentence_count": len(sentences),
                "avg_chunk_length": sum(len(c[1]) for c in chunks) / len(chunks) if chunks else 0,
            },
        )
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> list[str]:
        """
        Split text into sentences.
        
        Uses regex to find sentence boundaries while handling:
        - Periods in abbreviations (e.g., "Dr.", "U.S.A.")
        - Question marks and exclamation marks
        - Multiple spaces/newlines
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        # Pattern to match sentence endings
        # Matches: . ! ? followed by space and capital letter, or end of string
        # But avoids matching periods in abbreviations
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])\s*$'
        
        # Split by sentence boundaries
        sentences = re.split(sentence_pattern, text)
        
        # Clean up sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                # Remove excessive whitespace
                sentence = re.sub(r'\s+', ' ', sentence)
                cleaned_sentences.append(sentence)
        
        # If no sentences found (no punctuation), treat entire text as one sentence
        if not cleaned_sentences:
            cleaned_sentences = [text]
        
        return cleaned_sentences

