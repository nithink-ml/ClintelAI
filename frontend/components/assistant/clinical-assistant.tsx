"use client";

import React, { useState } from "react";
import {
  ShieldCheck,
  Search,
  AlertTriangle,
  FileText,
  ExternalLink,
  Sparkles,
  PhoneCall,
  Info,
  CheckCircle2,
  Clock,
  Layers,
  ChevronRight,
  Database,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useLanguage } from "@/lib/i18n/language-context";

interface Citation {
  citation_index: number;
  chunk_id: string;
  document_id: string;
  source_name: string;
  authority_tier: string;
  title: string;
  section_title: string;
  url: string;
  published_date: string;
  snippet: string;
  relevance_score: number;
}

interface EmergencyEscalation {
  is_emergency: boolean;
  level: string;
  symptoms_detected: string[];
  action_message: string;
  emergency_numbers: string[];
}

interface RAGResponse {
  query: string;
  language: string;
  answer: string;
  citations: Citation[];
  confidence_score: number;
  abstained: boolean;
  abstention_reason: string | null;
  medical_safety_level: string;
  safety_disclaimer: string;
  emergency: EmergencyEscalation;
  retrieval_metadata: {
    chunks_evaluated: number;
    chunks_retained: number;
    top_similarity_score: number;
    retrieval_strategy: string;
    latency_ms: number;
  };
}

interface SourceSummary {
  document_id: string;
  title: string;
  source_name: string;
  authority_tier: string;
  domain: string;
  chunks_count: number;
  published_date: string;
  url: string;
}

