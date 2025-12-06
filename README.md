# Bharat-RAG

**Bharat-RAG** is an India-centric, cloud-neutral, protocol-first **retrieval engine** for multimodal documents (text, PDFs, scanned images, etc.).

The project has two main goals:

1. Define the **Bharat-RAG Protocol (BRP)** for ingestion and retrieval.
2. Provide a **lightweight reference implementation** that can run:
   - on a single laptop (individual users)
   - on-prem / government / enterprise clusters (India-scale)

> ⚠️ Status: **Pre-Alpha / Design Phase**  
> The `main` branch currently contains only documentation and repo scaffolding.  
> All code will be added via feature branches and merged through pull requests.

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

## Repository Layout (High-Level)

```text
bharat-rag/
  specs/                 # BRP protocol specifications (e.g. brp-v0.1.md)
  src/                   # Reference implementation (to be added later via PRs)
  tests/                 # Automated tests
  infra/                 # Docker/K8s manifests, etc.
  .github/               # GitHub workflows and templates
  README.md
  ROADMAP.md
  CONTRIBUTING.md
  CODE_OF_CONDUCT.md
  LICENSE
