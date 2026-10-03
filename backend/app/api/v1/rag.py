"""Evidence-Grounded Clinical Retrieval and Generation API endpoints."""

import re

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, log_audit_event, require_role
from app.core.logging import logger
from app.models.user import User
from app.rag.models import (
    IngestionReport,
    RAGQueryRequest,
    RAGQueryResponse,
)
from app.rag.pipeline import RAGPipeline

router = APIRouter()


def sanitize_query_for_audit(query: str) -> str:
    """Masks potential identifiable numbers, phone numbers, or emails from query logs."""
    masked = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_MASKED]", query)
    masked = re.sub(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE_MASKED]", masked)
    return masked


@router.post(
    "/query",
    response_model=RAGQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Evidence-Grounded Clinical Query",
    description=(
        "Retrieves verified clinical evidence from indexed authoritative guideline datasets (WHO, ICMR, MoHFW, PubMed) "
        "and generates a grounded response with structured inline citations and safety screening. "
        "Note: Uses a curated, versioned guideline dataset, not a real-time medical feed."
    ),
)
async def query_clinical_knowledge(
    request_data: RAGQueryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RAGQueryResponse:
    # 1. Retrieve RAG pipeline
    pipeline = RAGPipeline.get_instance()

    # 2. Execute RAG query (Safety + Retrieval + Grounded Synthesis)
    response = await pipeline.query(request_data)

    # 3. Privacy-safe Audit logging (PHI/PII masked)
    audit_summary = {
        "query_masked": sanitize_query_for_audit(request_data.query),
        "language": request_data.language,
        "abstained": response.abstained,
        "abstention_reason": response.abstention_reason,
        "is_emergency": response.emergency.is_emergency,
        "emergency_level": response.emergency.level,
        "citations_count": len(response.citations),
        "confidence_score": response.confidence_score,
        "top_score": response.retrieval_metadata.top_similarity_score,
        "llm_provider": response.llm_provider,
        "fallback_used": response.fallback_used,
        "generation_mode": response.retrieval_metadata.generation_mode,
    }

    try:
        await log_audit_event(
            db=db,
            action="RAG_QUERY",
            user_id=None,
            request=request,
            details=audit_summary,
        )
    except Exception as e:
        logger.warning(f"Audit logging skipped for query: {e}")

    return response


@router.get(
    "/sources",
    response_model=IngestionReport,
    status_code=status.HTTP_200_OK,
    summary="List Ingested Clinical Knowledge Sources",
    description="Returns the provenance, authority tiers, document counts, and URLs of all indexed sources.",
)
async def list_sources() -> IngestionReport:
    pipeline = RAGPipeline.get_instance()
    if not pipeline.is_initialized:
        await pipeline.initialize()
    return pipeline.get_ingestion_report()


@router.post(
    "/ingest",
    response_model=IngestionReport,
    status_code=status.HTTP_200_OK,
    summary="Trigger Knowledge Ingestion and Indexing",
    description="Admin-only endpoint to re-parse, embed, and index authoritative clinical guidelines.",
)
async def reindex_knowledge(
    request: Request,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> IngestionReport:
    pipeline = RAGPipeline.get_instance()
    report = await pipeline.initialize()

    await log_audit_event(
        db=db,
        action="RAG_REINDEX",
        user_id=current_user.id,
        request=request,
        details={
            "total_documents": report.total_documents,
            "total_chunks": report.total_chunks,
            "status": "SUCCESS",
        },
    )

    return report
