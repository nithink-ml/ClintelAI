# Authentication Security Model & Access Token Lifetime Rationale

**Platform:** ClintelAI  
**Phase:** Phase 2 Pre-Requisite Security Clarification  
**Date:** 2026-09-30  
**Status:** Approved & Documented  

---

## 1. Executive Summary & Configuration State

In ClintelAI's configuration, access tokens are configured with a 24-hour lifetime (`ACCESS_TOKEN_EXPIRE_MINUTES=1440` in `.env`, with default fallback of 60 minutes in application settings). Refresh tokens are configured with a 7-day lifetime (`REFRESH_TOKEN_EXPIRE_DAYS=7`).

This document clarifies the rationale, details the operational threat model, and describes the 24-hour token duration as a documented security and operational trade-off for the current architecture—balancing shift-length workflow continuity for frontline workers against token exposure risk—and not as a clinical safety determination.

---

## 2. Rationale for the 24-Hour Access Token Lifetime

### 2.1 Shift-Length Continuity for Healthcare Practitioners
ClintelAI is designed to serve frontline healthcare workers, community health volunteers (ASHAs / ANMs in India), and primary care clinic staff. 
- Clinical shifts frequently run 12 to 24 continuous hours in rural or semi-urban clinics.
- Requiring re-authentication every 15–60 minutes during active clinical workflows introduces dangerous cognitive disruption and delays when retrieving urgent medical guidelines.
- A 24-hour token guarantees uninterrupted operational access across a full healthcare shift.

### 2.2 Urgent Citizen Clinical Queries and Offline/Intermittent Connectivity
- In emergency or acute triage situations, citizens seeking critical guidance (e.g., dengue warning signs, acute chest pain protocols) must not be blocked by unexpected session timeouts.
- In bandwidth-constrained environments, repeated token refresh handshakes over flaky networks increase latency and point-of-care failure rates.

### 2.3 Layered Stateful Validation on Every Request
Although JWT access tokens are signed statelessly via HMAC-SHA256 (`HS256`), every protected API endpoint in ClintelAI utilizes the `get_current_user` dependency:
- The system queries the database (`SELECT users WHERE id = token.sub`) on **every authenticated request**.
- If a user's account is locked, flagged, or deactivated (`is_active=False`), the request is immediately rejected with HTTP 401 Unauthorized, regardless of the remaining JWT expiration time.
- Immediate revocation is thus strictly supported at the user account level without waiting for the 24-hour token to expire.

---

## 3. Threat Model Analysis

| Threat Vector | Severity | Existing Mitigations in ClintelAI | Residual Risk & Decision |
| :--- | :--- | :--- | :--- |
| **Token Theft via Network Interception (Man-in-the-Middle)** | High | Strict TLS/HTTPS in transit; CORS origins restricted to verified origins; tokens never sent in query parameters. | Acceptable. Tokens are only passed in `Authorization: Bearer <token>` headers. |
| **Token Theft via XSS (Cross-Site Scripting)** | High | React/Next.js automatic HTML escaping; strict Content Security Policy; no `dangerouslySetInnerHTML` on untrusted inputs; input sanitization across all forms. | Controlled. Tokens stored in secure browser memory / protected storage. |
| **Compromised User Account** | High | `is_active` database flag verified on every single authenticated request. Disabling user invalidates access immediately across all endpoints. | Neutralized. Revocation does not rely on token expiry. |
| **Token Substitution / Replay (Refresh vs. Access)** | Medium | JWT payload includes strict `type: "access"` and `jti` (unique UUID). `decode_token` and auth dependencies reject tokens whose `type != "access"`. | Fully Mitigated. Refresh tokens cannot be used to call protected APIs. |
| **Secret Compromise** | Critical | `SECRET_KEY` is loaded from environment variables (`.env`), never committed to source code. Minimum 32-character requirement enforced in production. | Protected. |

---

## 4. Architectural Decision & Confirmation

**Conclusion:**  
The 24-hour access-token duration is a documented security and operational trade-off:
1. Revocation is enforceable in real time via database user status verification (`is_active` verified on every authenticated request).
2. The operational trade-off favors shift-length uninterrupted continuity for healthcare practitioners and low-friction emergency citizen guidance over short token cycling.
3. Refresh tokens are tracked with cryptographically unique UUIDs (`jti`) and role-based permissions (`role: user | doctor | admin`).
4. This decision is strictly a software security/operational architecture trade-off for the current development phase, not a clinical safety determination.

**Implementation Decision:**  
Retain the current implementation as designed. For future production scaling with millions of concurrent users, a Redis-backed token denylist (using the `jti` claim) can be enabled to achieve sub-millisecond per-token revocation without altering the client token lifecycle.
