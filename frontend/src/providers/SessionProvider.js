"use client";

import React from "react";
import { useMe } from "@/features/auth/hooks";

const SessionCtx = React.createContext(null);

export function useSession() {
  return React.useContext(SessionCtx);
}

export default function SessionProvider({ children }) {
  const q = useMe({
    retry: false,
    refetchOnWindowFocus: false,
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
