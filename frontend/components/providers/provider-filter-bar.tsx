"use client";

import React, { useState, useEffect } from "react";
import {
  Search,
  MapPin,
  Crosshair,
  Filter,
  X,
  Stethoscope,
  Building2,
  Check,
  ChevronDown,
  Clock,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, ApiSpecialtyItem } from "@/lib/api";
import { useLanguage } from "@/lib/i18n/language-context";

export interface ProviderFilters {
  query: string;
  lat: number | null;
  lon: number | null;
  radiusKm: number;
  city: string;
  specialty: string;
  providerType: string;
  verificationStatus: string;
  openNow: boolean;
}

interface ProviderFilterBarProps {
  filters: ProviderFilters;
  onChange: (updated: Partial<ProviderFilters>) => void;
  onReset: () => void;
  isLoading?: boolean;
}

export function ProviderFilterBar({
  filters,
  onChange,
  onReset,
  isLoading,
}: ProviderFilterBarProps) {
  const { t } = useLanguage();
  const [specialties, setSpecialties] = useState<ApiSpecialtyItem[]>([]);
  const [isLocating, setIsLocating] = useState(false);
  const [locationStatus, setLocationStatus] = useState<string | null>(null);

  // Fetch available medical specialties
  useEffect(() => {
    api
      .getSpecialties()
      .then((data) => setSpecialties(data.specialties || []))
      .catch((err) => console.warn("Could not load specialties:", err));
  }, []);

  // Request browser GPS coordinates
  const handleAcquireLocation = () => {
    if (!navigator.geolocation) {
      setLocationStatus("Geolocation not supported by your browser");
      return;
    }

    setIsLocating(true);
    setLocationStatus("Locating...");

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setIsLocating(false);
        setLocationStatus("GPS Location Active");
        onChange({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          city: "", // Clear manual city when GPS used
        });
      },
      (err) => {
        setIsLocating(false);
        setLocationStatus("Location denied. Searching by city instead.");
        console.warn("GPS error:", err.message);
      },
      { timeout: 8000, enableHighAccuracy: true }
    );
  };

  const hasActiveFilters =
    Boolean(filters.query) ||
    filters.lat !== null ||
    Boolean(filters.city) ||
    Boolean(filters.specialty) ||
    filters.providerType !== "all" ||
    Boolean(filters.verificationStatus) ||
    filters.openNow;

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 p-4 sm:p-5 shadow-xs space-y-4">
      {/* Top Search Input & City Locality */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
        {/* Main Query Input */}
        <div className="md:col-span-6 relative">
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
            <Search className="w-4 h-4" />
          </div>
          <Input
            value={filters.query}
            onChange={(e) => onChange({ query: e.target.value })}
            placeholder={t.providers.searchPlaceholder}
            className="pl-10 pr-9 text-sm h-11 rounded-xl"
          />
          {filters.query && (
            <button
              type="button"
              onClick={() => onChange({ query: "" })}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* City / Locality Manual Input */}
        <div className="md:col-span-3 relative">
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
            <MapPin className="w-4 h-4" />
          </div>
          <Input
            value={filters.city}
            onChange={(e) =>
              onChange({ city: e.target.value, lat: null, lon: null })
            }
            placeholder="City (Chennai, Delhi, Kochi...)"
            className="pl-10 text-sm h-11 rounded-xl"
          />
        </div>

        {/* Use My Location GPS Button */}
        <div className="md:col-span-3 flex items-center gap-2">
          <Button
            type="button"
            variant={filters.lat !== null ? "primary" : "outline"}
            onClick={handleAcquireLocation}
            disabled={isLocating}
            className={`w-full h-11 text-xs font-semibold rounded-xl flex items-center justify-center gap-2 ${
              filters.lat !== null
                ? "bg-blue-600 text-white"
                : "text-slate-700 hover:bg-blue-50 hover:text-blue-600"
            }`}
          >
            <Crosshair
              className={`w-4 h-4 ${isLocating ? "animate-spin" : ""}`}
            />
            <span>
              {isLocating
                ? "Locating..."
                : filters.lat !== null
                ? "GPS Active"
                : t.providers.useMyLocation}
            </span>
          </Button>

          {/* Clear coordinates button if GPS active */}
          {filters.lat !== null && (
            <button
              onClick={() => {
                onChange({ lat: null, lon: null });
                setLocationStatus(null);
              }}
              className="p-2.5 rounded-xl border border-slate-200 text-slate-400 hover:text-slate-700 hover:bg-slate-100"
              title="Clear GPS location"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Second Row: Provider Type Tabs & Secondary Filters */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-1 border-t border-slate-100">
        {/* Provider Type Switcher Tabs */}
        <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-xl">
          {[
            { id: "all", label: t.providers.allTypes, icon: null },
            { id: "doctor", label: t.providers.doctorsOnly, icon: Stethoscope },
            { id: "hospital", label: t.providers.hospitalsOnly, icon: Building2 },
            { id: "clinic", label: t.providers.clinicsOnly, icon: null },
          ].map((type) => {
            const Icon = type.icon;
            const isSelected = filters.providerType === type.id;
            return (
              <button
                key={type.id}
                type="button"
                onClick={() => onChange({ providerType: type.id })}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                  isSelected
                    ? "bg-white text-slate-900 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {Icon && <Icon className="w-3.5 h-3.5 text-blue-600" />}
                <span>{type.label}</span>
              </button>
            );
          })}
        </div>

        {/* Filters Group: Specialty Dropdown, Radius, Verified Only */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Specialty Dropdown */}
          <div className="relative">
            <select
              value={filters.specialty}
              onChange={(e) => onChange({ specialty: e.target.value })}
              className="h-9 text-xs pl-3 pr-8 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 font-medium focus:ring-1 focus:ring-blue-500 focus:outline-none appearance-none"
              aria-label="Filter by Medical Specialty"
            >
              <option value="">{t.providers.allSpecialties}</option>
              {specialties.map((s) => (
                <option key={s.specialty} value={s.specialty}>
                  {s.specialty} ({s.count})
                </option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-3 pointer-events-none" />
          </div>

          {/* Search Radius Dropdown */}
          <div className="relative">
            <select
              value={filters.radiusKm}
              onChange={(e) => onChange({ radiusKm: parseFloat(e.target.value) })}
              className="h-9 text-xs pl-3 pr-8 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 font-medium focus:ring-1 focus:ring-blue-500 focus:outline-none appearance-none"
              aria-label="Filter by Search Radius"
            >
              <option value={2}>2 km radius</option>
              <option value={5}>5 km radius</option>
              <option value={10}>10 km radius</option>
              <option value={25}>25 km radius</option>
              <option value={50}>50 km radius</option>
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-3 pointer-events-none" />
          </div>

          {/* Verified Only Toggle */}
          <button
            type="button"
            onClick={() =>
              onChange({
                verificationStatus:
                  filters.verificationStatus === "VERIFIED" ? "" : "VERIFIED",
              })
            }
            className={`h-9 px-3 rounded-lg text-xs font-semibold border flex items-center gap-1.5 transition-colors ${
              filters.verificationStatus === "VERIFIED"
                ? "bg-emerald-50 text-emerald-800 border-emerald-300"
                : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
            }`}
          >
            <ShieldCheck
              className={`w-3.5 h-3.5 ${
                filters.verificationStatus === "VERIFIED"
                  ? "text-emerald-600"
                  : "text-slate-400"
              }`}
            />
            <span>{t.providers.verifiedOnly}</span>
          </button>

          {/* Open Now Toggle */}
          <button
            type="button"
            onClick={() => onChange({ openNow: !filters.openNow })}
            className={`h-9 px-3 rounded-lg text-xs font-semibold border flex items-center gap-1.5 transition-colors ${
              filters.openNow
                ? "bg-blue-50 text-blue-800 border-blue-300"
                : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
            }`}
          >
            <Clock
              className={`w-3.5 h-3.5 ${
                filters.openNow ? "text-blue-600" : "text-slate-400"
              }`}
            />
            <span>{t.providers.openNow}</span>
          </button>

          {/* Reset Filters Button */}
          {hasActiveFilters && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={onReset}
              className="text-xs text-slate-500 hover:text-slate-900 h-9"
            >
              <X className="w-3 h-3 mr-1" />
              <span>{t.providers.clearFilters}</span>
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
