"""
RAG Pipeline Orchestrator
Connects retrieval → reasoning → response generation.
Uses HuggingFace Inference API (free tier).
"""

import re
import time
import json
from typing import List, Dict, Optional, Tuple
from loguru import logger
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from models.schemas import (
    Domain, QueryMode, ChatRequest, ChatResponse,
    Citation, StructuredInsight
)
from pipeline.vector_store import VectorStore
from pipeline.domain_detection import detector
from prompts.templates import build_system_prompt, build_rag_prompt


class HuggingFaceLLM:
    """
    HuggingFace Inference API client.
    Free tier: limited rate, but functional for MVP.
    Falls back to a simple extractive response if API unavailable.
    """

    def __init__(self):
        self.api_url = f"{settings.HF_API_URL}/{settings.HF_MODEL}"
        self.headers = {
            "Authorization": f"Bearer {settings.HF_API_KEY}",
            "Content-Type": "application/json",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_new_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> str:
        """Generate response via HuggingFace Inference API."""

        # Format as Mistral instruction format
        prompt = f"<s>[INST] {system_prompt}\n\n{user_prompt} [/INST]"

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_new_tokens,
                "temperature": temperature,
                "top_p": 0.9,
                "repetition_penalty": 1.1,
                "do_sample": temperature > 0,
                "return_full_text": False,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                self.api_url,
                headers=self.headers,
                json=payload,
            )

        if resp.status_code != 200:
            logger.error(f"HF API error: {resp.status_code} {resp.text[:200]}")
            raise httpx.HTTPError(f"HF API returned {resp.status_code}")

        data = resp.json()

        # HF response format: [{"generated_text": "..."}]
        if isinstance(data, list) and data:
            return data[0].get("generated_text", "")
        elif isinstance(data, dict):
            return data.get("generated_text", str(data))

        return str(data)

    def _extractive_fallback(self, context_chunks: List[Dict], query: str) -> str:
        """
        Simple extractive fallback when LLM API is unavailable.
        Returns the most relevant chunk text with basic formatting.
        """
        if not context_chunks:
            return "I was unable to find relevant information in the provided documents."

        top_chunk = context_chunks[0]
        return (
            f"Based on the document (p.{top_chunk.get('page_num', '?')}):\n\n"
            f"{top_chunk['text']}\n\n"
            f"*Note: Using extractive fallback — LLM API unavailable.*"
        )


