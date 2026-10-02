"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Stethoscope,
  Building2,
  MapPin,
  List,
  Map as MapIcon,
  Columns2,
  AlertTriangle,
  PhoneCall,
  RotateCcw,
  Sparkles,
  ShieldCheck,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  api,
  ApiProviderCard,
  ApiProviderSearchResponse,
  ApiEmergencyEscalation,
} from "@/lib/api";
import { useLanguage } from "@/lib/i18n/language-context";
import { ProviderFilterBar, ProviderFilters } from "./provider-filter-bar";
import { ProviderCardComponent } from "./provider-card";
import { ProviderMapView } from "./provider-map-view";
import { ProviderDetailModal } from "./provider-detail-modal";

export function ProviderDiscovery() {
  const { t, language } = useLanguage();

  const [filters, setFilters] = useState<ProviderFilters>({
    query: "",
    lat: null,
    lon: null,
    radiusKm: 15,
    city: "",
    specialty: "",
    providerType: "all",
    verificationStatus: "",
    openNow: false,
  });

  const [viewMode, setViewMode] = useState<"list" | "map" | "split">("split");
  const [data, setData] = useState<ApiProviderSearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [selectedCard, setSelectedCard] = useState<ApiProviderCard | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  // Debounced search execution
  const executeSearch = useCallback(
    async (currentPage = 1) => {
      setIsLoading(true);
      setError(null);
      try {
        const res = await api.searchProviders({
          query: filters.query || undefined,
          lat: filters.lat ?? undefined,
          lon: filters.lon ?? undefined,
          radius_km: filters.radiusKm,
          city: filters.city || undefined,
          specialty: filters.specialty || undefined,
          provider_type: filters.providerType,
          verification_status: filters.verificationStatus || undefined,
          open_now: filters.openNow || undefined,
          page: currentPage,
          page_size: 10,
          language: language,
        });
        setData(res);
      } catch (err: any) {
        setError(err.message || "Failed to search providers");
      } finally {
        setIsLoading(false);
      }
    },
    [filters, language]
  );

  // Execute on filter change or language change
  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(1);
      executeSearch(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [filters, executeSearch]);

  const handleFilterChange = (updated: Partial<ProviderFilters>) => {
    setFilters((prev) => ({ ...prev, ...updated }));
  };

  const handleResetFilters = () => {
    setFilters({
      query: "",
      lat: null,
      lon: null,
      radiusKm: 15,
      city: "",
      specialty: "",
      providerType: "all",
      verificationStatus: "",
      openNow: false,
    });
  };

  const handleSelectCard = (card: ApiProviderCard) => {
    setSelectedCard(card);
    setIsDetailModalOpen(true);
  };

  const emergencyAlert = data?.emergency_escalation;

  return (
    <div className="space-y-6">
      {/* Header Headline */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-100/80 text-cyan-900 text-xs font-semibold mb-2">
            <ShieldCheck className="w-3.5 h-3.5 text-cyan-600" />
            <span>Phase 3 — PostGIS Spatial Provider Discovery</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            {t.providers.title}
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-2xl">
            {t.providers.subtitle}
          </p>
        </div>

        {/* View Mode Toggle Buttons */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl self-start sm:self-auto">
          <button
            type="button"
            onClick={() => setViewMode("list")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              viewMode === "list"
                ? "bg-white text-slate-900 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <List className="w-3.5 h-3.5" />
            <span>{t.providers.listView}</span>
          </button>
          <button
            type="button"
            onClick={() => setViewMode("split")}
            className={`hidden lg:flex px-3 py-1.5 rounded-lg text-xs font-semibold transition-all items-center gap-1.5 ${
              viewMode === "split"
                ? "bg-white text-slate-900 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Columns2 className="w-3.5 h-3.5" />
            <span>{t.providers.splitView}</span>
          </button>
          <button
            type="button"
            onClick={() => setViewMode("map")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              viewMode === "map"
                ? "bg-white text-slate-900 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <MapIcon className="w-3.5 h-3.5" />
            <span>{t.providers.mapView}</span>
          </button>
        </div>
      </div>

      {/* Red-Flag Emergency Escalation Banner */}
      {emergencyAlert && emergencyAlert.is_emergency && (
        <div className="bg-rose-50 border-2 border-rose-400 rounded-2xl p-4 sm:p-5 shadow-lg shadow-rose-500/10 animate-in fade-in-0 duration-300">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-rose-600 text-white flex items-center justify-center shrink-0 shadow-md shadow-rose-600/30">
                <AlertTriangle className="w-6 h-6 animate-pulse" />
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-extrabold uppercase px-2 py-0.5 rounded-md bg-rose-200/80 text-rose-900">
                    {emergencyAlert.level} EMERGENCY
                  </span>
                  <span className="font-bold text-sm text-slate-900">
                    {t.providers.emergencyAlertTitle}
                  </span>
                </div>
                <p className="text-xs text-rose-800 leading-relaxed font-medium">
                  {emergencyAlert.action_message}
                </p>
                {emergencyAlert.symptoms_detected.length > 0 && (
                  <div className="text-[11px] text-slate-600">
                    Trigger symptoms:{" "}
                    <span className="font-semibold text-rose-900">
                      {emergencyAlert.symptoms_detected.join(", ")}
                    </span>
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <a
                href="tel:112"
                className="px-4 py-2.5 rounded-xl bg-rose-600 text-white text-xs font-bold hover:bg-rose-700 transition-colors shadow-md shadow-rose-600/20 flex items-center gap-1.5"
              >
                <PhoneCall className="w-4 h-4" />
                <span>Call 112 (Police & Emergency)</span>
              </a>
              <a
                href="tel:108"
                className="px-4 py-2.5 rounded-xl bg-red-700 text-white text-xs font-bold hover:bg-red-800 transition-colors shadow-md shadow-red-700/20 flex items-center gap-1.5"
              >
                <PhoneCall className="w-4 h-4" />
                <span>Call 108 (Ambulance)</span>
              </a>
            </div>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <ProviderFilterBar
        filters={filters}
        onChange={handleFilterChange}
        onReset={handleResetFilters}
        isLoading={isLoading}
      />

      {/* Results Header: Count & Status */}
      <div className="flex items-center justify-between text-xs text-slate-500 px-1">
        <div>
          {isLoading ? (
            <span>Searching providers...</span>
          ) : data ? (
            <span className="font-semibold text-slate-800">
              {data.total} {t.providers.showingResults}
              {filters.city && ` in ${filters.city}`}
              {filters.specialty && ` • ${filters.specialty}`}
            </span>
          ) : null}
        </div>

        {data && data.total_pages > 1 && (
          <div className="flex items-center gap-2">
            <span>
              Page {data.page} of {data.total_pages}
            </span>
          </div>
        )}
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center justify-between">
          <span>{error}</span>
          <Button
            size="sm"
            variant="outline"
            onClick={() => executeSearch(page)}
          >
            Retry
          </Button>
        </div>
      )}

      {/* Main Content Layout: Split vs List vs Map */}
      {viewMode === "split" ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Provider Cards List */}
          <div className="lg:col-span-7 space-y-4">
            {isLoading ? (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="h-44 rounded-2xl bg-slate-100 animate-pulse border border-slate-200"
                  />
                ))}
              </div>
            ) : data && data.items.length > 0 ? (
              <div className="grid grid-cols-1 gap-4">
                {data.items.map((card) => (
                  <ProviderCardComponent
                    key={card.id}
                    card={card}
                    onSelect={handleSelectCard}
                    isSelected={selectedCard?.id === card.id}
                  />
                ))}
              </div>
            ) : (
              <EmptyStateView onReset={handleResetFilters} />
            )}
          </div>

          {/* Right Column: Sticky Interactive PostGIS Map */}
          <div className="lg:col-span-5 sticky top-24">
            <ProviderMapView
              items={data?.items || []}
              selectedCard={selectedCard}
              onSelectCard={handleSelectCard}
              userLat={filters.lat}
              userLon={filters.lon}
              radiusKm={filters.radiusKm}
            />
          </div>
        </div>
      ) : viewMode === "list" ? (
        <div className="space-y-4">
          {isLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div
                  key={i}
                  className="h-48 rounded-2xl bg-slate-100 animate-pulse border border-slate-200"
                />
              ))}
            </div>
          ) : data && data.items.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.items.map((card) => (
                <ProviderCardComponent
                  key={card.id}
                  card={card}
                  onSelect={handleSelectCard}
                  isSelected={selectedCard?.id === card.id}
                />
              ))}
            </div>
          ) : (
            <EmptyStateView onReset={handleResetFilters} />
          )}
        </div>
      ) : (
        /* Map-Only View */
        <div className="space-y-4">
          <ProviderMapView
            items={data?.items || []}
            selectedCard={selectedCard}
            onSelectCard={handleSelectCard}
            userLat={filters.lat}
            userLon={filters.lon}
            radiusKm={filters.radiusKm}
          />
        </div>
      )}

      {/* Pagination Controls */}
      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-4">
          <Button
            size="sm"
            variant="outline"
            disabled={page <= 1 || isLoading}
            onClick={() => {
              const prev = Math.max(page - 1, 1);
              setPage(prev);
              executeSearch(prev);
            }}
          >
            <ChevronLeft className="w-4 h-4 mr-1" />
            <span>Previous</span>
          </Button>

          <span className="text-xs text-slate-600 font-medium px-3">
            Page {page} of {data.total_pages}
          </span>

          <Button
            size="sm"
            variant="outline"
            disabled={page >= data.total_pages || isLoading}
            onClick={() => {
              const next = Math.min(page + 1, data.total_pages);
              setPage(next);
              executeSearch(next);
            }}
          >
            <span>Next</span>
            <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        </div>
      )}

      {/* Legal & Medical Disclaimer Footer */}
      <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-4 text-xs text-slate-500 leading-relaxed">
        <span className="font-bold text-slate-700">Notice: </span>
        {t.providers.disclaimer}
      </div>

      {/* Provider Details Dossier Modal */}
      <ProviderDetailModal
        card={selectedCard}
        isOpen={isDetailModalOpen}
        onClose={() => setIsDetailModalOpen(false)}
      />
    </div>
  );
}

function EmptyStateView({ onReset }: { onReset: () => void }) {
  const { t } = useLanguage();

  return (
    <div className="text-center py-12 px-4 bg-white rounded-2xl border border-slate-200/80 space-y-3">
      <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
        <MapPin className="w-6 h-6" />
      </div>
      <h3 className="font-bold text-slate-900 text-base">
        {t.providers.noResults}
      </h3>
      <p className="text-xs text-slate-500 max-w-md mx-auto">
        {t.providers.noResultsSub}
      </p>
      <div className="pt-2">
        <Button size="sm" variant="outline" onClick={onReset}>
          <RotateCcw className="w-3.5 h-3.5 mr-1" />
          <span>{t.providers.clearFilters}</span>
        </Button>
      </div>
    </div>
  );
}
