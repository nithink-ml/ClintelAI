"use client";

import React, { useEffect, useState } from "react";
import {
  X,
  ShieldCheck,
  MapPin,
  Calendar,
  AlertTriangle,
  PhoneCall,
  CheckCircle,
  ExternalLink,
  Clock,
  Radio,
  Share2,
} from "lucide-react";
import { api, ApiHealthAlertDetail, ApiHealthAlertSummary } from "@/lib/api";
import { SeverityBadge, FreshnessBadge, CategoryBadge, DemoAlertGuardrailBadge } from "./alert-badge";
import { Button } from "@/components/ui/button";

export interface AlertDetailModalProps {
  summaryAlert: ApiHealthAlertSummary | null;
  language: string;
  onClose: () => void;
}

export function AlertDetailModal({
  summaryAlert,
  language,
  onClose,
}: AlertDetailModalProps) {
  const [detail, setDetail] = useState<ApiHealthAlertDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!summaryAlert) return;

    let isMounted = true;
    const timer = setTimeout(() => {
      setIsLoading(true);
      setError(null);

      api
        .getAlertDetail(summaryAlert.id, language)
        .then((data) => {
          if (isMounted) setDetail(data);
        })
        .catch((err) => {
          if (isMounted) setError(err.message || "Failed to load alert details");
        })
        .finally(() => {
          if (isMounted) setIsLoading(false);
        });
    }, 0);

    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [summaryAlert, language]);

  if (!summaryAlert) return null;

  const alertData = detail || summaryAlert;
  const isNational = !alertData.state || alertData.state.toUpperCase() === "ALL_INDIA";
  const locationLabel = isNational
    ? "National Scope (All India)"
    : [alertData.city, alertData.district, alertData.state].filter(Boolean).join(", ");

  const issuedDate = new Date(alertData.issued_at).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const validUntilDate = alertData.valid_until
    ? new Date(alertData.valid_until).toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "Standing Advisory (Ongoing)";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-3xl max-h-[92vh] overflow-y-auto bg-white rounded-3xl shadow-2xl border border-slate-200 flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Sticky Header */}
        <div className="sticky top-0 z-10 bg-white/95 backdrop-blur-md px-6 py-4 border-b border-slate-100 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <SeverityBadge severity={alertData.severity} />
            <CategoryBadge category={alertData.category} />
            <FreshnessBadge freshness={alertData.freshness} />
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-full text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 sm:p-8 space-y-6">
          {/* Title & Location Banner */}
          <div className="space-y-3">
            <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 leading-tight">
              {alertData.title}
            </h2>

            <div className="flex flex-wrap items-center gap-y-2 gap-x-4 text-xs text-slate-500">
              <div className="flex items-center gap-1.5 text-slate-700 font-semibold">
                <MapPin className="w-4 h-4 text-blue-600 shrink-0" />
                <span>{locationLabel}</span>
                {alertData.affected_radius_km && (
                  <span className="text-[11px] font-normal text-slate-400">
                    ({alertData.affected_radius_km} km radius)
                  </span>
                )}
              </div>

              <div className="flex items-center gap-1.5">
                <Calendar className="w-4 h-4 text-slate-400" />
                <span>Issued: <strong>{issuedDate}</strong></span>
              </div>

              <div className="flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-slate-400" />
                <span>Validity: <strong>{validUntilDate}</strong></span>
              </div>

              <div className="flex items-center gap-1">
                <Radio className="w-3.5 h-3.5 text-emerald-500 animate-pulse" />
                <span className="font-semibold text-slate-700">Status: {alertData.status}</span>
              </div>
            </div>
          </div>

          {/* Demo Data Guardrail Banner */}
          {alertData.is_demo_data && (
            <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-300/80 text-amber-900 flex items-start gap-2.5 text-xs">
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <strong className="font-bold text-amber-950">DEMO SIMULATED DATASET:</strong>
                <p className="mt-0.5 leading-relaxed text-amber-900/90">
                  Simulated demonstration record for architectural and geographic validation. Do not use for actual clinical appointments or emergency care.
                </p>
              </div>
            </div>
          )}

          {/* Detailed Content Narrative */}
          <div className="space-y-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Epidemiological Bulletin & Overview
            </h3>
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 text-xs sm:text-sm text-slate-800 leading-relaxed whitespace-pre-line">
              {detail ? detail.content : alertData.summary}
            </div>
          </div>

          {/* Reported Symptoms (if available) */}
          {detail && detail.symptoms && detail.symptoms.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Reported Clinical Symptoms
              </h3>
              <div className="flex flex-wrap gap-2">
                {detail.symptoms.map((sym, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-red-50 text-red-800 border border-red-200"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
                    <span>{sym}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Precautionary Measures & Clinical Action Directives */}
          {detail && detail.precautionary_measures && detail.precautionary_measures.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Clinical Guidance & Precautionary Measures
              </h3>
              <div className="grid gap-2.5">
                {detail.precautionary_measures.map((measure, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-xl bg-blue-50/50 border border-blue-100 flex items-start gap-3 text-xs sm:text-sm text-blue-950"
                  >
                    <CheckCircle className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                    <span className="leading-relaxed">{measure}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Helplines Dial Action Bar */}
          {detail && detail.helpline_numbers && detail.helpline_numbers.length > 0 && (
            <div className="p-4 rounded-2xl bg-gradient-to-r from-red-500 to-rose-600 text-white space-y-3 shadow-md shadow-red-500/10">
              <div className="flex items-center gap-2">
                <PhoneCall className="w-4 h-4" />
                <span className="text-xs font-bold uppercase tracking-wider">
                  Designated Emergency & Advisory Helplines
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {detail.helpline_numbers.map((num, idx) => (
                  <a
                    key={idx}
                    href={`tel:${num}`}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white text-red-600 hover:bg-red-50 text-xs font-bold shadow-xs transition-colors"
                  >
                    <PhoneCall className="w-3.5 h-3.5 text-red-500" />
                    <span>Dial {num}</span>
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Source Provenance Authority Card */}
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-900 font-bold">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>Accredited Public Health Authority Source</span>
              </div>
              <a
                href={alertData.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 font-semibold text-blue-600 hover:underline"
              >
                <span>Verify Source Bulletin</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>

            <div className="text-slate-600 space-y-1">
              <div>
                <strong>Issuing Body:</strong> {alertData.source_name}
              </div>
              <div>
                <strong>Source URL:</strong>{" "}
                <span className="font-mono text-[11px] text-slate-500 break-all">
                  {alertData.source_url}
                </span>
              </div>
              {alertData.source_reference_id && (
                <div>
                  <strong>Official Reference:</strong> {alertData.source_reference_id}
                </div>
              )}
            </div>
          </div>

          {/* Legal / Clinical Disclaimer */}
          <div className="p-3.5 rounded-xl bg-slate-100 border border-slate-200 text-[11px] text-slate-500 leading-relaxed">
            <strong>Notice:</strong> Regional health alerts provide official public health advisories from accredited government and global health agencies. They do not constitute individualized clinical diagnosis or personalized medical advice. If you are experiencing acute medical symptoms, consult a qualified physician or call national emergency services (112 / 108).
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 px-6 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-3">
          <Button variant="outline" size="sm" onClick={onClose}>
            Close Advisory
          </Button>
        </div>
      </div>
    </div>
  );
}