class RAGPipeline:
    """
    Full RAG pipeline:
    1. Query understanding + mode detection
    2. Retrieval with MMR reranking
    3. Context construction
    4. Domain-aware prompting
    5. Generation + post-processing
    6. Citation extraction
    """

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.llm = HuggingFaceLLM()

    async def query(self, request: ChatRequest, doc_metadata: Dict) -> ChatResponse:
        """
        Main query entry point.
        Returns fully structured ChatResponse with citations.
        """
        start_time = time.time()

        # 1. Determine domain from documents
        domain = self._get_domain(request.doc_ids, doc_metadata)

        # 2. Determine query mode (auto-detect if conversational)
        mode = self._detect_query_mode(request.query, request.mode)

        # 3. Build retrieval query
        retrieval_query = self._build_retrieval_query(
            request.query,
            request.highlight_text,
            mode,
        )

        # 4. Retrieve relevant chunks
        chunks = self.vector_store.retrieve(
            query=retrieval_query,
            doc_ids=request.doc_ids,
            top_k=settings.TOP_K_RETRIEVAL,
        )

        if not chunks:
            return self._empty_response(domain, mode)

        # 5. Build prompts
        system_prompt = build_system_prompt(domain, mode, request.explain_level)
        user_prompt = build_rag_prompt(
            query=request.query,
            context_chunks=chunks,
            domain=domain,
            mode=mode,
            highlight_text=request.highlight_text,
            conversation_history=[m.dict() for m in request.conversation_history],
        )

        # 6. Generate response
        try:
            raw_response = await self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2 if mode == QueryMode.EXTRACTION else 0.35,
            )
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raw_response = self.llm._extractive_fallback(chunks, request.query)

        # 7. Post-process
        answer = self._clean_response(raw_response)

        # 8. Build citations
        citations = self._build_citations(chunks, doc_metadata)

        # 9. Extract structured insights (for extraction mode)
        structured_insights = []
        if mode == QueryMode.EXTRACTION:
            structured_insights = self._parse_structured_insights(answer, citations)

        # 10. Generate follow-up questions
        follow_ups = self._generate_follow_ups(request.query, domain, mode)

        elapsed_ms = int((time.time() - start_time) * 1000)
        confidence = self._estimate_confidence(chunks, answer)

        return ChatResponse(
            answer=answer,
            citations=citations,
            structured_insights=structured_insights,
            domain=domain,
            query_mode=mode,
            confidence=confidence,
            follow_up_questions=follow_ups,
            processing_time_ms=elapsed_ms,
        )

    def _get_domain(self, doc_ids: List[str], doc_metadata: Dict) -> Domain:
        """Get domain from stored document metadata."""
        for doc_id in doc_ids:
            meta = doc_metadata.get(doc_id)
            if meta and hasattr(meta, 'domain'):
                return meta.domain
        return Domain.GENERAL

    def _detect_query_mode(self, query: str, requested_mode: QueryMode) -> QueryMode:
        """Auto-detect mode from query intent if not explicitly set."""
        if requested_mode != QueryMode.CONVERSATIONAL:
            return requested_mode

        q = query.lower()

        if any(w in q for w in ["compare", "vs", "versus", "difference between", "contrast"]):
            return QueryMode.COMPARISON
        if any(w in q for w in ["extract", "list all", "give me all", "table of", "what are the values"]):
            return QueryMode.EXTRACTION
        if any(w in q for w in ["summarize", "summary", "overview", "key points", "main findings"]):
            return QueryMode.SUMMARY

        return QueryMode.CONVERSATIONAL

    def _build_retrieval_query(
        self, query: str, highlight_text: Optional[str], mode: QueryMode
    ) -> str:
        """Augment query for better retrieval."""
        if highlight_text:
            return f"{query} {highlight_text}"
        return query

    def _build_citations(
        self, chunks: List[Dict], doc_metadata: Dict
    ) -> List[Citation]:
        """Convert retrieved chunks to Citation objects."""
        citations = []
        seen = set()

        for i, chunk in enumerate(chunks):
            doc_id = chunk.get("doc_id", "")
            page = chunk.get("page_num", 0)
            key = (doc_id, page)

            if key in seen:
                continue
            seen.add(key)

            meta = doc_metadata.get(doc_id)
            filename = meta.filename if meta else doc_id

            citations.append(Citation(
                doc_id=doc_id,
                filename=filename,
                page=page,
                chunk_text=chunk["text"][:300] + "..." if len(chunk["text"]) > 300 else chunk["text"],
                relevance_score=chunk.get("similarity", 0.0),
                chunk_index=chunk.get("chunk_index", i),
            ))

        return citations

    def _parse_structured_insights(
        self, answer: str, citations: List[Citation]
    ) -> List[StructuredInsight]:
        """Try to parse JSON structured data from extraction-mode responses."""
        insights = []

        # Try to extract JSON block
        json_match = re.search(r'\{.*?"extracted_items".*?\}', answer, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                for item in data.get("extracted_items", []):
                    insights.append(StructuredInsight(
                        category="extracted",
                        label=item.get("label", ""),
                        value=item.get("value", ""),
                        confidence=0.85,
                        source_citation=citations[0] if citations else None,
                    ))
            except json.JSONDecodeError:
                pass

        return insights

    def _generate_follow_ups(
        self, query: str, domain: Domain, mode: QueryMode
    ) -> List[str]:
        """Generate domain-appropriate follow-up questions."""
        domain_follow_ups = {
            Domain.CHEMISTRY: [
                "What are the reaction conditions for this process?",
                "What is the reported yield?",
                "Are there alternative synthesis routes mentioned?",
            ],
            Domain.FINANCE: [
                "How does this compare to the previous period?",
                "What are the key risk factors?",
                "What guidance has management provided?",
            ],
            Domain.LAW: [
                "What precedents are cited in support?",
                "What are the potential counterarguments?",
                "Which jurisdiction does this apply to?",
            ],
            Domain.POLICY: [
                "Who are the key stakeholders affected?",
                "What is the implementation timeline?",
                "What monitoring mechanisms are proposed?",
            ],
            Domain.GENERAL: [
                "What evidence supports this claim?",
                "What are the key limitations?",
                "How does this compare to other findings?",
            ],
        }
        return domain_follow_ups.get(domain, domain_follow_ups[Domain.GENERAL])[:3]

    def _estimate_confidence(self, chunks: List[Dict], answer: str) -> float:
        """Estimate response confidence from retrieval scores."""
        if not chunks:
            return 0.2

        avg_similarity = sum(c.get("similarity", 0) for c in chunks) / len(chunks)
        # Penalize if answer mentions uncertainty
        uncertainty_signals = ["unclear", "not mentioned", "cannot determine", "insufficient"]
        uncertainty_count = sum(1 for s in uncertainty_signals if s in answer.lower())
        penalty = uncertainty_count * 0.1

        return round(max(0.1, min(0.95, avg_similarity - penalty)), 2)

    def _clean_response(self, text: str) -> str:
        """Clean LLM output artifacts."""
        # Remove instruction tokens that leaked
        text = re.sub(r'</?s>|\[INST\]|\[/INST\]', '', text)
        text = re.sub(r'^Assistant:\s*', '', text, flags=re.IGNORECASE)
        return text.strip()

    def _empty_response(self, domain: Domain, mode: QueryMode) -> ChatResponse:
        return ChatResponse(
            answer="I could not find relevant information in the provided documents for this query. "
                   "Please ensure the documents have been processed successfully and try rephrasing your question.",
            citations=[],
            domain=domain,
            query_mode=mode,
            confidence=0.0,
            follow_up_questions=[],
            processing_time_ms=0,
        )
