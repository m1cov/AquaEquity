import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { type LucideIcon } from "lucide-react";

interface Props {
  label: string;
  value: string;
  hint?: string;
  icon?: LucideIcon;
  tone?: "default" | "healthy" | "moderate" | "stressed";
}

export function StatCard({ label, value, hint, icon: Icon, tone = "default" }: Props) {
  const toneClass = {
    default: "text-primary bg-accent",
    healthy: "text-[hsl(var(--healthy))] bg-[hsl(var(--healthy)/0.12)]",
    moderate: "text-[hsl(var(--moderate))] bg-[hsl(var(--moderate)/0.12)]",
    stressed: "text-[hsl(var(--stressed))] bg-[hsl(var(--stressed)/0.12)]",
  }[tone];

  return (
    <Card className="p-5 bg-gradient-card shadow-elev-sm hover:shadow-elev-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs uppercase tracking-wide text-muted-foreground font-medium">{label}</div>
          <div className="mt-1.5 text-2xl font-semibold tracking-tight tabular-nums">{value}</div>
          {hint && <div className="mt-1 text-xs text-muted-foreground">{hint}</div>}
        </div>
        {Icon && (
          <div className={cn("h-10 w-10 rounded-lg grid place-items-center shrink-0", toneClass)}>
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>
    </Card>
  );
}
