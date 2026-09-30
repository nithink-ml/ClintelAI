# ClintelAI — Your Trusted AI Healthcare Companion

A multilingual, evidence-grounded healthcare intelligence and provider discovery platform built strictly around authoritative public health sources, transparent citations, zero-hallucination abstention, and patient safety.

---

## 🏥 Project Overview

ClintelAI addresses critical barriers in health communication and medical discovery:
1. **Unreliable Information & Hallucinations:** Strictly grounds every medical claim in allowlisted sources (WHO, ICMR, MoHFW, NCDC, PubMed-indexed literature). Mandates citation validation and automatic abstention when evidence is insufficient.
2. **Provider Discovery Fragmentation:** Enables verified discovery of doctors, clinics, and hospitals with transparent verification tags and data provenance.
3. **Language Barriers:** First-class support for six languages: **English, Tamil (தமிழ்), Hindi (हिन्दी), Malayalam (മലയാളം), Telugu (తెలుగు), and Kannada (ಕನ್ನಡ)**.
4. **Health Alerts & Awareness:** Surfaces verified regional advisories, outbreak notifications, and preventive guidelines directly from public health authorities.

> **Medical Disclaimer:** ClintelAI is an informational intelligence companion and does not offer clinical diagnosis or individualized medical treatment. Always consult a qualified healthcare provider. In medical emergencies, immediately contact emergency services (112 / 108).

---

## 🏗️ Architecture & Technology Stack

| Component | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Frontend** | Next.js (App Router), TypeScript, Tailwind CSS | Next.js 14.2.35, React 18 | Accessible, multilingual UI, responsive healthcare design |
| **Backend API** | FastAPI, Python 3.11, Uvicorn, Pydantic v2 | FastAPI 0.111.1, Pydantic 2.8 | Asynchronous REST API, citation gate, RAG pipeline orchestration |
| **Relational DB** | PostgreSQL + PostGIS | 16-3.4 | Users, conversations, provider directory with geospatial queries |
| **Vector Database** | ChromaDB (or Qdrant) | Chroma 0.5.5 | Semantic vector search for chunked medical literature & guidelines |
| **Cache & Limiter** | Redis | 7-alpine | Session caching, rate limiting, request throttling |
| **Containerization**| Docker & Docker Compose | Compose v2 | Local orchestration and reproducible deployments |

---

## 📁 Repository Structure

```
ClintelAI/
├── .env.example                     # Environment template with safe placeholders
├── .gitignore                       # Git exclusions for Python, Node, environment files
├── docker-compose.yml               # Multi-service stack (PostgreSQL, Redis, Chroma, Backend, Frontend)
├── docs/
│   └── external_services.md         # Documentation on external service limitations & fallbacks
├── infrastructure/
│   └── docker/
│       ├── backend.Dockerfile       # Python 3.11 slim image for FastAPI
│       └── frontend.Dockerfile      # Multi-stage Node 20 alpine image for Next.js
├── knowledge_base/
│   └── seed_providers_demo.json     # Seed provider dataset explicitly labeled as demo records
├── backend/
│   ├── app/
│   │   ├── api/                     # REST API routers (v1 endpoints)
│   │   ├── core/                    # App settings, logging, security config
│   │   ├── db/                      # SQLAlchemy session & base models
│   │   ├── schemas/                 # Pydantic data validation models
│   │   └── main.py                  # FastAPI application entrypoint & lifespan
│   ├── pyproject.toml               # Poetry/pip tool configurations
│   ├── requirements.txt             # Pinned Python dependencies
│   └── tests/                       # Pytest test suite (health checks, validation)
└── frontend/
    ├── app/                         # Next.js App Router (layout, pages, globals.css)
    ├── lib/                         # Client utilities & helpers
    ├── package.json                 # Node dependencies & build scripts
    ├── postcss.config.mjs           # PostCSS configuration
    ├── tailwind.config.ts           # Tailwind configuration with healthcare tokens
    └── tsconfig.json                # TypeScript compiler configuration
```

---

## 🚀 Getting Started

### Prerequisites

- **Python:** 3.11+
- **Node.js:** 20+ (with npm)
- **Docker & Docker Compose:** (Optional for full stack containerized setup)

### 1. Environment Setup

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 2. Local Backend Setup (FastAPI)

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run backend tests
pytest -v

# Start FastAPI development server
uvicorn app.main:app --reload --port 8000
```
- API Health Check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- Interactive OpenAPI Docs: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)

### 3. Local Frontend Setup (Next.js)

```bash
cd frontend
npm install

# Run type check and lint
npm run type-check
npm run lint

# Start Next.js development server
npm run dev
```
- Frontend application: [http://localhost:3000](http://localhost:3000)

### 4. Running via Docker Compose

```bash
# Start all services (PostgreSQL, Redis, ChromaDB, Backend, Frontend)
docker compose up -d

# View service logs
docker compose logs -f
```

---

## 🧪 Testing & Verification

- **Backend Pytest:**
  ```bash
  cd backend && source .venv/bin/activate && pytest -v
  ```
- **Frontend Type Check & Build:**
  ```bash
  cd frontend && npm run type-check && npm run build
  ```

---

## 🔒 Source Allowlist & Verification Principles

1. **Medical Allowlist:** Only documents originating from WHO, ICMR, MoHFW, NCDC, and PubMed are ingested into the RAG vector store.
2. **Citation Gate:** Every answer must map claims to retrieved passages with clickable URLs. If unsupported, the system abstains.
3. **Provider Verification:** Provider records are explicitly tagged as `demo_simulated`, `unverified`, or `verified_official`.

---

## 📅 Roadmap & Phase Status

- [x] **Phase 0: Fresh Repository Initialization & Scaffolding** *(Completed)*
- [ ] **Phase 1: Application Foundation & Authentication** *(Awaiting Approval)*
- [ ] **Phase 2: Trusted-Source Ingestion & AI Health Assistant**
- [ ] **Phase 3: Doctor Finder & Provider Discovery**
- [ ] **Phase 4: Health Alerts & Regional Awareness**
- [ ] **Phase 5: Security Hardening & Evaluation Suite**
- [ ] **Phase 6: Production CI/CD & Deployment**
