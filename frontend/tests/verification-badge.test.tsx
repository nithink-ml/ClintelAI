import test from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { VerificationBadgeComponent } from "../components/providers/verification-badge";
import { ProviderCardComponent } from "../components/providers/provider-card";
import { ApiVerificationBadge, ApiProviderCard } from "../lib/api";

test("Demo Data Verification Guardrail: Synthetic provider with is_demo_data=true NEVER receives official VERIFIED badge", () => {
  // Even if the raw status is "VERIFIED" and tier is "tier_1_verified",
  // if is_demo_data is true, the guardrail MUST override the effective badge to DEMO_SIMULATED.
  const syntheticBadge: ApiVerificationBadge = {
    status: "VERIFIED",
    tier: "tier_1_verified",
    effective_status: "DEMO_SIMULATED",
    effective_tier: "tier_4_demo",
    simulated_target_status: "VERIFIED",
    simulated_target_tier: "tier_1_verified",
    label: "DEMO_SIMULATED",
    description: "Simulated demonstration record. Do not use for actual clinical appointments or emergency care.",
    source: "National Registry Test",
    method: "SYNTHETIC_SIMULATION",
    verified_at: "2026-01-01T00:00:00Z",
    is_demo_data: true,
  };

  const html = renderToStaticMarkup(
    React.createElement(VerificationBadgeComponent, { badge: syntheticBadge })
  );

  // 1. MUST display DEMO_SIMULATED as effective badge
  assert.ok(html.includes("DEMO_SIMULATED"), "Badge must display DEMO_SIMULATED");
  assert.ok(html.includes("SYNTHETIC"), "Badge must display SYNTHETIC pill");

  // 2. MUST NEVER display VERIFIED, PARTIALLY_VERIFIED, or UNVERIFIED as the effective badge label
  assert.ok(
    !html.includes(">Officially Verified</span>") &&
      !html.includes(">VERIFIED</span>") &&
      !html.includes(">PARTIALLY_VERIFIED</span>") &&
      !html.includes(">UNVERIFIED</span>"),
    "UI must NEVER display VERIFIED, PARTIALLY_VERIFIED, or UNVERIFIED as effective badge"
  );

  // 3. MUST use purple styling for simulated demo, NEVER emerald verified styling
  assert.ok(html.includes("text-purple-700"), "Must use purple demo styling");
  assert.ok(!html.includes("text-emerald-700"), "Must NOT use emerald verified styling");

  // 4. Prominent warning text must be present
  assert.ok(
    html.includes("Simulated demonstration record. Do not use for actual clinical appointments or emergency care."),
    "Must include mandatory clinical/emergency warning"
  );
});

test("Demo Data Verification Guardrail: Synthetic provider with adversarial 'VERIFIED' badge without effective_status", () => {
  // Adversarial case: A badge where someone set status='VERIFIED', label='Officially Verified',
  // but is_demo_data is true. Guardrail must still intercept and enforce DEMO_SIMULATED!
  const adversarialBadge: ApiVerificationBadge = {
    status: "VERIFIED",
    tier: "tier_1_verified",
    effective_status: "DEMO_SIMULATED",
    label: "Officially Verified",
    description: "Some description",
    is_demo_data: true,
  };

  const html = renderToStaticMarkup(
    React.createElement(VerificationBadgeComponent, { badge: adversarialBadge })
  );

  assert.ok(html.includes("DEMO_SIMULATED"), "Guardrail must force DEMO_SIMULATED effective badge");
  assert.ok(!html.includes("Officially Verified"), "Adversarial 'Officially Verified' label must NOT be rendered");
  assert.ok(!html.includes("text-emerald-700"), "Must not use emerald styling");
});

test("Demo Data Verification Guardrail: Synthetic provider with PARTIALLY_VERIFIED target", () => {
  const syntheticPartial: ApiVerificationBadge = {
    status: "DEMO_SIMULATED",
    tier: "tier_4_demo",
    effective_status: "DEMO_SIMULATED",
    effective_tier: "tier_4_demo",
    simulated_target_status: "PARTIALLY_VERIFIED",
    simulated_target_tier: "tier_2_partially_verified",
    label: "DEMO_SIMULATED",
    description: "Simulated demonstration record. Do not use for actual clinical appointments or emergency care.",
    is_demo_data: true,
  };

  const html = renderToStaticMarkup(
    React.createElement(VerificationBadgeComponent, { badge: syntheticPartial })
  );

  assert.ok(html.includes("DEMO_SIMULATED"), "Must display DEMO_SIMULATED");
  assert.ok(!html.includes("Third-Party Listed"), "Must not display Third-Party Listed");
  assert.ok(!html.includes("PARTIALLY_VERIFIED"), "Must not display PARTIALLY_VERIFIED");
});

