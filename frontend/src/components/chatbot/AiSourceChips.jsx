"use client";

function sourceLabel(source) {
  return (
    source.label ||
    source.chapter_label ||
    source.course_title ||
    "This material"
  );
}

export default function AiSourceChips({ sources = [] }) {
  if (!sources.length) return null;

  const unique = [];
  const seen = new Set();

  for (const source of sources) {
    const label = sourceLabel(source);
    const key = label.trim().toLowerCase();
    if (!key || seen.has(key)) continue;
    seen.add(key);
    unique.push({ ...source, label });
  }

  if (!unique.length) return null;

  return (
    <div className="ml-8 flex flex-wrap items-center gap-1.5">
      <span className="text-xs text-ds-text-muted">Based on:</span>
      {unique.map((source, index) => (
        <span
          key={`${source.label}-${index}`}
          className="rounded-full border border-ds-border bg-ds-surface px-2.5 py-0.5 text-xs text-ds-text-secondary"
        >
          {source.label}
        </span>
      ))}
    </div>
  );
}
