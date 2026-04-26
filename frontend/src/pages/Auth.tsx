import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { z } from "zod";
import { useAuth } from "@/hooks/useAuth";
import { authApi } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "@/hooks/use-toast";
import { Droplets } from "lucide-react";

const signUpSchema = z.object({
  firstName: z.string().trim().min(1, "First name required").max(80),
  lastName: z.string().trim().min(1, "Last name required").max(80),
  username: z.string().trim().min(1, "Username required").max(80),
  email: z.string().trim().email("Invalid email").max(255),
  password: z.string().min(6, "At least 6 characters").max(72),
  phoneNumber: z.string().trim().max(30).optional().default(""),
});

const signInSchema = z.object({
  email: z.string().trim().email("Invalid email").max(255),
  password: z.string().min(1, "Password required").max(72),
});

export default function Auth() {
  const { user, signIn } = useAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  if (user) return <Navigate to="/dashboard" replace />;

  async function onSignIn(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const raw = Object.fromEntries(new FormData(e.currentTarget).entries());
    const parsed = signInSchema.safeParse(raw);
    if (!parsed.success) {
      const errs: Record<string, string> = {};
      parsed.error.issues.forEach((i) => { errs[i.path[0] as string] = i.message; });
      setErrors(errs);
      return;
    }
    setErrors({});
    setBusy(true);
    try {
      const result = await authApi.login(parsed.data.email, parsed.data.password);
      signIn({ id: result.id, email: result.email, username: result.username });
      navigate("/dashboard");
    } catch (e: any) {
      toast({ title: "Sign in failed", description: e.message ?? "Invalid credentials", variant: "destructive" });
    } finally {
      setBusy(false);
    }
  }

  async function onSignUp(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const raw = Object.fromEntries(new FormData(e.currentTarget).entries());
    const parsed = signUpSchema.safeParse(raw);
    if (!parsed.success) {
      const errs: Record<string, string> = {};
      parsed.error.issues.forEach((i) => { errs[i.path[0] as string] = i.message; });
      setErrors(errs);
      return;
    }
    setErrors({});
    setBusy(true);
    try {
      await authApi.register({
        fristName: parsed.data.firstName,
        lastName: parsed.data.lastName,
        email: parsed.data.email,
        username: parsed.data.username,
        password: parsed.data.password,
        phoneNumber: parsed.data.phoneNumber ?? "",
      });
      // Auto sign in after registration
      const result = await authApi.login(parsed.data.email, parsed.data.password);
      signIn({ id: result.id, email: result.email, username: result.username });
      toast({ title: "Welcome to AquaField!", description: "Account created." });
      navigate("/dashboard");
    } catch (e: any) {
      toast({ title: "Sign up failed", description: e.message ?? "Unknown error", variant: "destructive" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen grid place-items-center bg-gradient-hero p-4">
      <div className="w-full max-w-md">
        <div className="flex items-center gap-2.5 justify-center mb-6 text-primary-foreground">
          <div className="h-10 w-10 rounded-lg bg-white/15 grid place-items-center backdrop-blur">
            <Droplets className="h-5 w-5" />
          </div>
          <div className="leading-tight">
            <div className="font-semibold tracking-tight text-lg">AquaField</div>
            <div className="text-xs opacity-80">Smart irrigation · MK</div>
          </div>
        </div>

        <Card className="p-6">
          <Tabs defaultValue="signin">
            <TabsList className="grid w-full grid-cols-2 mb-4">
              <TabsTrigger value="signin">Sign in</TabsTrigger>
              <TabsTrigger value="signup">Sign up</TabsTrigger>
            </TabsList>

            <TabsContent value="signin">
              <form onSubmit={onSignIn} className="grid gap-3">
                <Field label="Email" name="email" type="email" error={errors.email} />
                <Field label="Password" name="password" type="password" error={errors.password} />
                <Button type="submit" disabled={busy} className="mt-2">
                  {busy ? "Signing in…" : "Sign in"}
                </Button>
              </form>
            </TabsContent>

            <TabsContent value="signup">
              <form onSubmit={onSignUp} className="grid gap-3">
                <div className="grid grid-cols-2 gap-3">
                  <Field label="First name" name="firstName" error={errors.firstName} placeholder="Petar" />
                  <Field label="Last name" name="lastName" error={errors.lastName} placeholder="Stojanov" />
                </div>
                <Field label="Username" name="username" error={errors.username} placeholder="petar.stojanov" />
                <Field label="Email" name="email" type="email" error={errors.email} />
                <Field label="Password" name="password" type="password" error={errors.password} placeholder="At least 6 characters" />
                <Field label="Phone (optional)" name="phoneNumber" type="tel" error={errors.phoneNumber} placeholder="+389 70 123 456" />
                <Button type="submit" disabled={busy} className="mt-2">
                  {busy ? "Creating…" : "Create account"}
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </Card>
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
