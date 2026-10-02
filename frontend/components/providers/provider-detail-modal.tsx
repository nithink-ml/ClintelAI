"use client";

import React, { useEffect, useState } from "react";
import {
  X,
  Stethoscope,
  Building2,
  MapPin,
  Phone,
  Clock,
  Award,
  Globe,
  FileCheck2,
  Calendar,
  AlertTriangle,
  ExternalLink,
  ShieldCheck,
} from "lucide-react";
import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/ui/button";
import {
  api,
  ApiProviderCard,
  ApiDoctorDetail,
  ApiFacilityDetail,
} from "@/lib/api";
import { VerificationBadgeComponent } from "./verification-badge";

interface ProviderDetailModalProps {
  card: ApiProviderCard | null;
  isOpen: boolean;
  onClose: () => void;
}

export function ProviderDetailModal({
  card,
  isOpen,
  onClose,
}: ProviderDetailModalProps) {
  const [data, setData] = useState<{
    cardId: string | null;
    doc: ApiDoctorDetail | null;
    fac: ApiFacilityDetail | null;
  }>({ cardId: null, doc: null, fac: null });

  useEffect(() => {
    if (!isOpen || !card) {
      return;
    }

    let isMounted = true;

    if (card.card_type === "doctor") {
      api
        .getDoctorDetails(card.id)
        .then((doc) => {
          if (isMounted) setData({ cardId: card.id, doc, fac: null });
        })
        .catch((err) => console.warn("Failed to load doctor details:", err));
    } else {
      api
        .getFacilityDetails(card.id)
        .then((fac) => {
          if (isMounted) setData({ cardId: card.id, doc: null, fac });
        })
        .catch((err) => console.warn("Failed to load facility details:", err));
    }

    return () => {
      isMounted = false;
    };
  }, [isOpen, card]);

  if (!card) return null;

  const isDoctor = card.card_type === "doctor";
  const doctorDetail = data.cardId === card.id ? data.doc : null;
  const facilityDetail = data.cardId === card.id ? data.fac : null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={card.title}
      description={card.subtitle}
      className="max-w-2xl"
    >
      <div className="space-y-6 max-h-[75vh] overflow-y-auto pr-1">
        {/* Verification Status & Provenance Header */}
        <div className="bg-slate-50 border border-slate-200/90 rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Verification Status
            </div>
            <VerificationBadgeComponent badge={card.verification} />
          </div>

          {card.distance_km !== null && card.distance_km !== undefined && (
            <div className="text-right">
              <span className="text-xs text-slate-500">Proximity</span>
              <div className="text-sm font-bold font-mono text-blue-600">
                {card.distance_km.toFixed(1)} km away
              </div>
            </div>
          )}
        </div>

        {/* Synthetic Demo Warning */}
        {card.is_demo_data && (
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 text-xs text-amber-900 space-y-1">
            <div className="font-bold flex items-center gap-1.5 text-amber-800">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              <span>Simulated Verification Dataset</span>
            </div>
            <p className="text-amber-800 leading-relaxed font-medium">
              Simulated demonstration record. Do not use for actual clinical appointments or emergency care.
            </p>
          </div>
        )}

        {/* Doctor-Specific Details */}
        {isDoctor && (
          <div className="space-y-4">
            <h4 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-2">
              Professional Credentials
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                <span className="text-slate-500 font-medium">Primary Specialty</span>
                <div className="font-bold text-slate-900 mt-0.5 text-sm">
                  {doctorDetail?.primary_specialty || card.specialty || "General Medicine"}
                </div>
              </div>

              <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                <span className="text-slate-500 font-medium">Qualifications</span>
                <div className="font-bold text-slate-900 mt-0.5">
                  {doctorDetail?.qualifications || card.qualifications || "MBBS"}
                </div>
              </div>

              <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                <span className="text-slate-500 font-medium">Medical Registration Council</span>
                <div className="font-bold text-slate-900 mt-0.5">
                  {doctorDetail?.registration_council || "State Medical Council (Simulated)"}
                </div>
              </div>

              <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                <span className="text-slate-500 font-medium">Registration License No.</span>
                <div className="font-mono font-bold text-slate-900 mt-0.5">
                  {doctorDetail?.registration_number || "MC-TN-2016-DEMO"}
                </div>
              </div>
            </div>

            {/* Doctor Affiliated Clinics */}
            {doctorDetail?.affiliations && doctorDetail.affiliations.length > 0 && (
              <div className="space-y-2 pt-2">
                <span className="text-xs font-bold text-slate-800">
                  Affiliated Hospitals & Clinics
                </span>
                <div className="space-y-2">
                  {doctorDetail.affiliations.map((aff, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-xl border border-slate-200/80 bg-white flex items-center justify-between text-xs"
                    >
                      <div className="flex items-center gap-2.5">
                        <Building2 className="w-4 h-4 text-cyan-600 shrink-0" />
                        <div>
                          <div className="font-bold text-slate-900">
                            {aff.facility_name}
                          </div>
                          <div className="text-slate-500 capitalize">
                            {aff.facility_type} • {aff.role || "Consultant"}
                          </div>
                        </div>
                      </div>
                      {aff.schedule_summary && (
                        <span className="text-xs text-blue-600 font-medium bg-blue-50 px-2.5 py-1 rounded-md">
                          {aff.schedule_summary}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Facility-Specific Details */}
        {!isDoctor && (
          <div className="space-y-4">
            <h4 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-2">
              Facility Information & Schedule
            </h4>

            {card.emergency_services_available && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 flex items-center gap-2 text-rose-800 text-xs font-bold">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse shrink-0" />
                <span>24-Hour Emergency & Trauma Care Available</span>
              </div>
            )}

            {/* Operating Hours Table */}
            {card.operating_hours && (
              <div className="space-y-2">
                <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-blue-500" />
                  <span>Operating Hours</span>
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  {Object.entries(card.operating_hours).map(([day, hours]) => (
                    <div
                      key={day}
                      className="p-2 rounded-lg bg-slate-50 border border-slate-100 text-center"
                    >
                      <span className="font-semibold text-slate-500 capitalize text-[11px] block">
                        {day}
                      </span>
                      <span className="font-mono text-slate-800 text-[11px] mt-0.5 block">
                        {hours}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Address and Contact Information */}
        <div className="space-y-3 pt-2 border-t border-slate-100 text-xs text-slate-700">
          <div className="flex items-start gap-2">
            <MapPin className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-slate-900 block">Address</span>
              <span>{card.address_line}</span>
            </div>
          </div>

          {card.phone && (
            <div className="flex items-center gap-2">
              <Phone className="w-4 h-4 text-blue-500 shrink-0" />
              <div>
                <span className="font-bold text-slate-900 mr-2">Contact:</span>
                <a
                  href={`tel:${card.phone}`}
                  className="text-blue-600 font-semibold hover:underline"
                >
                  {card.phone}
                </a>
              </div>
            </div>
          )}
        </div>

        {/* Registry Provenance Metadata Card */}
        <div className="bg-slate-900 text-white rounded-2xl p-4 text-xs space-y-2">
          <div className="font-bold flex items-center justify-between text-slate-200 pb-1.5 border-b border-slate-800">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Registry Provenance & Verification Audit</span>
            </span>
            <span className="font-mono text-[10px] text-slate-400">
              Tier: {card.verification.tier}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] text-slate-300">
            <div>
              <span className="text-slate-500 block">Verification Source</span>
              <span className="font-medium text-slate-200">
                {card.verification.source || "National Registry"}
              </span>
            </div>
            <div>
              <span className="text-slate-500 block">Verification Method</span>
              <span className="font-mono text-slate-200">
                {card.verification.method || "REGISTRY_MATCH"}
              </span>
            </div>
          </div>
        </div>

        {/* Medical Disclaimer Banner */}
        <div className="text-[11px] text-slate-500 bg-slate-50 p-3 rounded-xl border border-slate-200/80 leading-relaxed">
          <span className="font-bold text-slate-700">Notice: </span>
          Directory listing does not constitute clinical endorsement. ClintelAI does not rank healthcare providers by skill. Always verify credentials independently. In medical emergencies, immediately dial 112 or 108.
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between pt-3 border-t border-slate-100">
          <a
            href={`https://www.openstreetmap.org/?mlat=${card.latitude}&mlon=${card.longitude}#map=16/${card.latitude}/${card.longitude}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-blue-600 transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            <span>Open in OpenStreetMap</span>
          </a>

          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={onClose}>
              Close
            </Button>
            {card.phone && (
              <a href={`tel:${card.phone}`}>
                <Button size="sm" className="bg-blue-600 hover:bg-blue-700 text-white">
                  <Phone className="w-3.5 h-3.5 mr-1" />
                  <span>Call Provider</span>
                </Button>
              </a>
            )}
          </div>
        </div>
      </div>
    </Modal>
  );
}
