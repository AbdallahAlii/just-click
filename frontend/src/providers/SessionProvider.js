"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { useMe } from "@/features/auth/hooks";

const SessionCtx = React.createContext(null);

const PUBLIC_AUTH_PREFIXES = [
  "/login",
  "/signup",
  "/verify-email",
  "/forgot-password",
  "/reset-password",
  "/privacy",
  "/terms",
  "/contact",
];

export function useSession() {
  return React.useContext(SessionCtx);
}

export default function SessionProvider({ children }) {
  const pathname = usePathname();
  const isPublicAuthRoute = PUBLIC_AUTH_PREFIXES.some((prefix) => pathname?.startsWith(prefix));

  const q = useMe({
    enabled: !isPublicAuthRoute,
    retry: false,
  });
  const user = q.data?.data?.user || null;

  const value = React.useMemo(() => {
    return {
      ...q,
      user,
      roles: user?.roles || [],
      permissions: user?.permissions || [],
      userType: user?.user_type || null,
      isAdmin: (user?.user_type || "").toLowerCase() === "admin",
    };
  }, [q, user]);

  return <SessionCtx.Provider value={value}>{children}</SessionCtx.Provider>;
}
