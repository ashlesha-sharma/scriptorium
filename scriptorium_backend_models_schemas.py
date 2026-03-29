from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class Domain(str, Enum):
    CHEMISTRY = "chemistry"
    FINANCE = "finance"
    LAW = "law"
    POLICY = "policy"
    GENERAL = "general"


class ProcessingStage(str, Enum):
    UPLOADING = "uploading"
    PARSING = "parsing"
    OCR = "ocr"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    READY = "ready"
    FAILED = "failed"


# ─── Document Schemas ────────────────────────────────────────────────────────

class DocumentMetadata(BaseModel):
    doc_id: str
    filename: str
    file_size: int
    page_count: int
    domain: Domain
    domain_confidence: float
    processing_stage: ProcessingStage
    created_at: datetime
    chunk_count: int = 0
    ocr_applied: bool = False
    tags: List[str] = []


class DocumentListItem(BaseModel):
    doc_id: str
    filename: str
    domain: Domain
    processing_stage: ProcessingStage
    page_count: int
    created_at: datetime


class DocumentResponse(BaseModel):
    success: bool
    doc_id: str
    filename: str
    message: str
    metadata: Optional[DocumentMetadata] = None


class DocumentStatusResponse(BaseModel):
    doc_id: str
    stage: ProcessingStage
    progress: int  # 0-100
    message: str


# ─── Citation Schemas ─────────────────────────────────────────────────────────

class Citation(BaseModel):
    doc_id: str
    filename: str
    page: int
    chunk_text: str
    relevance_score: float
    chunk_index: int


# ─── Chat Schemas ─────────────────────────────────────────────────────────────

class QueryMode(str, Enum):
    CONVERSATIONAL = "conversational"
    EXTRACTION = "extraction"
    COMPARISON = "comparison"
    SUMMARY = "summary"
    HIGHLIGHT = "highlight"


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    citations: List[Citation] = []
    structured_data: Optional[Dict[str, Any]] = None
    domain: Optional[Domain] = None
    query_mode: Optional[QueryMode] = None


class ChatRequest(BaseModel):
    query: str
    doc_ids: List[str]  # which documents to query against
    conversation_history: List[ChatMessage] = []
    mode: QueryMode = QueryMode.CONVERSATIONAL
    highlight_text: Optional[str] = None  # for highlight-to-query
    explain_level: str = "expert"  # "eli5" | "intermediate" | "expert"
    session_id: Optional[str] = None


class StructuredInsight(BaseModel):
    category: str
    label: str
    value: str
    confidence: float
    source_citation: Optional[Citation] = None


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]
    structured_insights: List[StructuredInsight] = []
    domain: Domain
    query_mode: QueryMode
    confidence: float
    follow_up_questions: List[str] = []
    processing_time_ms: int


# ─── Insight Schemas ──────────────────────────────────────────────────────────

class AutoInsightRequest(BaseModel):
    doc_ids: List[str]
    focus: Optional[str] = None  # optional focus area


class KeyFinding(BaseModel):
    title: str
    description: str
    importance: str  # "critical" | "high" | "medium"
    citation: Optional[Citation] = None


class AutoInsightResponse(BaseModel):
    executive_summary: str
    key_findings: List[KeyFinding]
    extracted_data_points: List[StructuredInsight]
    domain: Domain
    document_count: int
    citations: List[Citation]


# ─── Comparison Schemas ───────────────────────────────────────────────────────

class ComparisonRequest(BaseModel):
    doc_ids: List[str]
    aspect: str  # what to compare (e.g., "methodology", "results", "arguments")


class ComparisonCell(BaseModel):
    doc_id: str
    filename: str
    value: str
    citation: Optional[Citation] = None


class ComparisonRow(BaseModel):
    attribute: str
    cells: List[ComparisonCell]


class ComparisonResponse(BaseModel):
    comparison_table: List[ComparisonRow]
    synthesis: str
    domain: Domain
    citations: List[Citation]


# ─── Export Schemas ───────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    session_id: str
    doc_ids: List[str]
    format: str  # "pdf" | "markdown"
    include_citations: bool = True
    include_insights: bool = True
