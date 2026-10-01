"""Unit tests for RAG parsing, embedding, vector store, retrieval, safety, and generation."""

import pytest

from app.rag.embedder import SemanticEmbedder
from app.rag.generator import GroundedGenerator
from app.rag.models import (
    ClinicalDocument,
    DocumentSection,
    EvidenceChunk,
    RAGQueryRequest,
)
from app.rag.parser import DocumentParser
from app.rag.pipeline import RAGPipeline
from app.rag.retriever import HybridClinicalRetriever
from app.rag.safety import MedicalSafetyEngine
from app.rag.vector_store import ChromaVectorStore


@pytest.mark.asyncio
async def test_document_parser_and_chunking():
    doc = ClinicalDocument(
        document_id="TEST-GUIDELINE-01",
        title="Test Clinical Guideline for Viral Fever",
        source_name="WHO",
        authority_tier="Tier 1: Global Health Authority",
        url="https://who.int/test",
        published_date="2023-01-01",
        last_reviewed_date="2024-01-01",
        license="CC BY",
        domain="infectious_disease",
        sections=[
            DocumentSection(
                title="Management",
                content=(
                    "Viral fever should be managed with paracetamol and oral hydration. "
                    "Avoid aspirin and NSAIDs in suspected dengue cases to prevent bleeding."
                ),
            ),
            DocumentSection(
                title="Red Flags",
                content="Persistent vomiting and rapid breathing require immediate hospital transfer.",
            ),
        ],
    )

    chunks = DocumentParser.chunk_document(doc, max_chunk_chars=300)
    assert len(chunks) == 2
    assert chunks[0].document_id == "TEST-GUIDELINE-01"
    assert chunks[0].chunk_id == "TEST-GUIDELINE-01-chk-01"
    assert "paracetamol" in chunks[0].keywords
    assert "hydration" in chunks[0].keywords


def test_semantic_embedder():
    v1 = SemanticEmbedder.embed_text("dengue platelet count bleeding")
    v2 = SemanticEmbedder.embed_text("dengue transfusion low platelets")
    v3 = SemanticEmbedder.embed_text("quantum mechanics semiconductor manufacturing")

    assert len(v1) == SemanticEmbedder.DIMENSION
    assert len(v2) == SemanticEmbedder.DIMENSION

    # Cosine similarity between related medical texts should be much higher than unrelated
    sim_medical = SemanticEmbedder.cosine_similarity(v1, v2)
    sim_unrelated = SemanticEmbedder.cosine_similarity(v1, v3)

    assert sim_medical > 0.35
    assert sim_medical > sim_unrelated


def test_multilingual_semantic_embedding():
    # Tamil dengue query vs English dengue query
    v_en = SemanticEmbedder.embed_text("dengue fever platelet count")
    v_ta = SemanticEmbedder.embed_text("டெங்கு காய்ச்சல் பிளேட்லெட்")

    sim = SemanticEmbedder.cosine_similarity(v_en, v_ta)
    assert sim > 0.40


def test_medical_safety_emergency_detection():
    # Critical emergencies
    res_critical = MedicalSafetyEngine.evaluate_emergency(
        "I have crushing chest pain radiating to my left arm and jaw", language="en"
    )
    assert res_critical.is_emergency is True
    assert res_critical.level == "CRITICAL"
    assert "112" in res_critical.emergency_numbers

    # Indic emergency (Tamil)
    res_ta = MedicalSafetyEngine.evaluate_emergency("எனக்கு கடுமையான நெஞ்சு வலி உள்ளது", language="ta")
    assert res_ta.is_emergency is True
    assert "112" in res_ta.emergency_numbers

    # Non-emergency
    res_normal = MedicalSafetyEngine.evaluate_emergency(
        "What are typical dietary guidelines for hypertension?", language="en"
    )
    assert res_normal.is_emergency is False
    assert res_normal.level == "NONE"


def test_medical_safety_text_sanitizer():
    unsafe_text = "You are diagnosed with severe malaria. I prescribe 500mg chloroquine."
    safe_text = MedicalSafetyEngine.sanitize_medical_text(unsafe_text)

    assert "You are diagnosed with" not in safe_text
    assert "I prescribe" not in safe_text
    assert "Potential clinical considerations include" in safe_text


def test_grounded_generator_abstention():
    # Empty evidence must trigger abstention
    ans, citations, abstained, reason = GroundedGenerator.generate_response(
        query="Explain speculative trading in stocks", evidence=[], language="en"
    )
    assert abstained is True
    assert len(citations) == 0
    assert "Insufficient authoritative clinical evidence" in ans
    assert reason == "SIMILARITY_BELOW_THRESHOLD_OR_NO_EVIDENCE"


def test_grounded_generator_with_evidence():
    chunk = EvidenceChunk(
        chunk_id="WHO-01-chk-01",
        document_id="WHO-01",
        source_name="World Health Organization",
        authority_tier="Tier 1: Global Health Authority",
        title="WHO Guidelines on Dengue",
        section_title="Hydration and NSAID Precaution",
        url="https://who.int",
        published_date="2023-01-01",
        content="Oral hydration is the primary treatment. Avoid NSAIDs such as ibuprofen.",
        keywords=["hydration", "nsaids", "ibuprofen"],
    )

    ans, citations, abstained, _ = GroundedGenerator.generate_response(
        query="What is the treatment for dengue fever?",
        evidence=[(chunk, 0.85)],
        language="en",
    )
    assert abstained is False
    assert len(citations) == 1
    assert citations[0].chunk_id == "WHO-01-chk-01"
    assert "[1]" in ans
    assert "World Health Organization" in ans


