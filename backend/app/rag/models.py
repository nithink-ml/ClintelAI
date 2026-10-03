"""Pydantic and data models for RAG knowledge ingestion, retrieval, and generation."""

from pydantic import BaseModel, Field


class DocumentSection(BaseModel):
    title: str
    content: str


class ClinicalDocument(BaseModel):
    document_id: str
    title: str
    source_name: str
    authority_tier: str
    url: str
    published_date: str
    last_reviewed_date: str
    license: str
    language: str = "en"
    domain: str
    sections: list[DocumentSection]


class EvidenceChunk(BaseModel):
    chunk_id: str
    document_id: str
    source_name: str
    authority_tier: str
    title: str
    section_title: str
    url: str
    published_date: str
    content: str
    keywords: list[str] = Field(default_factory=list)


class Citation(BaseModel):
    citation_index: int
    chunk_id: str
    document_id: str
    source_name: str
    authority_tier: str
    title: str
    section_title: str
    url: str
    published_date: str
    snippet: str
    relevance_score: float


class EmergencyEscalation(BaseModel):
    is_emergency: bool = False
    level: str = "NONE"  # "NONE" | "HIGH" | "CRITICAL"
    symptoms_detected: list[str] = Field(default_factory=list)
    action_message: str = ""
    emergency_numbers: list[str] = Field(default_factory=lambda: ["112", "108"])


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=1000, description="Clinical or health query")
    language: str = Field(
        default="en",
        description="Target language: en, ta, hi, ml, te, kn",
        pattern="^(en|ta|hi|ml|te|kn)$",
    )
    domain_filter: str | None = Field(default=None, description="Optional domain filter")
    max_evidence_chunks: int = Field(default=4, ge=1, le=10)


class GroundedResponse(tuple):
    """Tuple-compatible response container preserving 4-item unpacking and adding generation metadata."""

    answer: str
    citations: list[Citation]
    abstained: bool
    abstention_reason: str | None
    llm_provider: str
    fallback_used: bool
    generation_mode: str

    def __new__(
        cls,
        answer: str,
        citations: list[Citation],
        abstained: bool,
        abstention_reason: str | None,
        llm_provider: str = "mock",
        fallback_used: bool = False,
        generation_mode: str = "MOCK_DIRECT",
    ):
        obj = super().__new__(cls, (answer, citations, abstained, abstention_reason))
        obj.answer = answer
        obj.citations = citations
        obj.abstained = abstained
        obj.abstention_reason = abstention_reason
        obj.llm_provider = llm_provider
        obj.fallback_used = fallback_used
        obj.generation_mode = generation_mode
        return obj


class RetrievalMetadata(BaseModel):
    chunks_evaluated: int
    chunks_retained: int
    top_similarity_score: float
    retrieval_strategy: str
    latency_ms: float
    llm_provider: str = "mock"
    fallback_used: bool = False
    generation_mode: str = "DIRECT"


class RAGQueryResponse(BaseModel):
    query: str
    language: str
    answer: str
    citations: list[Citation]
    confidence_score: float
    abstained: bool
    abstention_reason: str | None = None
    medical_safety_level: str = "INFORMATIONAL_VERIFIED"
    safety_disclaimer: str
    emergency: EmergencyEscalation
    llm_provider: str = "mock"
    fallback_used: bool = False
    retrieval_metadata: RetrievalMetadata


class IngestedSourceSummary(BaseModel):
    document_id: str
    title: str
    source_name: str
    authority_tier: str
    domain: str
    chunks_count: int
    published_date: str
    url: str


class IngestionReport(BaseModel):
    status: str
    total_documents: int
    total_chunks: int
    sources: list[IngestedSourceSummary]
    timestamp: str
