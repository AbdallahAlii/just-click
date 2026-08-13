"use client";

import { useEffect, useRef, useState } from "react";
import AiMessage from "./AiMessage";
import AiSourceChips from "./AiSourceChips";
import { Sparkles } from "lucide-react";

function ThinkingDots() {
  return (
    <div className="flex items-start gap-2.5">
      <span className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-ds-action/10 text-ds-action">
        <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
      </span>
      <span className="inline-flex gap-1 pt-2">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-ds-text-muted [animation-delay:0ms]" />
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-ds-text-muted [animation-delay:150ms]" />
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-ds-text-muted [animation-delay:300ms]" />
      </span>
    </div>
  );
}

export default function AiMessageList({ messages, isLoading, isWide = false }) {
  const scrollRef = useRef(null);
  const bottomRef = useRef(null);
  const [showScrollTop, setShowScrollTop] = useState(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isLoading]);

  useEffect(() => {
    const node = scrollRef.current;
    if (!node) return undefined;

    const onScroll = () => {
      setShowScrollTop(node.scrollTop > 240);
    };

    onScroll();
    node.addEventListener("scroll", onScroll, { passive: true });
    return () => node.removeEventListener("scroll", onScroll);
  }, []);

  const scrollToTop = () => {
    scrollRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="relative min-h-0 flex-1">
      <div
        ref={scrollRef}
        className={`h-full overflow-y-auto overscroll-contain ${
          isWide ? "px-6 py-5" : "px-3 py-3"
        }`}
      >
        <div
          className={`mx-auto flex flex-col gap-5 ${
            isWide ? "max-w-3xl" : "max-w-none"
          }`}
        >
          {messages.length === 0 && !isLoading && (
            <div className="flex items-start gap-2.5">
              <span className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-ds-action/10 text-ds-action">
                <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
              </span>
              <p className="text-sm leading-relaxed text-ds-text-secondary">
                Hi — I can help with this material. Ask me to summarize, explain,
                quiz you, or generate study questions.
              </p>
            </div>
          )}

          {messages.map((message, index) => (
            <div key={`${message.role}-${index}`} className="space-y-1.5">
              <AiMessage
                role={message.role}
                content={message.content}
                isError={message.isError}
              />
              {message.role === "assistant" && message.sources?.length > 0 && (
                <AiSourceChips sources={message.sources} />
              )}
            </div>
          ))}

          {isLoading && <ThinkingDots />}
          <div ref={bottomRef} />
        </div>
      </div>

      {showScrollTop && (
        <button
          type="button"
          onClick={scrollToTop}
          aria-label="Scroll chat to top"
          className="absolute bottom-4 right-4 flex h-9 w-9 items-center justify-center rounded-full border border-ds-border bg-ds-surface text-ds-text-secondary shadow-sm transition-colors hover:text-ds-action"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 15l7-7 7 7" />
          </svg>
        </button>
      )}
    </div>
  );
}
