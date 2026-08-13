"use client";

import { useMemo, useState } from "react";
import { groupSessionsByDate } from "./chatSessionStorage";
import { IconButton, IconPanelLeft } from "./AiChatIcons";
import { Plus, Search } from "lucide-react";

export default function AiChatSidebar({
  sessions = [],
  activeSessionId,
  onSelectSession,
  onNewChat,
  onCollapse,
  showCollapse = false,
  materialTitle = "Material",
}) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return sessions;
    return sessions.filter((item) =>
      (item.title || "").toLowerCase().includes(q),
    );
  }, [query, sessions]);

  const groups = useMemo(() => groupSessionsByDate(filtered), [filtered]);

  return (
    <aside className="flex h-full w-[260px] flex-shrink-0 flex-col border-r border-ds-border bg-ds-surface-secondary">
      <div className="flex flex-shrink-0 items-center justify-between gap-2 px-3 py-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-ds-text-primary">
            JustClick AI
          </p>
          <p className="truncate text-xs text-ds-text-muted" title={materialTitle}>
            {materialTitle}
          </p>
        </div>
        {showCollapse && onCollapse ? (
          <IconButton label="Collapse sidebar" onClick={onCollapse}>
            <IconPanelLeft />
          </IconButton>
        ) : null}
      </div>

      <div className="flex-shrink-0 space-y-2 px-3 pb-3">
        <button
          type="button"
          onClick={onNewChat}
          className="flex h-9 w-full items-center justify-center gap-1.5 rounded-lg bg-ds-action px-3 text-sm font-semibold text-white transition-colors hover:bg-ds-action-hover"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          New chat
        </button>
        <div className="relative">
          <Search
            className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ds-text-muted"
            aria-hidden="true"
          />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search chats…"
            className="h-9 w-full rounded-lg border border-ds-border bg-ds-surface pl-8 pr-2.5 text-sm text-ds-text-primary outline-none placeholder:text-ds-text-muted focus:ring-2 focus:ring-ds-action/20"
          />
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-2 pb-3">
        {groups.length === 0 ? (
          <p className="px-2 py-6 text-center text-xs leading-relaxed text-ds-text-muted">
            Your chats for this material will appear here.
          </p>
        ) : null}

        {groups.map((group) => (
          <div key={group.label} className="mb-3">
            <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-ds-text-muted">
              {group.label}
            </p>
            <div className="space-y-0.5">
              {group.sessions.map((session) => {
                const isActive = session.sessionId === activeSessionId;
                const title = session.title || "New chat";
                return (
                  <button
                    key={session.sessionId}
                    type="button"
                    onClick={() => onSelectSession(session.sessionId)}
                    title={title}
                    className={`w-full rounded-lg px-2.5 py-2 text-left text-[13px] transition-colors ${
                      isActive
                        ? "bg-ds-action/10 font-medium text-ds-action"
                        : "text-ds-text-secondary hover:bg-ds-surface hover:text-ds-text-primary"
                    }`}
                  >
                    <span className="block truncate leading-snug">{title}</span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
