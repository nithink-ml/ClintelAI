# Phase 4: Regional Health Alerts & Epidemiological Surveillance Architecture

## 1. Overview & System Boundaries

The Regional Health Alerts module (`backend/app/alerts/` and `frontend/components/alerts/`) is designed as an isolated bounded context within ClintelAI. It delivers official, verified public health advisories, outbreak bulletins, seasonal hazard notices, and environmental warnings to citizens across India.

### Core Architectural Guardrails
1. **Trusted Source Only**: Health alerts originate strictly from accredited government health ministries (MoHFW), statutory bodies (NCDC, ICMR, CPCB, IMD), global agencies (WHO), or official State Health Directorates. Social media, blogs, or unverified community submissions are categorically rejected.
2. **Non-Diagnostic Policy**: Health alerts are public health intelligence notices and explicitly do **not** constitute individualized clinical diagnosis or personalized medical advice. Every response and UI view includes a non-diagnostic disclaimer.
3. **Emergency Red-Flag Interception**: If a user's alert search query includes acute or life-threatening symptoms (e.g., crushing chest pain, difficulty breathing, massive hemorrhage), the system activates Phase 2 clinical safety boundaries and returns immediate emergency escalation directives (Dial 112 / 108).
4. **Demo Data Verification Guardrail**: The current canonical alert dataset is marked with `is_demo_data=True` and flagged as simulated demonstration records.
5. **Privacy Safeguard**: Geospatial searches using GPS coordinates (`lat`, `lon`) calculate distances in-memory via PostGIS and never write raw coordinates into persistent audit logs.

---

## 2. Trusted Public Health Source Catalog

| Authority / Agency | Scope | Official Domain / Pattern | Typical Advisories |
| :--- | :--- | :--- | :--- |
| **MoHFW** (Ministry of Health and Family Welfare) | National (ALL_INDIA) | `mohfw.gov.in` | National immunization campaigns (MR, Polio), seasonal guidelines |
| **NCDC** (National Centre for Disease Control) | National / Inter-State | `ncdc.gov.in` | Outbreak surveillance (Cholera, Influenza, Zoonoses) |
| **WHO** (World Health Organization - SEARO / India) | Global / Regional | `who.int` | Global health emergencies, Nipah containment protocols |
| **State Health Directorates** (e.g., TN-DPH, DHS Kerala, Karnataka Health) | State / District | `dph.tn.gov.in`, `dhs.kerala.gov.in`, `karnataka.gov.in` | Local vector-borne advisories (Dengue, Chikungunya), heatwave red alerts |
| **CPCB / IMD** (Central Pollution Control Board / Meteorological Dept) | Regional / Metro | `cpcb.nic.in`, `imd.gov.in` | Severe AQI smog warnings, extreme heatwave directives |

### Source Validation Filter Rules
The backend validates incoming alert creation payloads against `HealthAlertService.validate_trusted_source()`:
- Rejects URLs containing `twitter.com`, `x.com`, `facebook.com`, `instagram.com`, `reddit.com`, `t.me`, `whatsapp`, `blogspot`, `wordpress`, `unverified`.
- Requires the source name or source URL to match accredited institutional health authority patterns.

---

## 3. Geospatial Matching & National Scope Propagation

Regional matching uses PostgreSQL PostGIS spatial indexes and administrative hierarchy fallback:

```sql
-- Spatial Proximity Matching (Radius in meters)
ST_DWithin(
    CAST(health_alerts.geom AS geography),
    CAST(ST_SetSRID(ST_MakePoint(user_lon, user_lat), 4326) AS geography),
    coalesce(health_alerts.affected_radius_km, 50.0) * 1000.0
)
```

### National Scope Propagation Rule
Alerts with `state IS NULL` or `UPPER(state) = 'ALL_INDIA'` (such as National Measles-Rubella immunization campaigns or pandemic alerts) automatically match **all** queries across India regardless of the user's specific state, district, or GPS coordinate.

---

## 4. Temporal Freshness Evaluation Matrix

Because public health alerts in current architecture are synced periodically rather than via automated streaming webhooks, every alert is assigned a deterministic `FreshnessStatus`:

| Status | Age Window | Clinical Context & Action Directive |
| :--- | :--- | :--- |
| `FRESH` | $< 24$ hours | Fresh bulletin published recently. Highly relevant active guidelines. |
| `RECENT` | $24\text{h} - 7\text{d}$ | Active health advisory published within the past week. |
| `STALE` | $> 7$ days | Published over a week ago. Users are advised to verify active status with primary source. |
| `EXPIRED` | Past `valid_until` | Past scheduled validity date or archived advisory. Kept for historical surveillance. |

---

## 5. Multilingual Translation & Syndication

ClintelAI supports 6 languages: **English (`en`)**, **Tamil (`ta`)**, **Hindi (`hi`)**, **Malayalam (`ml`)**, **Telugu (`te`)**, and **Kannada (`kn`)**.
- Stored in the `translations` JSON column of `health_alerts`.
- Contains translated `title`, `summary`, `content`, and `precautionary_measures`.
- In search and detail endpoints, specifying `?language=<code>` dynamically localizes text while falling back gracefully to English if specific keys are absent.

---

## 6. External Feeds, API Integration & Production Ingestion

For production deployments connecting to live government RSS feeds and APIs:

| Feed Provider | Feed Type / Protocol | Recommended Poll Interval | Rate Limit / Quota |
| :--- | :--- | :--- | :--- |
| **MoHFW RSS Bulletin** | RSS 2.0 XML / HTTPS | 30 minutes | 60 req/hour per IP |
| **CPCB AQI Real-Time API** | REST JSON / OAuth2 | 15 minutes | 120 req/hour |
| **WHO Disease Outbreak News** | Atom Feed / HTTPS | 60 minutes | Standard web scraping etiquette |
| **State Health Surveillance (IDSP)** | Periodic JSON Bulletin | 60 minutes | Institutional API key required |

### Ingestion Pipeline Architecture (Production Recommendation)
1. **Airflow / Celery Cron Worker**: Polls allowlisted government feeds at recommended intervals.
2. **Schema Ingestion Gate**: Validates source domain, parses spatial geometry, sanitizes text.
3. **Translation Worker**: Automatically runs Indic translation pipelines (Bhashini API / Google Cloud Translation) into Tamil, Hindi, Malayalam, Telugu, and Kannada.
4. **Audit Logger**: Records `HEALTH_ALERT_INGESTED` event into `audit_logs` table.

---

## 7. Role-Based Access Control (RBAC)

- **Search & Detail (`GET /api/v1/alerts/search`, `GET /api/v1/alerts/{id}`)**: Publicly accessible.
- **Ingestion (`POST /api/v1/alerts`)**: Restricted to `admin` and `health_authority` roles.
- **Updates (`PATCH /api/v1/alerts/{id}`)**: Restricted to `admin` and `health_authority` roles.
- **Canonical Synchronization (`POST /api/v1/alerts/sync`)**: Restricted to `admin` role.
