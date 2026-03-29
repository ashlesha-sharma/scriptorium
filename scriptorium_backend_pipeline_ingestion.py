"""
Document Ingestion & OCR Pipeline
Handles PDF parsing, scanned document OCR, and text extraction.
"""

import io
import re
import unicodedata
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
from loguru import logger

from config import settings


@dataclass
class PageContent:
    page_num: int
    text: str
    is_ocr: bool
    word_count: int
    has_tables: bool
    has_images: bool


@dataclass
class DocumentContent:
    doc_id: str
    filename: str
    pages: List[PageContent]
    full_text: str
    page_count: int
    ocr_applied: bool
    metadata: Dict


class DocumentIngester:
    """
    Responsible for:
    1. Parsing native PDFs (text layer extraction via PyMuPDF)
    2. Detecting scanned pages (low text density → trigger OCR)
    3. Running Tesseract OCR on image-based pages
    4. Cleaning and normalizing extracted text
    """

    MIN_TEXT_DENSITY = 50  # chars per page below which OCR is triggered

    def __init__(self):
        try:
            pytesseract.get_tesseract_version()
            self.ocr_available = True
        except Exception:
            logger.warning("Tesseract not found. OCR disabled.")
            self.ocr_available = False

    def ingest(self, file_path: Path, doc_id: str, filename: str) -> DocumentContent:
        """
        Main ingestion entry point. Returns structured DocumentContent.
        """
        logger.info(f"Ingesting: {filename} ({doc_id})")

        pages: List[PageContent] = []
        ocr_applied = False

        try:
            doc = fitz.open(str(file_path))
            total_pages = len(doc)
            logger.info(f"PDF has {total_pages} pages")

            for page_num in range(total_pages):
                page = doc[page_num]
                native_text = page.get_text("text")
                cleaned = self._clean_text(native_text)

                # Detect if page is scanned (insufficient native text)
                is_scanned = len(cleaned.strip()) < self.MIN_TEXT_DENSITY

                if is_scanned and self.ocr_available:
                    logger.debug(f"Page {page_num + 1}: scanned, applying OCR")
                    ocr_text = self._ocr_page(file_path, page_num)
                    text = self._clean_text(ocr_text)
                    is_ocr = True
                    ocr_applied = True
                else:
                    text = cleaned
                    is_ocr = False

                # Detect structural features
                has_tables = self._detect_tables(page, text)
                has_images = len(page.get_images()) > 0

                pages.append(PageContent(
                    page_num=page_num + 1,
                    text=text,
                    is_ocr=is_ocr,
                    word_count=len(text.split()),
                    has_tables=has_tables,
                    has_images=has_images,
                ))

            doc.close()

            # Build full text with page markers
            full_text = self._build_full_text(pages)

            # Extract PDF metadata
            pdf_meta = fitz.open(str(file_path)).metadata or {}

            return DocumentContent(
                doc_id=doc_id,
                filename=filename,
                pages=pages,
                full_text=full_text,
                page_count=total_pages,
                ocr_applied=ocr_applied,
                metadata={
                    "title": pdf_meta.get("title", filename),
                    "author": pdf_meta.get("author", ""),
                    "subject": pdf_meta.get("subject", ""),
                    "creator": pdf_meta.get("creator", ""),
                    "file_size": file_path.stat().st_size,
                },
            )

        except Exception as e:
            logger.error(f"Ingestion failed for {filename}: {e}")
            raise

    def _ocr_page(self, pdf_path: Path, page_num: int) -> str:
        """Convert PDF page to image and run Tesseract OCR."""
        try:
            images = convert_from_path(
                str(pdf_path),
                first_page=page_num + 1,
                last_page=page_num + 1,
                dpi=300,
            )
            if not images:
                return ""

            img = images[0]
            # Pre-process: grayscale, contrast
            img = img.convert("L")

            text = pytesseract.image_to_string(
                img,
                lang=settings.OCR_LANGUAGES,
                config="--psm 6",  # uniform block of text
            )
            return text

        except Exception as e:
            logger.error(f"OCR failed on page {page_num}: {e}")
            return ""

    def _clean_text(self, text: str) -> str:
        """Normalize and clean extracted text."""
        if not text:
            return ""

        # Normalize unicode
        text = unicodedata.normalize("NFKC", text)

        # Remove null bytes and control chars (except newlines/tabs)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

        # Fix hyphenated line breaks (common in PDFs)
        text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)

        # Collapse excessive whitespace
        text = re.sub(r' {3,}', '  ', text)
        text = re.sub(r'\n{4,}', '\n\n\n', text)

        # Remove page headers/footers patterns (short isolated lines)
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip very short isolated lines that look like page numbers
            if re.match(r'^\d{1,3}$', stripped):
                continue
            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines).strip()

    def _detect_tables(self, page: fitz.Page, text: str) -> bool:
        """Heuristic table detection."""
        # PyMuPDF table detection (v1.23+)
        try:
            tabs = page.find_tables()
            if tabs and len(tabs.tables) > 0:
                return True
        except AttributeError:
            pass

        # Fallback: look for tab-separated or pipe-delimited patterns
        pipe_rows = len(re.findall(r'\|.+\|', text))
        tab_rows = len(re.findall(r'\t.+\t', text))
        return (pipe_rows > 3) or (tab_rows > 3)

    def _build_full_text(self, pages: List[PageContent]) -> str:
        """Concatenate pages with clear page markers."""
        parts = []
        for page in pages:
            if page.text.strip():
                parts.append(f"[PAGE {page.page_num}]\n{page.text}")
        return "\n\n".join(parts)


ingester = DocumentIngester()
