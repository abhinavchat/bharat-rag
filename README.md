# Bharat-RAG

**Bharat-RAG** is an India-centric, cloud-neutral, protocol-first **retrieval engine** for multimodal documents (text, PDFs, scanned images, videos, websites, etc.).

The project has two main goals:

1. Define the **Bharat-RAG Protocol (BRP)** for ingestion and retrieval ([See the specification in detail](docs/PRD.md).).
2. Provide a **lightweight reference implementation** that can run:
   - on a single laptop (individual users)
   - on-prem / government / enterprise clusters (India-scale)

> 🚧 Status: **Pre-Alpha / Active Development**  
> Core ingestion, retrieval, and RAG answering features are implemented.

---

## Design Principles

- **Protocol-first**: BRP is defined as a JSON/HTTP spec that anyone can implement.
- **Implementation-agnostic**: No requirement on a specific DB, vector store, or cloud.
- **Lightweight & memory-efficient**: Favour small local models, batching, and streaming.
- **Fault-tolerant**: Queue-based ingestion, stateless services, retries & dead-letter queues.
- **Cloud-neutral**: Can run on bare metal or any cloud; prefers open components.
- **India-centric**: Designed for multilingual, scanned, and government/enterprise documents,  
  with future integration into India Stack services.

---

## Current Features

### ✅ Implemented

- **Core Data Models**: Collections, Documents, Chunks, Ingestion Jobs
- **Text Ingestion**: Plain text, Markdown, DOCX files
- **PDF Ingestion**: Page-by-page extraction with metadata
- **Image Ingestion**: OCR using EasyOCR (English & Hindi support)
- **Video Ingestion**: Audio extraction and transcription using Whisper
- **Website Ingestion**: Article extraction from web pages
- **Retrieval API**: Semantic search with vector similarity
- **RAG Answering**: Context-aware answers with citations (local LLM support)
- **Local LLM Integration**: Hugging Face transformers-based local LLM (no external APIs)
- **Job Tracking**: Async ingestion with progress monitoring
- **Observability**: Request-scoped logging with context tracking

### 🚧 Planned

- Advanced chunking strategies
- Multi-tenant support
- Dashboard UI
- 3D asset ingestion (future)

---

## Quick Start

### Prerequisites

- **Python 3.12+**
- **PostgreSQL** with `pgvector` extension
- **ffmpeg** (for video processing)
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt-get install ffmpeg`
  - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/bharat-rag.git
   cd bharat-rag
   ```

2. **Install dependencies**
   ```bash
   # Install uv (Python package manager)
   pip install uv
   
   # Install project dependencies
   uv sync
   ```

3. **Set up database**
   ```bash
   # Create PostgreSQL database with pgvector
   createdb bharatrag
   psql bharatrag -c "CREATE EXTENSION vector;"
   
   # Set database URL (or use .env file)
   export DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/bharatrag"
   ```

4. **Run migrations**
   ```bash
   uv run alembic upgrade head
   ```

5. **Configure LLM (Optional)**
   
   By default, Bharat-RAG uses a simple extractive LLM. To use a local Hugging Face model:
   
   ```bash
   # Use local LLM (runs models directly, no external APIs)
   export BHARATRAG_LLM_BACKEND=local
   export BHARATRAG_LLM_MODEL_NAME=gpt2  # or any Hugging Face model
   export BHARATRAG_LLM_DEVICE=cpu  # or 'cuda' if GPU available
   ```
   
   **Recommended Models:**
   - `gpt2` - Very small, fast, good for testing (default)
   - `microsoft/DialoGPT-small` - Small conversational model
   - `TinyLlama/TinyLlama-1.1B-Chat-v1.0` - Instruction-tuned, better quality (requires more memory)
   
   **Note:** Models are downloaded from Hugging Face on first use. Ensure you have sufficient disk space (models can be 500MB-2GB+).

