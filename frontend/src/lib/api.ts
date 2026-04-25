/**
 * AquaField API client.
 *
 * Replaces the previous Supabase integration. All requests go through a
 * thin typed `fetch` wrapper that adds a base URL, sets JSON headers, and
 * surfaces a useful error message for non-2xx responses.
 */
import type { AlertRow, Farm, FarmReading } from "@/hooks/useFarmData";

const API_BASE_URL =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ??
  "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) message = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      // ignore parse errors; fall back to status text
    }
    throw new ApiError(res.status, message);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  // ---------- Farms ----------
  listFarms: () => request<Farm[]>("/farms/"),
  listAllReadings: () => request<FarmReading[]>("/farms/readings/all"),
  refreshFarms: () =>
    request<{ refreshed_farms: number; new_readings: number; new_alerts: number }>(
      "/farms/refresh",
      { method: "POST" },
    ),

  // ---------- Alerts ----------
  listAlerts: () => request<AlertRow[]>("/alerts/?limit=100"),
  sendAlert: (payload: {
    farm_id: string | null;
    message: string;
    severity?: "info" | "warning" | "critical";
    channel?: string;
  }) =>
    request<AlertRow>("/alerts/send", {
      method: "POST",
      body: JSON.stringify({
        channel: "sms",
        status: "simulated",
        ...payload,
      }),
    }),

  // ---------- Estimator (EKF) ----------
  getEkfDemo: ({ days = 10, soilType = "loam" }: { days?: number; soilType?: string } = {}) => {
    const params = new URLSearchParams({ days: String(days), soil_type: soilType });
    return request<EkfDemoResponse>(`/estimates/demo?${params.toString()}`);
  },
  listSoilTypes: () => request<{ soil_types: string[] }>("/estimates/soil-types/list"),
  listCrops: () => request<{ default_crop_keys: string[]; crops: EkfCrop[] }>("/estimates/crops/list"),
};

export { ApiError, API_BASE_URL };

// ---------- Types for EKF demo ----------
export interface EkfDayRow {
  day: number;
  crop: string;
  display_name: string;
  soil_type: string;
  rain_mm: number;
  ndvi: number;
  et0_mm: number;
  et0_std_mm: number;
  irrigation_mm: number;
  x_pred_mm: number;
  P_pred: number;
  measurement_mm: number | null;
  moisture_std_mm: number | null;
  satellite_available: boolean;
  updated: boolean;
  soil_water_estimate_mm: number;
  uncertainty: number;
  relative_available_water: number;
  stress_level: "low" | "moderate" | "high" | "critical";
  kalman_gain: number | null;
  innovation: number | null;
}

export interface EkfScenario {
  crop: string;
  display_name: string;
  soil_type: string;
  days: number;
  auto_irrigate: boolean;
  parameters: {
    theta_fc_mm: number;
    theta_wp_mm: number;
    theta_max_mm: number;
    irrigation_trigger_mm: number;
    max_irrigation_mm_day: number;
  };
  crop_parameters: {
    kc_initial: number;
    kc_mid: number;
    kc_late: number;
    depletion_fraction_p: number;
    root_depth_m: number;
    default_ndvi: number;
    notes: string;
    source_url: string;
  };
  history: EkfDayRow[];
  final: EkfDayRow | null;
}

export interface EkfDemoResponse {
  title: string;
  unit_note: string;
  weather_assumption: string;
  method_note: string;
  available_crops: EkfCrop[];
  available_soil_types: string[];
  measurement_days: number[];
  scenarios: EkfScenario[];
}

export interface EkfCrop {
  key: string;
  display_name: string;
  kc_initial: number;
  kc_mid: number;
  kc_late: number;
  depletion_fraction_p: number;
  root_depth_m: number;
  default_ndvi: number;
  notes: string;
  source_url: string;
}
