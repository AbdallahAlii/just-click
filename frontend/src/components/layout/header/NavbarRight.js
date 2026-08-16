"use client";

import ButtonPrimary from "@/components/shared/buttons/ButtonPrimary";
import MobileMenuOpen from "@/components/shared/buttons/MobileMenuOpen";
import { useLogout } from "@/features/auth/hooks";
import { useSession } from "@/providers/SessionProvider";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo } from "react";

const fallbackUser = {
  username: "User",
  userType: "user",
  primaryRole: "No role",
  initials: "U",
  roles: [],
};

function getInitials(username) {
  return (
    username
      ?.split(/[\s._-]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join("") || "U"
  );
}

function normalizeRole(role) {
  return String(role || "")
    .trim()
    .toLowerCase();
}

function getWorkspaceConfig(user) {
  const roles = Array.isArray(user?.roles) ? user.roles : [];
  const normalizedRoles = roles.map(normalizeRole);
  const userType = normalizeRole(user?.userType);

  if (normalizedRoles.includes("super admin")) {
    return { label: "Workspace", href: "/admin/dashboards/admin-dashboard" };
  }

  if (normalizedRoles.includes("teacher") || userType === "teacher") {
    return {
      label: "Workspace",
      href: "/teacher/dashboards/teacher-dashboard",
    };
  }

  if (normalizedRoles.includes("student") || userType === "student") {
    return { label: "Workspace", href: "/materials" };
  }

  if (userType === "admin") {
    return { label: "Workspace", href: "/admin/dashboards/admin-dashboard" };
  }

  return { label: "Workspace", href: "/materials" };
}

const NavbarRight = () => {
  const router = useRouter();
  const { user: apiUser, isLoading, isError } = useSession();
  const logoutMutation = useLogout();

  const user = useMemo(() => {
    if (!apiUser) return fallbackUser;

    const username = apiUser?.username || fallbackUser.username;
    const userType = apiUser?.user_type || fallbackUser.userType;
    const roles = Array.isArray(apiUser?.roles) ? apiUser.roles : [];
    const primaryRole = roles[0] || fallbackUser.primaryRole;

    return {
      username,
      userType,
      primaryRole,
      roles,
      initials: getInitials(username),
    };
  }, [apiUser]);

  const safeUser = isError ? fallbackUser : user;
  const workspace = useMemo(() => getWorkspaceConfig(safeUser), [safeUser]);
  const isLoggedIn = !!apiUser && !isError;

  const handleLogout = async () => {
    try {
      await logoutMutation.mutateAsync();
      router.replace("/login");
      router.refresh();
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  return (
    <div className="flex items-center gap-3 sm:gap-4">
      <div className="hidden items-center gap-3 sm:flex">
        {isLoading ? (
          <>
            <div className="h-10 w-20 animate-pulse rounded-xl bg-ds-surface-secondary" />
            <div className="h-10 w-28 animate-pulse rounded-xl bg-ds-surface-secondary" />
          </>
        ) : isLoggedIn ? (
          <>
            <ButtonPrimary variant="secondary" path="/materials" size="sm">
              Materials
            </ButtonPrimary>
            <ButtonPrimary path={workspace.href} size="sm">
              {workspace.label}
            </ButtonPrimary>
            <Link
              href="/user-profile"
              className="flex h-10 w-10 items-center justify-center rounded-full bg-ds-action text-sm font-bold text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action focus-visible:ring-offset-2 dark:focus-visible:ring-offset-ds-page"
              title={safeUser.username}
            >
              {safeUser.initials}
            </Link>
            <button
              type="button"
              onClick={handleLogout}
              disabled={logoutMutation.isPending}
              className="text-sm font-semibold text-ds-text-secondary transition-colors hover:text-ds-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action focus-visible:ring-offset-2 disabled:opacity-50 rounded-md"
            >
              {logoutMutation.isPending ? "Signing out..." : "Log out"}
            </button>
          </>
        ) : (
          <>
            <Link
              href="/login"
              className="text-sm font-semibold text-ds-text-secondary transition-colors hover:text-ds-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action focus-visible:ring-offset-2 rounded-md"
            >
              Log in
            </Link>
            <ButtonPrimary path="/signup" size="sm">
              Get started
            </ButtonPrimary>
          </>
        )}
      </div>

      <div className="sm:hidden">
        <MobileMenuOpen />
      </div>
    </div>
  );
};

export default NavbarRight;
