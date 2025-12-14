# **Product Requirements Document (PRD)**

## **Bharat-RAG (BRP Protocol & Reference Implementation)**

---

## 1. Purpose & Vision

### 1.1 Purpose

Bharat-RAG is an **India-centric, open, extensible Retrieval-Augmented Generation (RAG) system** designed to operate as:

* a **protocol (BRP – Bharat-RAG Protocol)** for interoperable knowledge ingestion, retrieval, and answering
* a **reference implementation** demonstrating one correct, scalable, fault-tolerant realization of the protocol

The system prioritizes **sovereignty, portability, efficiency, and architectural correctness** over vendor lock-in or opaque SaaS dependency.

---

### 1.2 Vision

Enable individuals, organizations, and public institutions in India to:

* build **private, local, or sovereign knowledge systems**
* ingest heterogeneous data formats (text, documents, media, 3D, web)
* retrieve and answer queries transparently
* interoperate across implementations via a common protocol

Bharat-RAG is intended to be:

* **Protocol-first**
* **Cloud-agnostic**
* **LLM-agnostic**
* **India-stack friendly**
* **Deployable from laptop → data center**

---

## 2. Scope

### In Scope

* BRP protocol definition (API, resources, semantics)
* Reference server implementation (single-user → org-scale)
* Asynchronous ingestion & job tracking
* Multimodal ingestion support
* Retrieval and answer synthesis
* Single-user dashboard

### Out of Scope (v0.x)

* Model training or fine-tuning
* Federated RAG across organizations
* Real-time collaborative editing
* Fully distributed multi-region orchestration

---

## 3. Users & Personas

### 3.1 Primary Personas

#### A. Individual Power User

* Runs Bharat-RAG locally
* Ingests PDFs, notes, videos, websites
* Wants transparency & source attribution

#### B. Organization / Enterprise

* Hosts Bharat-RAG internally
* Integrates with internal systems
* Requires auditability & access control

#### C. Government / Public Institution

* Sovereign deployment
* Sensitive datasets
* Compliance, explainability, provenance

#### D. Protocol Implementer

* Implements BRP in a different language or stack
* Needs clear, stable, vendor-neutral specification

---

## 4. Core Design Principles

### Protocol-First

* BRP defines **observable behavior**
* Reference implementation is non-normative

### Asynchronous by Default

* All ingestion is job-based
* Non-blocking API guarantees

### Deterministic Semantics

* Clear state transitions
* Explicit success/failure guarantees

### Memory & Resource Efficiency

* Chunk-level processing
* No hidden full-document loads

### Sovereignty & Portability

* No hard dependency on foreign cloud providers
* Runs on Indian or on-prem infrastructure

---

## 5. System Overview

### 5.1 Logical Architecture

```
Client
  |
BRP API Layer
  |
Ingestion Jobs  ←→  Job Store
  |
Extractors / OCR / STT / Parsers
  |
Chunk Store  ←→  Vector Index
  |
Retriever  ←→  LLM Backend
```

---

## 6. Bharat-RAG Protocol (BRP)

> **Normative section**
> Anyone can implement BRP without using this repository.

---

### 6.1 Core Resources

| Resource     | Description                   |
| ------------ | ----------------------------- |
| Org          | Administrative namespace      |
| Collection   | Logical grouping of documents |
| Document     | One logical source of content |
| Chunk        | Smallest retrievable unit     |
| IngestionJob | Async processing unit         |
| Query        | Retrieval request             |
| Answer       | Retrieval + synthesis         |

---

### 6.2 Ingestion (Protocol)

#### Endpoint

```
POST /brp/v0/orgs/{org_id}/collections/{collection_id}/ingest
```

#### Characteristics

* Asynchronous
* One job produces **at least one Document**
* Server MUST return immediately with `job_id`

#### Response

```json
{
  "job_id": "ingest-uuid",
  "document_id": "doc-uuid",
  "status": "PENDING"
}
```

