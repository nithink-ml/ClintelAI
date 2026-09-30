"use client";

import React, { useState } from "react";
import { Modal } from "@/components/ui/modal";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { AlertBanner } from "@/components/ui/alert-banner";
import { useAuth } from "@/lib/auth-context";
import { useLanguage } from "@/lib/i18n/language-context";
import { SupportedLanguage } from "@/lib/i18n/translations";

export function AuthModal() {
  const {
    isAuthModalOpen,
    setIsAuthModalOpen,
    authModalMode,
    setAuthModalMode,
    login,
    register,
  } = useAuth();
  const { t, languages } = useLanguage();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [regLanguage, setRegLanguage] = useState<SupportedLanguage>("en");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const resetForm = () => {
    setEmail("");
    setPassword("");
    setFullName("");
    setError(null);
  };

  const handleClose = () => {
    resetForm();
    setIsAuthModalOpen(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (authModalMode === "login") {
        await login(email, password);
      } else {
        if (!fullName.trim()) {
          throw new Error("Full name is required");
        }
        await register(email, password, fullName, regLanguage);
      }
      resetForm();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isAuthModalOpen}
      onClose={handleClose}
      title={authModalMode === "login" ? t.auth.signInTitle : t.auth.signUpTitle}
      description={
        authModalMode === "login"
          ? t.auth.signInSubtitle
          : t.auth.signUpSubtitle
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <AlertBanner variant="error" title="Authentication Notice">
            {error}
          </AlertBanner>
        )}

        {authModalMode === "register" && (
          <>
            <Input
              label={t.auth.fullNameLabel}
              placeholder="e.g. Dr. Ramesh Kumar"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />

            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                {t.auth.preferredLanguageLabel}
              </label>
              <select
                value={regLanguage}
                onChange={(e) => setRegLanguage(e.target.value as SupportedLanguage)}
                className="w-full h-10 px-3 rounded-xl border border-slate-200 bg-white text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {languages.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.native} ({l.name})
                  </option>
                ))}
              </select>
            </div>
          </>
        )}

        <Input
          type="email"
          label={t.auth.emailLabel}
          placeholder="name@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <Input
          type="password"
          label={t.auth.passwordLabel}
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          helperText={
            authModalMode === "register"
              ? "Minimum 8 characters with letters and numbers"
              : undefined
          }
        />

        <div className="pt-2">
          <Button
            type="submit"
            className="w-full h-11"
            isLoading={loading}
          >
            {authModalMode === "login" ? t.auth.signInBtn : t.auth.signUpBtn}
          </Button>
        </div>

        <div className="text-center text-xs text-slate-500 pt-2 border-t border-slate-100">
          {authModalMode === "login" ? (
            <>
              {t.auth.dontHaveAccount}{" "}
              <button
                type="button"
                onClick={() => {
                  setError(null);
                  setAuthModalMode("register");
                }}
                className="text-blue-600 font-semibold hover:underline"
              >
                {t.auth.signUpLink}
              </button>
            </>
          ) : (
            <>
              {t.auth.alreadyHaveAccount}{" "}
              <button
                type="button"
                onClick={() => {
                  setError(null);
                  setAuthModalMode("login");
                }}
                className="text-blue-600 font-semibold hover:underline"
              >
                {t.auth.signInLink}
              </button>
            </>
          )}
        </div>
      </form>
    </Modal>
  );
}
