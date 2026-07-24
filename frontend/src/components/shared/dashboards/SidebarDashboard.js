"use client";

import { useLogout, useMe } from "@/features/auth/hooks";
import { usePathname, useRouter } from "next/navigation";
import { useMemo } from "react";
import ItemsDashboard from "./ItemsDashboard";

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

const profileIcon = (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="18"
    height="18"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
    <circle cx="12" cy="7" r="4"></circle>
  </svg>
);

const SidebarDashboard = () => {
  const pathname = usePathname();
  const router = useRouter();

  const { data: meData, isError: isMeError } = useMe();
  const logoutMutation = useLogout();

  const isAdmin = pathname.startsWith("/admin/");
  const isInstructor = !isAdmin && pathname.includes("/instructor");
  const isStudent = !isAdmin && !isInstructor;

  const apiUser = meData?.data?.user;

  const safeUser = useMemo(() => {
    if (isMeError || !apiUser) return fallbackUser;

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
  }, [apiUser, isMeError]);

  const getUserLabel = () => {
    const username = safeUser?.username || fallbackUser.username;
    const roles = Array.isArray(safeUser?.roles) ? safeUser.roles : [];
    const normalizedRoles = roles.map(normalizeRole);
    const userType = normalizeRole(safeUser?.userType);
    const primaryRole = safeUser?.primaryRole || fallbackUser.primaryRole;

    if (isAdmin) {
      return {
        name: username,
        role:
          primaryRole && primaryRole !== "No role"
            ? primaryRole
            : normalizedRoles.includes("super admin")
              ? "Administrator"
              : userType === "admin"
                ? "Administrator"
                : "Administrator",
      };
    }

    if (isInstructor) {
      return {
        name: username,
        role:
          primaryRole && primaryRole !== "No role"
            ? primaryRole
            : normalizedRoles.includes("teacher")
              ? "Instructor"
              : userType === "teacher"
                ? "Instructor"
                : "Instructor",
      };
    }

    return {
      name: username,
      role:
        primaryRole && primaryRole !== "No role"
          ? primaryRole
          : normalizedRoles.includes("student")
            ? "Student"
            : userType === "student"
              ? "Student"
              : "Student",
    };
  };

  const user = getUserLabel();

  const handleLogout = async () => {
    try {
      await logoutMutation.mutateAsync();
      router.replace("/login");
      router.refresh();
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  const adminItems = [
    {
      title: "MAIN",
      items: [
        {
          name: "Dashboard",
          path: "/admin/dashboards/admin-dashboard",
          icon: (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
              <polyline points="9 22 9 12 15 12 15 22"></polyline>
            </svg>
          ),
        },
        {
          name: "Academic",
          path: "/admin/dashboards/admin-academic/courses",
          icon: (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
              <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
            </svg>
          ),
          subItems: [
            {
              name: "Departments",
              path: "/admin/dashboards/admin-academic/departments",
            },
            {
              name: "Courses",
              path: "/admin/dashboards/admin-academic/courses",
            },
            {
              name: "All Materials",
              path: "/admin/dashboards/admin-academic/materials",
              activeMatch: "materials-root",
            },
            {
              name: "Upload Material",
              path: "/admin/dashboards/admin-academic/materials/create",
            },
            {
              name: "Access Reports",
              path: "/admin/dashboards/admin-academic/materials/reports",
            },
            {
              name: "Feedback Inbox",
              path: "/admin/dashboards/admin-academic/materials/feedback",
            },
            {
              name: "Notifications",
              path: "/admin/dashboards/admin-academic/notifications",
            },
          ],
        },
        {
          name: "Students",
          path: "/admin/dashboards/admin-people/students",
          icon: (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="9" cy="7" r="4"></circle>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
            </svg>
          ),
        },
        {
          name: "Onboarding Queue",
          path: "/admin/dashboards/admin-people/onboarding",
          icon: (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="8.5" cy="7" r="4"></circle>
              <line x1="20" y1="8" x2="20" y2="14"></line>
              <line x1="23" y1="11" x2="17" y2="11"></line>
            </svg>
          ),
        },
        {
          name: "Profile",
          path: "/user-profile",
          icon: profileIcon,
        },
      ],
    },
  ];

  const instructorItems = [
    {
      title: "MAIN",
      items: [
        {
          name: "Dashboard",
          path: "/dashboards/instructor-dashboard",
          icon: (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
              <polyline points="9 22 9 12 15 12 15 22"></polyline>
            </svg>
          ),
        },
        {
          name: "Profile",
          path: "/user-profile",
          icon: profileIcon,
        },
      ],
    },
  ];

  const studentItems = [
    {
      title: "MAIN",
      items: [
        {
          name: "Dashboard",
          path: "/dashboards/student-dashboard",
          icon: (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
              <polyline points="9 22 9 12 15 12 15 22"></polyline>
            </svg>
          ),
        },
        {
          name: "Profile",
          path: "/user-profile",
          icon: profileIcon,
        },
      ],
    },
  ];

  const items = isAdmin
    ? adminItems
    : isInstructor
      ? instructorItems
      : studentItems;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="px-5 pt-5 pb-4 border-b border-gray-200/80 dark:border-slate-800">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-fuchsia-500 to-violet-600 text-sm font-semibold text-white shadow-sm">
            {user.name.charAt(0)}
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-gray-900 dark:text-white">
              {user.name}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {user.role}
            </p>
          </div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <div className="space-y-6">
          {items?.map((section, idx) => (
            <div key={idx}>
              <p className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-gray-400 dark:text-gray-500">
                {section.title}
              </p>
              <div className="space-y-1">
                {section.items.map((item, i) => (
                  <ItemsDashboard key={i} item={item} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </nav>

      <div className="border-t border-gray-200/80 dark:border-slate-800 p-3">
        <button
          onClick={handleLogout}
          disabled={logoutMutation.isPending}
          className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-red-600 transition-colors hover:bg-red-50 dark:hover:bg-red-950/30 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <svg
            className="h-[18px] w-[18px]"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
            />
          </svg>
          {logoutMutation.isPending ? "Signing out..." : "Logout"}
        </button>
      </div>
    </div>
  );
};

export default SidebarDashboard;
