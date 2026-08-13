export default function MaterialsLoading() {
  return (
    <div className="min-h-screen bg-ds-page">
      <div className="container py-8 lg:py-10">
        <div className="mb-8 animate-pulse space-y-2">
          <div className="h-8 w-52 rounded-lg bg-ds-surface-secondary" />
          <div className="h-4 w-80 max-w-full rounded bg-ds-surface-secondary" />
        </div>

        <div className="mb-4 h-11 animate-pulse rounded-xl border border-ds-border bg-ds-surface" />

        <div className="mb-6 flex animate-pulse flex-wrap gap-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="h-10 w-32 rounded-xl border border-ds-border bg-ds-surface"
            />
          ))}
        </div>

        <div className="overflow-hidden rounded-2xl border border-ds-border bg-ds-surface divide-y divide-ds-border">
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className="flex animate-pulse flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:gap-4 sm:px-5"
            >
              <div className="flex min-w-0 flex-1 items-start gap-3">
                <div className="h-11 w-11 shrink-0 rounded-xl bg-ds-surface-secondary" />
                <div className="min-w-0 flex-1 space-y-2">
                  <div className="h-4 w-3/4 rounded bg-ds-surface-secondary" />
                  <div className="h-3 w-1/2 rounded bg-ds-surface-secondary" />
                  <div className="h-3 w-2/5 rounded bg-ds-surface-secondary" />
                </div>
              </div>
              <div className="h-9 w-24 rounded-lg bg-ds-surface-secondary" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
