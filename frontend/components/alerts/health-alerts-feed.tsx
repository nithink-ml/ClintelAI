"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  BellRing,
  Search,
  MapPin,
  Filter,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  PhoneCall,
  ShieldCheck,
  ChevronLeft,
  ChevronRight,
  Flame,
  Radio,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  api,
  ApiHealthAlertSummary,
  ApiHealthAlertSearchResponse,
  ApiEmergencyEscalation,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useLanguage } from "@/lib/i18n/language-context";
import { AlertCard } from "./alert-card";
import { AlertDetailModal } from "./alert-detail-modal";
import { SeverityBadge } from "./alert-badge";

const INDIAN_STATES = [
  "All States",
  "Tamil Nadu",
  "Kerala",
  "Karnataka",
  "Delhi",
  "West Bengal",
  "Telangana",
  "Maharashtra",
];

const CATEGORIES = [
  { value: "", label: "All Categories" },
  { value: "infectious_disease", label: "Infectious Disease" },
  { value: "outbreak", label: "Outbreak" },
  { value: "air_quality", label: "Air Quality" },
  { value: "heatwave", label: "Heatwave" },
  { value: "seasonal_epidemic", label: "Seasonal Epidemic" },
  { value: "vaccination_drive", label: "Vaccination Drive" },
];

const SEVERITIES = [
  { value: "", label: "All Severities" },
  { value: "CRITICAL", label: "Critical" },
  { value: "HIGH", label: "High" },
  { value: "MODERATE", label: "Moderate" },
  { value: "LOW", label: "Low" },
  { value: "INFORMATIONAL", label: "Informational" },
];

