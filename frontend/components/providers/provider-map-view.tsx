"use client";

import React, { useState } from "react";
import {
  MapPin,
  Stethoscope,
  Building2,
  Navigation,
  ExternalLink,
  Layers,
  ZoomIn,
  ZoomOut,
  Info,
  ShieldCheck,
} from "lucide-react";
import { ApiProviderCard } from "@/lib/api";
import { Button } from "@/components/ui/button";

interface ProviderMapViewProps {
  items: ApiProviderCard[];
  selectedCard: ApiProviderCard | null;
  onSelectCard: (card: ApiProviderCard) => void;
  userLat?: number | null;
  userLon?: number | null;
  radiusKm?: number;
}

export function ProviderMapView({
  items,
  selectedCard,
  onSelectCard,
  userLat,
  userLon,
  radiusKm = 10,
}: ProviderMapViewProps) {
  const [zoomLevel, setZoomLevel] = useState(1);
  const [hoveredCard, setHoveredCard] = useState<ApiProviderCard | null>(null);

  // Compute bounding center or fallback to first item / Chennai default
  const centerLat =
    userLat ??
    (items.length > 0 ? items[0].latitude : 13.0604);
  const centerLon =
    userLon ??
    (items.length > 0 ? items[0].longitude : 80.2496);

  // Calculate relative pixel offsets for visual canvas projection
  const scale = 1400 * zoomLevel; // degrees to canvas pixels

  return (
    <div className="relative w-full h-[520px] rounded-2xl bg-slate-900 overflow-hidden border border-slate-800 shadow-inner flex flex-col justify-between select-none">
      {/* Background Cartographic Grid & Styling */}
      <div
        className="absolute inset-0 opacity-20 pointer-events-none"
        style={{
          backgroundImage: `
            radial-gradient(circle at 50% 50%, rgba(59, 130, 246, 0.15) 0%, transparent 60%),
            linear-gradient(to right, rgba(255,255,255,0.06) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(255,255,255,0.06) 1px, transparent 1px)
          `,
          backgroundSize: "100% 100%, 40px 40px, 40px 40px",
        }}
      />

      {/* Top Map Toolbar: Coordinates, Radius, Active Pin Count */}
      <div className="relative z-10 p-3 sm:p-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 bg-slate-800/90 backdrop-blur-md px-3 py-1.5 rounded-xl border border-slate-700/80 text-xs text-slate-300">
          <Layers className="w-3.5 h-3.5 text-blue-400 shrink-0" />
          <span className="font-semibold text-white">
            {items.length} Providers Plotted
          </span>
          <span className="text-slate-500">•</span>
          <span className="text-slate-400 font-mono text-[11px]">
            Radius: {radiusKm} km
          </span>
        </div>

        {/* Map Control Buttons: Zoom In, Zoom Out */}
        <div className="flex items-center gap-1.5 bg-slate-800/90 backdrop-blur-md p-1 rounded-xl border border-slate-700/80">
          <button
            type="button"
            onClick={() => setZoomLevel((prev) => Math.min(prev + 0.3, 2.5))}
            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
            title="Zoom In"
            aria-label="Zoom in"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => setZoomLevel((prev) => Math.max(prev - 0.3, 0.6))}
            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
            title="Zoom Out"
            aria-label="Zoom out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Interactive Map Visual Stage */}
      <div className="relative flex-1 w-full h-full overflow-hidden">
        {/* Center Origin Crosshair */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none">
          {/* User Location Pulse Marker */}
          {userLat !== null && userLat !== undefined && (
            <div className="relative flex items-center justify-center">
              <span className="absolute w-8 h-8 rounded-full bg-blue-500/25 animate-ping" />
              <div className="w-4 h-4 rounded-full bg-blue-500 border-2 border-white shadow-lg flex items-center justify-center">
                <div className="w-1.5 h-1.5 rounded-full bg-white" />
              </div>
              <span className="absolute top-5 whitespace-nowrap text-[10px] font-bold text-blue-300 bg-slate-900/80 px-2 py-0.5 rounded-md border border-slate-700">
                You are here
              </span>
            </div>
          )}
        </div>

        {/* Plot Provider Pins */}
        {items.map((item, index) => {
          // Relative coordinates from center
          const deltaLat = item.latitude - centerLat;
          const deltaLon = item.longitude - centerLon;

          // Convert to percent offset from center (50%, 50%)
          // Invert deltaLat because latitude increases northwards (up)
          const leftPercent = 50 + (deltaLon * scale) / 5;
          const topPercent = 50 - (deltaLat * scale) / 5;

          // Clamping to visible canvas with small margin
          const clampedLeft = Math.max(8, Math.min(92, leftPercent));
          const clampedTop = Math.max(12, Math.min(88, topPercent));

          const isSelected = selectedCard?.id === item.id;
          const isDoctor = item.card_type === "doctor";

          return (
            <div
              key={item.id}
              className="absolute -translate-x-1/2 -translate-y-full transition-transform duration-200 cursor-pointer"
              style={{
                left: `${clampedLeft}%`,
                top: `${clampedTop}%`,
                zIndex: isSelected ? 40 : 20,
              }}
              onClick={() => onSelectCard(item)}
              onMouseEnter={() => setHoveredCard(item)}
              onMouseLeave={() => setHoveredCard(null)}
            >
              {/* Marker Pin */}
              <div
                className={`relative group flex flex-col items-center transition-all ${
                  isSelected ? "scale-125 -translate-y-1" : "hover:scale-110"
                }`}
              >
                <div
                  className={`p-2 rounded-2xl shadow-lg border flex items-center justify-center text-white ${
                    isSelected
                      ? "bg-gradient-to-tr from-blue-600 to-cyan-500 border-white ring-4 ring-blue-500/30"
                      : isDoctor
                      ? "bg-blue-600 border-blue-400"
                      : "bg-cyan-600 border-cyan-400"
                  }`}
                >
                  {isDoctor ? (
                    <Stethoscope className="w-4 h-4" />
                  ) : (
                    <Building2 className="w-4 h-4" />
                  )}
                </div>

                {/* Pin Tip */}
                <div
                  className={`w-2 h-2 rotate-45 -mt-1 ${
                    isSelected
                      ? "bg-cyan-500"
                      : isDoctor
                      ? "bg-blue-600"
                      : "bg-cyan-600"
                  }`}
                />

                {/* Label on marker */}
                <div className="mt-1 whitespace-nowrap bg-slate-900/90 text-white text-[10px] font-semibold px-2 py-0.5 rounded-md border border-slate-700 shadow-md">
                  {item.title.split(" ")[0]}
                  {item.distance_km !== null && item.distance_km !== undefined
                    ? ` • ${item.distance_km.toFixed(1)}km`
                    : ""}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected / Hovered Card Quick-Preview Overlay */}
      {(hoveredCard || selectedCard) && (
        <div className="relative z-30 mx-4 mb-4 p-3.5 bg-slate-800/95 backdrop-blur-md rounded-xl border border-slate-700 text-white flex items-center justify-between gap-3 shadow-xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600/20 text-blue-400 border border-blue-500/30 flex items-center justify-center shrink-0">
              {(hoveredCard || selectedCard)?.card_type === "doctor" ? (
                <Stethoscope className="w-5 h-5" />
              ) : (
                <Building2 className="w-5 h-5" />
              )}
            </div>
            <div>
              <div className="font-bold text-sm text-white line-clamp-1">
                {(hoveredCard || selectedCard)?.title}
              </div>
              <div className="text-xs text-slate-400 line-clamp-1">
                {(hoveredCard || selectedCard)?.address_line}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {(hoveredCard || selectedCard)?.distance_km !== null && (
              <span className="text-xs font-mono font-bold text-cyan-400">
                {(hoveredCard || selectedCard)?.distance_km?.toFixed(1)} km
              </span>
            )}
            <a
              href={`https://www.openstreetmap.org/?mlat=${
                (hoveredCard || selectedCard)?.latitude
              }&mlon=${
                (hoveredCard || selectedCard)?.longitude
              }#map=16/${(hoveredCard || selectedCard)?.latitude}/${
                (hoveredCard || selectedCard)?.longitude
              }`}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-200"
              title="Open full interactive map on OpenStreetMap"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        </div>
      )}

      {/* Mandatory OpenStreetMap & PostGIS Attribution Banner */}
      <div className="relative z-10 px-4 py-2 bg-slate-950/90 border-t border-slate-800 flex flex-wrap items-center justify-between text-[11px] text-slate-400">
        <div className="flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>PostGIS Spatial Engine (EPSG:4326 WGS 84 Spheroid)</span>
        </div>
        <div>
          Map data ©{" "}
          <a
            href="https://www.openstreetmap.org/copyright"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-400 hover:underline"
          >
            OpenStreetMap contributors
          </a>{" "}
          (ODbL)
        </div>
      </div>
    </div>
  );
}
