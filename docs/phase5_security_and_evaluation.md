# Phase 5: Security, Evaluation & Quality Engineering Report

**Platform:** ClintelAI — Multilingual, Trusted-Source Healthcare Intelligence Platform  
**Document Version:** 1.0.0  
**Phase:** 5 (Security Hardening, RAG & Provider Evaluation, Adversarial Testing, and Observability)  
**Date:** October 2026  
**Status:** Verification Complete — All Tests Passing (77/77 Backend, 11/11 Frontend)

---

## 1. Executive Summary

Phase 5 establishes the security architecture, clinical guardrails, adversarial resilience, and quality engineering standards for ClintelAI. The objective of Phase 5 is to systematically harden the platform against security vulnerabilities, ensure that clinical responses remain strictly evidence-grounded without hallucination, enforce data isolation between synthetic demo records and real provider records, ensure privacy protection for patient location and PII, implement deep observability and graceful degradation, and validate cross-module safety end-to-end.

### Key Milestones Achieved:
1. **Security Hardening**: Enforced OWASP security headers middleware (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection`, `Strict-Transport-Security`, `CSP`, `Referrer-Policy`, `Permissions-Policy`).
2. **Token Security & Rotation**: Implemented RFC 6749 Section 10.4 refresh token rotation and adversarial reuse detection with automatic cascading user session invalidation.
3. **PHI & Location Privacy**: Upgraded logging redaction (`SensitiveDataFilter`) and audit logging (`sanitize_audit_details`) to redact JWTs, credentials, emails, phone numbers, Aadhaar numbers, and coarsen GPS coordinates (~1.1 km resolution).
4. **Gemini LLM Provider Architecture**: Implemented a decoupled clinical LLM provider abstraction (`BaseLLMProvider`, `MockGroundedProvider`, `GeminiProvider`, `get_llm_provider`) with strict prompt constraints, zero ungrounded medical generation, and offline fallback.
5. **Observability & Readiness Probing**: Implemented `/readyz` deep readiness health check probing PostgreSQL PostGIS, Redis, and ChromaDB vector store.
6. **Adversarial & Cross-Module Safety Testing**: Implemented 14 adversarial test scenarios and 5 end-to-end clinical journey scenarios covering prompt injection, SQL-injection safety, XSS resilience, coordinate bounds validation, RBAC enforcement, and emergency escalation.
7. **Dependency Audit & Test Coverage**: Executed `pip-audit` (0 known Python vulnerabilities) and `npm audit`, recording 76% backend test coverage across 3,163 statements and 100% test pass rate across 88 total automated tests (77 backend + 11 frontend).

---

## 2. Threat Modeling & Security Posture (STRIDE / OWASP)

The ClintelAI threat model maps directly to the STRIDE framework and OWASP Top 10 Web Application Security Risks:

| Threat Category | Potential Attack Vector | ClintelAI Mitigation & Defense-in-Depth | Validation Test |
|---|---|---|---|
| **Spoofing** | Forged JWT access tokens, token theft, stolen refresh tokens | Cryptographically signed tokens (`HS256`, 32+ byte secret). Strict refresh token rotation; reusing a revoked refresh token triggers immediate user-wide session revocation. | `test_refresh_token_rotation_and_adversarial_reuse_detection`, `test_unauthorized_admin_endpoints_rbac` |
| **Tampering** | SQL injection in geospatial search; spoofing provider verification badges | Parameterized SQLAlchemy 2.0 and GeoAlchemy2 queries. Invariant runtime guardrail: records with `is_demo_data=True` are strictly forced to `effective_status="DEMO_SIMULATED"`. | `test_adversarial_sql_injection_resilience`, `test_demo_data_adversarial_tampering_isolation` |
| **Repudiation** | Denying critical clinical actions or unauthorized administrative operations | Immutable PostgreSQL audit logging (`audit_logs` table) recording user ID, action, client IP, user-agent, and sanitized operational parameters. | `test_privacy_redaction_and_location_coarsening`, `test_rbac_admin_seed` |
| **Information Disclosure** | Leakage of patient GPS coordinates, JWT tokens, or credentials in server logs | `SensitiveDataFilter` in Python logging automatically redacts JWTs, secrets, emails, phone numbers, and coarsens coordinates. `sanitize_audit_details` coarsens DB audit coordinates. | `test_privacy_redaction_and_location_coarsening`, `test_security_headers_enforced` |
| **Denial of Service** | Malformed coordinates, NaN values, excessive radius payloads, ReDoS | Strict Pydantic V2 bounds validation (`lat: ge=-90.0, le=90.0`, `lon: ge=-180.0, le=180.0`, `radius_km: ge=1.0, le=200.0/500.0`). Non-numeric or out-of-range parameters return HTTP 422 immediately. | `test_malformed_coordinate_bounds_and_nan` |
| **Elevation of Privilege** | Standard patient accounts attempting to trigger dataset re-seeding or RAG reindexing | FastAPI dependency `require_role("admin")` enforcing RBAC. Unauthenticated requests return HTTP 401; standard patient tokens return HTTP 403 Forbidden. | `test_unauthorized_admin_endpoints_rbac` |

---

## 3. RAG Clinical Grounding & Safety Architecture

The RAG pipeline operates under strict clinical safety boundaries:

```
[User Query]
      │
      ▼
[MedicalSafetyEngine] ──(Emergency Red-Flag Detected?)──► [IMMEDIATE EMERGENCY ESCALATION]
      │ (No Red-Flag)                                       • Helplines 112 / 108
      ▼                                                     • Clinical Hospital Recommendation
[Hybrid Clinical Retriever] (Dense 384d Semantic + BM25 Lexical + Reciprocal Rank Fusion)
      │
      ▼
[Evidence Similarity Threshold Check]
      ├── Score < 0.40 or No Evidence ──► [CLINICAL ABSTENTION]
      │                                     • Multi-lingual insufficient evidence notice
      │                                     • Advises consulting registered physician
      │
      ▼ (Score ≥ 0.40)
[LLM Provider: GroundedGenerator / GeminiProvider]
      • Strict Prompt Grounding on WHO / ICMR / MoHFW Chunks
      • Mandatory Inline Bracketed Citations ([1], [2])
      • Output Filter: MedicalSafetyEngine.sanitize_medical_text
      • Mandatory Localized Clinical Disclaimer
```

### Authoritative Source Whitelist:
Only indexed guidelines from accredited bodies are ingested:
1. **World Health Organization (WHO)**: Global disease management fact sheets and treatment protocols.
2. **Indian Council of Medical Research (ICMR)**: National treatment guidelines for antimicrobial use and vector-borne infections.
3. **Ministry of Health & Family Welfare (MoHFW)**: National health programs, clinical standards, and advisories.
4. **Statutory Health Authorities (NCDC, NVBDCP)**: Outbreak response protocols.

### Clinical Safety Boundaries:
- **Zero Hallucination / Strict Abstention**: If retrieved evidence score is below 0.40 or no matching guideline is indexed, ClintelAI abstains (`abstained=True`) rather than generating unverified advice.
- **Non-Diagnostic Constraint**: Medical assertions such as `"You have [condition]"` or `"Take [dose]"` are programmatically transformed by `MedicalSafetyEngine.sanitize_medical_text` into guideline associations and physician consultation instructions.
- **Emergency Priority**: Any query exhibiting critical or high-risk symptoms (crushing chest pain, slurred speech, unresponsiveness, severe respiratory distress) triggers immediate emergency escalation across all endpoints (RAG, Providers, Alerts).

---

## 4. Provider Discovery & Health Alerts Quality

### Provider Discovery:
- **Spatial Accuracy**: Verified using PostGIS `ST_DWithin` and `ST_Distance` on spherical geography coordinates (`SRID=4326`). Results are strictly sorted in ascending geographic distance order.
- **Demo Data Safeguards**: Synthetic providers seeded for local testing have `is_demo_data=True`. Runtime schemas enforce that `effective_status="DEMO_SIMULATED"` and `effective_tier="tier_4_demo"`, preventing demo providers from ever displaying an official `VERIFIED` badge.
- **Verification Provenance**: Real provider records retain source metadata, verification method, timestamp, and registry ID.

### Regional Health Alerts:
- **Trusted Publisher Enforcement**: `HealthAlertService.validate_trusted_source` validates source name and URL against trusted statutory domains (`gov.in`, `nic.in`, `who.int`, `icmr.org.in`). Social media URLs, blogs, and unverified feeds are rejected.
- **Freshness Engine**: Dynamic freshness status is computed on every query:
  - `FRESH`: Issued or verified within the last 24 hours.
  - `RECENT`: Issued or verified within 1 to 7 days.
  - `STALE`: Older than 7 days, accompanied by verification instructions.
  - `EXPIRED`: Past `valid_until` timestamp; excluded from active public searches.
- **Geographic Syndication**: Spatial proximity queries return localized alerts based on PostGIS distance. National public health advisories (`target_scope="ALL_INDIA"`, e.g. national immunization campaigns or nationwide heatwave advisories) propagate across all geographic queries.

---

## 5. Gemini Integration Architecture

ClintelAI implements a modular LLM provider architecture designed for production readiness:

```
                      ┌──────────────────────┐
                      │   BaseLLMProvider    │
                      └──────────┬───────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 │                               │
                 ▼                               ▼
      ┌─────────────────────┐         ┌─────────────────────┐
      │ MockGroundedProvider │         │   GeminiProvider    │
      └─────────────────────┘         └─────────────────────┘
         • Deterministic offline         • Google GenAI REST API
         • Zero flakiness in tests       • Strict grounding prompt
         • Instant fallback              • Temperature: 0.1
                                         • Secret key via settings
                                         • Graceful mock fallback
```

### Architecture Specifications:
1. **Secret Safety**: `GEMINI_API_KEY` is loaded strictly from environment configuration (`Settings.GEMINI_API_KEY`). It is never passed to the frontend bundle, never committed to git, and omitted from public models and health responses.
2. **Evidence-Grounded Prompting**: The Gemini prompt strictly provides retrieved WHO/ICMR/MoHFW chunks under an authoritative evidence block, instructing the model to rely exclusively on the text, forbid medical prescriptions or diagnostic claims, and include source citations.
3. **Resilience & Fallback**: If `GEMINI_API_KEY` is unset, or if network connectivity to the Gemini API times out or fails, `GeminiProvider` logs a warning and automatically delegates to `MockGroundedProvider`, guaranteeing uninterrupted service.
4. **Phase 6 Readiness Notice**: Offline test suites utilize `MockGroundedProvider` for deterministic execution. Live validation with a provisioned production Gemini key will be conducted during Phase 6 deployment.

---

## 6. Observability, Health & Graceful Degradation

### Health & Readiness Endpoints:
- **`/healthz`**: Lightweight liveness probe for container orchestrators and load balancers. Returns `{"status": "alive", "app": "ClintelAI"}`.
- **`/readyz`**: Deep readiness probe that actively inspects subsystem availability:
  - Database connectivity (SQL query check via `check_db_health()`).
  - Redis cache status and in-memory fallback state.
  - ChromaDB vector store initialization and indexed chunk counts.
  - Returns HTTP 200 with status `ready` when operational; returns HTTP 503 with status `degraded` if the primary database is unavailable.
- **`/api/v1/health`**: Comprehensive health dossier with operational metadata.

### Graceful Degradation Matrix:

| Subsystem | Failure Condition | Degradation Behavior | Recovery Mechanism |
|---|---|---|---|
| **PostgreSQL PostGIS** | Container stopped or connection timeout | `/readyz` returns HTTP 503 `degraded`. Queries fall back to `DATABASE_FALLBACK_URL` (SQLite) in development or return HTTP 503 in production. | Automatic pool reconnect with `pool_pre_ping=True`. |
| **Redis** | Redis service down | Seamless automatic fallback to local in-memory TTL cache (`REDIS_FALLBACK_IN_MEMORY=True`). Rate limiting and caching remain active. | Client reconnects automatically upon Redis availability. |
| **ChromaDB** | Vector DB service unreachable | RAG pipeline falls back to in-memory cosine similarity search over parsed evidence chunks. Knowledge retrieval remains functional. | Vector store reconnects upon service restart. |
| **External Geocoding (Nominatim)** | Rate limited or network failure | Falls back to internal regex/keyword city coordinate gazetteer (covering Chennai, Bengaluru, Kozhikode, Mumbai, Delhi, etc.). | Circuit breaker resets after configured window. |
| **Gemini API** | Quota exceeded, network timeout, or invalid key | `GeminiProvider` catches exceptions and immediately falls back to deterministic `MockGroundedProvider`. | Subsequent requests retry Gemini API call. |

---

## 7. Dependency & Supply Chain Security Audit

### Python Dependencies:
- **Tool**: `pip-audit --timeout 60`
- **Result**: `No known vulnerabilities found`
- **Audit Status**: **Clean (0 Vulnerabilities)** across all 80+ backend packages.

### Node / Frontend Dependencies:
- **Tool**: `npm audit`
- **Findings**: 7 high-severity advisory findings on transitive dependency `braces` (stack-exhaustion DoS through deeply nested glob patterns), introduced via `micromatch` in build-time devDependencies (`tailwindcss` and `eslint-config-next`).
- **Risk Assessment & Acceptance**:
  - The vulnerable code path exists exclusively in development and build-time tooling (`tailwindcss` CLI and `eslint` file globbing).
  - The production Next.js runtime artifact (`.next/standalone` / runner container) does not expose or execute file globbing against untrusted user input.
  - Upgrading requires a breaking change to TailwindCSS v4 (`npm audit fix --force` would install `tailwindcss@4.3.3`), which is incompatible with the current Tailwind v3 configuration.
  - **Accepted Risk**: Formally documented as an accepted build-time devDependency risk for Phase 5. Scheduled for review during Phase 6 dependency refresh.

### Container Base Images:
- Backend: `python:3.11-slim` (minimal attack surface, non-essential tools stripped).
- Frontend: `node:20-alpine` (multi-stage build, executed under non-root user `nextjs:nodejs` UID 1001).
- Datastores: `postgis/postgis:16-3.4`, `redis:7-alpine`, `chromadb/chroma:0.5.5`.

---

## 8. Automated Test Matrix & Evaluation Results

### Complete Test Execution Summary:
- **Total Backend Tests**: 77 passed / 77 total (100% pass rate in 13.79s)
- **Total Frontend Tests**: 11 passed / 11 total (100% pass rate in 142ms)
- **Phase 4 Health Alert Benchmark**: 15 / 15 passed (100%)
- **Phase 3 Provider Benchmark**: 12 / 12 passed (100%)
- **Phase 2 RAG Benchmark**: 10 / 10 passed (100%)
- **Code Linter**: `ruff check` — All checks passed (0 errors)
- **Frontend Linter**: `eslint` — Clean (0 errors)
- **TypeScript**: `tsc --noEmit` — Clean (0 errors)
- **Production Build**: `next build` — Succeeded (0 errors)

### Adversarial Security Test Suite (`test_adversarial_security.py`):
1. `test_security_headers_enforced`: OWASP security headers verified.
2. `test_readiness_probe_readyz`: Deep readiness probe verified.
3. `test_prompt_injection_rag_guardrails`: Prompt injection resistance verified.
4. `test_adversarial_sql_injection_resilience`: SQL-injection immunity verified.
5. `test_adversarial_xss_payload_resilience`: XSS script payload neutralization verified.
6. `test_malformed_coordinate_bounds_and_nan`: Invalid coordinate rejection (422) verified.
7. `test_unauthorized_admin_endpoints_rbac`: RBAC enforcement across admin endpoints verified.
8. `test_refresh_token_rotation_and_adversarial_reuse_detection`: Refresh token rotation and reuse revocation verified.
9. `test_demo_data_adversarial_tampering_isolation`: Demo data isolation verified.
10. `test_fake_alert_trusted_source_rejection`: Untrusted alert source rejection verified.
11. `test_emergency_symptoms_embedded_in_benign_queries`: Embedded red flag detection verified.
12. `test_unsupported_medical_question_abstention`: Fictional query abstention verified.
13. `test_diagnosis_and_prescription_abstention`: Prescription sanitization and disclaimer verified.
14. `test_privacy_redaction_and_location_coarsening`: Log redaction and coordinate coarsening verified.

### End-to-End Safety Test Suite (`test_e2e_safety.py`):
1. `test_e2e_cross_module_clinical_journey`: Full user journey across Auth -> Alerts -> RAG -> Providers.
2. `test_e2e_emergency_escalation_across_all_endpoints`: Emergency precedence across all user endpoints.
3. `test_e2e_multilingual_consistency`: Consistency across 6 Indic languages.
4. `test_e2e_all_india_propagation_for_national_advisories`: National scope alert syndication verified.
5. `test_e2e_error_handling_and_degradation`: Graceful 404, 422, and readiness degradation verified.

---

## 9. Code Coverage Analysis

```
================================ tests coverage ================================
TOTAL: 3,163 Statements | 759 Missed | 76% Overall Codebase Coverage
```

### Coverage Highlights on Security-Critical Modules:
- `app/api/deps.py` (Auth & Audit Sanitization): **87%**
- `app/core/security.py` (Password Hashing & JWT): **94%**
- `app/core/logging.py` (Sensitive Data Redaction): **100%**
- `app/rag/pipeline.py` (RAG Orchestration): **98%**
- `app/rag/retriever.py` (Hybrid Retrieval): **95%**
- `app/rag/embedder.py` (Semantic Embeddings): **95%**
- `app/rag/safety.py` (Clinical Boundaries & Emergencies): **94%**
- `app/rag/providers/mock.py` (Deterministic Grounded Provider): **96%**
- `app/rag/providers/factory.py` (LLM Provider Factory): **100%**
- `app/models/` (All SQLAlchemy Models): **100%**
- `app/schemas/` (Pydantic Request/Response Schemas): **100%**

> **Clinical Quality Engineering Notice:**  
> In accordance with medical AI safety standards, high test coverage and automated benchmark success verify software correctness and deterministic compliance with safety specifications; they do **NOT** claim or constitute independent clinical validation or therapeutic efficacy.

---

## 10. Conclusion & Phase 5 Sign-off

Phase 5 has successfully hardened the ClintelAI backend and frontend architectures, delivered an end-to-end adversarial evaluation suite, established verifiable RAG grounding and provider discovery guardrails, integrated the production Gemini provider abstraction with offline fallbacks, and documented all threat models, degradation modes, and dependency audits.

The platform is stable, hardened, and ready for review.
