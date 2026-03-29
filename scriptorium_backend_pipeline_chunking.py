"""
Smart Chunking Pipeline
Semantic + structural chunking that preserves context boundaries.
Domain-aware: respects equations, legal clauses, financial statements.
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from loguru import logger

from config import settings
from models.schemas import Domain
from pipeline.ingestion import DocumentContent, PageContent


@dataclass
class TextChunk:
    chunk_id: str
    doc_id: str
    text: str
    page_num: int
    chunk_index: int
    word_count: int
    char_count: int
    is_table: bool = False
    is_header: bool = False
    section_title: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


class SmartChunker:
    """
    Hierarchical chunking strategy:
    1. Split on structural boundaries (sections, paragraphs)
    2. Respect domain-specific units (equations, legal clauses, financial lines)
    3. Ensure chunks are within token limits
    4. Maintain overlap for context continuity
    """

    # Structural splitters in priority order
    SECTION_PATTERNS = [
        r'\n#{1,4}\s+.+',                    # Markdown headers
        r'\n[A-Z][A-Z\s]{5,}\n',            # ALL CAPS headers
        r'\n\d+\.\s+[A-Z].{10,}\n',         # Numbered sections
        r'\n(?:Section|Article|Chapter)\s+\d+', # Explicit section markers
        r'\n\[PAGE\s+\d+\]',                 # Page markers we added
    ]

    def chunk(
        self,
        doc_content: DocumentContent,
        domain: Domain,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ) -> List[TextChunk]:
        """
        Main chunking entry point.
        Returns ordered list of TextChunk objects.
        """
        chunk_size = chunk_size or settings.CHUNK_SIZE
        chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

        logger.info(
            f"Chunking {doc_content.filename} | domain={domain} | "
            f"chunk_size={chunk_size}"
        )

        chunks: List[TextChunk] = []
        chunk_index = 0

        # Process page by page to maintain page attribution
        for page in doc_content.pages:
            if not page.text.strip():
                continue

            page_chunks = self._chunk_page(
                text=page.text,
                doc_id=doc_content.doc_id,
                page_num=page.page_num,
                domain=domain,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                start_index=chunk_index,
            )

            chunks.extend(page_chunks)
            chunk_index += len(page_chunks)

        logger.info(f"Produced {len(chunks)} chunks from {doc_content.filename}")
        return chunks

    def _chunk_page(
        self,
        text: str,
        doc_id: str,
        page_num: int,
        domain: Domain,
        chunk_size: int,
        chunk_overlap: int,
        start_index: int,
    ) -> List[TextChunk]:
        """Chunk a single page's text."""

        # First: extract table blocks (keep intact)
        text, table_blocks = self._extract_tables(text)

        # Second: split on structural boundaries
        segments = self._split_on_boundaries(text, domain)

        # Third: merge segments into proper-sized chunks
        raw_chunks = self._merge_into_chunks(segments, chunk_size, chunk_overlap)

        chunks = []
        for i, raw in enumerate(raw_chunks):
            if not raw.strip():
                continue

            section = self._extract_section_title(raw)
            chunks.append(TextChunk(
                chunk_id=f"{doc_id}_{page_num}_{start_index + i}",
                doc_id=doc_id,
                text=raw.strip(),
                page_num=page_num,
                chunk_index=start_index + i,
                word_count=len(raw.split()),
                char_count=len(raw),
                is_table=False,
                section_title=section,
            ))

        # Add table chunks (kept intact)
        for table_text in table_blocks:
            if table_text.strip():
                chunks.append(TextChunk(
                    chunk_id=f"{doc_id}_{page_num}_{start_index + len(chunks)}",
                    doc_id=doc_id,
                    text=table_text.strip(),
                    page_num=page_num,
                    chunk_index=start_index + len(chunks),
                    word_count=len(table_text.split()),
                    char_count=len(table_text),
                    is_table=True,
                ))

        return chunks

    def _extract_tables(self, text: str) -> Tuple[str, List[str]]:
        """Extract table-like blocks and replace with placeholders."""
        table_blocks = []

        # Detect pipe-delimited tables
        def replace_table(match):
            table_blocks.append(match.group(0))
            return f"\n[TABLE_{len(table_blocks) - 1}]\n"

        table_pattern = r'(?:(?:\|[^\n]+\|\n?){3,})'
        cleaned = re.sub(table_pattern, replace_table, text)

        return cleaned, table_blocks

    def _split_on_boundaries(self, text: str, domain: Domain) -> List[str]:
        """Split text on structural boundaries."""

        # Primary: split on double newlines (paragraphs)
        paragraphs = re.split(r'\n\n+', text)

        segments = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Domain-specific: keep equations together (chemistry)
            if domain == Domain.CHEMISTRY:
                if re.search(r'[→⇌⟶]|==>|->|\bΔ\b|\b[A-Z]\d+\b', para):
                    segments.append(para)
                    continue

            # Domain-specific: keep legal clauses together
            if domain == Domain.LAW:
                if re.match(r'^(?:Article|Section|Clause|§)\s*\d+', para, re.I):
                    segments.append(para)
                    continue

            segments.append(para)

        return segments

    def _merge_into_chunks(
        self,
        segments: List[str],
        chunk_size: int,
        chunk_overlap: int,
    ) -> List[str]:
        """
        Merge segments greedily into chunks, then add overlap windows.
        """
        if not segments:
            return []

        chunks = []
        current_chunk = []
        current_size = 0

        for segment in segments:
            seg_size = len(segment.split())

            # If adding this segment would exceed chunk_size, flush current
            if current_size + seg_size > chunk_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))

                # Overlap: carry forward last N words
                overlap_text = self._get_overlap(current_chunk, chunk_overlap)
                current_chunk = [overlap_text] if overlap_text else []
                current_size = len(overlap_text.split()) if overlap_text else 0

            current_chunk.append(segment)
            current_size += seg_size

        # Flush remaining
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks

    def _get_overlap(self, chunks: List[str], overlap_words: int) -> str:
        """Get last N words from chunks list for overlap."""
        full_text = '\n\n'.join(chunks)
        words = full_text.split()
        if len(words) <= overlap_words:
            return full_text
        return ' '.join(words[-overlap_words:])

    def _extract_section_title(self, text: str) -> Optional[str]:
        """Try to extract a section title from chunk text."""
        lines = text.strip().split('\n')
        first_line = lines[0].strip()

        # Check if first line looks like a header
        if (
            len(first_line) < 100
            and (
                first_line.isupper()
                or re.match(r'^\d+[\.\)]\s+\w', first_line)
                or re.match(r'^#{1,4}\s+', first_line)
                or re.match(r'^(?:Section|Article|Chapter)\s+\d+', first_line, re.I)
            )
        ):
            return re.sub(r'^#+\s+', '', first_line)

        return None


chunker = SmartChunker()
