"use client";

import { useEffect, useRef } from "react";
import { ArrowUp } from "lucide-react";

export default function AiComposer({
  value,
  onChange,
  onSend,
  disabled,
  placeholder = "Ask JustClick AI about this material…",
  isWide = false,
  isSending = false,
}) {
  const textareaRef = useRef(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const next = Math.min(el.scrollHeight, isWide ? 180 : 140);
    el.style.height = `${Math.max(next, 44)}px`;
  }, [value, isWide]);

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!disabled && value.trim()) onSend();
    }
  };

  const canSend = !disabled && !!value.trim() && !isSending;

  return (
    <div
      className={`flex-shrink-0 border-t border-ds-border bg-ds-surface ${
        isWide ? "px-6 py-4" : "px-3 py-3"
      }`}
    >
      <div className={`mx-auto ${isWide ? "max-w-3xl" : ""}`}>
        <div className="relative rounded-xl border border-ds-border bg-ds-surface-secondary focus-within:border-ds-action/50 focus-within:ring-2 focus-within:ring-ds-action/20">
          <textarea
            ref={textareaRef}
            rows={1}
            value={value}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled || isSending}
            placeholder={placeholder}
            className="max-h-[180px] min-h-[44px] w-full resize-none bg-transparent px-3.5 py-3 pr-12 text-sm leading-5 text-ds-text-primary outline-none placeholder:text-ds-text-muted disabled:cursor-not-allowed disabled:opacity-50"
          />
          <button
            type="button"
            onClick={onSend}
            disabled={!canSend}
            className="absolute bottom-2 right-2 flex h-8 w-8 items-center justify-center rounded-lg bg-ds-action text-white transition-colors hover:bg-ds-action-hover disabled:cursor-not-allowed disabled:bg-ds-border disabled:text-ds-text-muted"
            aria-label="Send message"
          >
            {isSending ? (
              <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
            ) : (
              <ArrowUp className="h-4 w-4" aria-hidden="true" />
            )}
          </button>
        </div>
        <p className="mt-1.5 px-0.5 text-[11px] text-ds-text-muted">
          Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
