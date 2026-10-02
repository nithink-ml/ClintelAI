"use client";

import React, { useState } from "react";
import { ShieldCheck, AlertCircle, FileText, FlaskConical, Info } from "lucide-react";
import { ApiVerificationBadge } from "@/lib/api";

interface VerificationBadgeProps {
  badge: ApiVerificationBadge;
  showDetailsModal?: boolean;
}

export function VerificationBadgeComponent({ badge }: VerificationBadgeProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  const isVerified = badge.status === "VERIFIED";
  const isPartiallyVerified = badge.status === "PARTIALLY_VERIFIED";
  const isDemo = badge.is_demo_data;

  return (
    <div className="relative inline-flex flex-wrap items-center gap-1.5">
      {/* Primary Verification Status Badge */}
      <button
        type="button"
        onClick={() => setShowTooltip(!showTooltip)}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border transition-colors cursor-pointer ${
          isVerified
            ? "bg-emerald-50 text-emerald-700 border-emerald-300 hover:bg-emerald-100"
            : isPartiallyVerified
            ? "bg-amber-50 text-amber-700 border-amber-300 hover:bg-amber-100"
            : "bg-slate-100 text-slate-700 border-slate-300 hover:bg-slate-200"
        }`}
        title="Click to view verification provenance"
        aria-label="Verification details"
      >
        {isVerified ? (
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
        ) : isPartiallyVerified ? (
          <Info className="w-3.5 h-3.5 text-amber-600 shrink-0" />
        ) : (
          <AlertCircle className="w-3.5 h-3.5 text-slate-500 shrink-0" />
        )}
        <span>{badge.label}</span>
      </button>

      {/* Synthetic Demo Label Pill (Mandatory when is_demo_data is true) */}
      {isDemo && (
        <span
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-50 text-purple-700 border border-purple-200"
          title="Synthetic record generated for platform demonstration and testing"
        >
          <FlaskConical className="w-3 h-3 text-purple-600 shrink-0" />
          <span>SIMULATED DEMO</span>
        </span>
      )}

      {/* Popover Tooltip for Provenance & Audit Metadata */}
      {showTooltip && (
        <div className="absolute left-0 top-full mt-1.5 z-50 w-72 p-3 bg-white rounded-xl shadow-xl border border-slate-200 text-left text-xs text-slate-700 space-y-2 animate-in fade-in-0 zoom-in-95">
          <div className="font-bold text-slate-900 flex items-center justify-between pb-1 border-b border-slate-100">
            <span className="flex items-center gap-1">
              <FileText className="w-3.5 h-3.5 text-blue-600" />
              <span>Verification Provenance</span>
            </span>
            <span className="text-[10px] text-slate-400 font-mono">
              Tier: {badge.tier}
            </span>
          </div>

          <p className="text-[11px] text-slate-600 leading-snug">
            {badge.description}
          </p>

          {badge.source && (
            <div className="text-[11px]">
              <span className="font-semibold text-slate-900">Registry Source: </span>
              <span className="text-slate-600">{badge.source}</span>
            </div>
          )}

          {badge.method && (
            <div className="text-[11px]">
              <span className="font-semibold text-slate-900">Method: </span>
              <span className="font-mono text-slate-600">{badge.method}</span>
            </div>
          )}

          {badge.verified_at && (
            <div className="text-[10px] text-slate-400 pt-1 border-t border-slate-100">
              Verified: {new Date(badge.verified_at).toLocaleDateString()}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
