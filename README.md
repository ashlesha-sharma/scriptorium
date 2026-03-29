#  Scriptorium

> **Domain-adaptive RAG research intelligence system** > *Transforms static PDFs into dynamic, queryable knowledge systems.*

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?style=flat-square)
![Next.js](https://img.shields.io/badge/Next.js-14-black?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

---

##  What is Scriptorium?

Most RAG systems treat all documents the same. **Scriptorium doesn't.**

It detects the domain of your document and dynamically adapts its extraction logic, prompt templates, and output structure to match. 
*  **Chemistry paper?** It extracts yields, reactions, and catalysts. 
*  **Financial report?** It pulls revenue, margins, and ratios. 
*  **Legal document?** It highlights case citations, rulings, and arguments.

** Demo video:** [Watch the 3-min walkthrough here](#) *(← update this link)*

---

##  Key Features

| Feature | Description |
|---------|-------------|
|  **Domain Detection** | Automatic classification into Chemistry / Finance / Law / Policy. |
|  **Smart OCR** | Falls back to Tesseract OCR on scanned pages; uses native text on digital PDFs. |
|  **Semantic Chunking** | Boundary-aware chunking that respects equations, clauses, and paragraphs. |
|  **MMR Retrieval** | Maximal Marginal Relevance reranking ensures context is both relevant *and* diverse. |
|  **Highlight-to-Query** | Select any text in the viewer to instantly "Ask about this selection." |
|  **Multi-doc Compare** | Cross-document comparison on any user-defined aspect or metric. |
|  **Auto Insights** | Generates a one-click executive summary and extracts key findings. |
|  **Structured Extraction** | Tables, metrics, and variables are pulled and exported as typed JSON. |
|  **Citation Engine** | Every generated answer cites specific chunks, complete with page numbers. |

---

##  How it Works

```mermaid
graph TD
    A[PDF Upload] --> B(PyMuPDF: Native Text)
    A --> C(Tesseract: Scanned OCR)
    
    B --> D{Domain Detector}
    C --> D
    
    D -->|Chemistry| E[Yields, Reactions, Conditions]
    D -->|Finance| F[Revenue, Margins, Multiples]
    D -->|Law| G[Citations, Rulings, Clauses]
    D -->|Policy| H[Mandates, Stakeholders, Timelines]
    
    E --> I[Smart Semantic Chunker]
    F --> I
    G --> I
    H --> I
    
    I --> J[Embedding Engine<br>all-MiniLM-L6-v2]
    J --> K[(ChromaDB<br>Vector Store)]
    
    K --> L[MMR Retrieval +<br>Domain-Adaptive Prompting]
    L --> M((HuggingFace LLM<br>Mistral-7B-Instruct))
    
    M --> N[Structured Response<br>Answer + Citations + Insights]

Tech Stack
Backend: Python 3.10, FastAPI, PyMuPDF, Tesseract, sentence-transformers

Frontend: Next.js 14, TailwindCSS, Framer Motion, Zustand

AI Models: HuggingFace Inference API (free tier), all-MiniLM-L6-v2 (embeddings)

Vector Database: ChromaDB (local, persistent)

Getting Started
Prerequisites
Python ≥ 3.10

Node.js ≥ 18

Tesseract OCR installed on your machine

A free HuggingFace account and API key

1. Clone the repository
Bash
git clone git@github.com:YOUR_USERNAME/scriptorium.git
cd scriptorium
2. Start the Backend
Bash
cd backend
python -m venv venv

# Activate virtual environment
source venv/bin/activate       # On Mac/Linux
venv\Scripts\activate          # On Windows

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# IMPORTANT: Edit .env and add your HF_API_KEY

# Run the server
python main.py
3. Start the Frontend
Open a new terminal window:

Bash
cd frontend
npm install

# Setup environment variables
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Run the client
npm run dev
Navigate to http://localhost:3000 in your browser.

Project Structure
Plaintext
scriptorium/
├── backend/
│   ├── pipeline/
│   │   ├── ingestion.py        # PDF parsing + OCR
│   │   ├── domain_detection.py # Domain classifier
│   │   ├── chunking.py         # Smart semantic chunker
│   │   ├── vector_store.py     # ChromaDB + embeddings
│   │   └── rag.py              # Full RAG orchestrator
│   ├── prompts/
│   │   └── templates.py        # Domain-adaptive prompt system
│   ├── routers/
│   │   ├── documents.py        # Upload, status, insights
│   │   └── chat.py             # Query, compare
│   └── models/
│       └── schemas.py          # All typed API schemas
│
└── frontend/
    ├── components/
    │   ├── Layout/             # Sidebar, TopBar
    │   ├── Document/           # PDF Viewer + highlight
    │   ├── Chat/               # Messages, Input, Panel
    │   └── Intelligence/       # Insight Panel
    └── lib/
        ├── store.js            # Zustand state management
        └── api.js              # API client
Contributing
Contributions are welcome! If you'd like to add a new domain classifier or improve the chunking logic, please fork the repository and submit a pull request. For major changes, open an issue first to discuss what you would like to change.

License
Released under the MIT License — use freely, attribution appreciated.
