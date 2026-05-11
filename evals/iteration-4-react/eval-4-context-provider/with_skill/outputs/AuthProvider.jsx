import { createContext, useCallback, useContext, useMemo, useState } from "react";

const AuthContext = createContext(null);

export function AuthProvider({ children, initialUser = null }) {
  const [user, setUser] = useState(initialUser);

  const updateUser = useCallback((updates) => {
    setUser((prev) => {
      if (updates === null) return null;
      if (typeof updates === "function") return updates(prev);
      return { ...(prev ?? {}), ...updates };
    });
  }, []);

  const value = useMemo(() => ({ user, updateUser }), [user, updateUser]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (ctx === null) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
