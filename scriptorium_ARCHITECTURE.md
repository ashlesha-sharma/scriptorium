# Scriptorium — System Architecture & Setup Guide

> Domain-adaptive RAG Research Intelligence System  
> Version 1.0 · Production MVP

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [System Architecture](#2-system-architecture)
3. [Data Flow Diagram](#3-data-flow-diagram)
4. [Complete Folder Structure](#4-complete-folder-structure)
5. [Module-by-Module Breakdown](#5-module-by-module-breakdown)
6. [Domain Intelligence Layer](#6-domain-intelligence-layer)
7. [RAG Pipeline Deep Dive](#7-rag-pipeline-deep-dive)
8. [Frontend Architecture](#8-frontend-architecture)
9. [API Reference](#9-api-reference)
10. [Setup & Installation](#10-setup--installation)
11. [Environment Configuration](#11-environment-configuration)
12. [Free API Strategy](#12-free-api-strategy)
13. [Performance Characteristics](#13-performance-characteristics)
14. [Known Limitations & Roadmap](#14-known-limitations--roadmap)

---

## 1. Product Overview

### Core Insight

High-value knowledge across domains is locked inside unstructured PDFs. Scriptorium transforms static documents into dynamic, queryable knowledge systems through a domain-adaptive RAG pipeline that understands *what kind of document it is processing* — and adjusts its extraction logic, prompt templates, and output structure accordingly.

### What Makes It Different from Generic RAG

| Feature | Generic RAG | Scriptorium |
|---------|------------|-------------|
| Domain awareness | None | Chemistry / Finance / Law / Policy / General |
| Extraction logic | One-size-fits-all | Domain-routed handlers |
| Output structure | Free-form prose | Structured citations, tables, typed insights |
| OCR support | Rarely | Tesseract on scanned pages |
| Chunking strategy | Fixed token split | Semantic + structural boundary-aware |
| Retrieval | Top-k cosine | MMR (relevance + diversity) reranking |
| Highlight-to-query | No | Native text selection → context anchor |
| Multi-doc comparison | No | Cross-document MMR retrieval + comparison mode |

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SCRIPTORIUM SYSTEM                                │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         FRONTEND (Next.js)                           │  │
│  │                                                                      │  │
│  │  ┌─────────────┐    ┌──────────────────┐    ┌──────────────────┐   │  │
│  │  │   Sidebar   │    │  Document Viewer  │    │   Chat Panel     │   │  │
│  │  │  (Zustand)  │    │  (PDF iframe +    │    │  (Messages +     │   │  │
│  │  │             │    │   Highlight UI)   │    │   Input +        │   │  │
│  │  │  • Upload   │    │                  │    │   Citations +    │   │  │
│  │  │  • Library  │    │  Text Selection  │    │   Insights)      │   │  │
│  │  │  • Select   │    │  → "Ask about    │    │                  │   │  │
│  │  │  • Status   │    │    selection"    │    │  Mode Switcher:  │   │  │
│  │  └─────────────┘    └──────────────────┘    │  Convo/Extract/  │   │  │
│  │                                              │  Summary/Compare │   │  │
│  │  ┌───────────────────────────────────────┐  └──────────────────┘   │  │
│  │  │           Top Bar                     │                          │  │
│  │  │  Document context · Mode selector ·   │                          │  │
│  │  │  Explain level (ELI5/Intermediate/    │                          │  │
│  │  │  Expert)                              │                          │  │
│  │  └───────────────────────────────────────┘                          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │ HTTP/REST                              │
│                                    ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        BACKEND (FastAPI)                             │  │
│  │                                                                      │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐    │  │
│  │  │  /documents    │  │  /chat         │  │  /documents/{id}   │    │  │
│  │  │  • POST upload │  │  • POST query  │  │  • GET /file       │    │  │
│  │  │  • GET status  │  │  • POST compare│  │  • GET /status     │    │  │
│  │  │  • GET list    │  │                │  │  • DELETE          │    │  │
│  │  │  • POST insight│  │                │  │                    │    │  │
│  │  └────────────────┘  └────────────────┘  └────────────────────┘    │  │
│  │                                                                      │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │                    PROCESSING PIPELINE                        │  │  │
│  │  │                                                              │  │  │
│  │  │  ┌──────────┐  ┌──────────┐  ┌─────────────┐  ┌────────┐  │  │  │
│  │  │  │Ingestion │→ │  Domain  │→ │   Chunker   │→ │Embedder│  │  │  │
│  │  │  │(PyMuPDF+ │  │Detector  │  │(Semantic +  │  │(all-   │  │  │  │
│  │  │  │Tesseract)│  │(keyword+ │  │Structural)  │  │MiniLM) │  │  │  │
│  │  │  │          │  │ pattern) │  │             │  │        │  │  │  │
│  │  │  └──────────┘  └──────────┘  └─────────────┘  └────────┘  │  │  │
│  │  │                                                    │         │  │  │
│  │  │                                                    ▼         │  │  │
│  │  │                                           ┌──────────────┐  │  │  │
│  │  │                                           │  ChromaDB    │  │  │  │
│  │  │                                           │  (Persistent │  │  │  │
│  │  │                                           │   vectors)   │  │  │  │
│  │  │                                           └──────┬───────┘  │  │  │
│  │  │                                                  │           │  │  │
│  │  │  ┌──────────────────────────────────────────────▼─────┐    │  │  │
│  │  │  │                  RAG PIPELINE                       │    │  │  │
│  │  │  │                                                     │    │  │  │
│  │  │  │  Query → Retrieve (MMR) → Prompt Build              │    │  │  │
│  │  │  │       → HuggingFace LLM → Post-process              │    │  │  │
│  │  │  │       → Citations → Structured Insights             │    │  │  │
│  │  │  └─────────────────────────────────────────────────────┘    │  │  │
│  │  └──────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌──────────────────────────────────────┐                                  │
│  │  EXTERNAL (FREE TIER)                │                                  │
│  │  HuggingFace Inference API           │                                  │
│  │  Mistral-7B-Instruct-v0.3            │                                  │
│  └──────────────────────────────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Flow Diagram

### Upload + Processing Flow

```
User drops PDF
      │
      ▼
POST /api/documents/upload
      │
      ├─ Save raw PDF → /data/uploads/{doc_id}.pdf
      ├─ Register in DocumentStore (stage: UPLOADING)
      └─ Fire background task ──────────────────────────────────┐
                                                                 │
                                         ┌───────────────────────▼──────┐
                                         │   Background Processing      │
                                         │                              │
                                         │  1. PyMuPDF: extract text    │
                                         │     per page                 │
                                         │                              │
                                         │  2. Per page: text density   │
                                         │     < 50 chars?              │
                                         │     YES → Tesseract OCR      │
                                         │     NO  → use native text    │
                                         │                              │
                                         │  3. DomainDetector.detect()  │
                                         │     keyword freq + patterns  │
                                         │     → domain + confidence    │
                                         │                              │
                                         │  4. SmartChunker.chunk()     │
                                         │     structural boundaries    │
                                         │     → List[TextChunk]        │
                                         │                              │
                                         │  5. EmbeddingEngine.embed()  │
                                         │     sentence-transformers    │
                                         │     all-MiniLM-L6-v2         │
                                         │     → (N, 384) float32       │
                                         │                              │
                                         │  6. VectorStore.add_chunks() │
                                         │     ChromaDB upsert          │
                                         │                              │
                                         │  7. Stage → READY            │
                                         └──────────────────────────────┘

Frontend polls GET /api/documents/{id}/status every 2s
→ updates progress bar in sidebar
→ document becomes queryable
```

### Query Flow

```
User types query + hits Enter
         │
         ▼
POST /api/chat/query
{
  query: "...",
  doc_ids: ["abc123", "def456"],
  mode: "conversational",
  explain_level: "expert",
  highlight_text: "optional selection",
  conversation_history: [...]
}
         │
         ▼
RAGPipeline.query()
         │
         ├─ 1. Get domain from doc metadata
         │
         ├─ 2. _detect_query_mode()
         │      "compare X vs Y"   → COMPARISON
         │      "extract all..."   → EXTRACTION
         │      "summarize..."     → SUMMARY
         │      otherwise          → CONVERSATIONAL
         │
         ├─ 3. Build retrieval query
         │      query + highlight_text (if present)
         │
         ├─ 4. VectorStore.retrieve()
         │      query_embedding = embed(query)
         │      ChromaDB cosine search (top 12)
         │      MMR rerank → top 6
         │      (filtered to selected doc_ids)
         │
         ├─ 5. build_system_prompt(domain, mode, explain_level)
         │      BASE_SYSTEM
         │      + DOMAIN_ADDITIONS[domain]   ← chemistry/finance/law/etc
         │      + MODE_ADDITIONS[mode]       ← extraction/comparison/etc
         │      + EXPLAIN_LEVELS[level]      ← eli5/intermediate/expert
         │
         ├─ 6. build_rag_prompt(query, chunks, history, highlight)
         │      formats context as:
         │      --- Chunk 1 [Doc: abc123, p.4] ---
         │      {text}
         │      --- Chunk 2 [Doc: def456, p.7] ---
         │      {text}
         │      [User query]
         │      {query}
         │
         ├─ 7. HuggingFaceLLM.generate()
         │      POST api-inference.huggingface.co
         │      model: mistralai/Mistral-7B-Instruct-v0.3
         │      → raw response text
         │
         ├─ 8. _clean_response() — strip instruction tokens
         │
         ├─ 9. _build_citations() — chunk metadata → Citation objects
         │
         ├─ 10. _parse_structured_insights() — JSON extraction for EXTRACTION mode
         │
         └─ 11. Return ChatResponse {answer, citations, insights, confidence, follow_ups}
```

---

## 4. Complete Folder Structure

```
scriptorium/
│
├── backend/
│   ├── main.py                      # FastAPI app entry point, lifespan hooks
│   ├── config.py                    # Pydantic settings, env loading
│   ├── requirements.txt
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py               # All Pydantic request/response models
│   │                                #   Domain, ProcessingStage, ChatRequest,
│   │                                #   ChatResponse, Citation, StructuredInsight,
│   │                                #   AutoInsightResponse, ComparisonResponse
│   │
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── ingestion.py             # PDF parsing + OCR (PyMuPDF + Tesseract)
│   │   ├── domain_detection.py      # Keyword+pattern domain classifier
│   │   ├── chunking.py              # Semantic+structural smart chunker
│   │   ├── vector_store.py          # ChromaDB + sentence-transformers wrapper
│   │   ├── rag.py                   # Full RAG pipeline orchestrator
│   │   └── document_store.py        # In-memory+JSON document state registry
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── documents.py             # Upload, status, list, delete, insights
│   │   ├── chat.py                  # Query, compare endpoints
│   │   └── files.py                 # PDF file serving for viewer
│   │
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── templates.py             # Domain-specific prompt templates
│   │                                #   BASE_SYSTEM, DOMAIN_ADDITIONS,
│   │                                #   MODE_ADDITIONS, EXPLAIN_LEVELS
│   │
│   ├── agents/
│   │   └── __init__.py              # (Extension point for agent layer v2)
│   │
│   └── data/
│       ├── uploads/                 # Raw PDF files: {doc_id}.pdf
│       └── chroma/                  # ChromaDB persistent storage
│
├── frontend/
│   ├── pages/
│   │   ├── _app.js                  # App wrapper, Toaster
│   │   ├── _document.js             # HTML head, font imports
│   │   └── index.js                 # Main layout (Sidebar + TopBar + Viewer + Chat)
│   │
│   ├── components/
│   │   ├── Layout/
│   │   │   ├── Sidebar.js           # Document library, upload dropzone, status
│   │   │   └── TopBar.js            # Mode switcher, explain level, context pill
│   │   │
│   │   ├── Document/
│   │   │   └── DocumentViewer.js    # PDF iframe, zoom, page nav, highlight popup
│   │   │
│   │   ├── Chat/
│   │   │   ├── ChatPanel.js         # Message list, toolbar, compare bar, export
│   │   │   ├── MessageBubble.js     # User/AI/Loading/Error message renderers
│   │   │   └── ChatInput.js         # Textarea, highlight banner, send button
│   │   │
│   │   └── Intelligence/
│   │       └── InsightPanel.js      # Auto-insight panel (summary + findings)
│   │
│   ├── lib/
│   │   ├── store.js                 # Zustand global state
│   │   └── api.js                   # Axios API client
│   │
│   ├── styles/
│   │   └── globals.css              # Tailwind base + custom components + fonts
│   │
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── package.json
│
└── ARCHITECTURE.md                  # This file
```

---

## 5. Module-by-Module Breakdown

### `pipeline/ingestion.py` — DocumentIngester

Responsibility: transform raw PDF bytes into structured page-level text.

Key decisions:
- Uses **PyMuPDF** (fitz) as primary extractor — faster and more accurate than pdfplumber for native PDFs
- Text density heuristic: if a page has fewer than 50 characters after extraction, it is treated as a scanned image and routed to Tesseract
- OCR preprocessing: converts to grayscale before Tesseract to improve accuracy on low-contrast scans
- Hyphenated line-break repair: `(\w)-\n(\w)` → `\1\2` prevents broken compound words
- Page markers `[PAGE N]` are injected into full text to preserve page attribution through chunking

### `pipeline/domain_detection.py` — DomainDetector

Responsibility: classify document domain with no ML model overhead.

Mechanism:
- 5 domain vocabularies, each with ~40 keyword signals and 4-6 regex patterns
- Keyword score = `(hits / total_words) × 1000 × weight`
- Pattern score = presence-based, capped at 5 matches per pattern to avoid over-weighting repetitive docs
- Confidence = `best_score / total_score` (softmax-like normalization)
- Falls back to `GENERAL` if max score < 0.5 (below noise floor)

Why keyword-based over a model: Zero latency, zero dependencies, deterministic, debuggable, easily extensible. For an MVP processing academic/professional PDFs, domain vocabulary coverage is consistently adequate. A fine-tuned classifier can be slotted in later behind the same interface.

### `pipeline/chunking.py` — SmartChunker

Responsibility: split document text into semantically coherent, size-bounded chunks.

Strategy (3-layer hierarchy):
1. **Table isolation** — pipe-delimited tables are extracted whole before splitting (preserves column alignment)
2. **Structural boundaries** — split on `\n\n+` (paragraph breaks), with domain-specific overrides (chemistry equations stay together; legal clauses stay together)
3. **Greedy merge with overlap** — segments are merged greedily into `CHUNK_SIZE` word budgets; the last `CHUNK_OVERLAP` words of each chunk carry forward to the next for context continuity

Default parameters: `CHUNK_SIZE=512 words`, `CHUNK_OVERLAP=64 words`

### `pipeline/vector_store.py` — VectorStore + EmbeddingEngine

Responsibility: store and retrieve chunk embeddings.

**EmbeddingEngine**: wraps `sentence-transformers/all-MiniLM-L6-v2`
- 22M parameters, 384-dimensional output
- L2-normalized embeddings (cosine similarity = dot product)
- Batch encoding with `batch_size=32`

**VectorStore**: wraps ChromaDB persistent client
- Single collection `scriptorium_docs` for all documents
- Per-document filtering via `where: {"doc_id": {"$eq": doc_id}}`
- Retrieves `top_k × 2` candidates, then applies MMR

**MMR Reranking** (Maximal Marginal Relevance):
```
MMR(d) = λ × sim(query, d) − (1−λ) × max_sim(d, selected)
```
λ=0.6 balances relevance with diversity. Without this, retrieved chunks often contain near-duplicate sentences from the same page, wasting context window space.

### `pipeline/rag.py` — RAGPipeline

Responsibility: orchestrate the full query lifecycle.

Query mode auto-detection uses lightweight keyword signals:
- "compare/vs/versus/contrast" → COMPARISON
- "extract/list all/table of" → EXTRACTION
- "summarize/overview/key points" → SUMMARY
- default → CONVERSATIONAL

Confidence estimation: `avg(similarity scores) - uncertainty_penalty`, where uncertainty signals are words like "unclear", "not mentioned", "insufficient" in the response.

### `prompts/templates.py` — Prompt Architecture

The prompt system has 4 composable layers:

```
FINAL_SYSTEM = BASE_SYSTEM
             + DOMAIN_ADDITIONS[domain]     # ~200-300 tokens
             + MODE_ADDITIONS[mode]         # ~100-150 tokens
             + EXPLAIN_LEVELS[level]        # ~20 tokens
```

This architecture means zero prompt engineering effort when adding a new domain — just add an entry to `DOMAIN_ADDITIONS`.

---

## 6. Domain Intelligence Layer

### Detection Thresholds

| Domain | Primary Signals | Typical Confidence |
|--------|-----------------|--------------------|
| Chemistry | Reaction arrows, molecular formulas (e.g. H₂O), yield %, NMR/HPLC | 0.75–0.92 |
| Finance | $-prefixed numbers, EV/EBITDA, Q1/FY notation, "margin" | 0.70–0.88 |
| Law | "plaintiff", "whereas", § symbols, case citation patterns | 0.72–0.90 |
| Policy | "stakeholder", "implementation", SDG references, Act names | 0.65–0.82 |
| General | Fallback — anything with low domain signal density | 0.50 (fixed) |

### Domain-Specific Extraction Targets

**Chemistry:**
- Reaction conditions: temperature, pressure, atmosphere, time
- Stoichiometry: molar ratios, equivalents, concentrations
- Yields: isolated %, crude %, conversion %
- Spectroscopic identifiers: ¹H NMR, IR, MS (m/z)

**Finance:**
- Income statement: Revenue, EBITDA, Net Income (absolute + YoY %)
- Balance sheet: Total assets, debt/equity ratio, cash position
- Valuation: EV/EBITDA, P/E, EV/Revenue multiples
- Forward guidance: targets, ranges, assumptions

**Law:**
- Case metadata: name, citation, jurisdiction, court, date
- Arguments: issue, rule, application, conclusion (IRAC)
- Holdings: binding vs persuasive authority
- Contractual: parties, obligations, conditions, penalties

**Policy:**
- Mandate: objective, legal basis, scope
- Stakeholders: beneficiaries, implementing agencies, funders
- Timeline: phases, milestones, review mechanisms
- Budget: total allocation, per-component breakdown

---

## 7. RAG Pipeline Deep Dive

### Chunking Parameter Tuning Guide

| Document Type | Recommended chunk_size | Recommended overlap |
|---------------|------------------------|---------------------|
| Dense academic papers | 400 words | 80 words |
| Legal contracts | 600 words | 100 words (clauses) |
| Financial reports | 350 words | 50 words |
| Policy documents | 500 words | 80 words |
| Default (auto) | 512 words | 64 words |

### Embedding Model Comparison (free, local)

| Model | Dims | Speed | Quality | VRAM |
|-------|------|-------|---------|------|
| all-MiniLM-L6-v2 ✓ | 384 | Very fast | Good | ~50MB |
| all-mpnet-base-v2 | 768 | Moderate | Better | ~420MB |
| bge-small-en-v1.5 | 384 | Fast | Good | ~130MB |
| e5-small-v2 | 384 | Fast | Good | ~130MB |

Default choice `all-MiniLM-L6-v2` is optimal for local/CPU operation. Swap by changing `EMBEDDING_MODEL` in `.env`.

### LLM Options (Free Tier)

| Model | Context | Quality | Rate Limit |
|-------|---------|---------|------------|
| Mistral-7B-Instruct-v0.3 ✓ | 32k | Strong | ~30 req/hr |
| Zephyr-7B-beta | 32k | Strong | ~30 req/hr |
| Llama-3.1-8B-Instruct | 128k | Very strong | ~20 req/hr |
| Falcon-7B-Instruct | 2k | Moderate | ~50 req/hr |

Change by updating `HF_MODEL` in `.env`. All use the same Mistral instruction format in `prompts/templates.py` — if switching to Llama, update the `<s>[INST]` format in `rag.py::HuggingFaceLLM.generate()`.

---

## 8. Frontend Architecture

### State Management (Zustand)

Single store at `lib/store.js` with three slices:

```
documents[]         — all uploaded docs with processing_stage
selectedDocIds[]    — which docs are active in chat queries
sessions{}          — map of sessionId → message[]
UI flags            — sidebarOpen, queryMode, explainLevel,
                      highlightedText, isQuerying
```

Zustand was chosen over Redux for zero boilerplate, and over React Context to avoid re-render cascades on frequent message updates.

### Component Communication Pattern

```
index.js (layout)
    ├── Sidebar.js          — reads/writes: documents, selectedDocIds
    ├── TopBar.js           — reads: selectedDocIds; writes: queryMode, explainLevel
    ├── DocumentViewer.js   — reads: activeDocId, documents; writes: highlightedText
    └── ChatPanel.js        — reads: everything; writes: sessions, isQuerying
            ├── InsightPanel.js
            ├── MessageBubble.js
            └── ChatInput.js    — reads: highlightedText, queryMode
```

All components access shared state directly via `useStore()` — no prop drilling.

### Processing Stage → UI Mapping

```
UPLOADING  → Upload progress bar (0-30%)
PARSING    → "Parsing PDF structure…" + animated dot
OCR        → "Running OCR…" (only shown if scanned pages detected)
CHUNKING   → "Segmenting into knowledge units…"
EMBEDDING  → "Generating semantic embeddings…"
READY      → CheckCircle icon + domain badge (Chemistry/Finance/etc)
FAILED     → Red AlertCircle + "Re-upload" prompt
```

---

## 9. API Reference

### POST `/api/documents/upload`
Upload a PDF file for processing.

**Request**: `multipart/form-data`, field `file`  
**Response**:
```json
{
  "success": true,
  "doc_id": "a1b2c3d4",
  "filename": "annual_report_2024.pdf",
  "message": "Document uploaded. Processing started."
}
```

### GET `/api/documents/{doc_id}/status`
Poll processing progress.

**Response**:
```json
{
  "doc_id": "a1b2c3d4",
  "stage": "embedding",
  "progress": 85,
  "message": "Generating semantic embeddings..."
}
```
Stages: `uploading → parsing → ocr → chunking → embedding → ready`

### GET `/api/documents/`
List all documents.

### DELETE `/api/documents/{doc_id}`
Delete document + all vectors + file.

### POST `/api/documents/insights`
Auto-generate insights without a user query.

**Request**:
```json
{ "doc_ids": ["a1b2c3d4"], "focus": "financial performance" }
```

### POST `/api/chat/query`
Main query endpoint.

**Request**:
```json
{
  "query": "What is the reported yield for the Suzuki coupling reaction?",
  "doc_ids": ["a1b2c3d4"],
  "mode": "extraction",
  "explain_level": "expert",
  "highlight_text": "optional selected passage",
  "conversation_history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

**Response**:
```json
{
  "answer": "The Suzuki coupling reaction reports an isolated yield of 87% [Chunk 2, p.4]...",
  "citations": [
    {
      "doc_id": "a1b2c3d4",
      "filename": "synthesis_paper.pdf",
      "page": 4,
      "chunk_text": "...Pd(PPh₃)₄ catalyzed coupling afforded 87% isolated yield...",
      "relevance_score": 0.912,
      "chunk_index": 14
    }
  ],
  "structured_insights": [],
  "domain": "chemistry",
  "query_mode": "extraction",
  "confidence": 0.87,
  "follow_up_questions": [
    "What catalyst loading was used?",
    "What solvent system was employed?",
    "Are there alternative synthesis routes mentioned?"
  ],
  "processing_time_ms": 2340
}
```

### POST `/api/chat/compare`
Cross-document comparison.

**Request**: `{ "doc_ids": ["id1", "id2"], "aspect": "methodology" }`

### GET `/api/documents/{doc_id}/file`
Serve raw PDF for iframe viewer.

---

## 10. Setup & Installation

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | ≥ 3.10 | Backend runtime |
| Node.js | ≥ 18 | Frontend build |
| Tesseract OCR | 4.x or 5.x | Scanned PDF OCR |
| Poppler | any | pdf2image dependency |
| HuggingFace account | free | LLM inference API key |

---

### Step 1 — Install System Dependencies

**macOS:**
```bash
brew install tesseract poppler
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y \
  tesseract-ocr \
  tesseract-ocr-eng \
  poppler-utils \
  libgl1-mesa-glx \
  libglib2.0-0
```

**Windows:**
- Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
- Poppler: https://github.com/oschwartz10612/poppler-windows/releases
- Add both to your `PATH`

---

### Step 2 — Get a Free HuggingFace API Key

1. Go to https://huggingface.co/join → create free account
2. Settings → Access Tokens → New Token → type: `read`
3. Copy the token (starts with `hf_...`)

You get ~30,000 free inference requests/month. No credit card required.

---

### Step 3 — Backend Setup

```bash
# Navigate to backend directory
cd scriptorium/backend

# Create virtual environment
python -m venv venv

# Activate it
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model (for future NER features)
python -m spacy download en_core_web_sm

# Create environment file
cp .env.example .env
# Then edit .env and add your HF_API_KEY (see Step 4)
```

**First run will download the embedding model (~90MB) automatically:**
```bash
python main.py
# Output: Loading embedding model: sentence-transformers/all-MiniLM-L6-v2
# Output: Embedding model loaded ✓
# Output: Scriptorium ready on http://0.0.0.0:8000
```

---

### Step 4 — Frontend Setup

```bash
# Navigate to frontend directory
cd scriptorium/frontend

# Install dependencies
npm install

# Create environment file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start development server
npm run dev
# Output: ready - started server on 0.0.0.0:3000
```

Open http://localhost:3000

---

### Step 5 — Verify Everything Works

```bash
# Test backend health
curl http://localhost:8000/api/health

# Expected response:
# {"status": "healthy", "version": "1.0.0", "app": "Scriptorium"}

# Test document list
curl http://localhost:8000/api/documents/

# Expected: []
```

---

## 11. Environment Configuration

Create `backend/.env`:

```env
# ── Application ──────────────────────────────────
APP_NAME=Scriptorium
DEBUG=false

# ── LLM (required) ───────────────────────────────
HF_API_KEY=hf_your_key_here
HF_MODEL=mistralai/Mistral-7B-Instruct-v0.3

# ── Embedding Model ───────────────────────────────
# Change to a larger model for better quality:
# EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# ── RAG Parameters ────────────────────────────────
CHUNK_SIZE=512
CHUNK_OVERLAP=64
TOP_K_RETRIEVAL=6

# ── OCR ───────────────────────────────────────────
# If tesseract is not in PATH, specify full path:
# TESSERACT_CMD=/usr/local/bin/tesseract
OCR_LANGUAGES=eng

# ── CORS ──────────────────────────────────────────
# Add your deployment URL if not localhost:
# ALLOWED_ORIGINS=["http://localhost:3000","https://yourdomain.com"]
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 12. Free API Strategy

### Why HuggingFace Inference API

HuggingFace provides free serverless inference for thousands of open-source models. The free tier gives approximately 30,000 requests/month with no credit card. Rate limits are ~30 requests/hour for most models.

### Handling Rate Limits

The `HuggingFaceLLM` class uses `tenacity` for automatic retry with exponential backoff:

```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
async def generate(...):
```

If the API is unavailable (rate limited or down), the system automatically falls back to **extractive response mode** — it surfaces the most relevant retrieved chunk directly rather than failing silently.

### Upgrading to Better Models (Later)

To switch to OpenRouter (also has free tier for some models):

```python
# In rag.py, replace the generate() call:
self.api_url = "https://openrouter.ai/api/v1/chat/completions"
self.headers["Authorization"] = f"Bearer {settings.OPENROUTER_KEY}"

payload = {
    "model": "meta-llama/llama-3.1-8b-instruct:free",
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    "max_tokens": 1024,
}
```

---

## 13. Performance Characteristics

### Expected Timings (CPU-only, 8GB RAM)

| Operation | Time | Notes |
|-----------|------|-------|
| PDF upload + save | < 1s | Synchronous |
| Page parsing (native) | ~0.1s/page | PyMuPDF is very fast |
| OCR (scanned page) | 3–8s/page | Tesseract, 300 DPI |
| Domain detection | < 5ms | Keyword scan, no model |
| Chunking (50 pages) | ~0.3s | Pure Python |
| Embedding (100 chunks) | 8–15s | CPU inference |
| Total processing (20-page PDF) | 20–45s | Background, non-blocking |
| Query + LLM response | 5–25s | Network-bound (HF API) |

### Memory Usage

| Component | RAM |
|-----------|-----|
| FastAPI + Python runtime | ~150MB |
| Embedding model (MiniLM) | ~90MB |
| ChromaDB (1000 chunks) | ~50MB |
| Per uploaded document | ~2–5MB chunks |
| Next.js dev server | ~300MB |
| **Total** | **~600MB** |

Runs comfortably on any machine with 4GB RAM.

---

## 14. Known Limitations & Roadmap

### Current Limitations

| Area | Limitation | Impact |
|------|-----------|--------|
| OCR | Tesseract struggles with multi-column layouts and complex tables | Medium |
| LLM | HF free tier rate limits (30 req/hr) can cause delays | Medium |
| Chunking | Table extraction is regex-based, not ML-based | Low |
| Multi-doc | No cross-document entity resolution | Low |
| Auth | No user accounts — all docs visible to all users | High for production |
| File types | PDF only — no DOCX, HTML, PPTX | Medium |

### Roadmap (V2+)

**Phase 1 — Polish (Week 1-2)**
- [ ] User authentication (NextAuth.js + JWT)
- [ ] Persistent sessions in PostgreSQL
- [ ] Better table extraction (Camelot or tabula-py)
- [ ] Tagging system for documents

**Phase 2 — Intelligence (Week 3-4)**
- [ ] Named entity extraction using spaCy
- [ ] Cross-document entity linking ("Apple Inc." = "Apple" = "$AAPL")
- [ ] Citation graph (which chunks led to which answers)
- [ ] Streaming LLM responses (SSE)

**Phase 3 — Scale (Month 2)**
- [ ] Local LLM via Ollama (llama3.2, qwen2.5) — no API rate limits
- [ ] Background queue with Celery + Redis
- [ ] Multi-tenant storage (per-user ChromaDB namespaces)
- [ ] Export to PDF / Markdown / Notion

**Phase 4 — Advanced RAG (Month 3)**
- [ ] HyDE (Hypothetical Document Embeddings) for sparse query coverage
- [ ] Parent-child chunking (retrieve fine, read coarse)
- [ ] Query decomposition for complex multi-hop questions
- [ ] Document graph (nodes = chunks, edges = semantic similarity)

---

## Quick Reference Card

```
Start backend:    cd backend && python main.py
Start frontend:   cd frontend && npm run dev

Backend URL:      http://localhost:8000
Frontend URL:     http://localhost:3000
API docs:         http://localhost:8000/api/docs
ReDoc:            http://localhost:8000/api/redoc

Data location:    backend/data/uploads/    (raw PDFs)
                  backend/data/chroma/     (vector DB)
                  backend/data/document_state.json  (doc registry)

Logs:             Backend logs to stdout with timestamps
                  Set DEBUG=true in .env for verbose output

Reset everything: rm -rf backend/data/uploads/* \
                         backend/data/chroma/* \
                         backend/data/document_state.json
```

---

*Scriptorium v1.0 — Built as a startup-grade research intelligence product.*  
*Architecture by design, not by accident.*