export function ClinicalAssistant() {
  const { language } = useLanguage();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<RAGResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sources, setSources] = useState<SourceSummary[] | null>(null);
  const [showSources, setShowSources] = useState(false);

  const sampleQueries = [
    { label: "Dengue Fluid & Platelet Guidelines", q: "What are the fluid management and platelet transfusion guidelines for dengue?" },
    { label: "Hypertension First-Line Drugs", q: "What are the first-line drug classes and diagnostic thresholds for hypertension according to WHO?" },
    { label: "South Asian Diabetes Care", q: "What is the recommended diagnostic criteria and first-line treatment for Type 2 diabetes in South Asian phenotypes?" },
    { label: "Emergency Red-Flag Test", q: "Patient experiencing severe crushing chest pain radiating to the left arm and jaw" },
    { label: "Zero-Hallucination Abstention", q: "What is the best cryptocurrency investment strategy for 2026?" },
  ];

  const handleSearch = async (overrideQuery?: string) => {
    const q = overrideQuery || query;
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("http://localhost:8000/api/v1/rag/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: q,
          language: language,
          max_evidence_chunks: 4,
        }),
      });
      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }
      const data: RAGResponse = await res.json();
      setResponse(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to retrieve clinical evidence";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const fetchSources = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/rag/sources");
      if (res.ok) {
        const data = await res.json();
        setSources(data.sources);
        setShowSources(true);
      }
    } catch (e) {
      console.warn("Could not fetch sources:", e);
    }
  };

  return (
    <Card className="border-blue-200/80 shadow-md shadow-blue-500/5 overflow-hidden">
      <CardHeader className="bg-gradient-to-r from-blue-50/80 via-white to-indigo-50/80 border-b border-blue-100/70 pb-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold text-xs shadow-xs">
                RAG
              </div>
              <CardTitle className="text-xl font-bold text-slate-900">
                Evidence-Grounded Clinical Retrieval Assistant
              </CardTitle>
            </div>
            <CardDescription className="mt-1 text-slate-600 text-xs sm:text-sm">
              Queries validated against authoritative guidelines (WHO, ICMR, MoHFW, PubMed) with verifiable citations and strict zero-hallucination abstention.
            </CardDescription>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={fetchSources}
            className="text-xs border-blue-200 hover:bg-blue-50 self-start sm:self-auto"
          >
            <Database className="w-3.5 h-3.5 mr-1 text-blue-600" />
            <span>Authoritative Sources ({sources?.length || 11})</span>
          </Button>
        </div>
      </CardHeader>

      <CardContent className="p-5 sm:p-6 space-y-6">
        {/* Search Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch();
          }}
          className="flex flex-col sm:flex-row gap-2"
        >
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a clinical question (e.g. dengue fluid management, hypertension targets)..."
              className="pl-9 pr-4 py-2 border-slate-300 focus:border-blue-500 text-sm h-11"
            />
          </div>
          <Button type="submit" disabled={loading || !query.trim()} className="h-11 px-5 shadow-xs">
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Retrieving...</span>
              </span>
            ) : (
              <span className="flex items-center gap-1.5">
                <Sparkles className="w-4 h-4" />
                <span>Verify & Retrieve</span>
              </span>
            )}
          </Button>
        </form>

        {/* Quick Sample Queries */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mr-1">
            Quick Tests:
          </span>
          {sampleQueries.map((item, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => {
                setQuery(item.q);
                handleSearch(item.q);
              }}
              className="text-xs px-2.5 py-1 rounded-full bg-slate-100 hover:bg-blue-50 hover:text-blue-700 text-slate-700 transition-colors border border-slate-200/80"
            >
              {item.label}
            </button>
          ))}
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm flex items-center gap-2">
            <XCircle className="w-5 h-5 shrink-0 text-red-500" />
            <span>{error}</span>
          </div>
        )}

        {/* Sources Drawer / Modal View */}
        {showSources && sources && (
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
            <div className="flex items-center justify-between">
              <div className="font-bold text-sm text-slate-900 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>Indexed Authoritative Clinical Guidelines ({sources.length} Documents)</span>
              </div>
              <button
                onClick={() => setShowSources(false)}
                className="text-xs font-semibold text-slate-500 hover:text-slate-900"
              >
                Close
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-60 overflow-y-auto pr-1">
              {sources.map((s) => (
                <div key={s.document_id} className="p-2.5 rounded-lg bg-white border border-slate-200 text-xs space-y-1">
                  <div className="font-semibold text-slate-900 line-clamp-1">{s.title}</div>
                  <div className="flex items-center justify-between text-[11px] text-slate-500">
                    <span className="font-medium text-blue-600">{s.source_name}</span>
                    <span>{s.chunks_count} chunks</span>
                  </div>
                  <a
                    href={s.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-[10px] text-slate-400 hover:text-blue-600"
                  >
                    <span>{s.authority_tier}</span>
                    <ExternalLink className="w-2.5 h-2.5" />
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Query Results Presentation */}
        {response && (
          <div className="space-y-4 pt-2 border-t border-slate-100">
            {/* Metadata Status Chips */}
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-blue-100 text-blue-800 font-semibold text-[11px]">
                  <Layers className="w-3 h-3" />
                  {response.retrieval_metadata.chunks_retained} Verified Chunks Retained
                </span>
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 font-medium text-[11px]">
                  <Clock className="w-3 h-3" />
                  {response.retrieval_metadata.latency_ms} ms
                </span>
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold text-[11px]">
                  Confidence: {Math.round(response.confidence_score * 100)}%
                </span>
              </div>
              <span className="text-[11px] text-slate-400">
                Mode: {response.retrieval_metadata.retrieval_strategy}
              </span>
            </div>

            {/* Emergency Escalation Banner */}
            {response.emergency.is_emergency && (
              <div className="p-4 rounded-xl bg-red-500/10 border-2 border-red-500/80 space-y-2">
                <div className="flex items-center gap-2 text-red-700 font-bold text-sm sm:text-base">
                  <AlertTriangle className="w-5 h-5 shrink-0 text-red-600 animate-pulse" />
                  <span>EMERGENCY PROTOCOL TRIGGERED: Level {response.emergency.level}</span>
                </div>
                <p className="text-xs sm:text-sm text-red-900 leading-relaxed font-medium">
                  {response.emergency.action_message}
                </p>
                <div className="flex items-center gap-3 pt-1">
                  <span className="text-xs font-semibold text-red-800">Dial Immediately:</span>
                  {response.emergency.emergency_numbers.map((num) => (
                    <a
                      key={num}
                      href={`tel:${num}`}
                      className="inline-flex items-center gap-1 px-3 py-1 rounded-lg bg-red-600 text-white font-bold text-xs shadow-xs hover:bg-red-700"
                    >
                      <PhoneCall className="w-3 h-3" />
                      <span>{num}</span>
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Abstention Card */}
            {response.abstained && !response.emergency.is_emergency && (
              <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 space-y-2">
                <div className="flex items-center gap-2 text-amber-800 font-bold text-sm">
                  <ShieldCheck className="w-5 h-5 text-amber-600" />
                  <span>Strict Zero-Hallucination Abstention Triggered</span>
                </div>
                <p className="text-xs sm:text-sm text-amber-900 leading-relaxed">
                  {response.answer}
                </p>
                <div className="text-[11px] text-amber-700 font-medium pt-1">
                  Reason Code: <span className="font-mono bg-amber-100 px-1.5 py-0.5 rounded">{response.abstention_reason}</span>
                </div>
              </div>
            )}

            {/* Grounded Clinical Answer */}
            {!response.abstained && (
              <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-4">
                <div className="prose prose-sm max-w-none text-slate-800 space-y-2 whitespace-pre-line text-sm sm:text-base">
                  {response.answer}
                </div>

                {/* Structured Citations List */}
                {response.citations.length > 0 && (
                  <div className="pt-4 border-t border-slate-100 space-y-2.5">
                    <div className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5 text-blue-600" />
                      <span>Authoritative Source Citations ({response.citations.length})</span>
                    </div>
                    <div className="grid grid-cols-1 gap-2">
                      {response.citations.map((c) => (
                        <div
                          key={c.chunk_id}
                          className="p-3 rounded-lg bg-slate-50 border border-slate-200/80 hover:border-blue-300 transition-colors text-xs space-y-1.5"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-blue-700 flex items-center gap-1.5">
                              <span className="w-4 h-4 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px]">
                                {c.citation_index}
                              </span>
                              <span>{c.source_name}</span>
                            </span>
                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-semibold">
                              Relevance: {Math.round(c.relevance_score * 100)}%
                            </span>
                          </div>
                          <div className="font-semibold text-slate-900">{c.title} &gt; {c.section_title}</div>
                          <p className="text-slate-600 italic text-[11px] leading-relaxed">
                            &quot;{c.snippet}&quot;
                          </p>
                          <div className="flex items-center justify-between pt-1 border-t border-slate-200/50 text-[10px] text-slate-500">
                            <span>Published: {c.published_date} ({c.authority_tier})</span>
                            <a
                              href={c.url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-blue-600 hover:underline flex items-center gap-0.5 font-medium"
                            >
                              <span>Official Document</span>
                              <ExternalLink className="w-2.5 h-2.5" />
                            </a>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Localized Medical Disclaimer */}
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/70 text-[11px] text-slate-500 leading-relaxed flex items-start gap-2">
              <Info className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
              <span>{response.safety_disclaimer}</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
