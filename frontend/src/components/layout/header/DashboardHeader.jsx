"use client";

import { useLogout, useMe } from "@/features/auth/hooks";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

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

export default function DashboardHeader() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);
  const router = useRouter();

  const { data: meData, isLoading: isMeLoading, isError: isMeError } = useMe();
  const logoutMutation = useLogout();

  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 12);
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const apiUser = meData?.data?.user;

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

  const safeUser = isMeError ? fallbackUser : user;
  const workspace = useMemo(() => getWorkspaceConfig(safeUser), [safeUser]);

  const handleLogout = async () => {
    try {
      setIsOpen(false);
      await logoutMutation.mutateAsync();
      router.replace("/login");
      router.refresh();
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  return (
    <header>
      <div
        className={`fixed top-0 left-0 right-0 z-50 transition-colors duration-200 ${
          isScrolled
            ? "border-b border-ds-border bg-ds-surface/95 py-2.5 backdrop-blur-md"
            : "border-b border-transparent bg-ds-page/80 py-3 backdrop-blur-sm"
        }`}
      >
        <div className="container">
          <div className="flex items-center justify-between gap-4">
            <Link
              href="/materials"
              className="inline-flex items-center rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action focus-visible:ring-offset-2 dark:focus-visible:ring-offset-ds-page"
            >
              <span className="text-xl font-bold tracking-tight sm:text-2xl">
                <span className="text-ds-text-primary">Just</span>
                <span className="text-ds-action">Click</span>
              </span>
            </Link>

            <div className="flex items-center gap-2 sm:gap-2.5">
              <Link
                href={workspace.href}
                className="hidden sm:inline-flex h-9 items-center rounded-lg bg-ds-action px-3 text-sm font-semibold text-white transition-colors hover:bg-ds-action-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action focus-visible:ring-offset-2 dark:focus-visible:ring-offset-ds-page"
              >
                {workspace.label}
              </Link>

              <div className="relative" ref={menuRef}>
                <button
                  type="button"
                  onClick={() => setIsOpen((prev) => !prev)}
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-ds-action text-sm font-bold text-white transition-colors hover:bg-ds-action-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action focus-visible:ring-offset-2 dark:focus-visible:ring-offset-ds-page"
                  aria-expanded={isOpen}
                  aria-label={`Account menu for ${safeUser.username}`}
                  title={safeUser.username}
                >
                  {isMeLoading ? (
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  ) : (
                    safeUser.initials
                  )}
                </button>

                <div
                  className={`absolute right-0 mt-2 w-64 origin-top-right overflow-hidden rounded-xl border border-ds-border bg-ds-surface shadow-lg transition-all duration-150 ${
                    isOpen
                      ? "visible translate-y-0 scale-100 opacity-100"
                      : "pointer-events-none invisible -translate-y-1 scale-95 opacity-0"
                  }`}
                >
                  <div className="border-b border-ds-border bg-ds-surface-secondary px-4 py-3">
                    {isMeLoading ? (
                      <div className="space-y-2">
                        <div className="h-4 w-32 animate-pulse rounded bg-ds-border" />
                        <div className="h-3 w-20 animate-pulse rounded bg-ds-border" />
                      </div>
                    ) : (
                      <>
                        <p className="truncate text-sm font-semibold text-ds-text-primary">
                          {safeUser.username}
                        </p>
                        <p className="truncate text-xs font-medium capitalize text-ds-text-muted">
                          {safeUser.primaryRole}
                        </p>
                      </>
                    )}
                  </div>

                  <div className="space-y-0.5 p-2">
                    <Link
                      href={workspace.href}
                      onClick={() => setIsOpen(false)}
                      className="flex w-full items-center rounded-lg px-3 py-2.5 text-sm font-medium text-ds-text-secondary transition-colors hover:bg-ds-surface-hover hover:text-ds-text-primary"
                    >
                      {workspace.label}
                    </Link>

                    <Link
                      href="/user-profile"
                      onClick={() => setIsOpen(false)}
                      className="flex w-full items-center rounded-lg px-3 py-2.5 text-sm font-medium text-ds-text-secondary transition-colors hover:bg-ds-surface-hover hover:text-ds-text-primary"
                    >
                      Profile Settings
                    </Link>

                    <div className="my-1 h-px bg-ds-border" />

                    <button
                      type="button"
                      onClick={handleLogout}
                      disabled={logoutMutation.isPending}
                      className="flex w-full items-center rounded-lg px-3 py-2.5 text-sm font-medium text-ds-error transition-colors hover:bg-ds-error/10 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {logoutMutation.isPending ? "Signing out..." : "Sign out"}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="h-14 sm:h-16" aria-hidden="true" />
    </header>
  );
}
