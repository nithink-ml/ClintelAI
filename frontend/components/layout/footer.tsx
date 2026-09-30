"use client";

import React from "react";
import { AlertTriangle, ShieldCheck, Heart } from "lucide-react";
import { useLanguage } from "@/lib/i18n/language-context";

export function Footer() {
  const { t } = useLanguage();

  return (
    <footer className="bg-white border-t border-slate-200 mt-auto">
      {/* Medical Safety Disclaimer Strip */}
      <div className="bg-amber-50/70 border-b border-amber-200/60 px-4 py-3 text-xs text-amber-900">
        <div className="max-w-7xl mx-auto flex items-start sm:items-center gap-2.5">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5 sm:mt-0" />
          <p className="leading-relaxed font-medium">
            <strong>Mandatory Medical Notice:</strong> {t.disclaimerBanner}
          </p>
        </div>
      </div>

      {/* Main Footer Links & Citations */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8 text-xs">
          <div className="md:col-span-2 space-y-3">
            <div className="flex items-center gap-2 font-bold text-slate-900 text-sm">
              <ShieldCheck className="w-4 h-4 text-blue-600" />
              <span>ClintelAI Healthcare Platform</span>
            </div>
            <p className="text-slate-500 leading-relaxed max-w-md">
              A multilingual, evidence-grounded healthcare intelligence platform built strictly around allowlisted scientific and public health sources with zero-hallucination abstention.
            </p>
            <div className="text-[11px] text-slate-400">
              Approved Sources: WHO · ICMR · MoHFW · NCDC · PubMed
            </div>
          </div>

          <div className="space-y-2">
            <div className="font-bold text-slate-800 uppercase tracking-wider text-[11px]">
              Supported Languages
            </div>
            <ul className="space-y-1 text-slate-500">
              <li>English (Global)</li>
              <li>தமிழ் (Tamil)</li>
              <li>हिन्दी (Hindi)</li>
              <li>മലയാളം (Malayalam)</li>
              <li>తెలుగు (Telugu)</li>
              <li>ಕನ್ನಡ (Kannada)</li>
            </ul>
          </div>

          <div className="space-y-2">
            <div className="font-bold text-slate-800 uppercase tracking-wider text-[11px]">
              Emergency Helplines (India)
            </div>
            <ul className="space-y-1 text-slate-500">
              <li>National Emergency: <strong className="text-slate-800">112</strong></li>
              <li>Medical & Ambulance: <strong className="text-slate-800">108</strong></li>
              <li>Mental Health Helpline (KIRAN): <strong className="text-slate-800">1800-599-0019</strong></li>
              <li>Women Helpline: <strong className="text-slate-800">1091</strong></li>
            </ul>
          </div>
        </div>

        <div className="pt-6 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-400">
          <div>
            © {new Date().getFullYear()} ClintelAI. Dedicated to patient safety, privacy, and accessible healthcare intelligence.
          </div>
          <div className="flex items-center gap-1 text-[11px]">
            <span>Engineered with strict evidence validation</span>
            <Heart className="w-3.5 h-3.5 text-rose-500 fill-rose-500" />
          </div>
        </div>
      </div>
    </footer>
  );
}
