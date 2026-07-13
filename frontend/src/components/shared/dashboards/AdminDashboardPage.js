"use client";

/**
 * Shared admin page shell — consistent max-width, header, and spacing.
 */
export default function AdminDashboardPage({
  title,
  description,
  action,
  children,
  className = "",
}) {
  return (
    <div
      className={`w-full max-w-screen-2xl mx-auto space-y-6 sm:space-y-8 ${className}`}
    >
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-ds-text-primary">
            {title}
          </h1>
          {description ? (
            <p className="mt-2 text-sm leading-relaxed text-ds-text-muted max-w-3xl">
              {description}
            </p>
          ) : null}
        </div>
        {action ? (
          <div className="shrink-0 w-full sm:w-auto">{action}</div>
        ) : null}
      </header>
      {children}
    </div>
  );
}

export function AdminMetricCard({ label, value, hint, icon: Icon }) {
  return (
    <div className="rounded-2xl border border-ds-border bg-ds-surface p-4 sm:p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-ds-text-muted">
          {label}
        </p>
        {Icon ? (
          <span className="text-ds-text-muted" aria-hidden="true">
            <Icon className="w-4 h-4" />
          </span>
        ) : null}
      </div>
      <p className="mt-2 text-2xl sm:text-3xl font-bold text-ds-text-primary tabular-nums">
        {value}
      </p>
      {hint ? (
        <p className="mt-1.5 text-xs sm:text-sm text-ds-text-muted leading-snug">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

export function AdminReportCard({ title, children, emptyMessage, isEmpty }) {
  return (
    <section className="rounded-2xl border border-ds-border bg-ds-surface shadow-sm overflow-hidden h-full flex flex-col">
      <div className="px-4 sm:px-5 py-4 border-b border-ds-border-subtle">
        <h2 className="text-base sm:text-lg font-semibold text-ds-text-primary">
          {title}
        </h2>
      </div>
      <div className="px-4 sm:px-5 py-4 flex-1">
        {isEmpty && emptyMessage ? (
          <p className="text-sm text-ds-text-muted py-6 text-center">
            {emptyMessage}
          </p>
        ) : (
          children
        )}
      </div>
    </section>
  );
}

export function AdminReportRow({ primary, secondary, meta, href }) {
  const content = (
    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 sm:gap-4 py-3 border-b border-ds-border-subtle last:border-0 last:pb-0">
      <div className="min-w-0 flex-1">
        <p className="font-medium text-ds-text-primary break-words">{primary}</p>
        {secondary ? (
          <p className="mt-0.5 text-xs text-ds-text-muted break-words">
            {secondary}
          </p>
        ) : null}
      </div>
      {meta ? (
        <p className="text-sm text-ds-text-secondary shrink-0 tabular-nums">
          {meta}
        </p>
      ) : null}
    </div>
  );

  if (href) {
    return (
      <a
        href={href}
        className="block rounded-lg -mx-2 px-2 hover:bg-ds-surface-hover transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-focus"
      >
        {content}
      </a>
    );
  }

  return content;
}

export function AdminSkeletonBlock({ lines = 4 }) {
  return (
    <div className="space-y-3 animate-pulse" aria-hidden="true">
      {[...Array(lines)].map((_, i) => (
        <div
          key={i}
          className="h-12 rounded-xl bg-ds-surface-secondary"
          style={{ width: `${100 - i * 8}%` }}
        />
      ))}
    </div>
  );
}
