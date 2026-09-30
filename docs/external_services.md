# External Services, Integrations & Limitations

This document outlines the external services, APIs, data sources, and their operational limitations in ClintelAI.

---

## 1. LLM & Embedding Providers

### Supported Providers
- **Google Gemini (Default)**: `gemini-1.5-flash` / `gemini-1.5-pro` via `google-generativeai` SDK.
- **OpenAI**: `gpt-4o-mini` / `gpt-4o` via `openai` SDK.
- **Local / Mock Provider (`LLM_PROVIDER=mock`)**: Built-in deterministic mock provider for testing and offline execution.

### Limitations & Fallbacks
- **Rate Limits**: Free tier Gemini/OpenAI API keys are subject to strict RPM/TPM limits. The backend handles `429 Too Many Requests` by queuing requests and gracefully returning an informative advisory to the user.
- **Network Outage**: If the LLM provider is unreachable, the system falls back to a safe message asking the user to retry or consult a doctor directly.
- **Data Privacy**: No patient identifiers (names, phone numbers, exact addresses) are ever passed in prompts. Only sanitized health questions and retrieved allowlisted chunks are sent to the LLM.

---

## 2. Maps, Geocoding & Places Services

### Supported Providers
- **OpenStreetMap / Nominatim (Default - Open Source)**:
  - Free, no API key required.
  - Rate limit: 1 request/second per Nominatim Usage Policy.
  - Used for reverse geocoding and standard tile rendering with Leaflet.
- **Mapbox / Google Places (Optional)**:
  - Enabled when `MAPBOX_ACCESS_TOKEN` or `GOOGLE_MAPS_API_KEY` is provided.

### Limitations
- **Discovery vs. Verification**: Inclusion of a clinic or doctor on OpenStreetMap or Google Places does **NOT** constitute medical verification, qualification check, or real-time appointment availability.
- All third-party map places are strictly assigned **Tier 2 (Third-Party Listing)** or **Tier 3 (Unverified)**.

---

## 3. Official Health Authorities & Source Allowlist

### Allowlisted Authorities
1. **World Health Organization (WHO)** (`who.int`)
2. **Indian Council of Medical Research (ICMR)** (`icmr.gov.in`)
3. **Ministry of Health and Family Welfare, Government of India (MoHFW)** (`mohfw.gov.in`)
4. **National Centre for Disease Control (NCDC)** (`ncdc.mohfw.gov.in`)
5. **State Health Departments** (Official `.gov.in` portals)
6. **PubMed Central / NCBI** (`ncbi.nlm.nih.gov`)

### Limitations & Scraping Policy
- Scraped/ingested only through official public feeds, open APIs, and public PDFs.
- Restricted or copyright-gated sites are strictly prohibited from the ingestion crawler.
- Chunks are timestamped and re-verified. Content older than official revision cycles is flagged for review.

---

## 4. Medical Registries & Doctor Verification Tiers

### Official Registries (Tier 1 Target)
- **National Medical Commission (NMC) - Indian Medical Register**
- **State Medical Councils (e.g., Tamil Nadu, Karnataka, Maharashtra Medical Councils)**
- **Ayushman Bharat Digital Mission (ABDM) Healthcare Professional Registry (HPR)**

### Limitations
- Direct real-time API access to the NMC register or ABDM requires official institutional authorization and credentials.
- In demo/development environments, ClintelAI utilizes a verified mock registry containing explicitly labeled demo records with synthetic registration IDs.
- **Crucial Rule**: A verified registration confirms qualifications at the time of registration, but does NOT guarantee current clinic open hours, live bed availability, or instantaneous appointment slots.
