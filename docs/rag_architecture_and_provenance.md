# Evidence-Grounded Clinical RAG Architecture & Provenance Documentation

**Platform:** ClintelAI  
**Phase:** Phase 2 — Evidence-Grounded RAG and Clinical Knowledge Retrieval  
**Date:** 2026-09-30  
**Status:** Implemented & Verified  

---

## 1. Overview & Source Freshness Declaration

The ClintelAI Clinical Retrieval-Augmented Generation (RAG) system provides structured, evidence-grounded health information retrieved exclusively from an allowlisted corpus of authoritative clinical guidelines.

> [!IMPORTANT]
> **Source Freshness Notice:**
> The current knowledge base is constructed from an **indexed, curated, and versioned JSON clinical guideline dataset** reflecting official publications from WHO, ICMR, MoHFW, and PubMed with verified publication dates.
> 
> **It is NOT a live, real-time medical knowledge feed, dynamic web crawler, or automated streaming pipeline.**
> Clinical guidelines are updated via deliberate, controlled administrative re-indexing (`POST /api/v1/rag/ingest`) after human clinical provenance verification.

---

## 2. Reconciled Knowledge-Base Inventory

The verified guideline repository contains **11 documents** partitioned into **32 distinct semantic evidence chunks** indexed in ChromaDB (`clintelai_clinical_knowledge`):

| Source Organization | Documents | Chunks | Document Identifiers | Authority Tier |
| :--- | :--- | :--- | :--- | :--- |
| **World Health Organization (WHO)** | 4 | 13 | `WHO-DENGUE-2023`<br>`WHO-HYPERTENSION-2023`<br>`WHO-TUBERCULOSIS-2024`<br>`WHO-AMR-2023` | Tier 1: Global Health Authority |
| **Indian Council of Medical Research (ICMR)** | 3 | 10 | `ICMR-DENGUE-STG-2023`<br>`ICMR-DIABETES-STG-2023`<br>`ICMR-ARI-PNEUMONIA-2023` | Tier 1: National Health Research Agency (India) |
| **Ministry of Health & Family Welfare (MoHFW)** | 2 | 5 | `MOHFW-TB-NTEP-2024`<br>`MOHFW-MATERNAL-EMERGENCY-2023` | Tier 1: National Health Ministry (Govt. of India) |
| **PubMed Central / Peer-Reviewed Reviews** | 2 | 4 | `PUBMED-31548210`<br>`PUBMED-34210982` | Tier 2: Peer-Reviewed Clinical Systematic Reviews |
| **Total** | **11** | **32** | **All 11 verified and indexed in ChromaDB** | — |

---

## 3. Provenance & Metadata Schema

Every indexed chunk strictly retains immutable provenance metadata:
- `document_id`: Unique identifier referencing the primary source guideline.
- `chunk_id`: Hierarchical identifier (`<doc_id>-chk-<index>`).
- `source_name`: Publishing agency (e.g., *Indian Council of Medical Research*).
- `authority_tier`: Verification tier (`Tier 1` global/national or `Tier 2` peer-reviewed systematic review).
- `title` & `section_title`: Precise clinical guideline title and section heading.
- `published_date` & `last_reviewed_date`: Document timeline tracking.
- `url`: Canonical link to the official publication or guideline document.
- `keywords`: Extracted medical concepts utilized for hybrid lexical scoring.

---

## 4. Citation Binding & Non-Fabrication Guarantee

The RAG generation pipeline enforces strict evidence grounding:
1. Citations returned by `POST /api/v1/rag/query` are constructed **directly from retrieved `EvidenceChunk` objects**.
2. No generative model is permitted to invent, interpolate, or guess citation URLs, document titles, or source publication dates.
3. Every substantive clinical sentence maps to an inline index `[1]`, `[2]` corresponding to the exact retrieved chunk.
4. When evidence fails the calibrated similarity threshold (`< 0.45`), the engine **abstains completely**, returning an empty citations array (`citations: []`) and an explicit refusal message.

---

## 5. Medical Safety & Boundaries

- **Emergency Symptoms:** Red-flag clinical patterns (e.g. crushing chest pain, slurred speech, massive hemoptysis) trigger `EMERGENCY_ESCALATION` with emergency dispatch numbers (`112` and `108`).
- **Sanitization:** Disallows definitive diagnostic phrasing (e.g., replaces *"You have..."* with *"Clinical guidelines indicate symptoms may be associated with..."*).
- **Localized Disclaimers:** Accompanies every response in English, Tamil, Hindi, Malayalam, Telugu, or Kannada.
