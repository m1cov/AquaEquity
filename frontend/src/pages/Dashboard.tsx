import { useMemo, useState } from "react";
import { useFarms } from "@/hooks/useFarmData";
import { FarmCard } from "@/components/FarmCard";
import { AddFarmDialog } from "@/components/AddFarmDialog";
import { AttentionToday } from "@/components/AttentionToday";
import { useAuth } from "@/hooks/useAuth";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Droplets, Leaf, Sprout, RefreshCw, User } from "lucide-react";
import { formatLiters } from "@/lib/irrigation";
import { useQueryClient } from "@tanstack/react-query";
import type { EnrichedFarm } from "@/hooks/useFarmData";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function Dashboard() {
  const { data: allFarms = [], isLoading, isFetching } = useFarms();
  const { user } = useAuth();
  const qc = useQueryClient();
  const [details, setDetails] = useState<EnrichedFarm | null>(null);

  const farms = useMemo(
    () => allFarms.filter((f) => f.owner_name === user?.username),
    [allFarms, user?.username],
  );

  const summary = useMemo(() => {
    const totalHa = farms.reduce((s, f) => s + Number(f.size_ha), 0);
    const totalQuota = farms.reduce((s, f) => s + Number(f.water_quota_liters), 0);
    const totalRec = farms.reduce((s, f) => s + f.recommendedLiters, 0);
    return { totalHa, totalQuota, totalRec, used: Math.min(100, (totalRec / Math.max(1, totalQuota)) * 100) };
  }, [farms]);

  const farmer = user?.username ?? farms[0]?.owner_name ?? "Farmer";

  return (
    <div className="container py-8 space-y-6">
      {/* Farmer panel */}
      <Card className="p-6 bg-gradient-card shadow-elev-sm">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="h-14 w-14 rounded-full bg-gradient-hero grid place-items-center text-primary-foreground shadow-elev-md">
              <User className="h-7 w-7" />
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-muted-foreground">Farmer</div>
              <div className="text-xl font-semibold tracking-tight">{farmer}</div>
              <div className="text-sm text-muted-foreground mt-0.5">
                {farms.length} fields · {summary.totalHa.toFixed(1)} ha
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-6 md:max-w-xl flex-1">
            <Mini icon={<Sprout className="h-4 w-4" />} label="Fields" value={String(farms.length)} />
            <Mini icon={<Leaf className="h-4 w-4" />} label="Avg NDVI" value={
              farms.length
                ? (farms.map(f => f.ndvi ?? 0).reduce((a, b) => a + b, 0) / farms.length).toFixed(2)
                : "—"
            } />
            <Mini icon={<Droplets className="h-4 w-4" />} label="Today's plan" value={formatLiters(summary.totalRec)} />
          </div>

          <Button
            variant="outline"
            onClick={() => qc.invalidateQueries({ queryKey: ["farms-enriched"] })}
            disabled={isFetching}
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>

        <div className="mt-5">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-1.5">
            <span>Water quota usage (today vs allocation)</span>
            <span className="tabular-nums">{formatLiters(summary.totalRec)} / {formatLiters(summary.totalQuota)}</span>
          </div>
          <Progress value={summary.used} className="h-2.5" />
        </div>

        <div className="mt-5 flex justify-end">
          <AddFarmDialog defaultOwner={farmer} />
        </div>
      </Card>

      {/* Attention today */}
      {!isLoading && farms.length > 0 && <AttentionToday farms={farms} />}

      {/* Farm grid */}
      <div>
        <div className="flex items-end justify-between mb-3">
          <div>
            <h2 className="text-lg font-semibold tracking-tight">Your fields</h2>
            <p className="text-sm text-muted-foreground">Per-field crop health, soil moisture and irrigation plan.</p>
          </div>
        </div>
        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-72 rounded-xl" />)}
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {farms.map((f) => <FarmCard key={f.id} farm={f} onDetails={setDetails} />)}
          </div>
        )}
      </div>

      <Dialog open={!!details} onOpenChange={(o) => !o && setDetails(null)}>
        <DialogContent className="max-w-2xl">
          {details && (
            <>
              <DialogHeader>
                <DialogTitle>{details.name}</DialogTitle>
              </DialogHeader>
              <div className="grid gap-4">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <Stat label="Region" value={details.region} />
                  <Stat label="Size" value={`${details.size_ha} ha`} />
                  <Stat label="Crop type" value={details.crop_name ?? "—"} />
                  <Stat label="Soil type" value={details.soil_type ?? "—"} />
                  <Stat label="NDVI" value={details.ndvi?.toFixed(2) ?? "—"} />
                  <Stat label="Soil moisture" value={details.soilMoisture != null ? `${details.soilMoisture.toFixed(0)}%` : "—"} />
                  <Stat label="Recommended water" value={formatLiters(details.recommendedLiters)} />
                  <Stat label="Window" value={`${details.windowStart} – ${details.windowEnd}`} />
                </div>
                <Card className="p-4">
                  <div className="text-sm font-medium mb-2">NDVI history</div>
                  <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={[...details.history].reverse().map((r, i) => ({
                        i, ndvi: Number(r.ndvi ?? 0), soil: Number(r.soil_moisture_pct ?? 0),
                      }))}>
                        <defs>
                          <linearGradient id="ndvi-d" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.4} />
                            <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" />
                        <XAxis dataKey="i" tick={{ fontSize: 10 }} />
                        <YAxis domain={[0, 1]} tick={{ fontSize: 10 }} />
                        <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid hsl(var(--border))" }} />
                        <Area dataKey="ndvi" stroke="hsl(var(--primary))" fill="url(#ndvi-d)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Mini({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-muted-foreground inline-flex items-center gap-1">{icon}{label}</div>
      <div className="mt-1 text-lg font-semibold tabular-nums">{value}</div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border p-3">
      <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 font-medium tabular-nums">{value}</div>
    </div>
  );
}