---

### 6.3 IngestionJob (Protocol Resource)

#### Status Enum

```
PENDING | RUNNING | COMPLETED | PARTIAL | FAILED | CANCELED
```

#### Guarantees

| Status    | Meaning                             |
| --------- | ----------------------------------- |
| COMPLETED | All produced chunks are queryable   |
| PARTIAL   | Some chunks available, errors exist |
| FAILED    | No usable output                    |
| RUNNING   | Not queryable yet                   |

---

### 6.4 Job Status Endpoint

```
GET /brp/v0/ingestion/jobs/{job_id}
```

Returns a complete, implementation-independent view of progress and errors.

---

### 6.5 Supported Source Kinds (Protocol)

| Kind        | Examples                    |
| ----------- | --------------------------- |
| inline_text | txt, md                     |
| file_ref    | pdf, docx, image, video, 3d |
| url         | website                     |
| media       | video/audio                 |

The protocol defines **fields and meaning**, not extraction technique.

---

### 6.6 Retrieval

```
POST /brp/v0/orgs/{org_id}/collections/{collection_id}/query
```

Returns ranked chunks with metadata and provenance.

---

### 6.7 Answering (RAG)

```
POST /brp/v0/orgs/{org_id}/collections/{collection_id}/answer
```

* MUST include:

  * synthesized answer
  * supporting chunks
  * confidence / provenance metadata

---

## 7. Reference Implementation (Non-Normative)

> Demonstrates one correct realization of BRP.

---

### 7.1 Implementation Scope

* FastAPI server
* SQLite/Postgres metadata store
* Qdrant/FAISS vector store
* Pluggable LLM backends
* Background job workers

---

### 7.2 Ingestion Pipeline (Reference)

```
Request → Job → Handler → Chunks → Embeddings → Index → Job Complete
```

Each format has its own handler implementing a shared interface.

---

### 7.3 Supported Formats (Reference v0)

| Format          | Status                           |
| --------------- | -------------------------------- |
| PDF             | Text, basic tables               |
| TXT / MD / DOCX | Full                             |
| Image           | OCR                              |
| Video           | Audio transcription              |
| Website         | Article extraction               |
| 3D              | Metadata + preview + description |

---

### 7.4 Dashboard

Single-user web UI:

* Collection management
* Ingestion upload
* Job monitoring
* Query & answer UI
* Source attribution display

---

## 8. Non-Functional Requirements

### Performance

* Chunk-level processing
* Streaming for large files

### Reliability

* Idempotent ingestion
* Partial success allowed

### Security

* No mandatory external calls
* Clear data ownership

### Portability

* Docker-based deployment
* Works without Kubernetes

---

## 9. India-Centric Considerations

* Hindi / Indic language support
* Local OCR/STT options
* India-based cloud compatibility
* Integration potential with:

  * DigiLocker
  * India Stack (future)
  * Government document corpora

---

## 10. Success Metrics

| Metric                 | Target                               |
| ---------------------- | ------------------------------------ |
| Spec implementability  | Independent implementations possible |
| Ingestion transparency | Full job traceability                |
| Resource usage         | Runs on laptop                       |
| Explainability         | Sources always visible               |
| Adoption               | Multiple non-fork protocol users     |

---

## 11. Roadmap (High-Level)

### v0.x

* Single-user reference
* Core protocol stabilized

### v1.x

* Multi-tenant orgs
* Access control
* Batch ingestion

### v2.x

* Distributed ingestion
* Federation
* Inter-BRP interoperability

---

## 12. Open Questions

* Batch ingestion semantics
* Protocol version negotiation
* Long-term embedding format standardization
* Cross-collection reasoning

---

## 13. Summary

Bharat-RAG is **not just another RAG framework**.

It is:

* a **protocol**
* a **reference system**
* a **sovereign knowledge substrate**

The protocol defines *what must be true*; the implementation shows *one way to make it true*.
