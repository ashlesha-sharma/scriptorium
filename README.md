# 📜 Scriptorium

> **Domain-adaptive RAG research intelligence system** > *Transforms static PDFs into dynamic, queryable knowledge systems.*

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?style=flat-square)
![Next.js](https://img.shields.io/badge/Next.js-14-black?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

---

## 💡 What is Scriptorium?

Most RAG systems treat all documents the same. **Scriptorium doesn't.**

It detects the domain of your document and dynamically adapts its extraction logic, prompt templates, and output structure to match. 
* 🧪 **Chemistry paper?** It extracts yields, reactions, and catalysts. 
* 📈 **Financial report?** It pulls revenue, margins, and ratios. 
* ⚖️ **Legal document?** It highlights case citations, rulings, and arguments.

**🎥 Demo video:** [Watch the 3-min walkthrough here](#) *(← update this link)*

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🧠 **Domain Detection** | Automatic classification into Chemistry / Finance / Law / Policy. |
| 👁️ **Smart OCR** | Falls back to Tesseract OCR on scanned pages; uses native text on digital PDFs. |
| 🧩 **Semantic Chunking** | Boundary-aware chunking that respects equations, clauses, and paragraphs. |
| 🎯 **MMR Retrieval** | Maximal Marginal Relevance reranking ensures context is both relevant *and* diverse. |
| 🖱️ **Highlight-to-Query** | Select any text in the viewer to instantly "Ask about this selection." |
| 📊 **Multi-doc Compare** | Cross-document comparison on any user-defined aspect or metric. |
| ⚡ **Auto Insights** | Generates a one-click executive summary and extracts key findings. |
| 🏗️ **Structured Extraction** | Tables, metrics, and variables are pulled and exported as typed JSON. |
| 📌 **Citation Engine** | Every generated answer cites specific chunks, complete with page numbers. |

---

## ⚙️ How it Works

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
