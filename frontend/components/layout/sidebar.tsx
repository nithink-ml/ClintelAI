"use client";

import React from "react";
import {
  Home,
  MessageSquareHeart,
  Stethoscope,
  BellRing,
  User,
  PhoneCall,
  ShieldAlert,
  Lock,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useLanguage } from "@/lib/i18n/language-context";
import { cn } from "@/lib/utils";

export interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const { isAuthenticated, setIsAuthModalOpen, setAuthModalMode, setIsProfileModalOpen } = useAuth();
  const { t } = useLanguage();

  const navItems = [
    {
      id: "home",
      label: t.nav.home,
      icon: <Home className="w-4 h-4" />,
      active: true,
      phaseBadge: null,
      onClick: () => {},
    },
    {
      id: "assistant",
      label: t.nav.assistant,
      icon: <MessageSquareHeart className="w-4 h-4" />,
      active: false,
      phaseBadge: "Phase 2",
      locked: true,
      onClick: () => {},
    },
    {
      id: "doctorFinder",
      label: t.nav.doctorFinder,
      icon: <Stethoscope className="w-4 h-4" />,
      active: false,
      phaseBadge: "Phase 3",
      locked: true,
      onClick: () => {},
    },
    {
      id: "healthAlerts",
      label: t.nav.healthAlerts,
      icon: <BellRing className="w-4 h-4" />,
      active: false,
      phaseBadge: "Phase 4",
      locked: true,
      onClick: () => {},
    },
    {
      id: "profile",
      label: t.nav.profile,
      icon: <User className="w-4 h-4" />,
      active: false,
      phaseBadge: null,
      onClick: () => {
        if (isAuthenticated) {
          setIsProfileModalOpen(true);
        } else {
          setAuthModalMode("login");
          setIsAuthModalOpen(true);
        }
        if (onClose) onClose();
      },
    },
  ];

  return (
    <>
      {/* Mobile Drawer Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-slate-900/30 backdrop-blur-xs md:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={cn(
          "fixed top-16 bottom-0 left-0 z-30 w-64 bg-white border-r border-slate-200 p-4 flex flex-col justify-between transition-transform duration-200 ease-in-out md:translate-x-0 md:static md:top-0",
          isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        )}
      >
        <div className="space-y-6">
          {/* Navigation Links */}
          <div className="space-y-1">
            <div className="px-3 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Platform Modules
            </div>

            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={item.onClick}
                className={cn(
                  "w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition-all text-left",
                  item.active
                    ? "bg-blue-50 text-blue-700 shadow-xs"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-50",
                  item.locked && "opacity-85 cursor-not-allowed"
                )}
              >
                <div className="flex items-center gap-2.5">
                  <span className={item.active ? "text-blue-600" : "text-slate-400"}>
                    {item.icon}
                  </span>
                  <span>{item.label}</span>
                </div>

                {item.phaseBadge && (
                  <span className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 border border-slate-200">
                    <Lock className="w-2.5 h-2.5" />
                    <span>{item.phaseBadge}</span>
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Verification Principles Box */}
          <div className="p-3.5 rounded-2xl bg-blue-50/60 border border-blue-100 text-xs space-y-2">
            <div className="flex items-center gap-1.5 font-bold text-blue-900">
              <ShieldAlert className="w-4 h-4 text-blue-600 shrink-0" />
              <span>Allowlisted Evidence</span>
            </div>
            <p className="text-[11px] text-blue-800/80 leading-relaxed">
              Medical knowledge strictly sourced from WHO, ICMR, MoHFW, NCDC, and PubMed with citation gating.
            </p>
          </div>
        </div>

        {/* Emergency SOS Card */}
        <div className="p-4 rounded-2xl bg-gradient-to-br from-red-500 to-rose-600 text-white shadow-md shadow-red-500/20 space-y-2">
          <div className="flex items-center gap-2 font-bold text-xs">
            <PhoneCall className="w-4 h-4" />
            <span>Emergency Services</span>
          </div>
          <p className="text-[11px] text-red-100 leading-snug">
            Immediate 24/7 medical and ambulance assistance across India.
          </p>
          <div className="pt-1 flex gap-2">
            <a
              href="tel:112"
              className="flex-1 py-1.5 rounded-xl bg-white text-red-600 text-center text-xs font-bold hover:bg-red-50 transition-colors"
            >
              Dial 112
            </a>
            <a
              href="tel:108"
              className="flex-1 py-1.5 rounded-xl bg-red-700/60 text-white text-center text-xs font-bold hover:bg-red-700 transition-colors"
            >
              Dial 108
            </a>
          </div>
        </div>
      </aside>
    </>
  );
}
