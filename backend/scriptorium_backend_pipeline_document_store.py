"""
Document State Manager
In-memory + disk state tracking for all documents.
Production would use Redis or a database.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger

from models.schemas import DocumentMetadata, DocumentListItem, ProcessingStage, Domain
from config import settings


class DocumentStore:
    """
    In-memory document registry with JSON persistence.
    Tracks all uploaded documents and their processing state.
    """

    STATE_FILE = settings.UPLOAD_DIR.parent / "document_state.json"

    def __init__(self):
        self._docs: Dict[str, DocumentMetadata] = {}
        self._load_state()

    def create_document(self, filename: str, file_size: int) -> str:
        """Register a new document, returns doc_id."""
        doc_id = str(uuid.uuid4())[:8]
        self._docs[doc_id] = DocumentMetadata(
            doc_id=doc_id,
            filename=filename,
            file_size=file_size,
            page_count=0,
            domain=Domain.GENERAL,
            domain_confidence=0.0,
            processing_stage=ProcessingStage.UPLOADING,
            created_at=datetime.utcnow(),
            chunk_count=0,
            ocr_applied=False,
        )
        self._save_state()
        return doc_id

    def update_stage(self, doc_id: str, stage: ProcessingStage, **kwargs):
        """Update processing stage and optional metadata fields."""
        if doc_id not in self._docs:
            return
        doc = self._docs[doc_id]
        doc.processing_stage = stage
        for key, val in kwargs.items():
            if hasattr(doc, key):
                setattr(doc, key, val)
        self._save_state()
        logger.info(f"[{doc_id}] Stage → {stage}")

    def get(self, doc_id: str) -> Optional[DocumentMetadata]:
        return self._docs.get(doc_id)

    def list_all(self) -> List[DocumentListItem]:
        return [
            DocumentListItem(
                doc_id=d.doc_id,
                filename=d.filename,
                domain=d.domain,
                processing_stage=d.processing_stage,
                page_count=d.page_count,
                created_at=d.created_at,
            )
            for d in sorted(self._docs.values(), key=lambda x: x.created_at, reverse=True)
        ]

    def delete(self, doc_id: str) -> bool:
        if doc_id in self._docs:
            del self._docs[doc_id]
            self._save_state()
            return True
        return False

    def all_metadata(self) -> Dict[str, DocumentMetadata]:
        return self._docs

    def _save_state(self):
        try:
            self.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            state = {
                doc_id: {
                    **meta.dict(),
                    "created_at": meta.created_at.isoformat(),
                }
                for doc_id, meta in self._docs.items()
            }
            with open(self.STATE_FILE, "w") as f:
                json.dump(state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _load_state(self):
        try:
            if self.STATE_FILE.exists():
                with open(self.STATE_FILE) as f:
                    state = json.load(f)
                for doc_id, data in state.items():
                    data["created_at"] = datetime.fromisoformat(data["created_at"])
                    self._docs[doc_id] = DocumentMetadata(**data)
                logger.info(f"Loaded {len(self._docs)} documents from state")
        except Exception as e:
            logger.error(f"Failed to load state: {e}")


document_store = DocumentStore()
