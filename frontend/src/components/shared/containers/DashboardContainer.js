"use client";

import { useEffect, useState } from "react";
import SidebarDashboard from "../dashboards/SidebarDashboard";

const DESKTOP_BREAKPOINT = 1024;

const DashboardContainer = ({ children }) => {
  const [isDesktop, setIsDesktop] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [hasMounted, setHasMounted] = useState(false);

  useEffect(() => {
    const syncScreenState = () => {
      const desktop = window.innerWidth >= DESKTOP_BREAKPOINT;
      setIsDesktop(desktop);
      setIsSidebarOpen(desktop);
    };

    syncScreenState();
    setHasMounted(true);

    window.addEventListener("resize", syncScreenState);
    return () => window.removeEventListener("resize", syncScreenState);
  }, []);

  const toggleSidebar = () => {
    setIsSidebarOpen((prev) => !prev);
  };

  const closeSidebar = () => {
    if (!isDesktop) setIsSidebarOpen(false);
  };

  if (!hasMounted) {
    return (
      <section>
        <div className="container-fluid-2">
          <div className="pt-4 pb-100px">{children}</div>
        </div>
      </section>
    );
  }

  return (
    <section className="relative">
      <div className="container-fluid-2">
        <div className="flex items-center pt-4 pb-4">
          <button
            onClick={toggleSidebar}
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-gray-200 bg-white text-gray-600 shadow-sm transition-all hover:bg-gray-50 hover:text-gray-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-primaryColor dark:border-ds-border dark:bg-ds-surface dark:text-ds-text-secondary dark:hover:bg-ds-surface-hover dark:hover:text-ds-text-primary"
            title={isSidebarOpen ? "Close Sidebar" : "Open Sidebar"}
            aria-label={isSidebarOpen ? "Close Sidebar" : "Open Sidebar"}
          >
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
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <line x1="3" y1="12" x2="21" y2="12"></line>
              <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
          </button>
        </div>

        <div className="relative pb-100px">
          {!isDesktop && (
            <>
              <div
                className={`fixed inset-0 z-40 bg-slate-950/35 backdrop-blur-[1px] transition-opacity duration-300 ${
                  isSidebarOpen
                    ? "pointer-events-auto opacity-100"
                    : "pointer-events-none opacity-0"
                }`}
                onClick={closeSidebar}
              />

              <aside
                className={`fixed left-0 top-0 z-50 h-dvh w-[88%] max-w-[340px] transform transition-transform duration-300 ${
                  isSidebarOpen ? "translate-x-0" : "-translate-x-full"
                }`}
              >
                <div className="flex h-full flex-col bg-white dark:bg-ds-surface shadow-2xl">
                  <div className="flex items-center justify-between border-b border-gray-200/80 px-5 py-4 dark:border-ds-border">
                    <h2 className="text-sm font-semibold text-gray-900 dark:text-ds-text-primary">
                      Dashboard Menu
                    </h2>

                    <button
                      onClick={closeSidebar}
                className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-gray-200 text-gray-500 transition-colors hover:bg-gray-50 hover:text-gray-900 dark:border-ds-border dark:text-ds-text-muted dark:hover:bg-ds-surface-hover dark:hover:text-ds-text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-focus"
                      aria-label="Close sidebar"
                    >
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
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                      </svg>
                    </button>
                  </div>

                  <div className="min-h-0 flex-1">
                    <SidebarDashboard />
                  </div>
                </div>
              </aside>
            </>
          )}

          {isDesktop ? (
            <div
              className={`grid gap-6 transition-all duration-300 ${
                isSidebarOpen ? "lg:grid-cols-12" : "grid-cols-1"
              }`}
            >
              {isSidebarOpen && (
                <aside className="hidden lg:block lg:col-span-3 xl:col-span-3 2xl:col-span-2">
                  <div className="sticky top-6 overflow-hidden rounded-3xl border border-gray-200/80 bg-white shadow-sm dark:border-ds-border dark:bg-ds-surface">
                    <div className="h-[calc(100vh-110px)] min-h-[620px]">
                      <SidebarDashboard />
                    </div>
                  </div>
                </aside>
              )}

              <main
                className={`min-w-0 ${
                  isSidebarOpen
                    ? "lg:col-span-9 xl:col-span-9 2xl:col-span-10"
                    : "col-span-1"
                }`}
              >
                {children}
              </main>
            </div>
          ) : (
            <main className="min-w-0">{children}</main>
          )}
        </div>
      </div>
    </section>
  );
};

export default DashboardContainer;
