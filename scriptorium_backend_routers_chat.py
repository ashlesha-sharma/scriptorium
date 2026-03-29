"""
Chat Router
Handles conversational queries, extraction, comparison, highlight-to-query.
"""

from fastapi import APIRouter, HTTPException
from loguru import logger

from models.schemas import (
    ChatRequest, ChatResponse, ComparisonRequest, ComparisonResponse,
    ComparisonRow, ComparisonCell, Citation, ProcessingStage
)
from pipeline.rag import RAGPipeline
from pipeline.vector_store import get_vector_store
from pipeline.document_store import document_store

router = APIRouter(prefix="/chat", tags=["chat"])


def _get_pipeline() -> RAGPipeline:
    return RAGPipeline(vector_store=get_vector_store())


# ─── Main Query ───────────────────────────────────────────────────────────────

@router.post("/query", response_model=ChatResponse)
async def query(request: ChatRequest):
    """
    Main query endpoint. Handles all QueryMode types.
    """
    # Validate documents
    for doc_id in request.doc_ids:
        doc = document_store.get(doc_id)
        if not doc:
            raise HTTPException(404, f"Document {doc_id} not found")
        if doc.processing_stage != ProcessingStage.READY:
            raise HTTPException(
                400,
                f"Document '{doc.filename}' is still processing. "
                f"Current stage: {doc.processing_stage}"
            )

    if not request.query.strip():
        raise HTTPException(400, "Query cannot be empty")

    logger.info(
        f"Query received | mode={request.mode} | docs={request.doc_ids} | "
        f"query='{request.query[:80]}...'"
    )

    pipeline = _get_pipeline()
    doc_metadata = document_store.all_metadata()

    response = await pipeline.query(request, doc_metadata)
    return response


# ─── Comparison ───────────────────────────────────────────────────────────────

@router.post("/compare", response_model=ComparisonResponse)
async def compare_documents(request: ComparisonRequest):
    """
    Compare multiple documents across a specific aspect.
    """
    if len(request.doc_ids) < 2:
        raise HTTPException(400, "Comparison requires at least 2 documents")

    vs = get_vector_store()
    all_rows: list[ComparisonRow] = []
    all_citations: list[Citation] = []

    # For each document, retrieve chunks relevant to the aspect
    aspects = [request.aspect] + [
        f"{request.aspect} methodology",
        f"{request.aspect} results",
        f"{request.aspect} conclusion",
    ]

    seen_docs = {}
    for doc_id in request.doc_ids:
        doc_meta = document_store.get(doc_id)
        if not doc_meta or doc_meta.processing_stage != ProcessingStage.READY:
            continue

        chunks = vs.retrieve(
            query=request.aspect,
            doc_ids=[doc_id],
            top_k=3,
        )

        if chunks:
            seen_docs[doc_id] = {
                "filename": doc_meta.filename,
                "best_chunk": chunks[0],
                "chunks": chunks,
            }
            all_citations.append(Citation(
                doc_id=doc_id,
                filename=doc_meta.filename,
                page=chunks[0]["page_num"],
                chunk_text=chunks[0]["text"][:250],
                relevance_score=chunks[0]["similarity"],
                chunk_index=chunks[0]["chunk_index"],
            ))

    if not seen_docs:
        raise HTTPException(404, "No relevant content found in documents")

    # Build comparison rows
    row = ComparisonRow(
        attribute=request.aspect,
        cells=[
            ComparisonCell(
                doc_id=doc_id,
                filename=data["filename"],
                value=data["best_chunk"]["text"][:300],
                citation=all_citations[i] if i < len(all_citations) else None,
            )
            for i, (doc_id, data) in enumerate(seen_docs.items())
        ]
    )
    all_rows.append(row)

    # Get domain
    first_doc = document_store.get(request.doc_ids[0])
    domain = first_doc.domain if first_doc else "general"

    synthesis = (
        f"Comparison of {len(seen_docs)} documents on '{request.aspect}'. "
        f"Key differences and similarities are highlighted above. "
        f"Review the source citations for full context."
    )

    return ComparisonResponse(
        comparison_table=all_rows,
        synthesis=synthesis,
        domain=domain,
        citations=all_citations,
    )
