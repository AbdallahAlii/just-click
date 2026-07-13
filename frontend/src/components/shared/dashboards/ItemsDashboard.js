"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const ItemDashboard = ({ item }) => {
  const currentPath = usePathname();
  const { name, path, icon, tag, subItems } = item;

  const hasSubItems = Array.isArray(subItems) && subItems.length > 0;

  const isSubPathActive = (sub) => {
    if (sub.activeMatch === "materials-root") {
      if (currentPath === sub.path) return true;
      if (!currentPath.startsWith(`${sub.path}/`)) return false;
      const suffix = currentPath.slice(sub.path.length + 1);
      return (
        !suffix.startsWith("reports") &&
        !suffix.startsWith("feedback") &&
        !suffix.startsWith("create")
      );
    }
    return currentPath === sub.path;
  };

  const isExactActive = currentPath === path;
  const isSubActive = hasSubItems
    ? subItems.some((sub) => isSubPathActive(sub))
    : false;

  const isActive = isExactActive || isSubActive;

  const [isOpen, setIsOpen] = useState(isSubActive);

  useEffect(() => {
    if (isSubActive) {
      setIsOpen(true);
    }
  }, [isSubActive]);

  const itemBaseClass =
    "group flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-sm transition-colors";

  const itemStateClass = isActive
    ? "bg-primaryColor/10 text-ds-action dark:text-ds-action"
    : "text-ds-text-secondary hover:bg-ds-surface-hover hover:text-ds-text-primary";

  const content = (
    <>
      <div className="flex min-w-0 items-center gap-3">
        <span
          className={`shrink-0 ${
            isActive
              ? "text-ds-action"
              : "text-ds-text-muted"
          }`}
        >
          {icon}
        </span>

        <span className="truncate font-medium">{name}</span>
      </div>

      <div className="ml-3 flex items-center gap-2">
        {tag ? (
          <span className="inline-flex min-w-[20px] items-center justify-center rounded-full bg-violet-600 px-2 py-0.5 text-[11px] font-semibold text-white">
            {tag}
          </span>
        ) : null}

        {hasSubItems ? (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={`shrink-0 transition-transform duration-200 ${
              isOpen ? "rotate-180" : ""
            }`}
          >
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        ) : null}
      </div>
    </>
  );

  return (
    <li>
      {hasSubItems ? (
        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          className={`${itemBaseClass} ${itemStateClass}`}
        >
          {content}
        </button>
      ) : (
        <Link href={path} className={`${itemBaseClass} ${itemStateClass}`}>
          {content}
        </Link>
      )}

      {hasSubItems ? (
        <ul
          className={`overflow-hidden pl-11 transition-all duration-300 ${
            isOpen ? "max-h-80 opacity-100 pt-1" : "max-h-0 opacity-0"
          }`}
        >
          {subItems.map((sub, index) => {
            const subActive = isSubPathActive(sub);

            return (
              <li key={index}>
                <Link
                  href={sub.path}
                  className={`block rounded-lg px-3 py-2 text-sm transition-colors min-h-[40px] focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-focus ${
                    subActive
                      ? "text-ds-action bg-primaryColor/10 font-medium"
                      : "text-ds-text-muted hover:text-ds-text-primary hover:bg-ds-surface-hover"
                  }`}
                >
                  {sub.name}
                </Link>
              </li>
            );
          })}
        </ul>
      ) : null}
    </li>
  );
};

export default ItemDashboard;