@pytest.mark.asyncio
async def test_chroma_vector_store_in_memory_fallback():
    # Initialize with non-existent host/port to verify in-memory resilience
    store = ChromaVectorStore(host="invalid-host-9999", port=9999)
    connected = await store.check_connection()
    assert connected is False

    chunk = EvidenceChunk(
        chunk_id="MEM-01",
        document_id="DOC-01",
        source_name="Test Source",
        authority_tier="Tier 2",
        title="Test Guideline",
        section_title="Section 1",
        url="https://example.com",
        published_date="2023-01-01",
        content="Test clinical evidence content for fallback memory indexing.",
        keywords=["evidence", "clinical"],
    )
    emb = SemanticEmbedder.embed_text(chunk.content)
    added = await store.add_chunks([chunk], [emb])
    assert added == 1

    results = await store.query_dense(emb, top_k=1)
    assert len(results) == 1
    assert results[0][0].chunk_id == "MEM-01"
    assert results[0][1] > 0.90


@pytest.mark.asyncio
async def test_hybrid_retriever_ranking():
    store = ChromaVectorStore(host="in_memory", port=0)
    chunk1 = EvidenceChunk(
        chunk_id="CHK-HTN",
        document_id="DOC-HTN",
        source_name="WHO",
        authority_tier="Tier 1",
        title="Hypertension Guidelines",
        section_title="First Line Drugs",
        url="https://who.int",
        published_date="2023-01-01",
        content="First line pharmacological classes include thiazide diuretics and ACE inhibitors.",
        keywords=["hypertension", "diuretics", "systolic"],
    )
    chunk2 = EvidenceChunk(
        chunk_id="CHK-DNG",
        document_id="DOC-DNG",
        source_name="ICMR",
        authority_tier="Tier 1",
        title="Dengue STG",
        section_title="Fluid Therapy",
        url="https://icmr.gov.in",
        published_date="2023-01-01",
        content="Avoid prophylactic platelet transfusion when count is above 20,000.",
        keywords=["dengue", "platelets", "transfusion"],
    )
    emb1 = SemanticEmbedder.embed_text(chunk1.content)
    emb2 = SemanticEmbedder.embed_text(chunk2.content)
    await store.add_chunks([chunk1, chunk2], [emb1, emb2])

    retriever = HybridClinicalRetriever(store)
    results = await retriever.retrieve("blood pressure hypertension drug treatment", top_k=2, similarity_threshold=0.2)
    assert len(results) >= 1
    assert results[0][0].chunk_id == "CHK-HTN"


@pytest.mark.asyncio
async def test_pipeline_end_to_end():
    pipeline = RAGPipeline.get_instance()
    report = await pipeline.initialize()
    assert report.status == "SUCCESS"
    assert report.total_documents > 0
    assert report.total_chunks > 0

    # Query pipeline
    res = await pipeline.query(
        RAGQueryRequest(query="What is the platelet transfusion threshold in dengue?", language="en")
    )
    assert res.abstained is False
    assert len(res.citations) >= 1
    assert res.confidence_score > 0.50
    assert (
        "Indian Council of Medical Research" in res.citations[0].source_name
        or "WHO" in res.citations[0].source_name
        or "ICMR" in res.citations[0].source_name
    )


@pytest.mark.asyncio
async def test_citations_strictly_grounded_and_non_fabricated():
    """Verifies every citation corresponds to an actual indexed chunk with zero metadata fabrication."""
    pipeline = RAGPipeline.get_instance()
    await pipeline.initialize()

    indexed_chunks = {c.chunk_id: c for c in pipeline.chunks}
    indexed_docs = {d.document_id: d for d in pipeline.documents}

    test_queries = [
        "What are the fluid management and platelet transfusion guidelines for dengue according to ICMR?",
        "What is the diagnostic threshold and first-line treatment for Type 2 diabetes in South Asian phenotypes?",
        "What are the first-line drug classes for hypertension according to WHO?",
    ]

    total_verified = 0
    for q in test_queries:
        res = await pipeline.query(RAGQueryRequest(query=q))
        assert res.abstained is False
        assert len(res.citations) > 0

        for c in res.citations:
            total_verified += 1
            # 1. Chunk ID must exist in indexed knowledge base
            assert c.chunk_id in indexed_chunks, f"Chunk {c.chunk_id} not in indexed store"
            orig = indexed_chunks[c.chunk_id]

            # 2. Document ID must exist
            assert c.document_id in indexed_docs, f"Document {c.document_id} not in indexed docs"

            # 3. Exact metadata fidelity checks
            assert c.source_name == orig.source_name
            assert c.authority_tier == orig.authority_tier
            assert c.title == orig.title
            assert c.section_title == orig.section_title
            assert c.url == orig.url
            assert c.published_date == orig.published_date

            # 4. Snippet must be an exact substring of chunk content
            assert c.snippet in orig.content

    assert total_verified >= 6