6. **Start the server**
   ```bash
   uv run uvicorn bharatrag.main:app --reload
   ```

The API will be available at `http://localhost:8000`

### API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Supported Formats

| Format | Source Type | Features |
|--------|-------------|----------|
| `txt`, `md`, `docx` | `file` | Full text extraction |
| `pdf` | `file` | Page-by-page extraction, metadata |
| `png`, `jpg`, `jpeg` | `file` | OCR (English & Hindi) |
| `mp4`, `avi`, `mov` | `file` | Audio transcription with timestamps |
| `html` | `url` | Article extraction, metadata |

---

## Example Usage

### 1. Create a Collection

```bash
curl -X POST "http://localhost:8000/collections" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-documents"}'
```

### 2. Ingest a Document

```bash
curl -X POST "http://localhost:8000/ingestion-jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_id": "<collection-id>",
    "source_type": "file",
    "format": "pdf",
    "uri": "file:///path/to/document.pdf"
  }'
```

### 3. Query for Relevant Chunks

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_id": "<collection-id>",
    "query": "What is the main topic?",
    "top_k": 5
  }'
```

### 4. Get an Answer with Citations

```bash
curl -X POST "http://localhost:8000/answer" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_id": "<collection-id>",
    "question": "What is the main topic?",
    "top_k": 5
  }'
```

---

## Configuration

### LLM Backend Configuration

Bharat-RAG supports two LLM backends:

1. **Extractive LLM (Default)**: Simple, deterministic fallback that extracts and summarizes context
2. **Local LLM**: Uses Hugging Face transformers to run models locally (no external APIs)

**Environment Variables:**

```bash
# LLM Backend Selection
BHARATRAG_LLM_BACKEND=local  # or 'extractive' (default)

# Local LLM Settings (only used when LLM_BACKEND=local)
BHARATRAG_LLM_MODEL_NAME=gpt2  # Hugging Face model identifier
BHARATRAG_LLM_DEVICE=cpu  # 'cpu' or 'cuda' (for GPU)
BHARATRAG_LLM_MAX_LENGTH=512  # Maximum generation length
BHARATRAG_LLM_TEMPERATURE=0.7  # Generation temperature (0.0-2.0)
```

**Recommended Models:**

| Model | Size | Quality | Use Case |
|-------|------|---------|----------|
| `gpt2` | ~500MB | Basic | Testing, development |
| `microsoft/DialoGPT-small` | ~500MB | Good | Conversational Q&A |
| `TinyLlama/TinyLlama-1.1B-Chat-v1.0` | ~2GB | Better | Production (if resources allow) |

**Note:** 
- Models are downloaded from Hugging Face on first use
- Ensure sufficient disk space (500MB-2GB+ depending on model)
- CPU inference can be slow; GPU recommended for better performance
- All processing is local - no external API calls

---

## Development

### Running Tests

```bash
# Run all tests (without database)
BHARATRAG_RUN_DB_TESTS=0 uv run pytest

# Run all tests (with database)
BHARATRAG_RUN_DB_TESTS=1 uv run pytest

# Run specific test file
uv run pytest tests/unit/test_pdf_ingestion.py -v
```

### Code Quality

```bash
# Format and lint
uv run ruff check src/
uv run ruff format src/
```

### Docker

```bash
# Build image
docker build -t bharat-rag .

# Run container
docker run -p 8000:8000 bharat-rag
```

---

## Repository Layout

```text
bharat-rag/
  docs/                   # Documentation (PRD, etc.)
  specs/                  # BRP protocol specifications
  src/bharatrag/          # Reference implementation
    api/                  # FastAPI endpoints
    domain/               # Domain models
    services/             # Business logic
      ingestion_handlers/ # Format-specific handlers
    db/                   # Database models & migrations
  tests/                  # Automated tests
  infra/                  # Docker/K8s manifests
  .github/                # GitHub workflows and templates
  README.md
  CONTRIBUTING.md
  LICENSE
```

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
