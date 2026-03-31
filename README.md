# Scriptorium

> Domain-adaptive RAG research intelligence system  
> Transforms static PDFs into dynamic, queryable knowledge systems

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?style=flat-square)
![Next.js](https://img.shields.io/badge/Next.js-14-black?style=flat-square)
![ChromaDB](https://img.shields.io/badge/Vector_DB-ChromaDB-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

**Live Demo:** https://your-vercel-url.vercel.app  
**Demo Video:** https://youtube.com/watch?v=YOUR_VIDEO_ID

---

## What is Scriptorium?

Most RAG systems treat every document the same. A chemistry paper and a
financial report get identical processing. Scriptorium does not work that way.

It automatically detects the domain of your document and routes it to a
specialized extraction pipeline:

| Domain    | Auto-extracts                                    |
|-----------|--------------------------------------------------|
| Chemistry | Yields, reaction conditions, catalysts, NMR data |
| Finance   | Revenue, EBITDA, margins, multiples, cash flow   |
| Law       | Case citations, rulings, arguments, clauses      |
| Policy    | Mandates, stakeholders, timelines, budgets       |
| General   | Core thesis, evidence, methodology, conclusions  |

---

## Features

- **Domain Detection** — automatic classification on upload, zero config
- **OCR Pipeline** — Tesseract OCR on scanned pages, native text on digital PDFs
- **Smart Chunking** — structural boundary-aware, respects equations and clauses
- **MMR Retrieval** — diversity-aware reranking, not just top-k cosine similarity
- **Highlight-to-Query** — select any text in viewer, click "Ask about selection"
- **Multi-doc Compare** — cross-document comparison on any aspect you specify
- **Auto Insights** — one-click executive summary and ranked key findings
- **Citation Engine** — every answer cites specific chunks with page numbers
- **Explain Level** — ELI5 / Intermediate / Expert mode

---

## Architecture
```
PDF Upload
   |
   +-- PyMuPDF (native text) + Tesseract OCR (scanned pages)
   v
Domain Detector (keyword + pattern classifier, <5ms, no ML model)
   v
Smart Chunker (512 word chunks, 64 word overlap, boundary-aware)
   v
Embedding Engine (sentence-transformers/all-MiniLM-L6-v2, 384-dim)
   v
ChromaDB Vector Store (persistent, cosine similarity)
   v
MMR Retrieval top-6 (lambda=0.6, balances relevance + diversity)
   v
Domain-Adaptive Prompting (Base + Domain + Mode + ExplainLevel)
   v
HuggingFace LLM Mistral-7B-Instruct (free tier)
   v
Response: answer + citations + structured insights + follow-ups
```

---

## Tech Stack

**Backend:** Python 3.11, FastAPI, PyMuPDF, Tesseract, sentence-transformers, ChromaDB  
**Frontend:** Next.js 14, React 18, TailwindCSS, Framer Motion, Zustand  
**AI:** HuggingFace Inference API (free), Mistral-7B-Instruct-v0.3  
**Vector DB:** ChromaDB with HNSW cosine index

---

## Project Structure
```
scriptorium/
  backend/
    pipeline/
      ingestion.py        # PDF parsing + OCR
      domain_detection.py # Domain classifier
      chunking.py         # Smart chunker
      vector_store.py     # ChromaDB + embeddings + MMR
      rag.py              # Full RAG orchestrator
    prompts/templates.py  # Domain-adaptive prompts
    routers/              # API endpoints
  frontend/
    components/
      Layout/             # Sidebar + TopBar
      Document/           # PDF viewer + highlight-to-query
      Chat/               # Messages + input + citations
      Intelligence/       # Auto-insight panel
    lib/store.js          # Zustand state management
    lib/api.js            # Typed API client
```

---

## Local Setup

**Prerequisites:** Python 3.11, Node.js 18+, Tesseract OCR, HuggingFace API key

**Backend:**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# open .env and paste your HF_API_KEY
python main.py
```

**Frontend:**
```bash
cd frontend
npm install
echo 'NEXT_PUBLIC_API_URL=http://localhost:8000' > .env.local
npm run dev
```

Open http://localhost:3000

---

## License

MIT — built as a production MVP demonstrating system design and RAG engineering.
