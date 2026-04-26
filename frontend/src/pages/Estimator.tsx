import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Activity, Droplets, Satellite, Leaf, CloudRain } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { api, type EkfDayRow, type EkfScenario } from "@/lib/api";
import { useFarms } from "@/hooks/useFarmData";

type StressKey = "low" | "moderate" | "high" | "critical";

const stressMeta: Record<StressKey, { label: string; cls: string }> = {
  low: {
    label: "Low",
    cls: "bg-[hsl(var(--healthy)/0.15)] text-[hsl(var(--healthy))] border-transparent",
  },
  moderate: {
    label: "Moderate",
    cls: "bg-[hsl(var(--moderate)/0.15)] text-[hsl(var(--moderate))] border-transparent",
  },
  high: {
    label: "High",
    cls: "bg-[hsl(var(--severity-warning)/0.15)] text-[hsl(var(--severity-warning))] border-transparent",
  },
  critical: {
    label: "Critical",
    cls: "bg-[hsl(var(--stressed)/0.15)] text-[hsl(var(--stressed))] border-transparent",
  },
};

const SOIL_OPTIONS = [
  { value: "loam", label: "Loam" },
  { value: "clay_loam", label: "Clay loam" },
];

function fmt(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

function shortDate(iso: string): string {
  return new Date(iso + "T00:00:00").toLocaleDateString("en", {
    month: "short",
    day: "numeric",
  });
}

function StressPill({ level }: { level: string | null | undefined }) {
  const key = (level ?? "low").toLowerCase() as StressKey;
  const meta = stressMeta[key] ?? stressMeta.low;
  return (
    <Badge variant="outline" className={meta.cls}>
      {meta.label}
    </Badge>
  );
}

function ScenarioCard({
  scenario,
  farmName,
}: {
  scenario: EkfScenario;
  farmName?: string;
}) {
  const final = scenario.final;
  const cropParams = scenario.crop_parameters;
  const isLive = !!farmName;

  const totalIrrigation = useMemo(
    () => scenario.history.reduce((sum, row) => sum + row.irrigation_mm, 0),
    [scenario.history],
  );

  const satelliteDays = useMemo(
    () => scenario.history.filter((r) => r.updated).length,
    [scenario.history],
  );

  const chartData = useMemo(
    () =>
      scenario.history.map((row) => ({
        label: row.date ? shortDate(row.date) : String(row.day),
        estimate: row.soil_water_estimate_mm,
        prediction: row.x_pred_mm,
        measurement: row.measurement_mm,
      })),
    [scenario.history],
  );

  const fcLine = scenario.parameters.theta_fc_mm;
  const triggerLine = scenario.parameters.irrigation_trigger_mm;

  return (
    <Card className="p-5 bg-gradient-card shadow-elev-sm hover:shadow-elev-md transition-shadow space-y-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground">
            {isLive
              ? `${scenario.soil_type.replace("_", " ")} · last ${scenario.days} days`
              : `${scenario.soil_type.replace("_", " ")} · ${scenario.days} days`}
          </div>
          <h3 className="mt-0.5 text-lg font-semibold tracking-tight">
            {farmName ?? scenario.display_name}
          </h3>
          {farmName && (
            <div className="text-xs text-muted-foreground mt-0.5">
              {scenario.display_name}
            </div>
          )}
        </div>
        <StressPill level={final?.stress_level} />
      </div>

      <div className="flex flex-wrap gap-1.5">
        <Chip>
          Kc {fmt(cropParams.kc_initial, 2)} / {fmt(cropParams.kc_mid, 2)} /{" "}
          {fmt(cropParams.kc_late, 2)}
        </Chip>
        <Chip>p {fmt(cropParams.depletion_fraction_p, 2)}</Chip>
        <Chip>Roots {fmt(cropParams.root_depth_m, 1)} m</Chip>
        <Chip>NDVI {fmt(cropParams.default_ndvi, 2)}</Chip>
        {isLive && (
          <Chip>
            <Satellite className="h-3 w-3 mr-1 inline" />
            {satelliteDays}/{scenario.days} satellite days
          </Chip>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Metric
          label="Final soil water"
          value={`${fmt(final?.soil_water_estimate_mm)} mm`}
        />
        <Metric label="Uncertainty P" value={fmt(final?.uncertainty)} />
        <Metric label="Total irrigation" value={`${fmt(totalIrrigation)} mm`} />
        <Metric
          label="Available water"
          value={`${fmt((final?.relative_available_water ?? 0) * 100, 1)}%`}
        />
      </div>

      <div className="rounded-lg border bg-card p-3">
        <div className="mb-2 text-xs font-medium text-muted-foreground">
          Soil water (mm)
        </div>
        <div className="h-44">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 10 }}
                interval="preserveStartEnd"
              />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip
                contentStyle={{
                  borderRadius: 8,
                  border: "1px solid hsl(var(--border))",
                  fontSize: 12,
                }}
              />
              <Line
                dataKey="prediction"
                stroke="hsl(var(--muted-foreground))"
                strokeWidth={1.5}
                strokeDasharray="4 3"
                dot={false}
                isAnimationActive={false}
                name="Prediction"
              />
              <Line
                dataKey="estimate"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                dot={{ r: 2.5 }}
                isAnimationActive={false}
                name="Estimate"
              />
              <Line
                dataKey="measurement"
                stroke="hsl(var(--severity-warning))"
                strokeWidth={0}
                dot={{ r: 4, fill: "hsl(var(--severity-warning))" }}
                isAnimationActive={false}
                connectNulls={false}
                name="Satellite"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-2 flex flex-wrap gap-3 text-[10px] text-muted-foreground">
          <LegendDot color="hsl(var(--primary))" label="Estimate" />
          <LegendDot color="hsl(var(--muted-foreground))" label="Prediction" dashed />
          <LegendDot color="hsl(var(--severity-warning))" label="Satellite" dot />
          <span>FC {fmt(fcLine)} · Trigger {fmt(triggerLine)}</span>
        </div>
      </div>

      {cropParams.notes && (
        <p className="text-xs text-muted-foreground italic">{cropParams.notes}</p>
      )}

      <div className="rounded-lg border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-xs">{isLive ? "Date" : "Day"}</TableHead>
              <TableHead className="text-xs">ET₀</TableHead>
              <TableHead className="text-xs">Rain</TableHead>
              <TableHead className="text-xs">Irrig.</TableHead>
              <TableHead className="text-xs">Pred.</TableHead>
              <TableHead className="text-xs">Sat. z</TableHead>
              <TableHead className="text-xs">Estimate</TableHead>
              <TableHead className="text-xs">Stress</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {scenario.history.map((row: EkfDayRow) => (
              <TableRow
                key={`${scenario.crop}-${row.day}`}
                className={row.updated ? "bg-accent/30" : undefined}
              >
                <TableCell className="text-xs tabular-nums">
                  {row.date ? shortDate(row.date) : row.day}
                </TableCell>
                <TableCell className="text-xs tabular-nums">{fmt(row.et0_mm)}</TableCell>
                <TableCell className="text-xs tabular-nums">{fmt(row.rain_mm)}</TableCell>
                <TableCell className="text-xs tabular-nums">{fmt(row.irrigation_mm)}</TableCell>
                <TableCell className="text-xs tabular-nums">{fmt(row.x_pred_mm)}</TableCell>
                <TableCell className="text-xs tabular-nums">{fmt(row.measurement_mm)}</TableCell>
                <TableCell className="text-xs tabular-nums font-medium">
                  {fmt(row.soil_water_estimate_mm)}
                </TableCell>
                <TableCell><StressPill level={row.stress_level} /></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </Card>
  );
}

export default function Estimator() {
  const [days, setDays] = useState(10);
  const [soilType, setSoilType] = useState("loam");
  const [farmId, setFarmId] = useState("demo");

  const { data: farms = [] } = useFarms();
  const isLiveMode = farmId !== "demo";
  const selectedFarm = farms.find((f) => f.id === farmId);

  const liveQuery = useQuery({
    queryKey: ["ekf-live", farmId, days],
    queryFn: () => api.getLiveFarmEstimate(farmId, days),
    enabled: isLiveMode && farmId !== "demo",
  });

  const demoQuery = useQuery({
    queryKey: ["ekf-demo", days, soilType],
    queryFn: () => api.getEkfDemo({ days, soilType }),
    enabled: !isLiveMode,
  });

  const isLoading = isLiveMode ? liveQuery.isLoading : demoQuery.isLoading;
  const isError = isLiveMode ? liveQuery.isError : demoQuery.isError;
  const error = isLiveMode ? liveQuery.error : demoQuery.error;
  const scenarios: EkfScenario[] = isLiveMode
    ? (liveQuery.data ? [liveQuery.data] : [])
    : (demoQuery.data?.scenarios ?? []);

  return (
    <>
      {/* Hero */}
      <section className="bg-gradient-hero text-primary-foreground">
        <div className="container py-10 md:py-14">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 text-xs font-medium backdrop-blur">
              <span className="h-1.5 w-1.5 rounded-full bg-white animate-pulse" />
              Extended Kalman Filter · daily soil-water estimator
            </div>
            <h1 className="mt-4 text-3xl md:text-5xl font-semibold tracking-tight">
              Crop water balance estimator
            </h1>
            <p className="mt-3 text-primary-foreground/85 text-base md:text-lg">
              {isLiveMode
                ? "Real Open-Meteo weather and Sentinel-2 satellite data run through the EKF for your selected field."
                : "Simulated Skopje-like weather with FAO crop coefficients — select a field above for real data."}
            </p>
          </div>
          <div className="mt-6 flex gap-6 text-primary-foreground/80">
            <div className="inline-flex items-center gap-2 text-sm">
              <Droplets className="h-4 w-4" /> Soil water
            </div>
            <div className="inline-flex items-center gap-2 text-sm">
              <CloudRain className="h-4 w-4" /> Open-Meteo
            </div>
            <div className="inline-flex items-center gap-2 text-sm">
              <Satellite className="h-4 w-4" /> Sentinel-2
            </div>
            <div className="inline-flex items-center gap-2 text-sm">
              <Activity className="h-4 w-4" /> EKF correction
            </div>
            <div className="inline-flex items-center gap-2 text-sm">
              <Leaf className="h-4 w-4" /> FAO Kc
            </div>
          </div>
        </div>
      </section>

      {/* Controls */}
      <section className="container -mt-8 md:-mt-10 relative z-10">
        <Card className="p-5 bg-gradient-card shadow-elev-sm">
          <div className="flex flex-wrap items-end gap-4">
            {/* Farm picker */}
            {farms.length > 0 && (
              <div className="flex-1 min-w-[180px] max-w-[260px]">
                <Label className="text-xs uppercase tracking-wide text-muted-foreground">
                  Field (live data)
                </Label>
                <Select value={farmId} onValueChange={setFarmId}>
                  <SelectTrigger className="mt-1"><SelectValue placeholder="Demo mode" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="demo">Demo mode (simulated)</SelectItem>
                    {farms.map((f) => (
                      <SelectItem key={f.id} value={f.id}>
                        {f.name} · {f.crop_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="flex-1 min-w-[140px] max-w-[180px]">
              <Label htmlFor="days" className="text-xs uppercase tracking-wide text-muted-foreground">
                {isLiveMode ? "History days" : "Simulation days"}
              </Label>
              <Input
                id="days"
                type="number"
                min={1}
                max={60}
                value={days}
                onChange={(e) => setDays(Math.max(1, Math.min(60, Number(e.target.value) || 10)))}
                className="mt-1"
              />
            </div>

            {/* Soil type only relevant in demo mode */}
            {!isLiveMode && (
              <div className="flex-1 min-w-[160px] max-w-[220px]">
                <Label className="text-xs uppercase tracking-wide text-muted-foreground">
                  Soil type
                </Label>
                <Select value={soilType} onValueChange={setSoilType}>
                  <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {SOIL_OPTIONS.map((o) => (
                      <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="ml-auto text-xs text-muted-foreground max-w-xs text-right">
              {isLiveMode
                ? `${selectedFarm?.name ?? "Field"} · Open-Meteo weather · Sentinel-2 when available`
                : (demoQuery.data?.weather_assumption ?? "Loading scenario assumptions…")}
            </div>
          </div>
        </Card>
      </section>

      {/* Info banner */}
      <section className="container py-6">
        {!isLiveMode && demoQuery.data && (
          <Card className="p-4 border-dashed bg-accent/40 text-sm">
            <div className="font-medium text-accent-foreground">{demoQuery.data.title}</div>
            <p className="text-muted-foreground mt-1">{demoQuery.data.method_note}</p>
            <p className="text-muted-foreground mt-1">{demoQuery.data.unit_note}</p>
            {demoQuery.data.measurement_days?.length > 0 && (
              <p className="text-muted-foreground mt-1">
                Satellite correction days: {demoQuery.data.measurement_days.join(", ")}
              </p>
            )}
          </Card>
        )}
        {isLiveMode && liveQuery.data && (
          <Card className="p-4 border-dashed bg-accent/40 text-sm">
            <div className="font-medium text-accent-foreground">
              Live EKF run for {liveQuery.data.farm_name}
            </div>
            <p className="text-muted-foreground mt-1">
              Weather from Open-Meteo (real daily precipitation and ET₀). Sentinel-2 NDMI
              corrects the soil-water state on days when a cloud-free image is available.
              All water depths are mm over the field surface / root zone.
            </p>
          </Card>
        )}
        {isError && (
          <Card className="p-4 border-[hsl(var(--destructive))] text-sm text-[hsl(var(--destructive))]">
            Could not load estimate: {(error as Error)?.message ?? "Unknown error"}
          </Card>
        )}
      </section>

      {/* Scenarios */}
      <section className="container pb-10">
        {isLoading ? (
          <div className={`grid gap-5 ${isLiveMode ? "" : "md:grid-cols-2 xl:grid-cols-3"}`}>
            {Array.from({ length: isLiveMode ? 1 : 3 }).map((_, i) => (
              <Skeleton key={i} className="h-[640px] rounded-xl" />
            ))}
          </div>
        ) : (
          <div className={`grid gap-5 ${isLiveMode ? "max-w-2xl mx-auto" : "md:grid-cols-2 xl:grid-cols-3"}`}>
            {scenarios.map((s) => (
              <ScenarioCard
                key={`${s.crop}-${s.soil_type}`}
                scenario={s}
                farmName={isLiveMode ? (liveQuery.data?.farm_name) : undefined}
              />
            ))}
          </div>
        )}
      </section>
    </>
  );
}

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full border bg-secondary px-2.5 py-0.5 text-[11px] text-secondary-foreground">
      {children}
    </span>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border p-3">
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-0.5 font-semibold tabular-nums">{value}</div>
    </div>
  );
}

function LegendDot({
  color,
  label,
  dashed = false,
  dot = false,
}: { color: string; label: string; dashed?: boolean; dot?: boolean }) {
  if (dot) {
    return (
      <span className="inline-flex items-center gap-1.5">
        <span className="h-2 w-2 rounded-full" style={{ background: color }} />
        {label}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className="block h-0 w-4 border-t-2"
        style={{ borderColor: color, borderStyle: dashed ? "dashed" : "solid" }}
      />
      {label}
    </span>
  );
}
