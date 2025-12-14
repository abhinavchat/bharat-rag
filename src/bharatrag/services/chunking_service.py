class ChunkingService:
    def chunk(self, text: str, chunk_size: int = 500, overlap: int = 50):
        words = text.split()
        chunks = []
        start = 0
        idx = 0

        while start < len(words):
            end = start + chunk_size
            chunk_text = " ".join(words[start:end])
            chunks.append((idx, chunk_text))
            idx += 1
            start += chunk_size - overlap

        return chunks
