"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { api, ApiUserDetail } from "./api";
import { useLanguage } from "./i18n/language-context";

interface AuthContextType {
  user: ApiUserDetail | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    fullName: string,
    language?: string
  ) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  isAuthModalOpen: boolean;
  setIsAuthModalOpen: (open: boolean) => void;
  authModalMode: "login" | "register";
  setAuthModalMode: (mode: "login" | "register") => void;
  isProfileModalOpen: boolean;
  setIsProfileModalOpen: (open: boolean) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<ApiUserDetail | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Modals state
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState<"login" | "register">("login");
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);

  const { setLanguage } = useLanguage();

  // Load session from localStorage on mount
  useEffect(() => {
    const initAuth = async () => {
      try {
        const storedToken = localStorage.getItem("clintelai_token");
        const storedRefresh = localStorage.getItem("clintelai_refresh_token");

        if (storedToken) {
          setToken(storedToken);
          setRefreshToken(storedRefresh);
          try {
            const userData = await api.getMe(storedToken);
            setUser(userData);
            if (userData.preferences?.preferred_language) {
              setLanguage(userData.preferences.preferred_language);
            }
          } catch {
            // Token might be expired, attempt refresh
            if (storedRefresh) {
              try {
                const refreshed = await api.refresh(storedRefresh);
                localStorage.setItem("clintelai_token", refreshed.access_token);
                localStorage.setItem("clintelai_refresh_token", refreshed.refresh_token);
                setToken(refreshed.access_token);
                setRefreshToken(refreshed.refresh_token);
                const refreshedUser = await api.getMe(refreshed.access_token);
                setUser(refreshedUser);
              } catch {
                localStorage.removeItem("clintelai_token");
                localStorage.removeItem("clintelai_refresh_token");
                setToken(null);
                setRefreshToken(null);
                setUser(null);
              }
            }
          }
        }
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, [setLanguage]);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const res = await api.login({ email, password });
      localStorage.setItem("clintelai_token", res.access_token);
      localStorage.setItem("clintelai_refresh_token", res.refresh_token);
      setToken(res.access_token);
      setRefreshToken(res.refresh_token);

      const userData = await api.getMe(res.access_token);
      setUser(userData);
      if (userData.preferences?.preferred_language) {
        setLanguage(userData.preferences.preferred_language);
      }
      setIsAuthModalOpen(false);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (
    email: string,
    password: string,
    fullName: string,
    language?: string
  ) => {
    setIsLoading(true);
    try {
      const res = await api.register({
        email,
        password,
        full_name: fullName,
        preferred_language: language,
      });
      localStorage.setItem("clintelai_token", res.access_token);
      localStorage.setItem("clintelai_refresh_token", res.refresh_token);
      setToken(res.access_token);
      setRefreshToken(res.refresh_token);

      const userData = await api.getMe(res.access_token);
      setUser(userData);
      if (userData.preferences?.preferred_language) {
        setLanguage(userData.preferences.preferred_language);
      }
      setIsAuthModalOpen(false);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    if (refreshToken && token) {
      try {
        await api.logout(refreshToken, token);
      } catch (err) {
        console.warn("Logout error:", err);
      }
    }
    localStorage.removeItem("clintelai_token");
    localStorage.removeItem("clintelai_refresh_token");
    setToken(null);
    setRefreshToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    if (!token) return;
    try {
      const userData = await api.getMe(token);
      setUser(userData);
    } catch (err) {
      console.error("Failed to refresh user:", err);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        refreshUser,
        isAuthModalOpen,
        setIsAuthModalOpen,
        authModalMode,
        setAuthModalMode,
        isProfileModalOpen,
        setIsProfileModalOpen,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
