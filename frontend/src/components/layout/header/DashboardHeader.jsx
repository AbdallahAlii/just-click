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
    const handleScroll = () => setIsScrolled(window.scrollY > 20);
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
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ease-in-out ${
          isScrolled
            ? "bg-white/90 dark:bg-ds-surface/95 backdrop-blur-lg border-b border-borderColor/50 dark:border-ds-border shadow-sm py-2"
            : "bg-transparent dark:bg-transparent py-4"
        }`}
      >
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between transition-all duration-300">
            {/* Logo */}
            <Link
              href="/materials"
              className="flex items-center group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primaryColor rounded-lg"
            >
              <span className="text-2xl font-extrabold tracking-tight text-blackColor dark:text-whiteColor transition-transform group-hover:scale-105">
                Just<span className="text-primaryColor">Click</span>
              </span>
            </Link>

            <div className="flex items-center gap-3 sm:gap-4">
              {/* Workspace CTA Button */}
              <Link
                href={workspace.href}
                className="hidden sm:inline-flex items-center gap-2 rounded-xl bg-primaryColor px-3.5 py-2 text-sm font-medium text-white shadow-sm transition-all duration-200 hover:bg-primaryColor/90 hover:shadow-md hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primaryColor focus-visible:ring-offset-2 dark:focus-visible:ring-offset-blackColor"
              >
                <svg
                  className="h-3.5 w-3.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2.25}
                    d="M3 7.5A2.5 2.5 0 015.5 5h4A2.5 2.5 0 0112 7.5v4A2.5 2.5 0 019.5 14h-4A2.5 2.5 0 013 11.5v-4zM12 7.5A2.5 2.5 0 0114.5 5h4A2.5 2.5 0 0121 7.5v9a2.5 2.5 0 01-2.5 2.5h-4A2.5 2.5 0 0112 16.5v-9z"
                  />
                </svg>
                <span className="leading-none">{workspace.label}</span>
              </Link>

              {/* Profile Dropdown Container */}
              <div className="relative" ref={menuRef}>
                <button
                  onClick={() => setIsOpen((prev) => !prev)}
                  className="flex items-center gap-2.5 rounded-full p-1 pr-2.5 border border-transparent hover:border-borderColor dark:hover:border-borderColor-dark transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primaryColor"
                  aria-expanded={isOpen}
                  aria-label="User menu"
                >
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primaryColor text-sm font-bold text-white shadow-inner">
                    {isMeLoading ? (
                      <div className="h-4.5 w-4.5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                    ) : (
                      safeUser.initials
                    )}
                  </div>

                  <div className="hidden md:block text-left">
                    {isMeLoading ? (
                      <div className="space-y-1.5 py-1">
                        <div className="h-3 w-24 rounded bg-gray-200 dark:bg-gray-800 animate-pulse" />
                        <div className="h-2 w-16 rounded bg-gray-100 dark:bg-gray-900 animate-pulse" />
                      </div>
                    ) : (
                      <>
                        <p className="text-sm font-semibold leading-tight text-blackColor dark:text-whiteColor">
                          {safeUser.username}
                        </p>
                        <p className="text-xs font-medium text-gray-500 capitalize dark:text-gray-400">
                          {safeUser.primaryRole}
                        </p>
                      </>
                    )}
                  </div>

                  <svg
                    className={`h-4 w-4 text-gray-400 transition-transform duration-300 ${
                      isOpen ? "-rotate-180" : ""
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </button>

                {/* Dropdown Menu */}
                <div
                  className={`absolute right-0 mt-3 w-64 origin-top-right overflow-hidden rounded-2xl border border-borderColor/80 bg-white shadow-xl backdrop-blur-xl dark:border-borderColor-dark/80 dark:bg-blackColor transition-all duration-200 ease-out ${
                    isOpen
                      ? "scale-100 opacity-100 visible translate-y-0"
                      : "scale-95 opacity-0 invisible -translate-y-2 pointer-events-none"
                  }`}
                >
                  <div className="border-b border-borderColor/50 bg-gray-50/50 px-5 py-4 dark:border-borderColor-dark/50 dark:bg-white/[0.02]">
                    {isMeLoading ? (
                      <div className="space-y-2">
                        <div className="h-4 w-32 rounded bg-gray-200 dark:bg-gray-800 animate-pulse" />
                        <div className="h-3 w-20 rounded bg-gray-200 dark:bg-gray-800 animate-pulse" />
                      </div>
                    ) : (
                      <>
                        <p className="truncate text-sm font-bold text-blackColor dark:text-whiteColor">
                          {safeUser.username}
                        </p>
                        <p className="truncate text-xs font-medium text-gray-500 capitalize dark:text-gray-400">
                          {safeUser.primaryRole}
                        </p>
                      </>
                    )}
                  </div>

                  <div className="p-2 space-y-0.5">
                    <Link
                      href={workspace.href}
                      onClick={() => setIsOpen(false)}
                      className="group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-100 hover:text-blackColor dark:text-gray-300 dark:hover:bg-white/5 dark:hover:text-whiteColor"
                    >
                      <svg
                        className="h-5 w-5 text-gray-400 group-hover:text-primaryColor transition-colors"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={1.5}
                          d="M3 7.5A2.5 2.5 0 015.5 5h4A2.5 2.5 0 0112 7.5v4A2.5 2.5 0 019.5 14h-4A2.5 2.5 0 013 11.5v-4zM12 7.5A2.5 2.5 0 0114.5 5h4A2.5 2.5 0 0121 7.5v9a2.5 2.5 0 01-2.5 2.5h-4A2.5 2.5 0 0112 16.5v-9z"
                        />
                      </svg>
                      {workspace.label}
                    </Link>

                    <Link
                      href="/user-profile"
                      onClick={() => setIsOpen(false)}
                      className="group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-100 hover:text-blackColor dark:text-gray-300 dark:hover:bg-white/5 dark:hover:text-whiteColor"
                    >
                      <svg
                        className="h-5 w-5 text-gray-400 group-hover:text-primaryColor transition-colors"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={1.5}
                          d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                        />
                      </svg>
                      Profile Settings
                    </Link>

                    <div className="my-1.5 h-px bg-borderColor/50 dark:bg-borderColor-dark/50" />

                    <button
                      onClick={handleLogout}
                      disabled={logoutMutation.isPending}
                      className="group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-red-600 transition-colors hover:bg-red-50 hover:text-red-700 disabled:cursor-not-allowed disabled:opacity-50 dark:text-red-400 dark:hover:bg-red-500/10 dark:hover:text-red-300"
                    >
                      <svg
                        className="h-5 w-5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={1.5}
                          d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                        />
                      </svg>
                      {logoutMutation.isPending ? "Signing out..." : "Sign out"}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="h-[72px] md:h-[88px]" aria-hidden="true" />
    </header>
  );
}
