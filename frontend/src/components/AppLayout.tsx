import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Droplets, LayoutDashboard, Map as MapIcon, BellRing, Activity, LogOut, LogIn } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";

const tabs = [
  { to: "/", label: "Overview", icon: MapIcon },
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/estimator", label: "Estimator", icon: Activity },
  { to: "/alerts", label: "Alerts", icon: BellRing },
];

export default function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, signOut } = useAuth();

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between gap-6">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="h-9 w-9 rounded-lg bg-gradient-hero grid place-items-center text-primary-foreground shadow-elev-sm">
              <Droplets className="h-5 w-5" />
            </div>
            <div className="leading-tight">
              <div className="font-semibold tracking-tight">AquaField</div>
              <div className="text-[11px] text-muted-foreground">Smart irrigation · MK</div>
            </div>
          </Link>

          <nav className="flex items-center gap-1 rounded-lg bg-muted p-1">
            {tabs.map((t) => {
              const active = location.pathname === t.to;
              const Icon = t.icon;
              return (
                <NavLink
                  key={t.to}
                  to={t.to}
                  className={cn(
                    "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                    active
                      ? "bg-background text-foreground shadow-elev-sm"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  <span className="hidden sm:inline">{t.label}</span>
                </NavLink>
              );
            })}
          </nav>

          <div className="flex items-center gap-3">
            <div className="hidden md:flex items-center gap-2 text-xs text-muted-foreground">
              <span className="h-2 w-2 rounded-full bg-healthy animate-pulse" />
              Live · 5 min
            </div>
            {user ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => { signOut(); navigate("/"); }}
              >
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline">Sign out</span>
              </Button>
            ) : (
              <Button size="sm" onClick={() => navigate("/auth")}>
                <LogIn className="h-4 w-4" />
                <span className="hidden sm:inline">Sign in</span>
              </Button>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1 animate-fade-in">
        <Outlet />
      </main>

      <footer className="border-t py-4">
        <div className="container flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-muted-foreground">
          <div>AquaField · Helping rural communities share water fairly.</div>
          <div>Sentinel-2 NDVI · Open-Meteo soil moisture</div>
        </div>
      </footer>
    </div>
  );
}
