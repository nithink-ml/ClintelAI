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
};
