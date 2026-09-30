import React from "react";
import {
  ShieldCheck,
  Search,
  Activity,
  Globe2,
  FileCheck2,
  AlertTriangle,
  Stethoscope,
  Database,
  Server,
  Layers,
  Sparkles,
  ExternalLink,
} from "lucide-react";

const SUPPORTED_LANGUAGES = [
  { code: "en", name: "English", native: "English" },
  { code: "ta", name: "Tamil", native: "தமிழ்" },
  { code: "hi", name: "Hindi", native: "हिन्दी" },
  { code: "ml", name: "Malayalam", native: "മലയാളം" },
  { code: "te", name: "Telugu", native: "తెలుగు" },
  { code: "kn", name: "Kannada", native: "ಕನ್ನಡ" },
];

const TRUSTED_SOURCES = [
  { name: "World Health Organization (WHO)", tag: "Global Guideline" },
  { name: "Indian Council of Medical Research (ICMR)", tag: "Clinical Research" },
  { name: "Ministry of Health & Family Welfare (MoHFW)", tag: "Govt of India" },
  { name: "National Centre for Disease Control (NCDC)", tag: "Surveillance" },
  { name: "PubMed Central Scientific Literature", tag: "Peer-reviewed" },
];

export default function HomePage() {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Header / Navbar */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <span className="font-bold text-xl tracking-tight text-slate-900">
                Clintel<span className="text-blue-600">AI</span>
              </span>
              <span className="hidden sm:inline-block ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                Phase 0 Scaffold
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <div className="hidden md:flex items-center space-x-1.5 text-xs text-slate-600 bg-slate-100 rounded-lg p-1 border border-slate-200">
              <Globe2 className="w-3.5 h-3.5 ml-1.5 text-slate-500" />
              {SUPPORTED_LANGUAGES.map((lang, idx) => (
                <span
                  key={lang.code}
                  className={`px-2 py-0.5 rounded ${
                    idx === 0
                      ? "bg-white font-medium text-blue-600 shadow-sm"
                      : "text-slate-600 hover:text-slate-900 cursor-pointer"
                  }`}
                >
                  {lang.native}
                </span>
              ))}
            </div>

            <div className="flex items-center space-x-2 text-xs font-medium px-3 py-1.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>Services Initialized</span>
            </div>
          </div>
        </div>
      </header>

      {/* Safety Notice Banner */}
      <div className="bg-amber-50 border-b border-amber-200/80 px-4 py-2.5 text-xs text-amber-900 text-center font-medium">
        <div className="max-w-7xl mx-auto flex items-center justify-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
          <span>
            <strong>Informational Health Intelligence:</strong> ClintelAI provides evidence-grounded medical information and provider discovery. It is not a substitute for clinical diagnosis or treatment. In medical emergencies, immediately contact emergency services (112 / 108).
          </span>
        </div>
      </div>

      {/* Hero Section */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-16">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-100/70 text-blue-800 text-xs font-semibold uppercase tracking-wider mb-6">
            <Sparkles className="w-3.5 h-3.5 text-blue-600" />
            <span>Strict Evidence Grounding & Abstention</span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold text-slate-900 tracking-tight leading-tight">
            Your Trusted AI <br className="hidden sm:block" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-cyan-600">
              Healthcare Companion
            </span>
          </h1>
          <p className="mt-4 text-lg text-slate-600 leading-relaxed">
            Accessible, multilingual health guidance backed exclusively by authoritative public health sources, with transparent claim citations, provider discovery, and zero-hallucination abstention.
          </p>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <span className="inline-flex items-center px-4 py-2 rounded-lg bg-blue-600 text-white font-medium text-sm shadow-sm">
              <Stethoscope className="w-4 h-4 mr-2" />
              Phase 0 Foundation Active
            </span>
            <a
              href="http://localhost:8000/api/v1/docs"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center px-4 py-2 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 font-medium text-sm transition-colors shadow-sm"
            >
              <Server className="w-4 h-4 mr-2 text-slate-500" />
              Backend OpenAPI Docs
              <ExternalLink className="w-3.5 h-3.5 ml-1 text-slate-400" />
            </a>
          </div>
        </div>

        {/* 4 Core Pillars */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
          <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center mb-4">
              <FileCheck2 className="w-6 h-6" />
            </div>
            <h2 className="text-lg font-bold text-slate-900 mb-2">Evidence-Grounded AI</h2>
            <p className="text-sm text-slate-600 leading-relaxed mb-4">
              Every factual claim is validated against retrieved passages from allowlisted sources. If reliable evidence is absent, the system explicitly abstains.
            </p>
            <div className="text-xs font-semibold text-blue-600 flex items-center">
              <span>Citation Gate & Abstention</span>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-xl bg-cyan-50 text-cyan-600 flex items-center justify-center mb-4">
              <Search className="w-6 h-6" />
            </div>
            <h2 className="text-lg font-bold text-slate-900 mb-2">Doctor & Clinic Finder</h2>
            <p className="text-sm text-slate-600 leading-relaxed mb-4">
              Transparent provider discovery with explicit verification status labels, specialties, and distance indicators.
            </p>
            <div className="text-xs font-semibold text-cyan-600 flex items-center">
              <span>Discovery ≠ Clinical Endorsement</span>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-4">
              <Globe2 className="w-6 h-6" />
            </div>
            <h2 className="text-lg font-bold text-slate-900 mb-2">6 Indian Languages</h2>
            <p className="text-sm text-slate-600 leading-relaxed mb-4">
              Native script support for English, Tamil, Hindi, Malayalam, Telugu, and Kannada with cultural and localized clarity.
            </p>
            <div className="text-xs font-semibold text-indigo-600 flex items-center">
              <span>Multilingual Ingestion & RAG</span>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center mb-4">
              <Activity className="w-6 h-6" />
            </div>
            <h2 className="text-lg font-bold text-slate-900 mb-2">Verified Health Alerts</h2>
            <p className="text-sm text-slate-600 leading-relaxed mb-4">
              Official public health advisories, outbreak alerts, and seasonal prevention updates from MoHFW and state authorities.
            </p>
            <div className="text-xs font-semibold text-rose-600 flex items-center">
              <span>Public Health Surveillance</span>
            </div>
          </div>
        </div>

        {/* Phase 0 Architecture Status Dashboard */}
        <div className="bg-slate-900 text-white rounded-2xl p-6 sm:p-8 shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
            <div>
              <div className="flex items-center space-x-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <h2 className="text-lg font-bold text-white">System Architecture & Service Registry</h2>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Baseline infrastructure and components verified in Phase 0.
              </p>
            </div>
            <div className="text-xs font-mono bg-slate-800 px-3 py-1.5 rounded-lg text-slate-300 border border-slate-700 self-start sm:self-auto">
              Ready for Phase 1 Approval
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
            <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Backend API</span>
                <Server className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-base font-bold text-white">FastAPI 0.111.1</div>
              <p className="text-xs text-slate-400 mt-1">Health check & lifespan active</p>
            </div>

            <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Database</span>
                <Database className="w-4 h-4 text-blue-400" />
              </div>
              <div className="text-base font-bold text-white">PostgreSQL 16 + AsyncPG</div>
              <p className="text-xs text-slate-400 mt-1">SQLAlchemy 2.0 Async Session</p>
            </div>

            <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Vector Store</span>
                <Layers className="w-4 h-4 text-purple-400" />
              </div>
              <div className="text-base font-bold text-white">ChromaDB / Qdrant</div>
              <p className="text-xs text-slate-400 mt-1">Configured with mock fallback</p>
            </div>

            <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Frontend UI</span>
                <Globe2 className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="text-base font-bold text-white">Next.js 14.2 App Router</div>
              <p className="text-xs text-slate-400 mt-1">Tailwind CSS + TypeScript</p>
            </div>
          </div>

          {/* Trusted Sources Table */}
          <div className="mt-8 pt-6 border-t border-slate-800">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
              Approved Initial Source Allowlist
            </h3>
            <div className="flex flex-wrap gap-2">
              {TRUSTED_SOURCES.map((source) => (
                <div
                  key={source.name}
                  className="bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-1.5 text-xs text-slate-300 flex items-center space-x-2"
                >
                  <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
                  <span>{source.name}</span>
                  <span className="text-[10px] text-slate-400 bg-slate-900 px-1.5 py-0.5 rounded">
                    {source.tag}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-xs text-slate-500">
          <p className="font-medium text-slate-700 mb-1">
            ClintelAI — Standalone Multilingual Healthcare Intelligence Platform
          </p>
          <p>
            Developed following production-grade healthcare AI safety, evidence-grounded RAG, and strict phase control standards.
          </p>
        </div>
      </footer>
    </div>
  );
}
