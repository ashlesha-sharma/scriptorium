"""
Document Router
Handles: upload, status, list, delete, auto-insights
"""

import asyncio
import shutil
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from loguru import logger

from config import settings
from models.schemas import (
    DocumentResponse, DocumentListItem, DocumentStatusResponse,
    ProcessingStage, AutoInsightRequest, AutoInsightResponse,
    KeyFinding, StructuredInsight
)
from pipeline.document_store import document_store
from pipeline.ingestion import ingester
from pipeline.chunking import chunker
from pipeline.vector_store import get_vector_store
from pipeline.domain_detection import detector

router = APIRouter(prefix="/documents", tags=["documents"])


# ─── Upload ───────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Upload and process a PDF document."""

    # Validate
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported.")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(400, "File too large. Maximum 50MB.")

    # Register document
    doc_id = document_store.create_document(file.filename, len(content))
    file_path = settings.UPLOAD_DIR / f"{doc_id}.pdf"

    # Save to disk
    with open(file_path, "wb") as f:
        f.write(content)

    # Process in background
    background_tasks.add_task(
        _process_document,
        doc_id=doc_id,
        file_path=file_path,
        filename=file.filename,
    )

    return DocumentResponse(
        success=True,
        doc_id=doc_id,
        filename=file.filename,
        message="Document uploaded. Processing started.",
    )


async def _process_document(doc_id: str, file_path: Path, filename: str):
    """
    Background processing pipeline.
    Stages: Parsing → OCR → Domain Detection → Chunking → Embedding
    """
    try:
        # 1. Parse
        document_store.update_stage(doc_id, ProcessingStage.PARSING)
        await asyncio.sleep(0.1)  # yield event loop
        doc_content = ingester.ingest(file_path, doc_id, filename)
        document_store.update_stage(doc_id, ProcessingStage.PARSING, page_count=doc_content.page_count)

        # 2. OCR stage marker
        if doc_content.ocr_applied:
            document_store.update_stage(doc_id, ProcessingStage.OCR, ocr_applied=True)
            await asyncio.sleep(0.1)

        # 3. Domain detection
        domain, confidence, _ = detector.detect(doc_content.full_text[:10000])
        document_store.update_stage(
            doc_id, ProcessingStage.CHUNKING,
            domain=domain,
            domain_confidence=confidence,
        )

        # 4. Chunk
        await asyncio.sleep(0.1)
        chunks = chunker.chunk(doc_content, domain)

        # 5. Embed + store
        document_store.update_stage(doc_id, ProcessingStage.EMBEDDING)
        await asyncio.sleep(0.1)
        vs = get_vector_store()
        chunk_count = vs.add_chunks(chunks)

        # 6. Ready
        document_store.update_stage(
            doc_id, ProcessingStage.READY,
            chunk_count=chunk_count,
        )
        logger.info(f"Document {doc_id} ({filename}) processing complete ✓")

    except Exception as e:
        logger.error(f"Processing failed for {doc_id}: {e}")
        document_store.update_stage(doc_id, ProcessingStage.FAILED)


# ─── Status ───────────────────────────────────────────────────────────────────

@router.get("/{doc_id}/status", response_model=DocumentStatusResponse)
async def get_status(doc_id: str):
    doc = document_store.get(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    stage_progress = {
        ProcessingStage.UPLOADING: 10,
        ProcessingStage.PARSING: 30,
        ProcessingStage.OCR: 50,
        ProcessingStage.CHUNKING: 65,
        ProcessingStage.EMBEDDING: 85,
        ProcessingStage.READY: 100,
        ProcessingStage.FAILED: 0,
    }

    stage_messages = {
        ProcessingStage.UPLOADING: "Receiving document...",
        ProcessingStage.PARSING: "Parsing PDF structure...",
        ProcessingStage.OCR: "Applying OCR to scanned pages...",
        ProcessingStage.CHUNKING: "Segmenting into knowledge chunks...",
        ProcessingStage.EMBEDDING: "Generating semantic embeddings...",
        ProcessingStage.READY: "Ready for queries",
        ProcessingStage.FAILED: "Processing failed. Please re-upload.",
    }

    return DocumentStatusResponse(
        doc_id=doc_id,
        stage=doc.processing_stage,
        progress=stage_progress.get(doc.processing_stage, 0),
        message=stage_messages.get(doc.processing_stage, ""),
    )


# ─── List ─────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[DocumentListItem])
async def list_documents():
    return document_store.list_all()


# ─── Get metadata ─────────────────────────────────────────────────────────────

@router.get("/{doc_id}")
async def get_document(doc_id: str):
    doc = document_store.get(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


# ─── Delete ───────────────────────────────────────────────────────────────────

@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    if not document_store.get(doc_id):
        raise HTTPException(404, "Document not found")

    # Delete from vector store
    vs = get_vector_store()
    deleted_chunks = vs.delete_document(doc_id)

    # Delete file
    file_path = settings.UPLOAD_DIR / f"{doc_id}.pdf"
    if file_path.exists():
        file_path.unlink()

    # Delete from store
    document_store.delete(doc_id)

    return {"success": True, "deleted_chunks": deleted_chunks}


# ─── Auto Insights ────────────────────────────────────────────────────────────

@router.post("/insights", response_model=AutoInsightResponse)
async def auto_insights(request: AutoInsightRequest):
    """Generate automatic insights for a set of documents."""

    for doc_id in request.doc_ids:
        doc = document_store.get(doc_id)
        if not doc:
            raise HTTPException(404, f"Document {doc_id} not found")
        if doc.processing_stage != ProcessingStage.READY:
            raise HTTPException(400, f"Document {doc_id} is not ready yet")

    # Retrieve a broad sample of chunks for insight generation
    vs = get_vector_store()
    focus_query = request.focus or "main findings key results conclusions important data"

    chunks = vs.retrieve(
        query=focus_query,
        doc_ids=request.doc_ids,
        top_k=10,
    )

    # Get domain from first document
    doc_meta = document_store.get(request.doc_ids[0])
    domain = doc_meta.domain if doc_meta else "general"

    # Build simple extractive insights (no LLM needed for MVP)
    from models.schemas import Citation
    citations = []
    for chunk in chunks[:6]:
        doc = document_store.get(chunk["doc_id"])
        citations.append(Citation(
            doc_id=chunk["doc_id"],
            filename=doc.filename if doc else chunk["doc_id"],
            page=chunk["page_num"],
            chunk_text=chunk["text"][:250],
            relevance_score=chunk["similarity"],
            chunk_index=chunk["chunk_index"],
        ))

    # Generate key findings from top chunks
    key_findings = []
    for i, chunk in enumerate(chunks[:5]):
        # Extract first complete sentence as finding
        sentences = chunk["text"].split('. ')
        if sentences:
            finding_text = sentences[0] + ('.' if not sentences[0].endswith('.') else '')
            key_findings.append(KeyFinding(
                title=f"Finding {i + 1}",
                description=finding_text[:300],
                importance="high" if i < 2 else "medium",
                citation=citations[i] if i < len(citations) else None,
            ))

    # Executive summary from highest-scoring chunks
    summary_text = " ".join(c["text"][:150] for c in chunks[:3])

    return AutoInsightResponse(
        executive_summary=summary_text[:500] + "...",
        key_findings=key_findings,
        extracted_data_points=[],
        domain=domain,
        document_count=len(request.doc_ids),
        citations=citations,
    )
