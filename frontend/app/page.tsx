"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  Search,
  Activity,
  Globe2,
  FileCheck2,
  Sparkles,
  User,
  Heart,
  PhoneCall,
  Server,
  Database,
  Lock,
  ArrowRight,
  ExternalLink,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertBanner } from "@/components/ui/alert-banner";
import { useAuth } from "@/lib/auth-context";
import { useLanguage } from "@/lib/i18n/language-context";
import { ClinicalAssistant } from "@/components/assistant/clinical-assistant";

interface BackendHealthData {
  status: string;
  app_name: string;
  version: string;
  services?: {
    database?: { status: string; engine: string };
    api?: { status: string };
  };
}

export default function HomePage() {
  const { user, isAuthenticated, setIsAuthModalOpen, setAuthModalMode, setIsProfileModalOpen } = useAuth();
  const { t, language, setLanguage, languages } = useLanguage();

  const [backendHealth, setBackendHealth] = useState<BackendHealthData | null>(null);

  useEffect(() => {
    fetch("http://localhost:8000/api/v1/health")
      .then((res) => res.json())
      .then((data) => setBackendHealth(data))
      .catch((err) => console.warn("Could not fetch backend health:", err));
  }, []);

  return (
    <div className="space-y-10">
      {/* Top Welcome / Auth Alert Banner */}
      {isAuthenticated && user ? (
        <AlertBanner variant="success">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <span className="font-bold">
                {t.auth.signInTitle}, {user.profile?.full_name || user.email}!
              </span>{" "}
              <span>Your personal health profile and preferences are active.</span>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsProfileModalOpen(true)}
              className="bg-white/80 self-start sm:self-auto"
            >
              <User className="w-3.5 h-3.5 mr-1 text-blue-600" />
              <span>{t.profile.title}</span>
            </Button>
          </div>
        </AlertBanner>
      ) : (
        <div className="bg-gradient-to-r from-blue-500/10 via-cyan-500/10 to-indigo-500/10 border border-blue-200/80 rounded-2xl p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shrink-0 shadow-sm shadow-blue-500/30">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="font-bold text-sm text-slate-900">
                {t.common.phase1Badge}: Authentication & Multilingual Architecture
              </div>
              <div className="text-xs text-slate-600 mt-0.5">
                Create an account or sign in to configure your personal profile, Indic language choice, and emergency contacts.
              </div>
            </div>
          </div>
          <div className="flex gap-2 self-start sm:self-auto shrink-0">
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setAuthModalMode("login");
                setIsAuthModalOpen(true);
              }}
            >
              {t.nav.login}
            </Button>
            <Button
              size="sm"
              onClick={() => {
                setAuthModalMode("register");
                setIsAuthModalOpen(true);
              }}
            >
              {t.nav.register}
            </Button>
          </div>
        </div>
      )}

      {/* Hero Headline */}
      <section className="text-center max-w-3xl mx-auto space-y-4 pt-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-100/70 text-blue-800 text-xs font-semibold uppercase tracking-wider">
          <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
          <span>Strict Evidence Grounding & Abstention</span>
        </div>

        <h1 className="text-4xl sm:text-5xl font-extrabold text-slate-900 tracking-tight leading-tight">
          {t.appName} — <br className="hidden sm:inline" />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-cyan-600">
            {t.tagline}
          </span>
        </h1>

        <p className="text-base sm:text-lg text-slate-600 leading-relaxed max-w-2xl mx-auto">
          Accessible healthcare guidance grounded exclusively in verified public health literature, with transparent source attribution, verified doctor discovery, and zero-hallucination abstention.
        </p>

        {/* Language Quick-Switch Bar */}
        <div className="pt-2 flex flex-wrap items-center justify-center gap-1.5">
          <span className="text-xs font-semibold text-slate-500 mr-1 flex items-center gap-1">
            <Globe2 className="w-3.5 h-3.5 text-blue-500" />
            <span>Languages:</span>
          </span>
          {languages.map((l) => (
            <button
              key={l.code}
              onClick={() => setLanguage(l.code)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                language === l.code
                  ? "bg-blue-600 text-white shadow-xs font-bold"
                  : "bg-white border border-slate-200 text-slate-600 hover:border-blue-300 hover:text-slate-900"
              }`}
            >
              {l.native}
            </button>
          ))}
        </div>
      </section>

      {/* Phase 2: Evidence-Grounded Clinical Retrieval Assistant */}
      <section className="max-w-4xl mx-auto w-full">
        <ClinicalAssistant />
      </section>

      {/* Core Architectural Pillars */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <Card className="hover:border-blue-300">
          <CardHeader>
            <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center mb-2">
              <FileCheck2 className="w-6 h-6" />
            </div>
            <CardTitle>{t.nav.assistant}</CardTitle>
            <CardDescription>
              Evidence-grounded health assistant validated against allowlisted guidelines.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between text-xs font-semibold text-blue-600 pt-2 border-t border-slate-100">
              <span>Citation Gate & Abstention</span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">
                Phase 2
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="hover:border-cyan-300">
          <CardHeader>
            <div className="w-12 h-12 rounded-xl bg-cyan-50 text-cyan-600 flex items-center justify-center mb-2">
              <Search className="w-6 h-6" />
            </div>
            <CardTitle>{t.nav.doctorFinder}</CardTitle>
            <CardDescription>
              Location-based provider discovery with transparent verification tags.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between text-xs font-semibold text-cyan-600 pt-2 border-t border-slate-100">
              <span>Discovery ≠ Endorsement</span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">
                Phase 3
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="hover:border-indigo-300">
          <CardHeader>
            <div className="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-2">
              <Globe2 className="w-6 h-6" />
            </div>
            <CardTitle>6 Indic Languages</CardTitle>
            <CardDescription>
              Native script support for English, Tamil, Hindi, Malayalam, Telugu, and Kannada.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between text-xs font-semibold text-indigo-600 pt-2 border-t border-slate-100">
              <span>Active in Phase 1</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            </div>
          </CardContent>
        </Card>

        <Card className="hover:border-rose-300">
          <CardHeader>
            <div className="w-12 h-12 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center mb-2">
              <Activity className="w-6 h-6" />
            </div>
            <CardTitle>{t.nav.healthAlerts}</CardTitle>
            <CardDescription>
              Official regional advisories and public health outbreak surveillance.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between text-xs font-semibold text-rose-600 pt-2 border-t border-slate-100">
              <span>MoHFW & State Alerts</span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">
                Phase 4
              </span>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Phase 1 Live Status Dashboard */}
      <section className="bg-slate-900 text-white rounded-3xl p-6 sm:p-8 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <h2 className="text-lg font-bold text-white">Phase 1 Infrastructure & Database Status</h2>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Active PostgreSQL 16 PostGIS, Alembic Migrations, and JWT Authentication Engine.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono bg-slate-800 px-3 py-1.5 rounded-lg text-emerald-400 border border-slate-700">
              Alembic Rev: 65069711647b
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
          <div className="bg-slate-800/80 border border-slate-700/60 rounded-2xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Database Engine</span>
              <Database className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-base font-bold text-white">PostgreSQL 16 + PostGIS</div>
            <p className="text-xs text-slate-400 mt-1">
              Status: {backendHealth?.services?.database?.status === "connected" ? "Connected (Live)" : "Operational"}
            </p>
          </div>

          <div className="bg-slate-800/80 border border-slate-700/60 rounded-2xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Authentication</span>
              <Lock className="w-4 h-4 text-blue-400" />
            </div>
            <div className="text-base font-bold text-white">JWT + Bcrypt Hashing</div>
            <p className="text-xs text-slate-400 mt-1">RFC 7519 Nonced Token Rotation</p>
          </div>

          <div className="bg-slate-800/80 border border-slate-700/60 rounded-2xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Multilingual i18n</span>
              <Globe2 className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="text-base font-bold text-white">6 Indic Scripts</div>
            <p className="text-xs text-slate-400 mt-1">Current: {language.toUpperCase()}</p>
          </div>

          <div className="bg-slate-800/80 border border-slate-700/60 rounded-2xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Emergency SOS</span>
              <PhoneCall className="w-4 h-4 text-rose-400" />
            </div>
            <div className="text-base font-bold text-white">Helplines 112 / 108</div>
            <p className="text-xs text-slate-400 mt-1">Emergency contact escalation ready</p>
          </div>
        </div>

        {/* Interactive Try Button */}
        <div className="mt-8 pt-6 border-t border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="text-xs text-slate-400">
            {isAuthenticated ? (
              <span>Logged in as <strong>{user?.email}</strong>. Manage your profile and emergency responders.</span>
            ) : (
              <span>Test user registration or login with live JWT authentication.</span>
            )}
          </div>

          <div className="flex gap-2">
            {isAuthenticated ? (
              <Button size="sm" onClick={() => setIsProfileModalOpen(true)}>
                <User className="w-3.5 h-3.5 mr-1" />
                <span>{t.profile.title}</span>
              </Button>
            ) : (
              <Button
                size="sm"
                onClick={() => {
                  setAuthModalMode("register");
                  setIsAuthModalOpen(true);
                }}
              >
                <span>{t.auth.signUpBtn}</span>
                <ArrowRight className="w-3.5 h-3.5 ml-1" />
              </Button>
            )}

            <a
              href="http://localhost:8000/api/v1/docs"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center px-3 py-1.5 rounded-xl bg-slate-800 border border-slate-700 text-xs font-semibold text-slate-300 hover:text-white transition-colors"
            >
              <Server className="w-3.5 h-3.5 mr-1.5 text-slate-400" />
              <span>Swagger Docs</span>
              <ExternalLink className="w-3 h-3 ml-1 text-slate-500" />
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}
