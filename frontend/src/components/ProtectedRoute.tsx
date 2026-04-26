import { Link } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LogIn, Lock } from "lucide-react";

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  if (!user) {
    return (
      <div className="container py-16 grid place-items-center">
        <Card className="max-w-md w-full p-8 text-center space-y-4">
          <div className="mx-auto h-12 w-12 rounded-full bg-primary/10 grid place-items-center text-primary">
            <Lock className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-xl font-semibold tracking-tight">Sign in required</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Please sign in to access this page.
            </p>
          </div>
          <Button asChild className="w-full">
            <Link to="/auth">
              <LogIn className="h-4 w-4" /> Sign in
            </Link>
          </Button>
        </Card>
      </div>
    );
  }
  return <>{children}</>;
}
