"use client";

import React, { createContext, useContext, useSyncExternalStore } from "react";
import {
  LANGUAGES,
  LanguageInfo,
  SupportedLanguage,
  translations,
} from "./translations";

interface LanguageContextType {
  language: SupportedLanguage;
  setLanguage: (lang: SupportedLanguage) => void;
  languages: LanguageInfo[];
  t: typeof translations.en;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

let memoryLanguage: SupportedLanguage = "en";
const listeners = new Set<() => void>();

function subscribe(listener: () => void) {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

function getSnapshot(): SupportedLanguage {
  if (typeof window !== "undefined") {
    const saved = localStorage.getItem("clintelai_language") as SupportedLanguage;
    if (saved && ["en", "ta", "hi", "ml", "te", "kn"].includes(saved)) {
      return saved;
    }
  }
  return memoryLanguage;
}

function getServerSnapshot(): SupportedLanguage {
  return "en";
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const language = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const setLanguage = (lang: SupportedLanguage) => {
    memoryLanguage = lang;
    if (typeof window !== "undefined") {
      localStorage.setItem("clintelai_language", lang);
      document.documentElement.lang = lang;
    }
    listeners.forEach((l) => l());
  };

  const currentTranslations = translations[language] || translations.en;

  return (
    <LanguageContext.Provider
      value={{
        language,
        setLanguage,
        languages: LANGUAGES,
        t: currentTranslations,
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}

