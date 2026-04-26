import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, Droplets, MapPin, Clock, CloudRain, Cloud, Sun, CloudSun } from "lucide-react";
import type { EnrichedFarm } from "@/hooks/useFarmData";
import { formatLiters } from "@/lib/irrigation";
import { canonicalRegionName, regionCoord } from "@/lib/regionCoords";

interface ForecastDay {
  date: string;
  tMax: number;
  tMin: number;
  precip: number;
  code: number;
}

async function fetchForecast(lat: number, lon: number): Promise<ForecastDay[]> {
  const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=auto&forecast_days=5`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("forecast failed");
  const j = await res.json();
  const d = j.daily;
  return d.time.map((date: string, i: number) => ({
    date,
    tMax: d.temperature_2m_max[i],
    tMin: d.temperature_2m_min[i],
    precip: d.precipitation_sum[i],
    code: d.weathercode[i],
  }));
}

function weatherIcon(code: number, precip: number) {
  if (precip >= 1 || (code >= 51 && code <= 82)) return CloudRain;
  if (code >= 1 && code <= 3) return CloudSun;
  if (code >= 45) return Cloud;
  return Sun;
}

function dayLabel(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { weekday: "short" });
}

function AttentionCard({ farm }: { farm: EnrichedFarm }) {
  const normalizedRegion = canonicalRegionName(farm.region);
  const { lat, lon } = regionCoord(farm.region);
  const { data: forecast, isLoading } = useQuery({
    queryKey: ["forecast-region", normalizedRegion],
    queryFn: () => fetchForecast(lat, lon),
    staleTime: 30 * 60 * 1000,
  });

  const todayRain = forecast?.[0]?.precip ?? 0;
  const skipIrrigation = todayRain >= 2;

  return (
    <Card className="p-5 bg-gradient-card shadow-elev-sm flex flex-col gap-4">
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-semibold text-base leading-tight truncate">{farm.name}</h3>
          <div className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
            <MapPin className="h-3 w-3" />
            <span>{farm.region}</span>
          </div>
        </div>
        <Badge variant="outline" className="bg-[hsl(var(--stressed)/0.15)] text-[hsl(var(--stressed))] border-transparent">
          Needs attention
        </Badge>
      </header>

      <div
        className={`rounded-lg border p-4 ${
          skipIrrigation
            ? "bg-[hsl(var(--healthy)/0.1)] border-[hsl(var(--healthy)/0.3)]"
            : "bg-[hsl(var(--stressed)/0.1)] border-[hsl(var(--stressed)/0.3)]"
        }`}
      >
        {skipIrrigation ? (
          <>
            <div className="inline-flex items-center gap-2 font-semibold text-[hsl(var(--healthy))]">
              <CloudRain className="h-4 w-4" />
              SKIP IRRIGATION TODAY
            </div>
            <div className="mt-1 text-xs text-muted-foreground">
              {todayRain.toFixed(1)} mm rain expected — no irrigation needed.
            </div>
          </>
        ) : (
          <>
            <div className="inline-flex items-center gap-2 font-semibold text-[hsl(var(--stressed))]">
              <Droplets className="h-4 w-4" />
              IRRIGATE TODAY at {farm.windowStart}
            </div>
            <div className="mt-1.5 flex items-center justify-between text-xs">
              <span className="inline-flex items-center gap-1 text-muted-foreground">
                <Clock className="h-3 w-3" /> {farm.windowStart} – {farm.windowEnd}
              </span>
              <span className="tabular-nums font-semibold">{formatLiters(farm.recommendedLiters)}</span>
            </div>
          </>
        )}

        <div className="mt-4 rounded-md border bg-card/60 p-2.5">
          <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-2">
            5-day forecast
          </div>
          {isLoading || !forecast ? (
            <div className="h-14 animate-pulse rounded bg-muted/40" />
          ) : (
            <div className="grid grid-cols-5 gap-1.5">
              {forecast.map((d) => {
                const Icon = weatherIcon(d.code, d.precip);
                const rainy = d.precip >= 1;
                return (
                  <div
                    key={d.date}
                    className={`flex flex-col items-center rounded p-1.5 text-center ${
                      rainy ? "bg-[hsl(var(--primary)/0.08)]" : ""
                    }`}
                  >
                    <div className="text-[10px] text-muted-foreground">{dayLabel(d.date)}</div>
                    <Icon className={`h-4 w-4 my-1 ${rainy ? "text-primary" : "text-muted-foreground"}`} />
                    <div className="text-[10px] font-medium tabular-nums">{Math.round(d.tMax)}°</div>
                    {d.precip > 0 && (
                      <div className="text-[9px] text-primary tabular-nums">{d.precip.toFixed(1)}mm</div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

export function AttentionToday({ farms }: { farms: EnrichedFarm[] }) {
  const needsAttention = farms.filter((f) => f.stress !== "healthy" || (f.soilMoisture ?? 100) < 35);

  return (
    <Card className="p-6 bg-gradient-card shadow-elev-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-[hsl(var(--stressed)/0.15)] grid place-items-center text-[hsl(var(--stressed))]">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div>
            <div className="text-xs uppercase tracking-wide text-muted-foreground">Attention today</div>
            <div className="text-xl font-semibold tracking-tight tabular-nums">
              {needsAttention.length} {needsAttention.length === 1 ? "field needs" : "fields need"} attention
            </div>
          </div>
        </div>
      </div>

      {needsAttention.length === 0 ? (
        <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
          All your fields are healthy today. No irrigation action required.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {needsAttention.map((f) => (
            <AttentionCard key={f.id} farm={f} />
          ))}
        </div>
      )}
    </Card>
  );
}
