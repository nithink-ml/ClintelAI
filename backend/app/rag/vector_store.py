"""Vector store client for ChromaDB with asynchronous HTTP interface and resilient in-memory fallback."""

from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.rag.embedder import SemanticEmbedder
from app.rag.models import EvidenceChunk


class ChromaVectorStore:
    """Manages clinical evidence chunks in ChromaDB with local fallback."""

    COLLECTION_NAME = "clintelai_clinical_knowledge"

    def __init__(self, host: str | None = None, port: int | None = None):
        self.host = host or settings.CHROMA_HOST
        self.port = port or settings.CHROMA_PORT
        # Handle container vs host port differences
        # In Docker network, port is 8000; from host it might be mapped to 8001
        self.base_url = f"http://{self.host}:{self.port}/api/v1"
        self._collection_id: str | None = None
        self._is_connected = False
        
        # Local in-memory mirror store for resilient fallback
        self._memory_chunks: dict[str, EvidenceChunk] = {}
        self._memory_embeddings: dict[str, list[float]] = {}

    async def _get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=5.0)

    async def check_connection(self) -> bool:
        """Verifies ChromaDB connectivity."""
        candidate_ports = [self.port]
        if self.host in ("localhost", "127.0.0.1") and 8001 not in candidate_ports:
            candidate_ports.append(8001)

        for p in candidate_ports:
            try:
                base = f"http://{self.host}:{p}/api/v1"
                async with httpx.AsyncClient(timeout=2.0) as client:
                    res = await client.get(f"{base}/heartbeat")
                    if res.status_code == 200:
                        self.port = p
                        self.base_url = base
                        self._is_connected = True
                        return True
            except Exception as e:
                logger.debug(f"ChromaDB connection check failed on port {p}: {e}")
        self._is_connected = False
        return False

    async def get_or_create_collection(self) -> str | None:
        """Retrieves or creates the clinical knowledge collection."""
        if self._collection_id:
            return self._collection_id

        if not await self.check_connection():
            logger.warning("ChromaDB is unavailable. Vector store running in in-memory fallback mode.")
            return None

        try:
            async with await self._get_client() as client:
                # 1. Check if collection exists
                res = await client.get(f"/collections/{self.COLLECTION_NAME}")
                if res.status_code == 200:
                    data = res.json()
                    self._collection_id = data.get("id")
                    return self._collection_id

                # 2. Create if not found
                create_res = await client.post(
                    "/collections",
                    json={
                        "name": self.COLLECTION_NAME,
                        "metadata": {
                            "description": "Authoritative clinical guidelines from WHO, ICMR, MoHFW, and PubMed",
                            "dimension": SemanticEmbedder.DIMENSION,
                        },
                    },
                )
                if create_res.status_code in (200, 201):
                    data = create_res.json()
                    self._collection_id = data.get("id")
                    logger.info(f"Initialized ChromaDB collection: {self.COLLECTION_NAME} (ID: {self._collection_id})")
                    return self._collection_id
        except Exception as e:
            logger.error(f"Error initializing ChromaDB collection: {e}")

        return None

    async def add_chunks(self, chunks: list[EvidenceChunk], embeddings: list[list[float]]) -> int:
        """Indexes evidence chunks into ChromaDB and memory mirror."""
        if not chunks:
            return 0

        # Always store in memory mirror for resilient lookup
        for chunk, emb in zip(chunks, embeddings):
            self._memory_chunks[chunk.chunk_id] = chunk
            self._memory_embeddings[chunk.chunk_id] = emb

        coll_id = await self.get_or_create_collection()
        if not coll_id:
            logger.info(f"Stored {len(chunks)} chunks in in-memory vector store mirror.")
            return len(chunks)

        try:
            ids = [c.chunk_id for c in chunks]
            documents = [c.content for c in chunks]
            metadatas = [
                {
                    "document_id": c.document_id,
                    "source_name": c.source_name,
                    "authority_tier": c.authority_tier,
                    "title": c.title,
                    "section_title": c.section_title,
                    "url": c.url,
                    "published_date": c.published_date,
                    "keywords": ",".join(c.keywords),
                }
                for c in chunks
            ]

            payload = {
                "ids": ids,
                "embeddings": embeddings,
                "documents": documents,
                "metadatas": metadatas,
            }

            async with await self._get_client() as client:
                res = await client.post(f"/collections/{coll_id}/add", json=payload)
                if res.status_code in (200, 201):
                    logger.info(f"Successfully indexed {len(chunks)} chunks in ChromaDB collection.")
                    return len(chunks)
                else:
                    logger.warning(f"ChromaDB add response {res.status_code}: {res.text}. Falling back to memory store.")
        except Exception as e:
            logger.error(f"Failed to add chunks to ChromaDB: {e}. Utilizing in-memory mirror.")

        return len(chunks)

    async def query_dense(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        where_filter: dict[str, Any] | None = None,
    ) -> list[tuple[EvidenceChunk, float]]:
        """Queries the vector store using dense vector similarity."""
        coll_id = await self.get_or_create_collection()

        # If ChromaDB is connected and active
        if coll_id and self._is_connected:
            try:
                payload: dict[str, Any] = {
                    "query_embeddings": [query_embedding],
                    "n_results": top_k * 2,  # Fetch more to allow post-filtering
                }
                if where_filter:
                    payload["where"] = where_filter

                async with await self._get_client() as client:
                    res = await client.post(f"/collections/{coll_id}/query", json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        ids = data.get("ids", [[]])[0]
                        distances = data.get("distances", [[]])[0] if "distances" in data else []
                        
                        results: list[tuple[EvidenceChunk, float]] = []
                        metadatas = data.get("metadatas", [[]])[0] if "metadatas" in data else []
                        documents = data.get("documents", [[]])[0] if "documents" in data else []

                        for i, chunk_id in enumerate(ids):
                            chunk = self._memory_chunks.get(chunk_id)
                            if not chunk and metadatas and i < len(metadatas) and metadatas[i]:
                                m = metadatas[i]
                                kw = m.get("keywords", "").split(",") if m.get("keywords") else []
                                chunk = EvidenceChunk(
                                    chunk_id=chunk_id,
                                    document_id=m.get("document_id", "DOC"),
                                    source_name=m.get("source_name", "Authoritative Source"),
                                    authority_tier=m.get("authority_tier", "Tier 1"),
                                    title=m.get("title", ""),
                                    section_title=m.get("section_title", ""),
                                    url=m.get("url", ""),
                                    published_date=m.get("published_date", ""),
                                    content=documents[i] if documents and i < len(documents) else "",
                                    keywords=kw,
                                )
                                self._memory_chunks[chunk_id] = chunk

                            if not chunk:
                                continue

                            # Convert distance to similarity score
                            dist = distances[i] if i < len(distances) else 0.5
                            chunk_emb = self._memory_embeddings.get(chunk_id)
                            if chunk_emb:
                                sim = SemanticEmbedder.cosine_similarity(query_embedding, chunk_emb)
                            else:
                                sim = max(0.0, 1.0 - (dist / 2.0))

                            results.append((chunk, sim))

                        results.sort(key=lambda x: x[1], reverse=True)
                        return results[:top_k]
            except Exception as e:
                logger.warning(f"ChromaDB query failed: {e}. Executing in-memory dense vector search.")

        # Fallback in-memory search
        return self._query_memory(query_embedding, top_k, where_filter)

    def _query_memory(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        where_filter: dict[str, Any] | None = None,
    ) -> list[tuple[EvidenceChunk, float]]:
        """In-memory cosine similarity search across all stored chunks."""
        scores: list[tuple[EvidenceChunk, float]] = []

        for chunk_id, chunk in self._memory_chunks.items():
            # Check filter
            if where_filter:
                match = True
                for k, v in where_filter.items():
                    if getattr(chunk, k, None) != v:
                        match = False
                        break
                if not match:
                    continue

            emb = self._memory_embeddings.get(chunk_id)
            if not emb:
                continue

            sim = SemanticEmbedder.cosine_similarity(query_embedding, emb)
            scores.append((chunk, sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def get_all_chunks(self) -> list[EvidenceChunk]:
        """Returns all chunks in the store."""
        return list(self._memory_chunks.values())

    def get_chunk_count(self) -> int:
        """Returns total indexed chunk count."""
        return len(self._memory_chunks)
