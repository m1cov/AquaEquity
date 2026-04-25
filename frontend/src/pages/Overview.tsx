import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { FarmMap } from "@/components/FarmMap";
import { StatCard } from "@/components/StatCard";
import { useFarms } from "@/hooks/useFarmData";
import { Droplets, Leaf, Sprout, AlertTriangle } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import type { EnrichedFarm } from "@/hooks/useFarmData";
import { formatLiters } from "@/lib/irrigation";

export default function Overview() {
  const { data: farms = [], isLoading } = useFarms();
  const [selected, setSelected] = useState<EnrichedFarm | null>(null);

  const stats = useMemo(() => {
    if (!farms.length) return { count: 0, ndvi: 0, soil: 0, stressed: 0 };
    const ndviVals = farms.map((f) => f.ndvi).filter((v): v is number => v != null);
    const soilVals = farms.map((f) => f.soilMoisture).filter((v): v is number => v != null);
    return {
      count: farms.length,
      ndvi: ndviVals.length ? ndviVals.reduce((a, b) => a + b, 0) / ndviVals.length : 0,
      soil: soilVals.length ? soilVals.reduce((a, b) => a + b, 0) / soilVals.length : 0,
      stressed: farms.filter((f) => f.stress === "stressed").length,
    };
  }, [farms]);

  const byRegion = useMemo(() => {
    const map = new Map<string, EnrichedFarm[]>();
    farms.forEach((f) => {
      const arr = map.get(f.region) ?? [];
      arr.push(f);
      map.set(f.region, arr);
    });
    return Array.from(map.entries()).map(([region, list]) => {
      const ndviVals = list.map((f) => f.ndvi).filter((v): v is number => v != null);
      const soilVals = list.map((f) => f.soilMoisture).filter((v): v is number => v != null);
      return {
        region,
        farms: list.length,
        avgNdvi: ndviVals.length ? ndviVals.reduce((a, b) => a + b, 0) / ndviVals.length : 0,
        avgSoil: soilVals.length ? soilVals.reduce((a, b) => a + b, 0) / soilVals.length : 0,
        atRisk: list.filter((f) => f.stress !== "healthy").length,
      };
    });
  }, [farms]);

  return (
    <>
      {/* Hero */}
      <section className="bg-gradient-hero text-primary-foreground">
        <div className="container py-10 md:py-14">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 text-xs font-medium backdrop-blur">
              <span className="h-1.5 w-1.5 rounded-full bg-white animate-pulse" />
              Live Sentinel-2 + Open-Meteo
            </div>
            <h1 className="mt-4 text-3xl md:text-5xl font-semibold tracking-tight">
              Smart irrigation for North Macedonia
            </h1>
            <p className="mt-3 text-primary-foreground/85 text-base md:text-lg">
              Real-time crop stress and soil moisture insights help rural farmers
              irrigate efficiently and share water fairly.
            </p>
          </div>
        </div>
      </section>

      <section className="container -mt-8 md:-mt-10 relative z-10">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
          <StatCard label="Active farms" value={String(stats.count)} icon={Sprout} />
          <StatCard label="Avg NDVI" value={stats.ndvi ? stats.ndvi.toFixed(2) : "—"} hint="Crop health index" icon={Leaf} tone="healthy" />
          <StatCard label="Avg soil moisture" value={stats.soil ? `${stats.soil.toFixed(0)}%` : "—"} icon={Droplets} />
          <StatCard label="Farms at risk" value={String(stats.stressed)} hint="Stressed crops" icon={AlertTriangle} tone={stats.stressed ? "stressed" : "healthy"} />
        </div>
      </section>

      <section className="container py-8 md:py-10 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="mb-3 flex items-end justify-between">
            <div>
              <h2 className="text-lg font-semibold tracking-tight">Farm map</h2>
              <p className="text-sm text-muted-foreground">Color = crop stress level. Click a farm for details.</p>
            </div>
          </div>
          {isLoading ? (
            <Skeleton className="h-[520px] rounded-xl" />
          ) : (
            <FarmMap farms={farms} onSelect={setSelected} />
          )}

          <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
            <Legend color="hsl(145 60% 42%)" label="Healthy (NDVI ≥ 0.6)" />
            <Legend color="hsl(38 92% 50%)" label="Moderate (0.4–0.6)" />
            <Legend color="hsl(0 75% 52%)" label="Stressed (< 0.4)" />
          </div>
        </div>

        <div>
          <h2 className="text-lg font-semibold tracking-tight mb-3">Regions</h2>
          <div className="space-y-3">
            {byRegion.map((r) => (
              <Card key={r.region} className="p-4 bg-gradient-card">
                <div className="flex items-center justify-between">
                  <div className="font-medium">{r.region}</div>
                  <div className="text-xs text-muted-foreground">{r.farms} farm{r.farms !== 1 && "s"}</div>
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                  <Metric label="NDVI" value={r.avgNdvi ? r.avgNdvi.toFixed(2) : "—"} />
                  <Metric label="Soil" value={r.avgSoil ? `${r.avgSoil.toFixed(0)}%` : "—"} />
                  <Metric label="At risk" value={String(r.atRisk)} tone={r.atRisk ? "stressed" : "healthy"} />
                </div>
              </Card>
            ))}
            {!byRegion.length && !isLoading && (
              <Card className="p-6 text-sm text-muted-foreground">No farms yet.</Card>
            )}
          </div>
        </div>
      </section>

      {/* Detail drawer */}
      <Sheet open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <SheetContent className="w-full sm:max-w-md">
          {selected && (
            <>
              <SheetHeader>
                <SheetTitle>{selected.name}</SheetTitle>
              </SheetHeader>
              <div className="mt-4 space-y-3 text-sm">
                <Row label="Region" value={selected.region} />
                <Row label="Size" value={`${selected.size_ha} ha`} />
                <Row label="NDVI" value={selected.ndvi?.toFixed(2) ?? "—"} />
                <Row label="Soil moisture" value={selected.soilMoisture != null ? `${selected.soilMoisture.toFixed(0)}%` : "—"} />
                <Row label="Recommended water" value={formatLiters(selected.recommendedLiters)} />
                <Row label="Irrigation window" value={`${selected.windowStart} – ${selected.windowEnd}`} />
              </div>
              <Button asChild className="mt-6 w-full">
                <Link to="/dashboard">Open in dashboard</Link>
              </Button>
            </>
          )}
        </SheetContent>
      </Sheet>
    </>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="h-3 w-3 rounded-sm" style={{ background: color }} />
      <span>{label}</span>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: "healthy" | "stressed" }) {
  const cls = tone === "stressed" ? "text-[hsl(var(--stressed))]" : tone === "healthy" ? "text-[hsl(var(--healthy))]" : "text-foreground";
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className={`mt-0.5 font-semibold tabular-nums ${cls}`}>{value}</div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b pb-2 last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium tabular-nums">{value}</span>
    </div>
  );
}
