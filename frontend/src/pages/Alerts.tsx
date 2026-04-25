import { useMemo, useState } from "react";
import { useAlerts, useFarms } from "@/hooks/useFarmData";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Send, Info, AlertTriangle, AlertOctagon, MessageSquare } from "lucide-react";
import { api } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "@/hooks/use-toast";

const severityMeta: Record<string, { label: string; cls: string; Icon: React.ComponentType<{ className?: string }> }> = {
  info: { label: "Info", cls: "bg-[hsl(var(--severity-info)/0.15)] text-[hsl(var(--severity-info))] border-transparent", Icon: Info },
  warning: { label: "Warning", cls: "bg-[hsl(var(--severity-warning)/0.15)] text-[hsl(var(--severity-warning))] border-transparent", Icon: AlertTriangle },
  critical: { label: "Critical", cls: "bg-[hsl(var(--severity-critical)/0.15)] text-[hsl(var(--severity-critical))] border-transparent", Icon: AlertOctagon },
};

export default function Alerts() {
  const { data: alerts = [], isLoading } = useAlerts();
  const { data: farms = [] } = useFarms();
  const qc = useQueryClient();
  const [farmFilter, setFarmFilter] = useState<string>("all");
  const [sevFilter, setSevFilter] = useState<string>("all");
  const [sending, setSending] = useState(false);

  const farmName = (id: string | null) => farms.find((f) => f.id === id)?.name ?? "—";

  const filtered = useMemo(() => {
    return alerts.filter((a) => {
      if (farmFilter !== "all" && a.farm_id !== farmFilter) return false;
      if (sevFilter !== "all" && a.severity !== sevFilter) return false;
      return true;
    });
  }, [alerts, farmFilter, sevFilter]);

  async function sendTestAlert() {
    setSending(true);
    try {
      await api.sendAlert({
        farm_id: farms[0]?.id ?? null,
        message: `Test alert: irrigation recommended at ${farms[0]?.name ?? "your farm"}.`,
        severity: "info",
      });
      toast({ title: "Test alert sent", description: "Simulated SMS logged below." });
      qc.invalidateQueries({ queryKey: ["alerts"] });
    } catch (e: any) {
      toast({ title: "Could not send", description: e.message ?? "Unknown error", variant: "destructive" });
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="container py-8 space-y-6">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Alerts</h1>
          <p className="text-sm text-muted-foreground">Recent SMS and dashboard alerts for your farms.</p>
        </div>
        <Button onClick={sendTestAlert} disabled={sending}>
          <Send className="h-4 w-4" /> Send test alert
        </Button>
      </div>

      <Card className="p-4 border-dashed bg-accent/40">
        <div className="flex items-start gap-3 text-sm">
          <MessageSquare className="h-5 w-5 text-primary mt-0.5" />
          <div className="flex-1">
            <div className="font-medium text-accent-foreground">SMS delivery is simulated</div>
            <div className="text-muted-foreground mt-0.5">
              Alerts are logged in this dashboard. Connect Twilio later to send real SMS messages to farmers.
            </div>
          </div>
          <Button variant="outline" size="sm" disabled>Enable Twilio</Button>
        </div>
      </Card>

      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Farm</span>
            <Select value={farmFilter} onValueChange={setFarmFilter}>
              <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All farms</SelectItem>
                {farms.map((f) => <SelectItem key={f.id} value={f.id}>{f.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Severity</span>
            <Select value={sevFilter} onValueChange={setSevFilter}>
              <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="info">Info</SelectItem>
                <SelectItem value="warning">Warning</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="ml-auto text-xs text-muted-foreground">{filtered.length} alert{filtered.length !== 1 && "s"}</div>
        </div>
      </Card>

      <Card>
        {isLoading ? (
          <div className="p-6 space-y-3">
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Farm</TableHead>
                <TableHead>Message</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead>Channel</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((a) => {
                const sev = severityMeta[a.severity] ?? severityMeta.info;
                const Icon = sev.Icon;
                return (
                  <TableRow key={a.id}>
                    <TableCell className="whitespace-nowrap text-muted-foreground text-xs tabular-nums">
                      {new Date(a.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="font-medium">{farmName(a.farm_id)}</TableCell>
                    <TableCell className="max-w-md">{a.message}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={sev.cls}><Icon className="h-3 w-3 mr-1" />{sev.label}</Badge>
                    </TableCell>
                    <TableCell className="capitalize text-muted-foreground">{a.channel}</TableCell>
                    <TableCell className="capitalize text-muted-foreground">{a.status}</TableCell>
                  </TableRow>
                );
              })}
              {!filtered.length && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-sm text-muted-foreground py-10">
                    No alerts yet. Click "Send test alert" to create one.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        )}
      </Card>
    </div>
  );
}
