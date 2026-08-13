"use client";

import Link from "next/link";

const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t border-ds-border bg-ds-surface-secondary">
      <div className="mx-auto w-full max-w-[1400px] px-6 sm:px-8 lg:px-12">
        <div className="flex flex-col gap-10 py-12 md:flex-row md:items-center md:justify-between md:gap-14 md:py-14">
          <div className="flex min-w-0 flex-1 items-center">
            <Link
              href="/"
              className="inline-flex items-center rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action focus-visible:ring-offset-2 dark:focus-visible:ring-offset-ds-page"
            >
              <span className="text-2xl font-bold tracking-tight md:text-[28px]">
                <span className="text-ds-text-primary">Just</span>
                <span className="text-ds-action">Click</span>
              </span>
            </Link>
          </div>

          <div className="flex flex-wrap items-center justify-start gap-x-8 gap-y-3 md:flex-1 md:justify-center">
            <Link
              href="/privacy"
              className="text-sm font-medium text-ds-text-secondary transition-colors hover:text-ds-action focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action rounded-md"
            >
              Privacy
            </Link>
            <Link
              href="/terms"
              className="text-sm font-medium text-ds-text-secondary transition-colors hover:text-ds-action focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action rounded-md"
            >
              Terms
            </Link>
            <Link
              href="/contact"
              className="text-sm font-medium text-ds-text-secondary transition-colors hover:text-ds-action focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action rounded-md"
            >
              Contact
            </Link>
          </div>

          <div className="flex min-w-0 flex-1 items-center md:justify-end">
            <p className="text-sm font-medium text-ds-text-muted">
              © {currentYear} JustClick
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
