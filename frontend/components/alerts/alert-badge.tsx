"use client";

import React from "react";
import {
  AlertTriangle,
  Clock,
  Sparkles,
  Archive,
  ShieldAlert,
  Flame,
  Wind,
  Droplets,
  Activity,
  Syringe,
  Info,
} from "lucide-react";
import { ApiFreshnessStatus } from "@/lib/api";
import { cn } from "@/lib/utils";

export interface SeverityBadgeProps {
  severity: "CRITICAL" | "HIGH" | "MODERATE" | "LOW" | "INFORMATIONAL" | string;
  className?: string;
}

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  const sev = severity.toUpperCase();

  switch (sev) {
    case "CRITICAL":
      return (
        <span
          className={cn(
            "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold tracking-tight bg-red-100 text-red-800 border border-red-300 animate-pulse",
            className
          )}
        >
          <span className="w-2 h-2 rounded-full bg-red-600 shrink-0" />
          <span>CRITICAL HAZARD</span>
        </span>
      );
    case "HIGH":
      return (
        <span
          className={cn(
            "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold tracking-tight bg-amber-100 text-amber-800 border border-amber-300",
            className
          )}
        >
          <span className="w-2 h-2 rounded-full bg-amber-600 shrink-0" />
          <span>HIGH ALERT</span>
        </span>
      );
    case "MODERATE":
      return (
        <span
          className={cn(
            "inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-yellow-50 text-yellow-800 border border-yellow-200",
            className
          )}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-yellow-500 shrink-0" />
          <span>MODERATE ADVISORY</span>
        </span>
      );
    case "LOW":
      return (
        <span
          className={cn(
            "inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200",
            className
          )}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0" />
          <span>PREVENTIVE NOTICE</span>
        </span>
      );
    default:
      return (
        <span
          className={cn(
            "inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200",
            className
          )}
        >
          <Info className="w-3 h-3 text-slate-500" />
          <span>INFORMATIONAL</span>
        </span>
      );
  }
}

export interface FreshnessBadgeProps {
  freshness: ApiFreshnessStatus;
  className?: string;
}

export function FreshnessBadge({ freshness, className }: FreshnessBadgeProps) {
  const status = freshness?.status?.toUpperCase() || "RECENT";

  switch (status) {
    case "FRESH":
      return (
        <span
          title={freshness.notice}
          className={cn(
            "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 shadow-2xs",
            className
          )}
        >
          <Sparkles className="w-3 h-3 text-emerald-600" />
          <span>Fresh Bulletin (&lt;24h)</span>
        </span>
      );
    case "RECENT":
      return (
        <span
          title={freshness.notice}
          className={cn(
            "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-cyan-50 text-cyan-700 border border-cyan-200",
            className
          )}
        >
          <Clock className="w-3 h-3 text-cyan-600" />
          <span>Recent Advisory (&lt;7d)</span>
        </span>
      );
    case "STALE":
      return (
        <span
          title={freshness.notice}
          className={cn(
            "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200",
            className
          )}
        >
          <AlertTriangle className="w-3 h-3 text-amber-600" />
          <span>Stale Bulletin (&gt;7d)</span>
        </span>
      );
    case "EXPIRED":
      return (
        <span
          title={freshness.notice}
          className={cn(
            "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-300",
            className
          )}
        >
          <Archive className="w-3 h-3 text-slate-500" />
          <span>Archived / Expired</span>
        </span>
      );
    default:
      return null;
  }
}

export interface CategoryBadgeProps {
  category: string;
  className?: string;
}

export function CategoryBadge({ category, className }: CategoryBadgeProps) {
  const cat = category.toLowerCase();

  let icon = <Activity className="w-3 h-3" />;
  let label = "Health Advisory";

  if (cat.includes("infectious") || cat.includes("outbreak")) {
    icon = <ShieldAlert className="w-3 h-3 text-rose-600" />;
    label = cat.includes("outbreak") ? "Outbreak Notice" : "Infectious Disease";
  } else if (cat.includes("air")) {
    icon = <Wind className="w-3 h-3 text-slate-600" />;
    label = "Air Quality Warning";
  } else if (cat.includes("heat")) {
    icon = <Flame className="w-3 h-3 text-orange-600" />;
    label = "Heatwave Directive";
  } else if (cat.includes("water") || cat.includes("food")) {
    icon = <Droplets className="w-3 h-3 text-cyan-600" />;
    label = "Water & Food Safety";
  } else if (cat.includes("vaccin")) {
    icon = <Syringe className="w-3 h-3 text-indigo-600" />;
    label = "Immunization Drive";
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200/80",
        className
      )}
    >
      {icon}
      <span>{label}</span>
    </span>
  );
}

export function DemoAlertGuardrailBadge({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-300/80 text-amber-900 flex items-center gap-1.5 text-[11px] font-medium",
        className
      )}
    >
      <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
      <span>
        <strong className="font-bold text-amber-950">DEMO RECORD:</strong> Simulated demonstration dataset. Verify with official state health directorates for actual clinical care.
      </span>
    </div>
  );
}
