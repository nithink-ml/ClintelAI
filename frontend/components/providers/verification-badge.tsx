"use client";

import React, { useState } from "react";
import { ShieldCheck, AlertCircle, FileText, FlaskConical, Info, AlertTriangle } from "lucide-react";
import { ApiVerificationBadge } from "@/lib/api";

interface VerificationBadgeProps {
  badge: ApiVerificationBadge;
  showDetailsModal?: boolean;
}

export function VerificationBadgeComponent({ badge }: VerificationBadgeProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  // STRICT DEMO DATA VERIFICATION GUARDRAIL:
  // If provider.is_demo_data == true, the UI must NEVER display VERIFIED,
  // PARTIALLY_VERIFIED, or UNVERIFIED as the provider's effective verification badge.
  // DEMO_SIMULATED must be the effective display status for every synthetic provider.
  const isDemo = Boolean(
    badge.is_demo_data ||
      badge.effective_status === "DEMO_SIMULATED" ||
      badge.status === "DEMO_SIMULATED"
  );

  // If isDemo, effective badge status and label MUST be DEMO_SIMULATED
  const effectiveStatus = isDemo ? "DEMO_SIMULATED" : (badge.effective_status || badge.status);
  const effectiveLabel = isDemo ? "DEMO_SIMULATED" : badge.label;

  const isVerified = !isDemo && effectiveStatus === "VERIFIED";
  const isPartiallyVerified = !isDemo && effectiveStatus === "PARTIALLY_VERIFIED";

  return (
    <div className="relative inline-flex flex-wrap items-center gap-1.5" data-testid="verification-badge-container">
      {/* Primary Verification Status Badge */}
      <button
        type="button"
        data-testid="verification-badge-button"
        onClick={() => setShowTooltip(!showTooltip)}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border transition-colors cursor-pointer ${
          isDemo
            ? "bg-purple-50 text-purple-700 border-purple-300 hover:bg-purple-100"
            : isVerified
            ? "bg-emerald-50 text-emerald-700 border-emerald-300 hover:bg-emerald-100"
            : isPartiallyVerified
            ? "bg-amber-50 text-amber-700 border-amber-300 hover:bg-amber-100"
            : "bg-slate-100 text-slate-700 border-slate-300 hover:bg-slate-200"
        }`}
        title={
          isDemo
            ? "Simulated demonstration record. Do not use for actual clinical appointments or emergency care."
            : "Click to view verification provenance"
        }
        aria-label="Verification details"
      >
        {isDemo ? (
          <FlaskConical className="w-3.5 h-3.5 text-purple-600 shrink-0" />
        ) : isVerified ? (
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
        ) : isPartiallyVerified ? (
          <Info className="w-3.5 h-3.5 text-amber-600 shrink-0" />
        ) : (
          <AlertCircle className="w-3.5 h-3.5 text-slate-500 shrink-0" />
        )}
        <span data-testid="verification-status-label">{effectiveLabel}</span>
      </button>

      {/* Synthetic Demo Label Pill (Mandatory when is_demo_data is true) */}
      {isDemo && (
        <span
          data-testid="demo-synthetic-pill"
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200"
          title="Simulated demonstration record. Do not use for actual clinical appointments or emergency care."
        >
          <AlertTriangle className="w-3 h-3 text-amber-600 shrink-0" />
          <span>SYNTHETIC</span>
        </span>
      )}

      {/* Popover Tooltip for Provenance & Audit Metadata */}
      {showTooltip && (
        <div
          data-testid="verification-tooltip"
          className="absolute left-0 top-full mt-1.5 z-50 w-72 p-3 bg-white rounded-xl shadow-xl border border-slate-200 text-left text-xs text-slate-700 space-y-2 animate-in fade-in-0 zoom-in-95"
        >
          <div className="font-bold text-slate-900 flex items-center justify-between pb-1 border-b border-slate-100">
            <span className="flex items-center gap-1">
              <FileText className="w-3.5 h-3.5 text-blue-600" />
              <span>Verification Provenance</span>
            </span>
            <span className="text-[10px] text-slate-400 font-mono">
              Tier: {isDemo ? "tier_4_demo" : badge.tier}
            </span>
          </div>

          {isDemo ? (
            <div className="bg-amber-50 border border-amber-200 rounded p-1.5 text-[11px] text-amber-900 font-medium leading-snug">
              Simulated demonstration record. Do not use for actual clinical appointments or emergency care.
            </div>
          ) : (
            <p className="text-[11px] text-slate-600 leading-snug">
              {badge.description}
            </p>
          )}

          {badge.simulated_target_status && isDemo && (
            <div className="text-[10px] text-slate-500 border-t border-slate-100 pt-1">
              <span className="font-semibold text-slate-700">Simulated Target: </span>
              <span className="font-mono text-purple-700">{badge.simulated_target_status} ({badge.simulated_target_tier || badge.tier})</span>
            </div>
          )}

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