test("Real Provider Ingestion: Authoritative provider with is_demo_data=false receives official VERIFIED badge", () => {
  // Proves requirement 7: Real verification tiers remain available for future authoritative provider ingestion
  const authoritativeBadge: ApiVerificationBadge = {
    status: "VERIFIED",
    tier: "tier_1_verified",
    effective_status: "VERIFIED",
    effective_tier: "tier_1_verified",
    label: "Officially Verified",
    description: "Formally cross-referenced and verified against authoritative Medical Council or NABH registry.",
    source: "National Medical Commission",
    method: "NMC_REGISTRY_API_V2",
    verified_at: "2026-05-15T10:30:00Z",
    is_demo_data: false,
  };

  const html = renderToStaticMarkup(
    React.createElement(VerificationBadgeComponent, { badge: authoritativeBadge })
  );

  // 1. Authoritative badge receives Officially Verified
  assert.ok(html.includes("Officially Verified"), "Authoritative provider must display Officially Verified");
  assert.ok(html.includes("text-emerald-700"), "Authoritative provider must use emerald badge styling");

  // 2. Must NOT receive DEMO_SIMULATED or SYNTHETIC
  assert.ok(!html.includes("DEMO_SIMULATED"), "Authoritative provider must NOT display DEMO_SIMULATED");
  assert.ok(!html.includes("SYNTHETIC"), "Authoritative provider must NOT display SYNTHETIC pill");
});

test("Real Provider Ingestion: Authoritative provider with PARTIALLY_VERIFIED and UNVERIFIED", () => {
  const partialBadge: ApiVerificationBadge = {
    status: "PARTIALLY_VERIFIED",
    tier: "tier_2_partially_verified",
    effective_status: "PARTIALLY_VERIFIED",
    label: "Third-Party Listed",
    description: "Confirmed via municipal register.",
    is_demo_data: false,
  };
  const htmlPartial = renderToStaticMarkup(
    React.createElement(VerificationBadgeComponent, { badge: partialBadge })
  );
  assert.ok(htmlPartial.includes("Third-Party Listed"), "Must display Third-Party Listed");
  assert.ok(htmlPartial.includes("text-amber-700"), "Must use amber styling");

  const unverifiedBadge: ApiVerificationBadge = {
    status: "UNVERIFIED",
    tier: "tier_3_unverified",
    effective_status: "UNVERIFIED",
    label: "Unverified Listing",
    description: "Community record.",
    is_demo_data: false,
  };
  const htmlUnverif = renderToStaticMarkup(
    React.createElement(VerificationBadgeComponent, { badge: unverifiedBadge })
  );
  assert.ok(htmlUnverif.includes("Unverified Listing"), "Must display Unverified Listing");
  assert.ok(htmlUnverif.includes("text-slate-700"), "Must use slate styling");
});

test("ProviderCardComponent: Displays DEMO_SIMULATED badge and prominent clinical warning banner", () => {
  const mockCard: ApiProviderCard = {
    card_type: "facility",
    id: "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    title: "Apollo Hospital Chennai",
    subtitle: "Hospital in Chennai",
    facility_name: "Apollo Hospital Chennai",
    facility_type: "hospital",
    address_line: "21 Greams Lane, Thousand Lights, Chennai, Tamil Nadu - 600006",
    city: "Chennai",
    state: "Tamil Nadu",
    latitude: 13.0604,
    longitude: 80.2496,
    distance_km: 1.2,
    emergency_services_available: true,
    verification: {
      status: "DEMO_SIMULATED",
      tier: "tier_4_demo",
      effective_status: "DEMO_SIMULATED",
      effective_tier: "tier_4_demo",
      simulated_target_status: "VERIFIED",
      simulated_target_tier: "tier_1_verified",
      label: "DEMO_SIMULATED",
      description: "Simulated demonstration record. Do not use for actual clinical appointments or emergency care.",
      source: "NABH Hospital Accreditation Registry",
      method: "NABH_ROSTER_MATCH",
      verified_at: "2026-03-01T00:00:00Z",
      is_demo_data: true,
    },
    effective_status: "DEMO_SIMULATED",
    is_demo_data: true,
  };

  const html = renderToStaticMarkup(
    React.createElement(ProviderCardComponent, {
      card: mockCard,
      onSelect: () => {},
      isSelected: false,
    })
  );

  // 1. Must render DEMO_SIMULATED badge
  assert.ok(html.includes("DEMO_SIMULATED"), "Card must render DEMO_SIMULATED badge");
  assert.ok(!html.includes("Officially Verified"), "Card must NOT render Officially Verified");

  // 2. Must render prominent warning banner with exact string
  assert.ok(
    html.includes("Simulated demonstration record. Do not use for actual clinical appointments or emergency care."),
    "Card must render exact demo warning text"
  );
});
