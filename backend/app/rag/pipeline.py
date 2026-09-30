"""End-to-end Evidence-Grounded RAG Pipeline orchestrator."""

import time
from pathlib import Path

from app.core.config import settings
from app.core.logging import logger
from app.rag.embedder import SemanticEmbedder
from app.rag.generator import GroundedGenerator
from app.rag.models import (
    ClinicalDocument,
    EvidenceChunk,
    IngestedSourceSummary,
    IngestionReport,
    RAGQueryRequest,
    RAGQueryResponse,
    RetrievalMetadata,
)
from app.rag.parser import DocumentParser
from app.rag.retriever import HybridClinicalRetriever
from app.rag.safety import MedicalSafetyEngine
from app.rag.vector_store import ChromaVectorStore


class RAGPipeline:
    """Coordinates document ingestion, vector indexing, hybrid retrieval, safety screening, and grounded response synthesis."""

    _instance: "RAGPipeline | None" = None

    def __init__(self, sources_dir: Path | str | None = None):
        self.sources_dir = Path(sources_dir or (Path(__file__).parent / "data" / "sources"))
        self.vector_store = ChromaVectorStore()
        self.retriever = HybridClinicalRetriever(self.vector_store)
        self.documents: list[ClinicalDocument] = []
        self.chunks: list[EvidenceChunk] = []
        self.is_initialized = False

    @classmethod
    def get_instance(cls) -> "RAGPipeline":
        if cls._instance is None:
            cls._instance = RAGPipeline()
        return cls._instance

    async def initialize(self) -> IngestionReport:
        """Loads and indexes authoritative clinical guidelines into the vector store."""
        start_time = time.time()
        logger.info(f"Initializing RAG Knowledge Ingestion Pipeline from {self.sources_dir}...")

        # 1. Parse and chunk authoritative documents
        self.documents, self.chunks = DocumentParser.load_sources_from_directory(self.sources_dir)
        logger.info(f"Parsed {len(self.documents)} authoritative documents into {len(self.chunks)} evidence chunks.")

        # 2. Compute 384-dimensional dense semantic embeddings
        contents = [c.content for c in self.chunks]
        embeddings = SemanticEmbedder.embed_batch(contents)

        # 3. Index chunks into vector store
        await self.vector_store.add_chunks(self.chunks, embeddings)
        self.is_initialized = True

        elapsed = round(time.time() - start_time, 2)
        logger.info(f"RAG Pipeline initialization completed in {elapsed}s.")

        return self.get_ingestion_report()

    def get_ingestion_report(self) -> IngestionReport:
        """Generates summary report of ingested knowledge sources."""
        sources_summary: list[IngestedSourceSummary] = []
        for doc in self.documents:
            doc_chunks = [c for c in self.chunks if c.document_id == doc.document_id]
            sources_summary.append(
                IngestedSourceSummary(
                    document_id=doc.document_id,
                    title=doc.title,
                    source_name=doc.source_name,
                    authority_tier=doc.authority_tier,
                    domain=doc.domain,
                    chunks_count=len(doc_chunks),
                    published_date=doc.published_date,
                    url=doc.url,
                )
            )

        return IngestionReport(
            status="SUCCESS",
            total_documents=len(self.documents),
            total_chunks=len(self.chunks),
            sources=sources_summary,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

    async def query(self, request: RAGQueryRequest) -> RAGQueryResponse:
        """Processes a clinical query through safety evaluation, hybrid retrieval, and grounded synthesis."""
        start_time = time.perf_counter()

        if not self.is_initialized:
            await self.initialize()

        # 1. Medical Safety & Emergency Symptom Evaluation
        emergency = MedicalSafetyEngine.evaluate_emergency(request.query, language=request.language)

        # 2. Hybrid Retrieval
        evidence = await self.retriever.retrieve(
            query=request.query,
            top_k=request.max_evidence_chunks,
            similarity_threshold=settings.RAG_SIMILARITY_THRESHOLD,
            domain_filter=request.domain_filter,
        )

        # 3. Grounded Synthesis & Citation Binding (or Abstention)
        answer, citations, abstained, abstention_reason = GroundedGenerator.generate_response(
            query=request.query,
            evidence=evidence,
            language=request.language,
            emergency_detected=emergency.is_emergency,
        )

        # 4. Confidence Score Estimation
        if abstained or not evidence:
            confidence = 0.0
        else:
            top_score = evidence[0][1]
            avg_score = sum(s for _, s in evidence) / len(evidence)
            confidence = round(0.7 * top_score + 0.3 * avg_score, 4)

        # 5. Localized Clinical Disclaimer
        disclaimer = MedicalSafetyEngine.get_disclaimer(language=request.language)

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return RAGQueryResponse(
            query=request.query,
            language=request.language,
            answer=answer,
            citations=citations,
            confidence_score=confidence,
            abstained=abstained,
            abstention_reason=abstention_reason,
            medical_safety_level="EMERGENCY_ESCALATION" if emergency.is_emergency else "INFORMATIONAL_VERIFIED",
            safety_disclaimer=disclaimer,
            emergency=emergency,
            retrieval_metadata=RetrievalMetadata(
                chunks_evaluated=self.vector_store.get_chunk_count(),
                chunks_retained=len(evidence),
                top_similarity_score=evidence[0][1] if evidence else 0.0,
                retrieval_strategy="hybrid_dense_lexical_rrf",
                latency_ms=latency_ms,
            ),
        )
