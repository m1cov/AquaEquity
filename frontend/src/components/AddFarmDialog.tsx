import { useMemo, useState } from "react";
import { z } from "zod";
import { api } from "@/lib/api";
import { useFarms } from "@/hooks/useFarmData";
import { useAuth } from "@/hooks/useAuth";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Plus } from "lucide-react";
import { toast } from "@/hooks/use-toast";
import { haFromCorners } from "@/lib/irrigation";

const SOIL_TYPES = ["loam", "sandy", "clay", "silty", "peat", "chalk", "sandy_loam", "moist"] as const;
const CROP_NAMES = ["tomato", "wheat", "corn", "potato", "pepper", "maize", "sunflower"] as const;

const metaSchema = z.object({
  name: z.string().trim().min(1, "Name required").max(80),
  owner_name: z.string().trim().min(1, "Owner required").max(80),
  water_quota_liters: z.coerce.number().nonnegative().max(100_000_000),
});

type Corner = { x: string; y: string };

function parseCorner(c: Corner) {
  return { x: parseFloat(c.x), y: parseFloat(c.y) };
}

function isValid(n: number) {
  return isFinite(n) && !isNaN(n);
}

export function AddFarmDialog({ defaultOwner }: { defaultOwner?: string }) {
  const qc = useQueryClient();
  const { user } = useAuth();
  const { data: allFarms = [] } = useFarms();
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [region, setRegion] = useState("");
  const [soilType, setSoilType] = useState("");
  const [cropName, setCropName] = useState("");

  // 4 corners: X = latitude, Y = longitude (Java API convention)
  const [tl, setTl] = useState<Corner>({ x: "41.502", y: "21.398" });
  const [tr, setTr] = useState<Corner>({ x: "41.502", y: "21.412" });
  const [bl, setBl] = useState<Corner>({ x: "41.492", y: "21.398" });
  const [br, setBr] = useState<Corner>({ x: "41.492", y: "21.412" });

  const regions = useMemo(() => {
    const seen = new Set<string>();
    allFarms.forEach((f) => { if (f.region) seen.add(f.region); });
    return Array.from(seen).sort();
  }, [allFarms]);

  const computedHa = useMemo(() => {
    const tLp = parseCorner(tl), tRp = parseCorner(tr), bRp = parseCorner(br), bLp = parseCorner(bl);
    if (![tLp, tRp, bRp, bLp].every(p => isValid(p.x) && isValid(p.y))) return null;
    return haFromCorners(tLp.x, tLp.y, tRp.x, tRp.y, bRp.x, bRp.y, bLp.x, bLp.y);
  }, [tl, tr, br, bl]);

  function resetForm() {
    setRegion(""); setSoilType(""); setCropName(""); setErrors({});
    setTl({ x: "41.502", y: "21.398" }); setTr({ x: "41.502", y: "21.412" });
    setBl({ x: "41.492", y: "21.398" }); setBr({ x: "41.492", y: "21.412" });
  }

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const parsed = metaSchema.safeParse(Object.fromEntries(fd.entries()));
    if (!parsed.success) {
      const errs: Record<string, string> = {};
      parsed.error.issues.forEach((i) => { errs[i.path[0] as string] = i.message; });
      setErrors(errs); return;
    }
    if (!region) { setErrors((e) => ({ ...e, region: "Region required" })); return; }
    if (!soilType) { setErrors((e) => ({ ...e, soil_type: "Select a soil type" })); return; }
    if (!cropName) { setErrors((e) => ({ ...e, crop_name: "Select a crop type" })); return; }
    if (computedHa === null || computedHa <= 0) {
      setErrors((e) => ({ ...e, corners: "Enter valid corner coordinates" })); return;
    }
    if (!user) {
      toast({ title: "Please sign in", description: "You must be signed in to add a field.", variant: "destructive" });
      return;
    }
    setErrors({});

    const tLp = parseCorner(tl), tRp = parseCorner(tr), bRp = parseCorner(br), bLp = parseCorner(bl);
    const centerLat = (tLp.x + tRp.x + bRp.x + bLp.x) / 4;
    const centerLon = (tLp.y + tRp.y + bRp.y + bLp.y) / 4;

    const { name, owner_name, water_quota_liters } = parsed.data;
    setSubmitting(true);
    try {
      await api.createFarm({
        name,
        owner_name,
        water_quota_liters,
        region,
        soil_type: soilType,
        crop_name: cropName,
        size_ha: Math.round(computedHa * 100) / 100,
        latitude: centerLat,
        longitude: centerLon,
        top_left_x: tLp.x, top_left_y: tLp.y,
        top_right_x: tRp.x, top_right_y: tRp.y,
        bottom_left_x: bLp.x, bottom_left_y: bLp.y,
        bottom_right_x: bRp.x, bottom_right_y: bRp.y,
      });
      toast({ title: "Field added", description: `${name} (${computedHa.toFixed(2)} ha) created.` });
      setOpen(false);
      resetForm();
      qc.invalidateQueries({ queryKey: ["farms-enriched"] });
    } catch (e: any) {
      toast({ title: "Could not add field", description: e.message ?? "Unknown error", variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (!o) resetForm(); }}>
      <DialogTrigger asChild>
        <Button><Plus className="h-4 w-4" />Add new field</Button>
      </DialogTrigger>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Add new field</DialogTitle>
        </DialogHeader>
        <form onSubmit={onSubmit} className="grid gap-4">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Field name" name="name" error={errors.name} placeholder="South Plot" />
            <Field label="Owner" name="owner_name" error={errors.owner_name} defaultValue={defaultOwner} />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label>Region</Label>
              <Select value={region} onValueChange={setRegion}>
                <SelectTrigger><SelectValue placeholder="Select region" /></SelectTrigger>
                <SelectContent>
                  {regions.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}
                </SelectContent>
              </Select>
              {errors.region && <p className="text-xs text-destructive">{errors.region}</p>}
            </div>
            <Field label="Water quota (L)" name="water_quota_liters" type="number" error={errors.water_quota_liters} defaultValue="100000" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label>Soil type</Label>
              <Select value={soilType} onValueChange={setSoilType}>
                <SelectTrigger><SelectValue placeholder="Select soil type" /></SelectTrigger>
                <SelectContent>
                  {SOIL_TYPES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                </SelectContent>
              </Select>
              {errors.soil_type && <p className="text-xs text-destructive">{errors.soil_type}</p>}
            </div>
            <div className="grid gap-1.5">
              <Label>Crop type</Label>
              <Select value={cropName} onValueChange={setCropName}>
                <SelectTrigger><SelectValue placeholder="Select crop" /></SelectTrigger>
                <SelectContent>
                  {CROP_NAMES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
              {errors.crop_name && <p className="text-xs text-destructive">{errors.crop_name}</p>}
            </div>
          </div>

          {/* 4-corner polygon inputs */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <Label className="text-sm font-medium">Field boundary (Lat / Lon)</Label>
              {computedHa !== null && computedHa > 0 && (
                <Badge variant="secondary" className="tabular-nums text-xs">
                  {computedHa.toFixed(2)} ha
                </Badge>
              )}
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-3">
              <CornerInput label="Top-left" value={tl} onChange={setTl} />
              <CornerInput label="Top-right" value={tr} onChange={setTr} />
              <CornerInput label="Bottom-left" value={bl} onChange={setBl} />
              <CornerInput label="Bottom-right" value={br} onChange={setBr} />
            </div>
            {errors.corners && <p className="text-xs text-destructive mt-1">{errors.corners}</p>}
            <p className="text-[11px] text-muted-foreground mt-1.5">
              Hectares are calculated automatically from the 4 corner coordinates.
            </p>
          </div>

          <DialogFooter className="mt-1">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={submitting}>{submitting ? "Adding…" : "Add field"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function CornerInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: Corner;
  onChange: (v: Corner) => void;
}) {
  return (
    <div className="rounded-lg border p-3 grid gap-2">
      <div className="text-xs font-medium text-muted-foreground">{label}</div>
      <div className="grid grid-cols-2 gap-2">
        <div className="grid gap-1">
          <label className="text-[10px] text-muted-foreground">Lat (X)</label>
          <Input
            type="number"
            step="0.0001"
            value={value.x}
            onChange={(e) => onChange({ ...value, x: e.target.value })}
            className="h-7 text-xs tabular-nums"
          />
        </div>
        <div className="grid gap-1">
          <label className="text-[10px] text-muted-foreground">Lon (Y)</label>
          <Input
            type="number"
            step="0.0001"
            value={value.y}
            onChange={(e) => onChange({ ...value, y: e.target.value })}
            className="h-7 text-xs tabular-nums"
          />
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  name,
  error,
  ...props
}: { label: string; name: string; error?: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={name}>{label}</Label>
      <Input id={name} name={name} {...props} />
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
