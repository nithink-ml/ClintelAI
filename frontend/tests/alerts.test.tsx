import test from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  SeverityBadge,
  FreshnessBadge,
  CategoryBadge,
  DemoAlertGuardrailBadge,
} from "../components/alerts/alert-badge";
import { AlertCard } from "../components/alerts/alert-card";
import { AlertDetailModal } from "../components/alerts/alert-detail-modal";
import { ApiHealthAlertSummary, ApiFreshnessStatus } from "../lib/api";

test("Phase 4: SeverityBadge renders all public health urgency levels correctly", () => {
  // CRITICAL
  const critHtml = renderToStaticMarkup(
    React.createElement(SeverityBadge, { severity: "CRITICAL" })
  );
  assert.ok(critHtml.includes("CRITICAL HAZARD"), "Must render CRITICAL HAZARD");
  assert.ok(critHtml.includes("bg-red-100"), "Must have red styling");

  // HIGH
  const highHtml = renderToStaticMarkup(
    React.createElement(SeverityBadge, { severity: "HIGH" })
  );
  assert.ok(highHtml.includes("HIGH ALERT"), "Must render HIGH ALERT");
  assert.ok(highHtml.includes("bg-amber-100"), "Must have amber styling");

  // MODERATE
  const modHtml = renderToStaticMarkup(
    React.createElement(SeverityBadge, { severity: "MODERATE" })
  );
  assert.ok(modHtml.includes("MODERATE ADVISORY"), "Must render MODERATE ADVISORY");

  // LOW
  const lowHtml = renderToStaticMarkup(
    React.createElement(SeverityBadge, { severity: "LOW" })
  );
  assert.ok(lowHtml.includes("PREVENTIVE NOTICE"), "Must render PREVENTIVE NOTICE");

  // INFORMATIONAL
  const infoHtml = renderToStaticMarkup(
    React.createElement(SeverityBadge, { severity: "INFORMATIONAL" })
  );
  assert.ok(infoHtml.includes("INFORMATIONAL"), "Must render INFORMATIONAL");
});

test("Phase 4: FreshnessBadge accurately renders temporal freshness statuses", () => {
  const freshStatus: ApiFreshnessStatus = {
    status: "FRESH",
    age_hours: 4.5,
    last_verified_at: "2026-10-03T00:00:00Z",
    notice: "Fresh bulletin published within the last 24 hours.",
  };
  const freshHtml = renderToStaticMarkup(
    React.createElement(FreshnessBadge, { freshness: freshStatus })
  );
  assert.ok(freshHtml.includes("Fresh Bulletin"), "Must render Fresh Bulletin");
  assert.ok(freshHtml.includes("bg-emerald-50"), "Must have emerald fresh styling");

  const staleStatus: ApiFreshnessStatus = {
    status: "STALE",
    age_hours: 192.0,
    last_verified_at: "2026-10-03T00:00:00Z",
    notice: "Advisory was issued more than 7 days ago.",
  };
  const staleHtml = renderToStaticMarkup(
    React.createElement(FreshnessBadge, { freshness: staleStatus })
  );
  assert.ok(staleHtml.includes("Stale Bulletin"), "Must render Stale Bulletin");

  const expiredStatus: ApiFreshnessStatus = {
    status: "EXPIRED",
    age_hours: 720.0,
    last_verified_at: "2026-10-03T00:00:00Z",
    notice: "Past scheduled validity date.",
  };
  const expHtml = renderToStaticMarkup(
    React.createElement(FreshnessBadge, { freshness: expiredStatus })
  );
  assert.ok(expHtml.includes("Archived / Expired"), "Must render Archived / Expired");
});

test("Phase 4: DemoAlertGuardrailBadge enforces mandatory synthetic demonstration notice", () => {
  const html = renderToStaticMarkup(
    React.createElement(DemoAlertGuardrailBadge, {})
  );
  assert.ok(html.includes("DEMO RECORD:"), "Must include DEMO RECORD flag");
  assert.ok(
    html.includes("Simulated demonstration dataset. Verify with official state health directorates for actual clinical care."),
    "Must include mandatory non-clinical warning"
  );
});

