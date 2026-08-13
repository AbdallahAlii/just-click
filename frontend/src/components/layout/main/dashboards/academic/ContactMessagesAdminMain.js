"use client";

import { useMemo, useState } from "react";
import toast from "react-hot-toast";
import {
  useAdminContactMessages,
  useHandleContactMessage,
} from "@/features/contact/hooks";
import { getApiErrorMessage } from "@/lib/apiErrors";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "open", label: "Open" },
  { value: "in_progress", label: "In progress" },
  { value: "resolved", label: "Resolved" },
  { value: "spam", label: "Spam" },
];

export default function ContactMessagesAdminMain() {
  const [status, setStatus] = useState("open");
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState(null);
  const [reply, setReply] = useState("");
  const [notes, setNotes] = useState("");
  const [nextStatus, setNextStatus] = useState("resolved");

  const params = useMemo(() => ({ status, page, per_page: 20 }), [status, page]);
  const { data, isLoading, refetch } = useAdminContactMessages(params);
  const handleMut = useHandleContactMessage();

  const items = data?.data?.items || [];
  const pagination = data?.data?.pagination || {};
  const selected = items.find((i) => i.id === selectedId) || null;

  const onSelect = (item) => {
    setSelectedId(item.id);
    setReply(item.admin_reply || "");
    setNotes(item.admin_notes || "");
    setNextStatus(item.status || "in_progress");
  };

  const onHandle = async ({ sendEmail }) => {
    if (!selectedId) return;
    try {
      await handleMut.mutateAsync({
        contactId: selectedId,
        payload: {
          status: nextStatus,
          admin_notes: notes,
          admin_reply: reply,
          send_reply_email: Boolean(sendEmail),
        },
      });
      toast.success(sendEmail ? "Reply emailed and saved." : "Message updated.");
      refetch();
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Could not update message."));
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-ds-text-primary">
            Contact messages
          </h1>
          <p className="text-sm text-ds-text-muted mt-1">
            Public Contact Us submissions. Notifications also go to{" "}
            justclick.cmc@gmail.com via EmailOutbox.
          </p>
        </div>
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
            setSelectedId(null);
          }}
          className="h-10 rounded-lg border border-ds-border bg-ds-surface-input px-3 text-sm text-ds-text-primary"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value || "all"} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-2 rounded-2xl border border-ds-border bg-ds-surface overflow-hidden">
          {isLoading ? (
            <p className="p-4 text-sm text-ds-text-muted">Loading...</p>
          ) : items.length === 0 ? (
            <p className="p-4 text-sm text-ds-text-muted">No messages.</p>
          ) : (
            <ul className="divide-y divide-ds-border-subtle">
              {items.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(item)}
                    className={`w-full text-left px-4 py-3 transition ${
                      selectedId === item.id
                        ? "bg-ds-action/10"
                        : "hover:bg-ds-surface-secondary"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-ds-text-primary truncate">
                        {item.subject}
                      </p>
                      <span className="text-[11px] uppercase text-ds-text-muted">
                        {item.status}
                      </span>
                    </div>
                    <p className="text-xs text-ds-text-muted mt-1 truncate">
                      {item.name} · {item.email}
                    </p>
                    <p className="text-[11px] text-ds-text-muted mt-0.5">
                      {item.created_at
                        ? new Date(item.created_at).toLocaleString()
                        : ""}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {pagination.pages > 1 ? (
            <div className="flex items-center justify-between px-4 py-3 border-t border-ds-border-subtle">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="text-xs font-semibold text-ds-action disabled:opacity-40"
              >
                Previous
              </button>
              <span className="text-xs text-ds-text-muted">
                Page {pagination.page} / {pagination.pages}
              </span>
              <button
                type="button"
                disabled={page >= pagination.pages}
                onClick={() => setPage((p) => p + 1)}
                className="text-xs font-semibold text-ds-action disabled:opacity-40"
              >
                Next
              </button>
            </div>
          ) : null}
        </div>

        <div className="lg:col-span-3 rounded-2xl border border-ds-border bg-ds-surface p-5">
          {!selected ? (
            <p className="text-sm text-ds-text-muted">
              Select a message to review and reply.
            </p>
          ) : (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold text-ds-text-primary">
                  {selected.subject}
                </h2>
                <p className="text-sm text-ds-text-muted mt-1">
                  {selected.name} · {selected.email}
                </p>
                <p className="text-xs text-ds-text-muted mt-1">
                  {selected.created_at
                    ? new Date(selected.created_at).toLocaleString()
                    : ""}
                </p>
              </div>

              <div className="rounded-xl bg-ds-surface-secondary border border-ds-border-subtle px-4 py-3">
                <p className="text-sm text-ds-text-secondary whitespace-pre-wrap">
                  {selected.message}
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-ds-text-muted mb-1.5">
                  Status
                </label>
                <select
                  value={nextStatus}
                  onChange={(e) => setNextStatus(e.target.value)}
                  className="h-10 w-full rounded-lg border border-ds-border bg-ds-surface-input px-3 text-sm"
                >
                  {STATUS_OPTIONS.filter((o) => o.value).map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-ds-text-muted mb-1.5">
                  Internal notes
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  className="w-full rounded-lg border border-ds-border bg-ds-surface-input px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-ds-text-muted mb-1.5">
                  Reply to sender
                </label>
                <textarea
                  value={reply}
                  onChange={(e) => setReply(e.target.value)}
                  rows={4}
                  className="w-full rounded-lg border border-ds-border bg-ds-surface-input px-3 py-2 text-sm"
                  placeholder="Optional reply emailed through EmailOutbox..."
                />
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={handleMut.isPending}
                  onClick={() => onHandle({ sendEmail: false })}
                  className="h-10 px-4 rounded-lg bg-ds-surface-secondary text-sm font-semibold text-ds-text-primary border border-ds-border hover:bg-ds-surface-hover disabled:opacity-60"
                >
                  Save status
                </button>
                <button
                  type="button"
                  disabled={handleMut.isPending || !reply.trim()}
                  onClick={() => onHandle({ sendEmail: true })}
                  className="h-10 px-4 rounded-lg bg-ds-action text-sm font-semibold text-white hover:bg-ds-action-hover disabled:opacity-60"
                >
                  Save & email reply
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