export function HealthAlertsFeed() {
  const { user, token } = useAuth();
  const { t, language } = useLanguage();

  const [query, setQuery] = useState("");
  const [selectedState, setSelectedState] = useState("All States");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedSeverity, setSelectedSeverity] = useState("");
  const [statusFilter, setStatusFilter] = useState<"ACTIVE" | "EXPIRED" | "ALL">("ACTIVE");

  const [userCoords, setUserCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [isLocating, setIsLocating] = useState(false);
  const [locationName, setLocationName] = useState<string | null>(null);

  const [page, setPage] = useState(1);
  const [pageSize] = useState(6);

  const [data, setData] = useState<ApiHealthAlertSearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [activeModalAlert, setActiveModalAlert] = useState<ApiHealthAlertSummary | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  const isAdmin = user?.role === "admin";

  // Execute Search
  const fetchAlerts = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const stateParam = selectedState === "All States" ? undefined : selectedState;
      const resp = await api.searchAlerts({
        query: query.trim() || undefined,
        lat: userCoords?.lat,
        lon: userCoords?.lon,
        state: stateParam,
        category: selectedCategory || undefined,
        severity: selectedSeverity || undefined,
        status: statusFilter,
        language,
        page,
        page_size: pageSize,
      });

      setData(resp);
    } catch (err: any) {
      setError(err.message || "Failed to load health alerts");
    } finally {
      setIsLoading(false);
    }
  }, [
    query,
    selectedState,
    selectedCategory,
    selectedSeverity,
    statusFilter,
    userCoords,
    language,
    page,
    pageSize,
  ]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchAlerts();
    }, 150);
    return () => clearTimeout(timer);
  }, [fetchAlerts]);

  // Geolocation Trigger
  const handleUseLocation = () => {
    if (!navigator.geolocation) {
      alert("Geolocation is not supported by your browser");
      return;
    }

    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setUserCoords({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
        });
        setLocationName("GPS Location");
        setSelectedState("All States");
        setIsLocating(false);
        setPage(1);
      },
      () => {
        // Fallback demo location: Chennai (13.0827, 80.2707)
        setUserCoords({ lat: 13.0827, lon: 80.2707 });
        setLocationName("Chennai (Demo Fallback)");
        setSelectedState("All States");
        setIsLocating(false);
        setPage(1);
      },
      { timeout: 5000 }
    );
  };

  const handleClearLocation = () => {
    setUserCoords(null);
    setLocationName(null);
    setPage(1);
  };

  const handleResetFilters = () => {
    setQuery("");
    setSelectedState("All States");
    setSelectedCategory("");
    setSelectedSeverity("");
    setStatusFilter("ACTIVE");
    setUserCoords(null);
    setLocationName(null);
    setPage(1);
  };

  const handleAdminSync = async () => {
    if (!token) return;
    setIsSyncing(true);
    setSyncMessage(null);
    try {
      const res = await api.syncCanonicalAlerts(token);
      setSyncMessage(res.message || "Alerts synchronized successfully.");
      fetchAlerts();
    } catch (err: any) {
      setSyncMessage(`Sync failed: ${err.message}`);
    } finally {
      setIsSyncing(false);
    }
  };

  const alerts = data?.items || [];
  const emergency = data?.emergency_escalation;
  const criticalCount = data?.critical_active_count || 0;

  return (
    <div className="space-y-6">
      {/* Header & Subtitle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-red-100 text-red-600 flex items-center justify-center shadow-2xs">
              <BellRing className="w-4 h-4" />
            </div>
            <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
              {t.alerts?.title || "Regional Health Alerts & Advisories"}
            </h2>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-700">
              Phase 4
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-600 mt-1 max-w-2xl leading-relaxed">
            {t.alerts?.subtitle ||
              "Official epidemiological bulletins, seasonal hazard warnings, and public health advisories from accredited public authorities."}
          </p>
        </div>

        {/* Admin Tools */}
        {isAdmin && (
          <div className="flex items-center gap-2 self-start sm:self-auto">
            <Button
              size="sm"
              variant="outline"
              onClick={handleAdminSync}
              disabled={isSyncing}
              className="text-xs border-slate-300"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isSyncing ? "animate-spin" : ""}`} />
              <span>{isSyncing ? "Syncing..." : "Sync Canonical Alerts"}</span>
            </Button>
          </div>
        )}
      </div>

      {syncMessage && (
        <div className="p-3 rounded-xl bg-blue-50 border border-blue-200 text-xs text-blue-800 font-medium">
          {syncMessage}
        </div>
      )}

      {/* Emergency Red-Flag Escalation Card */}
      {emergency && emergency.is_emergency && (
        <div className="rounded-2xl p-5 bg-gradient-to-r from-red-600 to-rose-700 text-white shadow-xl shadow-red-600/20 space-y-3 animate-in zoom-in-95 duration-200">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-white/20 flex items-center justify-center shrink-0">
              <AlertTriangle className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="font-extrabold text-sm sm:text-base">
                {t.alerts?.emergencyNotice || "Emergency Red-Flag Symptoms Detected"}
              </div>
              <div className="text-xs text-red-100">
                Symptoms: {emergency.symptoms_detected.join(", ")}
              </div>
            </div>
          </div>

          <p className="text-xs sm:text-sm text-white/95 leading-relaxed">
            {emergency.action_message}
          </p>

          <div className="pt-1 flex flex-wrap gap-2.5">
            {emergency.emergency_numbers.map((num) => (
              <a
                key={num}
                href={`tel:${num}`}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white text-red-600 font-extrabold text-xs shadow-md hover:bg-red-50 transition-colors"
              >
                <PhoneCall className="w-4 h-4 text-red-600" />
                <span>Dial {num} Immediately</span>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* High Urgency Critical Alerts Broadcast Banner */}
      {criticalCount > 0 && statusFilter === "ACTIVE" && (
        <div className="rounded-2xl p-4 bg-red-50 border border-red-200/90 text-red-950 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
          <div className="flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-red-600"></span>
            </span>
            <div className="text-xs sm:text-sm">
              <strong className="font-bold text-red-900">
                {criticalCount} Active Critical Public Health Alert{criticalCount > 1 ? "s" : ""}
              </strong>{" "}
              <span>in official surveillance directories. Prioritize preventive measures.</span>
            </div>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setSelectedSeverity("CRITICAL")}
            className="text-xs border-red-300 text-red-700 bg-white hover:bg-red-50 self-start sm:self-auto shrink-0"
          >
            <span>Filter Critical Only</span>
          </Button>
        </div>
      )}

      {/* Interactive Filter Bar */}
      <div className="p-4 sm:p-5 rounded-2xl bg-white border border-slate-200/90 shadow-xs space-y-4">
        {/* Search input + location buttons */}
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
          <div className="sm:col-span-8 relative">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(1);
              }}
              placeholder={
                t.alerts?.searchPlaceholder ||
                "Search health alerts (e.g., Dengue, Nipah, Heatwave, AQI)..."
              }
              className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50"
            />
          </div>

          <div className="sm:col-span-4 flex gap-2">
            <button
              type="button"
              onClick={handleUseLocation}
              disabled={isLocating}
              className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold border transition-all ${
                userCoords
                  ? "bg-blue-50 text-blue-700 border-blue-200"
                  : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
              }`}
            >
              <MapPin className="w-3.5 h-3.5 text-blue-600 shrink-0" />
              <span className="truncate">
                {isLocating ? "Locating..." : locationName || "Near Me"}
              </span>
            </button>

            {userCoords && (
              <button
                type="button"
                onClick={handleClearLocation}
                className="px-2.5 py-2 rounded-xl text-xs font-medium text-slate-500 hover:text-slate-700 border border-slate-200 hover:bg-slate-50"
                title="Clear GPS"
              >
                Clear
              </button>
            )}

            {(query || selectedState !== "All States" || selectedCategory || selectedSeverity || statusFilter !== "ACTIVE") && (
              <button
                type="button"
                onClick={handleResetFilters}
                className="px-2.5 py-2 rounded-xl text-xs font-medium text-slate-500 hover:text-slate-700 border border-slate-200 hover:bg-slate-50 flex items-center gap-1"
                title="Reset Filters"
              >
                <RotateCcw className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>

        {/* Secondary Filter Selectors */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 border-t border-slate-100 text-xs">
          {/* State */}
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">
              {t.alerts?.state || "State"}
            </label>
            <select
              value={selectedState}
              onChange={(e) => {
                setSelectedState(e.target.value);
                setPage(1);
              }}
              className="w-full p-2 rounded-xl border border-slate-200 bg-white font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {INDIAN_STATES.map((st) => (
                <option key={st} value={st}>
                  {st}
                </option>
              ))}
            </select>
          </div>

          {/* Category */}
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">
              {t.alerts?.category || "Category"}
            </label>
            <select
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value);
                setPage(1);
              }}
              className="w-full p-2 rounded-xl border border-slate-200 bg-white font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          {/* Severity */}
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">
              {t.alerts?.severity || "Severity"}
            </label>
            <select
              value={selectedSeverity}
              onChange={(e) => {
                setSelectedSeverity(e.target.value);
                setPage(1);
              }}
              className="w-full p-2 rounded-xl border border-slate-200 bg-white font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {SEVERITIES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>

          {/* Status Lifecycle Tabs */}
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">
              {t.alerts?.status || "Status"}
            </label>
            <div className="flex rounded-xl bg-slate-100 p-1 border border-slate-200">
              <button
                type="button"
                onClick={() => {
                  setStatusFilter("ACTIVE");
                  setPage(1);
                }}
                className={`flex-1 py-1 rounded-lg text-[11px] font-bold transition-all ${
                  statusFilter === "ACTIVE"
                    ? "bg-white text-slate-900 shadow-2xs"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                Active
              </button>
              <button
                type="button"
                onClick={() => {
                  setStatusFilter("EXPIRED");
                  setPage(1);
                }}
                className={`flex-1 py-1 rounded-lg text-[11px] font-bold transition-all ${
                  statusFilter === "EXPIRED"
                    ? "bg-white text-slate-900 shadow-2xs"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                Expired
              </button>
              <button
                type="button"
                onClick={() => {
                  setStatusFilter("ALL");
                  setPage(1);
                }}
                className={`flex-1 py-1 rounded-lg text-[11px] font-bold transition-all ${
                  statusFilter === "ALL"
                    ? "bg-white text-slate-900 shadow-2xs"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                All
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Results Header */}
      <div className="flex items-center justify-between text-xs text-slate-500 px-1">
        <div>
          Showing{" "}
          <strong className="text-slate-800 font-bold">{data?.total || 0}</strong>{" "}
          public health bulletin{data?.total === 1 ? "" : "s"}
          {selectedState !== "All States" && ` in ${selectedState}`}
        </div>
        <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
          <span>Accredited Sources: MoHFW, NCDC, WHO, State Directorates</span>
        </div>
      </div>

      {/* Alerts Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-56 rounded-2xl bg-slate-100 animate-pulse border border-slate-200/80 p-5 space-y-3"
            >
              <div className="h-4 w-1/3 bg-slate-200 rounded" />
              <div className="h-6 w-3/4 bg-slate-200 rounded" />
              <div className="h-14 w-full bg-slate-200 rounded" />
              <div className="h-4 w-1/2 bg-slate-200 rounded" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="p-8 text-center rounded-2xl bg-red-50 border border-red-200 text-red-800 space-y-3">
          <AlertTriangle className="w-8 h-8 text-red-500 mx-auto" />
          <div className="font-bold text-sm">{error}</div>
          <Button size="sm" variant="outline" onClick={fetchAlerts}>
            Retry Request
          </Button>
        </div>
      ) : alerts.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-white border border-slate-200 space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
            <Radio className="w-6 h-6" />
          </div>
          <div className="font-bold text-slate-800 text-base">
            {t.alerts?.noResults || "No active health advisories matched your criteria."}
          </div>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            {t.alerts?.noResultsSub || "Try selecting All States or clearing search filters."}
          </p>
          <Button size="sm" variant="outline" onClick={handleResetFilters}>
            Reset Filters
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {alerts.map((al) => (
            <AlertCard
              key={al.id}
              alert={al}
              onSelect={(selected) => setActiveModalAlert(selected)}
            />
          ))}
        </div>
      )}

      {/* Pagination Controls */}
      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t border-slate-200 text-xs">
          <Button
            size="sm"
            variant="outline"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            <ChevronLeft className="w-3.5 h-3.5 mr-1" />
            Previous
          </Button>

          <span className="text-slate-500 font-medium">
            Page {page} of {data.total_pages}
          </span>

          <Button
            size="sm"
            variant="outline"
            disabled={page >= data.total_pages}
            onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
          >
            Next
            <ChevronRight className="w-3.5 h-3.5 ml-1" />
          </Button>
        </div>
      )}

      {/* Official Legal / Clinical Disclaimer */}
      <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-[11px] text-slate-500 leading-relaxed space-y-1">
        <div className="font-semibold text-slate-700">Official Clinical Information Disclaimer:</div>
        <div>{data?.disclaimer || t.alerts?.disclaimer}</div>
      </div>

      {/* Detail Modal */}
      <AlertDetailModal
        summaryAlert={activeModalAlert}
        language={language}
        onClose={() => setActiveModalAlert(null)}
      />
    </div>
  );
}
