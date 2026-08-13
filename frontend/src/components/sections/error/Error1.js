"use client";

import Link from "next/link";

const Error1 = () => {
  return (
    <section className="bg-ds-page">
      <div className="container flex min-h-[70vh] flex-col items-center justify-center py-16 text-center">
        <p className="text-6xl font-bold tracking-tight text-ds-action sm:text-7xl">
          404
        </p>
        <h1 className="mt-4 text-2xl font-bold tracking-tight text-ds-text-primary sm:text-3xl">
          Page not found
        </h1>
        <p className="mt-3 max-w-md text-ds-text-secondary leading-relaxed">
          The page you&apos;re looking for doesn&apos;t exist or may have moved.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/"
            className="inline-flex min-h-[44px] items-center justify-center rounded-xl bg-ds-action px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-ds-action-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action focus-visible:ring-offset-2 dark:focus-visible:ring-offset-ds-page"
          >
            Go home
          </Link>
          <button
            type="button"
            onClick={() => window.history.back()}
            className="inline-flex min-h-[44px] items-center justify-center rounded-xl border border-ds-border bg-ds-surface px-5 py-2.5 text-sm font-semibold text-ds-text-primary transition-colors hover:bg-ds-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action focus-visible:ring-offset-2 dark:focus-visible:ring-offset-ds-page"
          >
            Back
          </button>
        </div>
      </div>
    </section>
  );
};

export default Error1;
