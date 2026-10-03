/**
 * ClintelAI Backend REST API Client
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface ApiTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface ApiProfile {
  id: string;
  user_id: string;
  full_name: string;
  date_of_birth?: string | null;
  gender?: string | null;
  phone_number?: string | null;
  blood_group?: string | null;
  city?: string | null;
  state?: string | null;
  pincode?: string | null;
}

export interface ApiPreferences {
  id: string;
  user_id: string;
  preferred_language: "en" | "ta" | "hi" | "ml" | "te" | "kn";
  theme: "light" | "dark" | "system";
  emergency_alerts_enabled: boolean;
  location_sharing_enabled: boolean;
}

export interface ApiEmergencyContact {
  id: string;
  user_id: string;
  name: string;
  relationship: string;
  phone_number: string;
  is_primary: boolean;
  created_at: string;
}

export interface ApiUserDetail {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  profile?: ApiProfile | null;
  preferences?: ApiPreferences | null;
  emergency_contacts?: ApiEmergencyContact[];
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const errorMsg =
      data.detail ||
      (Array.isArray(data.detail) ? data.detail[0]?.msg : null) ||
      `HTTP Error ${response.status}`;
    throw new Error(errorMsg);
  }

  return data as T;
}

export const api = {
  // Auth
  register: (payload: {
    email: string;
    password: string;
    full_name: string;
    preferred_language?: string;
  }) => request<ApiTokenResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  }),

  login: (payload: { email: string; password: string }) =>
    request<ApiTokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  refresh: (refreshToken: string) =>
    request<ApiTokenResponse>("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    }),

  logout: (refreshToken: string, token: string) =>
    request<{ detail: string }>("/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    }, token),

  getMe: (token: string) =>
    request<ApiUserDetail>("/auth/me", { method: "GET" }, token),

  // Profile
  updateProfile: (payload: Partial<ApiProfile>, token: string) =>
    request<ApiProfile>("/users/me/profile", {
      method: "PUT",
      body: JSON.stringify(payload),
    }, token),

  // Preferences
  updatePreferences: (payload: Partial<ApiPreferences>, token: string) =>
    request<ApiPreferences>("/users/me/preferences", {
      method: "PUT",
      body: JSON.stringify(payload),
    }, token),

  // Emergency Contacts
  getEmergencyContacts: (token: string) =>
    request<ApiEmergencyContact[]>("/users/me/emergency-contacts", { method: "GET" }, token),

  addEmergencyContact: (
    payload: { name: string; relationship: string; phone_number: string; is_primary: boolean },
    token: string
  ) =>
    request<ApiEmergencyContact>("/users/me/emergency-contacts", {
      method: "POST",
      body: JSON.stringify(payload),
    }, token),

  deleteEmergencyContact: (id: string, token: string) =>
    request<{ detail: string }>(`/users/me/emergency-contacts/${id}`, {
      method: "DELETE",
    }, token),

  // Phase 3: Provider Discovery & Verification
  searchProviders: (params: {
    query?: string;
    lat?: number;
    lon?: number;
    radius_km?: number;
    city?: string;
    state?: string;
    specialty?: string;
    provider_type?: string;
    verification_status?: string;
    open_now?: boolean;
    page?: number;
    page_size?: number;
    language?: string;
  }) => {
    const searchParams = new URLSearchParams();
    if (params.query) searchParams.append("query", params.query);
    if (params.lat !== undefined && params.lat !== null) searchParams.append("lat", params.lat.toString());
    if (params.lon !== undefined && params.lon !== null) searchParams.append("lon", params.lon.toString());
    if (params.radius_km !== undefined) searchParams.append("radius_km", params.radius_km.toString());
    if (params.city) searchParams.append("city", params.city);
    if (params.state) searchParams.append("state", params.state);
    if (params.specialty) searchParams.append("specialty", params.specialty);
    if (params.provider_type) searchParams.append("provider_type", params.provider_type);
    if (params.verification_status) searchParams.append("verification_status", params.verification_status);
    if (params.open_now !== undefined) searchParams.append("open_now", params.open_now.toString());
    if (params.page) searchParams.append("page", params.page.toString());
    if (params.page_size) searchParams.append("page_size", params.page_size.toString());
    if (params.language) searchParams.append("language", params.language);

    const queryStr = searchParams.toString();
    return request<ApiProviderSearchResponse>(`/providers/search${queryStr ? `?${queryStr}` : ""}`, {
      method: "GET",
    });
  },

  getNearbyProviders: (params: {
    lat: number;
    lon: number;
    radius_km?: number;
    specialty?: string;
    provider_type?: string;
    page?: number;
    page_size?: number;
    language?: string;
  }) => {
    const searchParams = new URLSearchParams();
    searchParams.append("lat", params.lat.toString());
    searchParams.append("lon", params.lon.toString());
    if (params.radius_km) searchParams.append("radius_km", params.radius_km.toString());
    if (params.specialty) searchParams.append("specialty", params.specialty);
    if (params.provider_type) searchParams.append("provider_type", params.provider_type);
    if (params.page) searchParams.append("page", params.page.toString());
    if (params.page_size) searchParams.append("page_size", params.page_size.toString());
    if (params.language) searchParams.append("language", params.language);

    return request<ApiProviderSearchResponse>(`/providers/nearby?${searchParams.toString()}`, {
      method: "GET",
    });
  },

  getSpecialties: () =>
    request<ApiSpecialtiesResponse>("/providers/specialties", { method: "GET" }),

  getFacilityDetails: (facilityId: string) =>
    request<ApiFacilityDetail>(`/providers/facilities/${facilityId}`, { method: "GET" }),

  getDoctorDetails: (doctorId: string) =>
    request<ApiDoctorDetail>(`/providers/doctors/${doctorId}`, { method: "GET" }),

  geocodeLocation: (query: string) =>
    request<ApiGeocodeResult>(`/providers/geocode?query=${encodeURIComponent(query)}`, {
      method: "GET",
    }),

  // Regional Health Alerts
  searchAlerts: (params: {
    query?: string;
    lat?: number | null;
    lon?: number | null;
    state?: string;
    district?: string;
    city?: string;
    category?: string;
    severity?: string;
    status?: string;
    language?: string;
    page?: number;
    page_size?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params.query) searchParams.append("query", params.query);
    if (params.lat !== undefined && params.lat !== null) searchParams.append("lat", params.lat.toString());
    if (params.lon !== undefined && params.lon !== null) searchParams.append("lon", params.lon.toString());
    if (params.state) searchParams.append("state", params.state);
    if (params.district) searchParams.append("district", params.district);
    if (params.city) searchParams.append("city", params.city);
    if (params.category) searchParams.append("category", params.category);
    if (params.severity) searchParams.append("severity", params.severity);
    if (params.status) searchParams.append("status", params.status);
    if (params.language) searchParams.append("language", params.language);
    if (params.page) searchParams.append("page", params.page.toString());
    if (params.page_size) searchParams.append("page_size", params.page_size.toString());

    return request<ApiHealthAlertSearchResponse>(`/alerts/search?${searchParams.toString()}`, {
      method: "GET",
    });
  },

  getAlertDetail: (alertId: string, language?: string) => {
    const searchParams = new URLSearchParams();
    if (language) searchParams.append("language", language);
    return request<ApiHealthAlertDetail>(`/alerts/${alertId}?${searchParams.toString()}`, {
      method: "GET",
    });
  },

  getAlertMetadata: () =>
    request<ApiAlertMetadataResponse>("/alerts/meta/categories", { method: "GET" }),

  syncCanonicalAlerts: (token: string) =>
    request<{ status: string; message: string; stats: any }>("/alerts/sync", {
      method: "POST",
    }, token),
};

export interface ApiVerificationBadge {
  status: "VERIFIED" | "PARTIALLY_VERIFIED" | "UNVERIFIED" | "DEMO_SIMULATED";
  tier: string;
  effective_status: "VERIFIED" | "PARTIALLY_VERIFIED" | "UNVERIFIED" | "DEMO_SIMULATED";
  effective_tier?: string;
  simulated_target_status?: string | null;
  simulated_target_tier?: string | null;
  label: string;
  description: string;
  source?: string | null;
  method?: string | null;
  verified_at?: string | null;
  is_demo_data: boolean;
}

export interface ApiProviderCard {
  card_type: "doctor" | "facility";
  id: string;
  title: string;
  subtitle: string;
  facility_name?: string | null;
  facility_type?: string | null;
  specialty?: string | null;
  qualifications?: string | null;
  experience_years?: number | null;
  address_line: string;
  city: string;
  state: string;
  latitude: number;
  longitude: number;
  distance_km?: number | null;
  phone?: string | null;
  emergency_services_available: boolean;
  languages_spoken?: string[];
  operating_hours?: Record<string, string> | null;
  verification: ApiVerificationBadge;
  effective_status?: string;
  is_demo_data: boolean;
}

export interface ApiEmergencyEscalation {
  is_emergency: boolean;
  level: "CRITICAL" | "HIGH";
  symptoms_detected: string[];
  action_message: string;
  emergency_numbers: string[];
}

export interface ApiProviderSearchResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: ApiProviderCard[];
  emergency_escalation?: ApiEmergencyEscalation | null;
  applied_filters: Record<string, any>;
  disclaimer: string;
}

export interface ApiSpecialtyItem {
  specialty: string;
  count: number;
}

export interface ApiSpecialtiesResponse {
  specialties: ApiSpecialtyItem[];
}

export interface ApiFacilityDetail {
  id: string;
  name: string;
  facility_type: string;
  address: {
    address_line1: string;
    address_line2?: string | null;
    locality?: string | null;
    city: string;
    state: string;
    pincode: string;
    country: string;
  };
  location: {
    latitude: number;
    longitude: number;
  };
  distance_km?: number | null;
  phone?: string | null;
  emergency_phone?: string | null;
  email?: string | null;
  website?: string | null;
  operating_hours?: Record<string, any> | null;
  emergency_services_available: boolean;
  verification: ApiVerificationBadge;
  effective_status?: string;
  is_demo_data: boolean;
  source_name: string;
  source_url?: string | null;
  affiliated_doctors?: any[];
  created_at: string;
  updated_at: string;
}

export interface ApiDoctorDetail {
  id: string;
  full_name: string;
  gender?: string | null;
  qualifications: string;
  primary_specialty: string;
  secondary_specialties: string[];
  registration_number?: string | null;
  registration_council?: string | null;
  experience_years?: number | null;
  languages_spoken: string[];
  consultation_fee?: number | null;
  bio?: string | null;
  verification: ApiVerificationBadge;
  effective_status?: string;
  is_demo_data: boolean;
  source_name: string;
  source_url?: string | null;
  affiliations: Array<{
    facility_id: string;
    facility_name: string;
    facility_type: string;
    role?: string | null;
    schedule_summary?: string | null;
  }>;
  created_at: string;
  updated_at: string;
}

export interface ApiGeocodeResult {
  query: string;
  display_name: string;
  latitude: number;
  longitude: number;
  city?: string | null;
  state?: string | null;
  country: string;
  provider: string;
  attribution: string;
}

export interface ApiFreshnessStatus {
  status: "FRESH" | "RECENT" | "STALE" | "EXPIRED";
  age_hours: number;
  last_verified_at: string;
  notice: string;
}

export interface ApiHealthAlertSummary {
  id: string;
  title: string;
  summary: string;
  category: string;
  severity: "CRITICAL" | "HIGH" | "MODERATE" | "LOW" | "INFORMATIONAL";
  status: "ACTIVE" | "EXPIRED" | "DRAFT" | "INFORMATIONAL";
  source_name: string;
  source_url: string;
  source_reference_id?: string | null;
  issued_at: string;
  valid_from: string;
  valid_until?: string | null;
  country: string;
  state?: string | null;
  district?: string | null;
  city?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  affected_radius_km?: number | null;
  distance_km?: number | null;
  freshness: ApiFreshnessStatus;
  is_demo_data: boolean;
}

export interface ApiHealthAlertDetail extends ApiHealthAlertSummary {
  content: string;
  locality?: string | null;
  symptoms: string[];
  precautionary_measures: string[];
  helpline_numbers: string[];
  translations?: Record<string, any> | null;
  provenance_audit?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface ApiHealthAlertSearchResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: ApiHealthAlertSummary[];
  critical_active_count: number;
  emergency_escalation?: ApiEmergencyEscalation | null;
  applied_filters: Record<string, any>;
  disclaimer: string;
}

export interface ApiAlertMetadataResponse {
  categories: string[];
  severities: string[];
  statuses: string[];
}


