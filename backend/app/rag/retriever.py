"""Hybrid clinical retriever combining semantic dense search and medical keyword indexing."""

import math
import re
from typing import Any

from app.rag.embedder import SemanticEmbedder
from app.rag.models import EvidenceChunk
from app.rag.vector_store import ChromaVectorStore


class HybridClinicalRetriever:
    """Performs hybrid semantic and lexical retrieval over clinical knowledge chunks."""

    def __init__(self, vector_store: ChromaVectorStore):
        self.vector_store = vector_store

    def _lexical_score(self, query: str, chunk: EvidenceChunk) -> float:
        """Calculates lexical relevance score based on token and phrase overlap."""
        query_lower = query.lower()
        q_tokens = set()
        for term, mapped in SemanticEmbedder.MULTILINGUAL_CONCEPT_MAP.items():
            if term in query_lower:
                q_tokens.add(mapped)
        for t in re.findall(r"\b[a-z0-9\-\+]{3,}\b", query_lower):
            q_tokens.add(t)

        if not q_tokens:
            return 0.0

        content_lower = chunk.content.lower()
        title_lower = f"{chunk.title} {chunk.section_title}".lower()
        chunk_keywords = {k.lower() for k in chunk.keywords}

        matches = 0
        total_weight = 0.0

        for token in q_tokens:
            token_weight = 0.0
            matched = False
            # Higher weight for title/keyword matches
            if token in title_lower:
                token_weight += 2.0
                matched = True
            if token in chunk_keywords:
                token_weight += 1.5
                matched = True

            if token in content_lower:
                matched = True
                matches += 1
                count = content_lower.count(token)
                tf_boost = min(1.0, math.log1p(count) * 0.3)
                token_weight += 1.0 + tf_boost

            if matched:
                total_weight += token_weight

        # Exact multi-token phrase match bonus
        query_clean = query.lower().strip()
        if len(q_tokens) > 1 and query_clean in content_lower:
            total_weight += 3.0

        max_possible = len(q_tokens) * 3.5
        score = min(1.0, total_weight / max_possible) if max_possible > 0 else 0.0
        return score

    async def retrieve(
        self,
        query: str,
        top_k: int = 4,
        similarity_threshold: float = 0.45,
        domain_filter: str | None = None,
    ) -> list[tuple[EvidenceChunk, float]]:
        """Executes hybrid retrieval and returns reranked, filtered evidence chunks."""
        if not query or not query.strip():
            return []

        # 1. Dense Semantic Retrieval
        query_embedding = SemanticEmbedder.embed_text(query)
        where_filter: dict[str, Any] | None = None
        if domain_filter:
            where_filter = {"domain": domain_filter}

        dense_results = await self.vector_store.query_dense(
            query_embedding=query_embedding,
            top_k=top_k * 3,
            where_filter=where_filter,
        )

        dense_scores: dict[str, float] = {chunk.chunk_id: score for chunk, score in dense_results}
        all_candidate_chunks: dict[str, EvidenceChunk] = {chunk.chunk_id: chunk for chunk, _ in dense_results}

        # Also evaluate lexical match on candidate chunks and memory chunks
        for chunk in self.vector_store.get_all_chunks():
            if chunk.chunk_id not in all_candidate_chunks:
                lex_score = self._lexical_score(query, chunk)
                if lex_score > 0.25:
                    all_candidate_chunks[chunk.chunk_id] = chunk
                    dense_scores[chunk.chunk_id] = SemanticEmbedder.cosine_similarity(
                        query_embedding,
                        self.vector_store._memory_embeddings.get(chunk.chunk_id, []),
                    )

        # 2. Combine Dense + Lexical with Hybrid weighting
        hybrid_scores: list[tuple[EvidenceChunk, float]] = []
        for chunk_id, chunk in all_candidate_chunks.items():
            s_dense = dense_scores.get(chunk_id, 0.0)
            s_lex = self._lexical_score(query, chunk)

            # Weighted combination: 60% semantic, 40% lexical
            s_hybrid = (0.60 * s_dense) + (0.40 * s_lex)

            # Authority tier boost (Tier 1 authorities get slight confidence boost)
            if "Tier 1" in chunk.authority_tier:
                s_hybrid = min(1.0, s_hybrid * 1.05)

            if s_hybrid >= similarity_threshold:
                hybrid_scores.append((chunk, round(s_hybrid, 4)))

        # 3. Sort by hybrid score descending
        hybrid_scores.sort(key=lambda x: x[1], reverse=True)
        return hybrid_scores[:top_k]
