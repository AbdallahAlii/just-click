export default function MaterialDetailLoading() {
  return (
    <div className="min-h-screen bg-ds-page">
      <div className="container py-8 lg:py-12 animate-pulse">
        <div className="mb-8 h-4 w-36 rounded bg-ds-surface-secondary" />

        <div className="mb-3 h-5 w-16 rounded-lg bg-ds-surface-secondary" />
        <div className="mb-3 h-9 w-3/4 max-w-2xl rounded-lg bg-ds-surface-secondary" />
        <div className="mb-2 h-5 w-48 rounded bg-ds-surface-secondary" />
        <div className="mb-6 h-4 w-40 rounded bg-ds-surface-secondary" />
        <div className="mb-8 h-4 w-72 rounded bg-ds-surface-secondary" />

        <div className="mb-10 flex flex-wrap gap-2">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-11 w-28 rounded-xl bg-ds-surface-secondary"
            />
          ))}
        </div>

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          <div className="space-y-6 lg:col-span-8">
            <div className="h-40 rounded-2xl border border-ds-border bg-ds-surface" />
            <div className="h-32 rounded-2xl border border-ds-border bg-ds-surface" />
            <div className="h-48 rounded-2xl border border-ds-border bg-ds-surface" />
          </div>
          <div className="space-y-4 lg:col-span-4">
            <div className="h-48 rounded-2xl border border-ds-border bg-ds-surface" />
            <div className="h-40 rounded-2xl border border-ds-border bg-ds-surface" />
          </div>
        </div>
      </div>
    </div>
  );
}
