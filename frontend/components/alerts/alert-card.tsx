"use client";

import React from "react";
import {
  MapPin,
  Calendar,
  Building,
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  Radio,
} from "lucide-react";
import { ApiHealthAlertSummary } from "@/lib/api";
import { SeverityBadge, FreshnessBadge, CategoryBadge, DemoAlertGuardrailBadge } from "./alert-badge";
import { Button } from "@/components/ui/button";

export interface AlertCardProps {
  alert: ApiHealthAlertSummary;
  onSelect: (alert: ApiHealthAlertSummary) => void;
}

export function AlertCard({ alert, onSelect }: AlertCardProps) {
  const isNational = !alert.state || alert.state.toUpperCase() === "ALL_INDIA";
  const locationLabel = isNational
    ? "National Scope (All India)"
    : [alert.city, alert.district, alert.state].filter(Boolean).join(", ");

  const issuedDate = new Date(alert.issued_at).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });

  const validUntilDate = alert.valid_until
    ? new Date(alert.valid_until).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : "Standing Advisory";

  return (
    <div
      onClick={() => onSelect(alert)}
      className="group relative rounded-2xl bg-white border border-slate-200/90 hover:border-blue-400 p-5 shadow-xs hover:shadow-md transition-all duration-200 flex flex-col justify-between cursor-pointer space-y-4"
    >
      {/* Top Header: Severity, Category, Freshness */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <SeverityBadge severity={alert.severity} />
          <CategoryBadge category={alert.category} />
        </div>
        <FreshnessBadge freshness={alert.freshness} />
      </div>

      {/* Main Content: Title & Summary */}
      <div className="space-y-2">
        <h3 className="text-base sm:text-lg font-bold text-slate-900 group-hover:text-blue-600 transition-colors leading-snug">
          {alert.title}
        </h3>
        <p className="text-xs sm:text-sm text-slate-600 line-clamp-3 leading-relaxed">
          {alert.summary}
        </p>
      </div>

      {/* Metadata Chips: Location, Source Authority, Dates */}
      <div className="pt-2 border-t border-slate-100 flex flex-col gap-2 text-xs text-slate-500">
        <div className="flex flex-wrap items-center justify-between gap-2">
          {/* Location & Radius */}
          <div className="flex items-center gap-1.5 text-slate-700 font-medium">
            <MapPin className="w-3.5 h-3.5 text-blue-600 shrink-0" />
            <span>{locationLabel}</span>
            {alert.affected_radius_km && (
              <span className="text-[10px] text-slate-400">
                ({alert.affected_radius_km} km radius)
              </span>
            )}
            {alert.distance_km !== null && alert.distance_km !== undefined && (
              <span className="ml-1 px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-700 text-[10px] font-bold">
                {alert.distance_km} km away
              </span>
            )}
          </div>

          {/* Validity Period */}
          <div className="flex items-center gap-1 text-[11px] text-slate-400">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <span>{issuedDate} — {validUntilDate}</span>
          </div>
        </div>

        {/* Source Authority Provenance */}
        <div className="flex items-center justify-between gap-2 pt-1">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-600">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
            <span className="truncate max-w-[240px] sm:max-w-xs font-medium">
              {alert.source_name}
            </span>
          </div>

          <a
            href={alert.source_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-600 hover:text-blue-800 hover:underline"
          >
            <span>Official Bulletin</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>

      {/* Demo Data Guardrail */}
      {alert.is_demo_data && <DemoAlertGuardrailBadge />}

      {/* Bottom Action Footer */}
      <div className="pt-1 flex items-center justify-between text-xs">
        <span className="text-[11px] text-slate-400 flex items-center gap-1">
          <Radio className="w-3 h-3 text-emerald-500 animate-pulse" />
          <span>Status: <strong className="text-slate-700">{alert.status}</strong></span>
        </span>

        <Button
          size="sm"
          variant="outline"
          className="text-xs group-hover:bg-blue-50 group-hover:text-blue-700 group-hover:border-blue-200"
        >
          <span>View Advisory</span>
          <ChevronRight className="w-3.5 h-3.5 ml-1 text-slate-400 group-hover:text-blue-600 transition-transform group-hover:translate-x-0.5" />
        </Button>
      </div>
    </div>
  );
}
