"use client";

import Link from "next/link";

const NavbarLogo = () => {
  return (
    <div className="flex items-center">
      <Link
        href="/"
        aria-label="JustClick Home"
        className="inline-flex items-center rounded-md select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action focus-visible:ring-offset-2 dark:focus-visible:ring-offset-ds-page"
      >
        <span className="text-xl font-bold leading-none tracking-tight sm:text-2xl">
          <span className="text-ds-text-primary">Just</span>
          <span className="text-ds-action">Click</span>
        </span>
      </Link>
    </div>
  );
};

export default NavbarLogo;
