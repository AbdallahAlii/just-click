"use client";

import ReactMarkdown from "react-markdown";
import { Sparkles } from "lucide-react";

export default function AiMessage({ role, content, isError = false }) {
  const isUser = role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-ds-surface-secondary px-3.5 py-2.5 text-sm leading-relaxed text-ds-text-primary">
          {content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2.5">
      <span className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-ds-action/10 text-ds-action">
        <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
      </span>
      <div
        className={`min-w-0 max-w-[48rem] flex-1 text-sm leading-relaxed ${
          isError ? "text-ds-error" : "text-ds-text-secondary"
        }`}
      >
        <ReactMarkdown
          components={{
            p: ({ children }) => <p className="my-2 first:mt-0 last:mb-0">{children}</p>,
            ul: ({ children }) => (
              <ul className="my-2 ml-5 list-disc space-y-1.5">{children}</ul>
            ),
            ol: ({ children }) => (
              <ol className="my-2 ml-5 list-decimal space-y-1.5">{children}</ol>
            ),
            li: ({ children }) => <li className="leading-relaxed">{children}</li>,
            h2: ({ children }) => (
              <h2 className="mt-4 mb-1.5 text-base font-semibold text-ds-text-primary">
                {children}
              </h2>
            ),
            h3: ({ children }) => (
              <h3 className="mt-3 mb-1 text-sm font-semibold text-ds-text-primary">
                {children}
              </h3>
            ),
            strong: ({ children }) => (
              <strong className="font-semibold text-ds-text-primary">{children}</strong>
            ),
            code: ({ children, className }) => {
              const isBlock = typeof className === "string" && className.includes("language-");
              if (isBlock) {
                return (
                  <code className="my-2 block overflow-x-auto rounded-lg bg-ds-surface-secondary p-3 text-xs text-ds-text-primary">
                    {children}
                  </code>
                );
              }
              return (
                <code className="rounded bg-ds-surface-secondary px-1 py-0.5 text-xs text-ds-text-primary">
                  {children}
                </code>
              );
            },
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
}
