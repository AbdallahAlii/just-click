"use client";

import mobileMenu from "@/libs/mobileMenu";
import { useEffect } from "react";

const MobileMenuOpen = () => {
  useEffect(() => {
    mobileMenu();
  }, []);
  return (
    <button
      type="button"
      aria-label="Open menu"
      className="open-mobile-menu rounded-md text-2xl text-ds-text-primary transition-colors hover:text-ds-action focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action focus-visible:ring-offset-2 dark:focus-visible:ring-offset-ds-page"
    >
      <i className="icofont-navigation-menu" aria-hidden="true"></i>
    </button>
  );
};

export default MobileMenuOpen;
