"use client";

const QUICK_CHIPS = [
  "Summarize this material",
  "Explain simply",
  "Make a quiz",
  "Generate Q&A",
  "Key exam points",
];

export default function AiQuickChips({ onSelect, disabled, isWide = false }) {
  return (
    <div
      className={`flex flex-shrink-0 flex-wrap gap-1.5 pb-2 ${
        isWide ? "mx-auto w-full max-w-3xl px-6" : "px-3"
      }`}
    >
      {QUICK_CHIPS.map((chip) => (
        <button
          key={chip}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(chip)}
          className="rounded-full border border-ds-border bg-ds-surface px-3 py-1 text-xs text-ds-text-secondary transition-colors hover:border-ds-action/40 hover:text-ds-action disabled:cursor-not-allowed disabled:opacity-50"
        >
          {chip}
        </button>
      ))}
    </div>
  );
}
