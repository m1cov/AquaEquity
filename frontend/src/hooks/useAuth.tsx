import { createContext, useContext, useState, type ReactNode } from "react";

export interface AuthUser {
  id: number;
  email: string;
  username: string;
}

interface AuthCtx {
  user: AuthUser | null;
  loading: false;
  signIn: (u: AuthUser) => void;
  signOut: () => void;
}

const STORAGE_KEY = "aquafield_user";

const Ctx = createContext<AuthCtx>({
  user: null,
  loading: false,
  signIn: () => {},
  signOut: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? (JSON.parse(raw) as AuthUser) : null;
    } catch {
      return null;
    }
  });

  function signIn(u: AuthUser) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(u));
    setUser(u);
  }

  function signOut() {
    localStorage.removeItem(STORAGE_KEY);
    setUser(null);
  }

  return (
    <Ctx.Provider value={{ user, loading: false, signIn, signOut }}>
      {children}
    </Ctx.Provider>
  );
}

export const useAuth = () => useContext(Ctx);
