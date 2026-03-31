"""
File serving router - serves uploaded PDFs to the frontend viewer.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from config import settings
from pipeline.document_store import document_store

router = APIRouter(prefix="/documents", tags=["files"])

@router.get("/{doc_id}/file")
async def serve_document(doc_id: str):
    doc = document_store.get(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    file_path = settings.UPLOAD_DIR / f"{doc_id}.pdf"
    if not file_path.exists():
        raise HTTPException(404, "File not found on disk")
    return FileResponse(
        str(file_path),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={doc.filename}"},
    )
