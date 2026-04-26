import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import {
  recommendedLiters,
  recommendedWindow,
  stressFromNdvi,
  type StressLevel,
} from "@/lib/irrigation";

export interface Farm {
  id: string;
  name: string;
  region: string;
  owner_name: string;
  size_ha: number;
  latitude: number;
  longitude: number;
  water_quota_liters: number;
  crop_name?: string;
  soil_type?: string;
  top_left_x?: number | null;
  top_left_y?: number | null;
  top_right_x?: number | null;
  top_right_y?: number | null;
  bottom_left_x?: number | null;
  bottom_left_y?: number | null;
  bottom_right_x?: number | null;
  bottom_right_y?: number | null;
}

export interface FarmReading {
  id: string;
  farm_id: string;
  ndvi: number | null;
  soil_moisture_pct: number | null;
  recommended_water_liters: number | null;
  recommended_window_start: string | null;
  recommended_window_end: string | null;
  stress_level: string | null;
  fetched_at: string;
}

export interface AlertRow {
  id: string;
  farm_id: string | null;
  message: string;
  severity: string;
  channel: string;
  status: string;
  created_at: string;
}

export interface EnrichedFarm extends Farm {
  ndvi: number | null;
  soilMoisture: number | null;
  stress: StressLevel;
  recommendedLiters: number;
  windowStart: string;
  windowEnd: string;
  history: FarmReading[];
  lastReadingAt: string | null;
}

const REFRESH_MS = 5 * 60 * 1000;

async function triggerRefresh() {
  try {
    await api.refreshFarms();
  } catch (e) {
    // Non-fatal: the cached readings will still load below.
    console.warn("/farms/refresh failed", e);
  }
}

export function useFarms() {
  return useQuery({
    queryKey: ["farms-enriched"],
    refetchInterval: REFRESH_MS,
    queryFn: async (): Promise<EnrichedFarm[]> => {
      // Best-effort: ask the backend to refresh, then read.
      await triggerRefresh();

      const [farms, readings] = await Promise.all([
        api.listFarms(),
        api.listAllReadings(),
      ]);

      // Group readings per farm, newest-first (backend already sorts desc).
      const readingsByFarm = new Map<string, FarmReading[]>();
      for (const r of readings) {
        const list = readingsByFarm.get(r.farm_id) ?? [];
        list.push(r);
        readingsByFarm.set(r.farm_id, list);
      }

      return farms.map((f) => {
        const history = readingsByFarm.get(f.id) ?? [];
        const latest = history[0];
        const ndvi = latest?.ndvi ?? null;
        const soil = latest?.soil_moisture_pct ?? null;
        const liters =
          latest?.recommended_water_liters ?? recommendedLiters(soil, ndvi, f.size_ha);
        const win =
          latest?.recommended_window_start && latest?.recommended_window_end
            ? { start: latest.recommended_window_start, end: latest.recommended_window_end }
            : recommendedWindow(liters);
        return {
          ...f,
          ndvi,
          soilMoisture: soil,
          stress: (latest?.stress_level as StressLevel) || stressFromNdvi(ndvi),
          recommendedLiters: liters,
          windowStart: win.start,
          windowEnd: win.end,
          history,
          lastReadingAt: latest?.fetched_at ?? null,
        };
      });
    },
  });
}

export function useAlerts() {
  return useQuery({
    queryKey: ["alerts"],
    refetchInterval: REFRESH_MS,
    queryFn: () => api.listAlerts(),
  });
}
