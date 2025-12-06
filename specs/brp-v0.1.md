# Bharat-RAG Protocol (BRP) – v0.1 (Draft)

> ⚠️ This is a **draft** specification. It will evolve as the reference implementation and use-cases mature.

## 1. Introduction

The **Bharat-RAG Protocol (BRP)** defines an implementation-agnostic API for:

- Ingesting documents into logical collections
- Performing semantic retrieval over those collections

BRP is designed to be:

- **Cloud-neutral** – no dependency on a specific cloud provider
- **LLM-provider-neutral** – does not require any particular external LLM API
- **India-centric** – friendly for multilingual, scanned, and government/enterprise documents
- **Scalable** – usable from a single laptop to an India-scale cluster

This repository contains a **reference implementation** of BRP, but other
implementations (in any language/stack) are encouraged.

---

## 2. Core Concepts

- **Org**  
  A logical tenant (e.g., `"delhi-revenue"`, `"hospital-xyz"`).

- **Collection**  
  A named grouping of documents under an org (e.g., `"land-records-2024"`).

- **Document**  
  A user-level document (PDF, image, raw text, HTML, etc.).

- **Chunk**  
  The smallest retrievable unit of content. A document is usually split into multiple chunks.

- **EmbeddingConfig**  
  The configuration describing how embeddings are generated for a collection
  (e.g., model ID, dimension).

BRP does *not* mandate a specific storage engine, vector DB, or index type.

---

## 3. Authentication

BRP is agnostic to the underlying authentication system.

Recommended options for most deployments:

- **API keys** (via `X-API-Key` header), or
- **JWT bearer tokens** (via `Authorization: Bearer <token>` header)

All example requests in this document omit auth headers for brevity.

---

## 4. API Endpoints (HTTP/JSON)

Base prefix for all endpoints in this version:

```text
/brp/v0
```

### 4.1 Orgs
#### 4.1.1 Create Org

`POST /brp/v0/orgs`

Create a new logical tenant.

Request
```json
{
  "org_id": "delhi-revenue",
  "name": "Delhi Revenue Department"
}
```

Response – 201 Created

```json
{
  "org_id": "delhi-revenue",
  "name": "Delhi Revenue Department",
  "created_at": "2025-01-01T10:00:00Z"
}
```

### 4.2 Collections
#### 4.2.1 Create Collection

`POST /brp/v0/orgs/{org_id}/collections`

Creates a new collection under an existing org.

Request

```json
{
  "collection_id": "land-records-2024",
  "display_name": "Land Records 2024",
  "embedding": {
    "text_model_id": "brag-multi-mini-256",
    "dim": 256
  },
  "metadata_schema": {
    "state": "string",
    "district": "string",
    "language": "string"
  }
}
```

Response – 201 Created

```json
{
  "org_id": "delhi-revenue",
  "collection_id": "land-records-2024",
  "display_name": "Land Records 2024",
  "created_at": "2025-01-01T10:05:00Z"
}
```

### 4.3 Documents
#### 4.3.1 Ingest Raw Text Document

`POST /brp/v0/orgs/{org_id}/collections/{collection_id}/documents/raw-text`

Ingests a single raw-text document into a collection.
The server is free to chunk the text internally.

Request

```json
{
  "document_id": "doc-123",
  "text": "big string of text…",
  "metadata": {
    "state": "DL",
    "district": "South",
    "language": "en-IN"
  },
  "ingest_mode": "async"
}
```

Response – 202 Accepted

```json
{
  "job_id": "ingest-doc-123",
  "status": "QUEUED"
}
```

(Future versions of this spec will define document ingestion for PDFs, images, and status polling.)

### 4.4 Query
#### 4.4.1 Retrieve Only

`POST /brp/v0/orgs/{org_id}/collections/{collection_id}/query`

Executes a retrieval query over a collection.

Request
```json
{
  "query": "land records for South district before 2010",
  "top_k": 5,
  "filters": {
    "district": "South",
    "language": "en-IN"
  },
  "mode": "retrieve_only"
}
```

Response – 200 OK
```jaon
{
  "results": [
    {
      "chunk_id": "chunk-001",
      "document_id": "doc-123",
      "score": 0.86,
      "text": "…snippet…",
      "metadata": {
        "page": 3,
        "state": "DL",
        "district": "South"
      }
    }
  ],
  "protocol": "brp-v0.1"
}
```

## 5. Error Handling

BRP recommends standard HTTP status codes and a common error envelope.

Example
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Missing required field 'collection_id'",
    "details": {}
  }
}
```

## 6. Versioning

- This document describes BRP v0.1 (Draft).
- Minor revisions (v0.2, v0.3, …) should remain backward compatible where possible.
- Breaking changes will result in a major version bump (v1.0, v2.0, …).

## 7. Security & Privacy (High-Level)

- Deployments should enforce auth and authorization at the gateway.
- Sensitive document content may need to be encrypted at rest.
- Implementations deployed in India should consider applicable regulations
(e.g., DPDP) and domain-specific rules (healthcare, finance, etc.).

## 8. Open Questions

Some items intentionally left open for community discussion:
- Recommended minimal metadata fields for Indian government/enterprise docs
- Standardization of state/district codes
- Optional gRPC mapping for the same semantics
- Streaming variants of the query endpoint