test("Phase 4: AlertCard renders complete bulletin metadata, trusted source, and guardrails", () => {
  const mockAlert: ApiHealthAlertSummary = {
    id: "11111111-1111-4111-a111-111111111111",
    title: "Dengue & Monsoon Vector-Borne Epidemiological Advisory",
    summary: "State Health Department issues high-vigilance notice for vector-borne dengue transmission across Chennai.",
    category: "infectious_disease",
    severity: "HIGH",
    status: "ACTIVE",
    source_name: "Tamil Nadu Directorate of Public Health (TN-DPH)",
    source_url: "https://dph.tn.gov.in/alerts/dengue",
    issued_at: "2026-09-28T09:00:00Z",
    valid_from: "2026-09-28T09:00:00Z",
    valid_until: "2026-10-31T23:59:59Z",
    country: "India",
    state: "Tamil Nadu",
    district: "Chennai",
    city: "Chennai",
    latitude: 13.0827,
    longitude: 80.2707,
    affected_radius_km: 35.0,
    distance_km: 4.2,
    freshness: {
      status: "RECENT",
      age_hours: 120.0,
      last_verified_at: "2026-10-03T00:00:00Z",
      notice: "Active health advisory published within the past 7 days.",
    },
    is_demo_data: true,
  };

  const html = renderToStaticMarkup(
    React.createElement(AlertCard, {
      alert: mockAlert,
      onSelect: () => {},
    })
  );

  assert.ok(html.includes("Dengue &amp; Monsoon Vector-Borne Epidemiological Advisory"), "Card must render title");
  assert.ok(html.includes("Tamil Nadu Directorate of Public Health (TN-DPH)"), "Card must show accredited authority");
  assert.ok(html.includes("https://dph.tn.gov.in/alerts/dengue"), "Card must have official bulletin URL");
  assert.ok(html.includes("Chennai, Tamil Nadu"), "Card must display locality/state");
  assert.ok(html.includes("4.2 km away"), "Card must display distance if near user");
  assert.ok(html.includes("HIGH ALERT"), "Card must display severity badge");
  assert.ok(html.includes("DEMO RECORD:"), "Card must enforce Demo Alert Guardrail flag");
});

test("Phase 4: AlertDetailModal renders clinical precautions, helplines, and non-diagnostic disclaimer", () => {
  const mockAlert: ApiHealthAlertSummary = {
    id: "22222222-2222-4222-a222-222222222222",
    title: "Nipah Virus Surveillance and Containment Advisory",
    summary: "Immediate containment protocols and epidemiological surveillance activated in Kozhikode district.",
    category: "outbreak",
    severity: "CRITICAL",
    status: "ACTIVE",
    source_name: "Directorate of Health Services Kerala (DHS Kerala)",
    source_url: "https://dhs.kerala.gov.in/alerts/nipah",
    issued_at: "2026-09-30T06:00:00Z",
    valid_from: "2026-09-30T06:00:00Z",
    valid_until: "2026-10-15T23:59:59Z",
    country: "India",
    state: "Kerala",
    district: "Kozhikode",
    city: "Kozhikode",
    affected_radius_km: 25.0,
    freshness: {
      status: "RECENT",
      age_hours: 72.0,
      last_verified_at: "2026-10-03T00:00:00Z",
      notice: "Active health advisory published within the past 7 days.",
    },
    is_demo_data: true,
  };

  const html = renderToStaticMarkup(
    React.createElement(AlertDetailModal, {
      summaryAlert: mockAlert,
      language: "en",
      onClose: () => {},
    })
  );

  // 1. Mandatory title and severity
  assert.ok(html.includes("Nipah Virus Surveillance"), "Modal must render advisory title");
  assert.ok(html.includes("CRITICAL HAZARD"), "Modal must render CRITICAL HAZARD badge");

  // 2. Issuing authority
  assert.ok(html.includes("Directorate of Health Services Kerala (DHS Kerala)"), "Must render official issuing body");

  // 3. Mandatory Non-Diagnostic Disclaimer
  assert.ok(
    html.includes("Regional health alerts provide official public health advisories from accredited government and global health agencies. They do not constitute individualized clinical diagnosis or personalized medical advice."),
    "Modal must contain mandatory non-diagnostic clinical disclaimer"
  );
  assert.ok(html.includes("112 / 108"), "Disclaimer must reference 112 / 108");
});
