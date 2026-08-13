"use client";

import ButtonPrimary from "@/components/shared/buttons/ButtonPrimary";
import Link from "next/link";

const MobileMenuSimple = () => {
  const navItems = [
    { name: "Features", path: "/#features" },
    { name: "How it works", path: "/#how" },
    { name: "FAQ", path: "/#faq" },
  ];

  return (
    <div className="flex flex-col space-y-6">
      <nav className="flex flex-col space-y-1 border-b border-ds-border pb-6">
        {navItems.map((item) => (
          <Link
            key={item.path}
            href={item.path}
            className="rounded-lg px-2 py-2.5 text-base font-medium text-ds-text-primary transition-colors hover:bg-ds-surface-hover hover:text-ds-action focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action"
          >
            {item.name}
          </Link>
        ))}
      </nav>

      <div className="flex flex-col gap-3">
        <ButtonPrimary variant="secondary" path="/login" width="full">
          Log in
        </ButtonPrimary>
        <ButtonPrimary path="/signup" width="full">
          Get started
        </ButtonPrimary>
      </div>

      <p className="pt-2 text-center text-xs text-ds-text-muted">
        JustClick — university materials portal
      </p>
    </div>
  );
};

export default MobileMenuSimple;
