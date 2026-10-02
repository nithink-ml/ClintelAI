"use client";

import React from "react";
import {
  Stethoscope,
  Building2,
  MapPin,
  Phone,
  Clock,
  Award,
  ExternalLink,
  ChevronRight,
  AlertTriangle,
} from "lucide-react";
import { ApiProviderCard } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { VerificationBadgeComponent } from "./verification-badge";

interface ProviderCardProps {
  card: ApiProviderCard;
  onSelect: (card: ApiProviderCard) => void;
  isSelected?: boolean;
}

export function ProviderCardComponent({ card, onSelect, isSelected }: ProviderCardProps) {
  const isDoctor = card.card_type === "doctor";

  return (
    <Card
      className={`transition-all duration-200 border overflow-hidden ${
        isSelected
          ? "border-blue-500 shadow-md ring-2 ring-blue-500/20"
          : "border-slate-200/90 hover:border-blue-300 hover:shadow-sm"
      }`}
    >
      <CardContent className="p-5 flex flex-col justify-between h-full space-y-4">
        {/* Top Header: Icon, Title, and Verification Badge */}
        <div className="space-y-2.5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <div
                className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 ${
                  isDoctor
                    ? "bg-blue-50 text-blue-600 border border-blue-100"
                    : "bg-cyan-50 text-cyan-600 border border-cyan-100"
                }`}
              >
                {isDoctor ? (
                  <Stethoscope className="w-5 h-5" />
                ) : (
                  <Building2 className="w-5 h-5" />
                )}
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-base leading-snug line-clamp-1">
                  {card.title}
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  {isDoctor
                    ? card.facility_name || card.subtitle
                    : card.subtitle}
                </p>
              </div>
            </div>

            {/* Distance Pill if available */}
            {card.distance_km !== null && card.distance_km !== undefined && (
              <span className="shrink-0 inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 text-xs font-bold border border-blue-100 font-mono">
                <MapPin className="w-3 h-3 text-blue-600" />
                <span>{card.distance_km.toFixed(1)} km</span>
              </span>
            )}
          </div>

          {/* Verification Badge with Provenance */}
          <div>
            <VerificationBadgeComponent badge={card.verification} />
          </div>
        </div>

        {/* Middle Metadata: Specialty, Qualifications, Address, Emergency Status */}
        <div className="space-y-2 text-xs text-slate-600">
          {/* Medical Specialty & Qualifications for Doctors */}
          {isDoctor && (
            <div className="flex flex-wrap items-center gap-1.5 pt-1">
              {card.specialty && (
                <span className="px-2 py-0.5 rounded-md bg-blue-100/70 text-blue-800 font-semibold text-[11px]">
                  {card.specialty}
                </span>
              )}
              {card.qualifications && (
                <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-medium text-[11px] flex items-center gap-1">
                  <Award className="w-3 h-3 text-slate-500" />
                  <span>{card.qualifications}</span>
                </span>
              )}
              {card.experience_years && (
                <span className="text-slate-500 text-[11px]">
                  • {card.experience_years} yrs exp
                </span>
              )}
            </div>
          )}

          {/* Address Line */}
          <div className="flex items-start gap-1.5 text-slate-600">
            <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
            <span className="line-clamp-2 leading-relaxed">
              {card.address_line}
            </span>
          </div>

          {/* Emergency Availability Indicator */}
          {card.emergency_services_available && (
            <div className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded-md border border-rose-200">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
              <span>24/7 Emergency Care Available</span>
            </div>
          )}

          {/* Operating hours note if present */}
          {card.operating_hours && (
            <div className="flex items-center gap-1 text-[11px] text-slate-500">
              <Clock className="w-3 h-3 text-slate-400 shrink-0" />
              <span>Standard OPD: Open Today</span>
            </div>
          )}
        </div>

        {/* Demo Warning Pill */}
        {card.is_demo_data && (
          <div className="bg-amber-50/70 border border-amber-200/80 rounded-lg px-2.5 py-1.5 text-[10px] text-amber-900 flex items-center gap-1.5 leading-tight font-medium">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
            <span>Simulated demonstration record. Do not use for actual clinical appointments or emergency care.</span>
          </div>
        )}

        {/* Bottom Actions: View Details, Directions, Call */}
        <div className="pt-2 border-t border-slate-100 flex items-center justify-between gap-2">
          {card.phone ? (
            <a
              href={`tel:${card.phone}`}
              className="inline-flex items-center gap-1 text-xs font-semibold text-slate-700 hover:text-blue-600 transition-colors py-1.5 px-2 rounded-lg hover:bg-slate-100"
            >
              <Phone className="w-3.5 h-3.5 text-blue-500" />
              <span>{card.phone}</span>
            </a>
          ) : (
            <span className="text-[11px] text-slate-400 italic">No phone listed</span>
          )}

          <div className="flex items-center gap-1.5">
            <a
              href={`https://www.openstreetmap.org/?mlat=${card.latitude}&mlon=${card.longitude}#map=16/${card.latitude}/${card.longitude}`}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              title="Open location on OpenStreetMap"
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
            <Button
              size="sm"
              variant="outline"
              onClick={() => onSelect(card)}
              className="text-xs font-semibold text-blue-600 hover:text-blue-700 hover:bg-blue-50/80 border-blue-200"
            >
              <span>Profile</span>
              <ChevronRight className="w-3 h-3 ml-0.5" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
