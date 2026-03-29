"""
Embedding Generation + ChromaDB Vector Store
Uses sentence-transformers (free, local) for embeddings.
ChromaDB for persistent vector storage.
"""

from typing import List, Dict, Optional, Tuple
from pathlib import Path
import numpy as np
from loguru import logger

from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings as ChromaSettings

from config import settings
from pipeline.chunking import TextChunk


class EmbeddingEngine:
    """
    Wraps sentence-transformers model.
    Model: all-MiniLM-L6-v2 (22M params, 384-dim, fast, free).
    """

    def __init__(self):
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.dimension = settings.EMBEDDING_DIMENSION
        logger.info("Embedding model loaded ✓")

    def embed(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Embed a list of texts. Returns (N, D) array."""
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 50,
            normalize_embeddings=True,  # cosine similarity ready
            convert_to_numpy=True,
        )
        return embeddings

    def embed_single(self, text: str) -> np.ndarray:
        """Embed a single text. Returns (D,) array."""
        return self.embed([text])[0]


class VectorStore:
    """
    ChromaDB-backed vector store.
    Supports per-document collections + cross-document search.
    """

    COLLECTION_NAME = "scriptorium_docs"

    def __init__(self, embedding_engine: EmbeddingEngine):
        self.embedding_engine = embedding_engine

        # Persistent ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(settings.CHROMA_DIR),
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        # Single collection for all documents (filter by doc_id)
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

        logger.info(
            f"VectorStore initialized | "
            f"Collection: {self.COLLECTION_NAME} | "
            f"Existing chunks: {self.collection.count()}"
        )

    def add_chunks(self, chunks: List[TextChunk]) -> int:
        """
        Embed and store a list of chunks.
        Returns number of chunks added.
        """
        if not chunks:
            return 0

        texts = [c.text for c in chunks]
        ids = [c.chunk_id for c in chunks]
        metadatas = [
            {
                "doc_id": c.doc_id,
                "page_num": c.page_num,
                "chunk_index": c.chunk_index,
                "word_count": c.word_count,
                "is_table": str(c.is_table),
                "section_title": c.section_title or "",
            }
            for c in chunks
        ]

        # Generate embeddings
        logger.info(f"Embedding {len(chunks)} chunks...")
        embeddings = self.embedding_engine.embed(texts)

        # Upsert into ChromaDB
        self.collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings.tolist(),
            metadatas=metadatas,
        )

        logger.info(f"Stored {len(chunks)} chunks in vector store")
        return len(chunks)

    def retrieve(
        self,
        query: str,
        doc_ids: Optional[List[str]] = None,
        top_k: int = None,
        include_tables: bool = True,
    ) -> List[Dict]:
        """
        Retrieve top-k chunks relevant to query.
        Optionally filter to specific documents.
        """
        top_k = top_k or settings.TOP_K_RETRIEVAL

        query_embedding = self.embedding_engine.embed_single(query)

        # Build filter
        where_filter = None
        if doc_ids:
            if len(doc_ids) == 1:
                where_filter = {"doc_id": {"$eq": doc_ids[0]}}
            else:
                where_filter = {"doc_id": {"$in": doc_ids}}

        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=min(top_k * 2, self.collection.count() or 1),  # over-retrieve for reranking
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        # Parse results
        retrieved = []
        if results["documents"] and results["documents"][0]:
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                # Convert distance to similarity score (cosine: dist = 1 - similarity)
                similarity = 1.0 - dist

                if not include_tables and meta.get("is_table") == "True":
                    continue

                retrieved.append({
                    "text": doc,
                    "doc_id": meta["doc_id"],
                    "page_num": meta["page_num"],
                    "chunk_index": meta["chunk_index"],
                    "section_title": meta.get("section_title", ""),
                    "is_table": meta.get("is_table") == "True",
                    "similarity": round(similarity, 4),
                })

        # Rerank: MMR (Maximal Marginal Relevance) for diversity
        reranked = self._mmr_rerank(query_embedding, retrieved, top_k, lambda_=0.6)

        return reranked

    def _mmr_rerank(
        self,
        query_embedding: np.ndarray,
        candidates: List[Dict],
        k: int,
        lambda_: float = 0.6,
    ) -> List[Dict]:
        """
        MMR reranking for relevance + diversity.
        λ=1 → pure relevance, λ=0 → pure diversity.
        """
        if not candidates or k <= 0:
            return candidates[:k]

        selected = []
        remaining = list(candidates)

        while len(selected) < k and remaining:
            if not selected:
                # First: pick highest similarity
                best = max(remaining, key=lambda x: x["similarity"])
            else:
                # MMR score: λ * sim(q, d) - (1-λ) * max_sim(d, selected)
                selected_texts = [s["text"] for s in selected]
                selected_embs = self.embedding_engine.embed(selected_texts)

                best = None
                best_score = -float("inf")

                for cand in remaining:
                    cand_emb = self.embedding_engine.embed_single(cand["text"])
                    rel_score = cand["similarity"]

                    # Max similarity to already-selected chunks
                    redundancy = max(
                        float(np.dot(cand_emb, sel_emb))
                        for sel_emb in selected_embs
                    )

                    mmr_score = lambda_ * rel_score - (1 - lambda_) * redundancy
                    if mmr_score > best_score:
                        best_score = mmr_score
                        best = cand

                if best is None:
                    break

            selected.append(best)
            remaining.remove(best)

        return selected

    def delete_document(self, doc_id: str) -> int:
        """Delete all chunks for a document."""
        results = self.collection.get(where={"doc_id": {"$eq": doc_id}})
        ids = results.get("ids", [])
        if ids:
            self.collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} chunks for doc {doc_id}")
        return len(ids)

    def get_document_chunk_count(self, doc_id: str) -> int:
        """Get number of chunks stored for a document."""
        results = self.collection.get(
            where={"doc_id": {"$eq": doc_id}},
            include=[],
        )
        return len(results.get("ids", []))


# Singletons
_embedding_engine: Optional[EmbeddingEngine] = None
_vector_store: Optional[VectorStore] = None


def get_embedding_engine() -> EmbeddingEngine:
    global _embedding_engine
    if _embedding_engine is None:
        _embedding_engine = EmbeddingEngine()
    return _embedding_engine


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore(get_embedding_engine())
    return _vector_store
