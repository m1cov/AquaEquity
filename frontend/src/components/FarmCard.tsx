import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Droplets, Leaf, Clock, MapPin, ArrowRight } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";
import type { EnrichedFarm } from "@/hooks/useFarmData";
import { formatLiters } from "@/lib/irrigation";

const stressBadge: Record<EnrichedFarm["stress"], { label: string; cls: string }> = {
  healthy: { label: "Healthy", cls: "bg-[hsl(var(--healthy)/0.15)] text-[hsl(var(--healthy))] border-transparent" },
  moderate: { label: "Moderate", cls: "bg-[hsl(var(--moderate)/0.15)] text-[hsl(var(--moderate))] border-transparent" },
  stressed: { label: "Stressed", cls: "bg-[hsl(var(--stressed)/0.15)] text-[hsl(var(--stressed))] border-transparent" },
};

export function FarmCard({ farm, onDetails }: { farm: EnrichedFarm; onDetails?: (f: EnrichedFarm) => void }) {
  const sb = stressBadge[farm.stress];
  const trend = [...farm.history].slice(0, 7).reverse().map((r, i) => ({
    i,
    ndvi: Number(r.ndvi ?? 0),
  }));
  // Ensure chart has at least 2 points
  if (trend.length < 2) {
    const v = farm.ndvi ?? 0.5;
    trend.push({ i: 0, ndvi: v }, { i: 1, ndvi: v });
  }
  const moisturePct = Math.min(100, Math.max(0, farm.soilMoisture ?? 0));

  return (
    <Card className="p-5 bg-gradient-card shadow-elev-sm hover:shadow-elev-md transition-shadow flex flex-col gap-4">
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-semibold text-base leading-tight truncate">{farm.name}</h3>
          <div className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground flex-wrap">
            <MapPin className="h-3 w-3" />
            <span>{farm.region}</span>
            <span>·</span>
            <span>{farm.size_ha} ha</span>
            {farm.crop_name && (<><span>·</span><span>{farm.crop_name}</span></>)}
            {farm.soil_type && (<><span>·</span><span>{farm.soil_type}</span></>)}
          </div>
        </div>
        <Badge variant="outline" className={sb.cls}>{sb.label}</Badge>
      </header>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-lg border bg-card p-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1"><Leaf className="h-3 w-3" /> NDVI</span>
            <span className="tabular-nums font-medium text-foreground">{farm.ndvi?.toFixed(2) ?? "—"}</span>
          </div>
          <div className="h-10 -mx-1 mt-1">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trend}>
                <defs>
                  <linearGradient id={`g-${farm.id}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area type="monotone" dataKey="ndvi" stroke="hsl(var(--primary))" strokeWidth={1.5} fill={`url(#g-${farm.id})`} isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-lg border bg-card p-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1"><Droplets className="h-3 w-3" /> Soil moisture</span>
            <span className="tabular-nums font-medium text-foreground">{farm.soilMoisture?.toFixed(0) ?? "—"}%</span>
          </div>
          <Progress value={moisturePct} className="h-2 mt-3" />
          <div className="mt-1.5 text-[10px] text-muted-foreground">Target ≥ 35%</div>
        </div>
      </div>

      <div className="rounded-lg bg-accent/60 border border-accent p-3 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-accent-foreground font-medium inline-flex items-center gap-1.5">
            <Droplets className="h-4 w-4" /> Recommended water
          </span>
          <span className="tabular-nums font-semibold">{formatLiters(farm.recommendedLiters)}</span>
        </div>
        <div className="mt-1.5 flex items-center gap-1.5 text-xs text-accent-foreground/80">
          <Clock className="h-3 w-3" />
          <span>Window {farm.windowStart} – {farm.windowEnd}</span>
        </div>
      </div>

      <Button variant="ghost" size="sm" className="self-end -mr-2" onClick={() => onDetails?.(farm)}>
        Details <ArrowRight className="h-4 w-4" />
      </Button>
    </Card>
  );
}
