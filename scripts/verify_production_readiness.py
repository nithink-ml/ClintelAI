"""ClintelAI Production Readiness Pre-Flight Verification Script."""

import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.config import Settings, settings
from app.db.session import check_db_health, engine
from app.rag.pipeline import RAGPipeline
from app.rag.providers.gemini import GeminiProvider
from sqlalchemy import text


async def run_preflight_checks() -> bool:
    print("=" * 70)
    print("ClintelAI Production Readiness Pre-Flight Verification")
    print("=" * 70)
    all_passed = True

    # 1. Production Validator Test
    print("[Check 1/6] Verifying Production Configuration Invariants...")
    try:
        # Must reject insecure secret keys in production
        try:
            Settings(ENVIRONMENT="production", DEBUG=False, SECRET_KEY="weak")
            print("  [FAIL] Insecure SECRET_KEY was not rejected in production.")
            all_passed = False
        except ValueError:
            print("  [PASS] Insecure SECRET_KEY correctly rejected in production.")

        # Must reject LLM_FALLBACK_ENABLED=True in production
        try:
            Settings(
                ENVIRONMENT="production",
                DEBUG=False,
                SECRET_KEY="a" * 32,
                LLM_FALLBACK_ENABLED=True,
            )
            print("  [FAIL] LLM_FALLBACK_ENABLED=True was not rejected in production.")
            all_passed = False
        except ValueError:
            print("  [PASS] LLM_FALLBACK_ENABLED=True correctly rejected in production.")
    except Exception as exc:
        print(f"  [FAIL] Configuration validator exception: {exc}")
        all_passed = False

    # 2. Database Connectivity & PostGIS
    print("\n[Check 2/6] Verifying Database Connectivity & Spatial Extensions...")
    db_health = await check_db_health()
    print(f"  Database status: {db_health.get('status')} ({db_health.get('engine')})")
    if db_health.get("status") in ["connected", "healthy"]:
        print("  [PASS] Database connectivity verified.")
        async with engine.connect() as conn:
            # Check PostGIS extension
            try:
                res = await conn.execute(text("SELECT postgis_full_version();"))
                postgis_ver = res.scalar()
                print(f"  [PASS] PostGIS active: {postgis_ver[:60]}...")
            except Exception:
                print("  [INFO] PostGIS function not available (running SQLite dev engine).")
    else:
        print("  [FAIL] Database connection could not be established.")
        all_passed = False

    # 3. ChromaDB Vector Store & Knowledge Base
    print("\n[Check 3/6] Verifying Clinical Vector Store & Knowledge Base...")
    try:
        pipeline = RAGPipeline.get_instance()
        await pipeline.initialize()
        chunks = pipeline.vector_store.get_chunk_count()
        print(f"  Total Indexed Clinical Chunks: {chunks}")
        if chunks >= 30:
            print("  [PASS] Vector store populated with authoritative clinical chunks.")
        else:
            print(f"  [WARN] Vector store has {chunks} chunks (expected >= 30).")
    except Exception as exc:
        print(f"  [FAIL] Vector store verification failed: {exc}")
        all_passed = False

    # 4. Gemini Provider Configuration & Safe Fallback
    print("\n[Check 4/6] Verifying Gemini Provider Configuration & Degraded Mode...")
    gemini = GeminiProvider()
    print(f"  Provider Name: {gemini.provider_name}")
    print(f"  Model Target: {gemini.model}")
    print(f"  API Key Present: {gemini.is_available}")
    print(f"  Fallback Enabled: {gemini.fallback_enabled}")
    if gemini.fallback_enabled:
        print("  [WARN] LLM_FALLBACK_ENABLED is currently True in environment.")
    else:
        print("  [PASS] LLM_FALLBACK_ENABLED is False (Production safe).")

    # 5. Production Dockerfile Non-Root User Verification
    print("\n[Check 5/6] Verifying Docker Container Hardening...")
    dockerfile_backend = (
        Path(__file__).resolve().parent.parent
        / "infrastructure"
        / "docker"
        / "backend.Dockerfile"
    )
    content = dockerfile_backend.read_text()
    if "USER appuser" in content and "appgroup" in content:
        print("  [PASS] Backend Dockerfile enforces non-root execution (appuser).")
    else:
        print("  [FAIL] Backend Dockerfile does not enforce non-root user.")
        all_passed = False

    if "HEALTHCHECK" in content:
        print("  [PASS] Backend Dockerfile defines container HEALTHCHECK.")
    else:
        print("  [FAIL] Backend Dockerfile missing HEALTHCHECK.")
        all_passed = False

    # 6. Rate Limiting Verification
    print("\n[Check 6/6] Verifying Production Rate Limiter Module...")
    try:
        from app.core.rate_limit import RateLimiter

        limiter = RateLimiter(requests=10, window_seconds=60, prefix="test")
        print("  [PASS] RateLimiter module successfully loaded.")
    except Exception as exc:
        print(f"  [FAIL] RateLimiter module import error: {exc}")
        all_passed = False

    print("=" * 70)
    if all_passed:
        print("RESULT: ALL PRODUCTION PRE-FLIGHT CHECKS PASSED.")
    else:
        print("RESULT: PRE-FLIGHT CHECKS DETECTED ISSUES.")
    print("=" * 70)
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(run_preflight_checks())
    sys.exit(0 if success else 1)
