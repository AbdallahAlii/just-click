"use client";

import AdminDashboardPage, {
  AdminMetricCard,
  AdminSkeletonBlock,
} from "@/components/shared/dashboards/AdminDashboardPage";
import {
  useAdminMaterialFeedback,
  useMaterialFeedbackAdminSummary,
  useReplyMaterialFeedback,
  useResolveMaterialFeedback,
} from "@/features/materials/hooks";
import { getApiErrorMessage } from "@/lib/apiErrors";
import Link from "next/link";
import { useMemo, useState } from "react";
import toast from "react-hot-toast";

const TYPE_LABELS = {
  comment: "Comment",
  clarification: "Question",
  broken_file: "Broken file",
  rating: "Rating",
};

const TABS = [
  { id: "attention", label: "Needs attention" },
  { id: "open", label: "Open issues" },
  { id: "comments", label: "Comments" },
  { id: "resolved", label: "Resolved" },
  { id: "all", label: "All" },
];

export default function MaterialFeedbackAdminMain() {
  const [activeTab, setActiveTab] = useState("attention");
  const [replyDrafts, setReplyDrafts] = useState({});

  const { data: summaryRes, isLoading: summaryLoading } =
    useMaterialFeedbackAdminSummary();
  const summary = summaryRes?.data || {};

  const listParams = useMemo(() => {
    if (activeTab === "open") return { status: "open", page: 1, limit: 50 };
    if (activeTab === "resolved")
      return { status: "resolved", page: 1, limit: 50 };
    if (activeTab === "comments")
      return { feedback_type: "comment", page: 1, limit: 50 };
    return { page: 1, limit: 50 };
  }, [activeTab]);

  const { data, isLoading, isError, refetch, isFetching } =
    useAdminMaterialFeedback(listParams);
  const replyMut = useReplyMaterialFeedback();
  const resolveMut = useResolveMaterialFeedback();

  const items = data?.data?.data || [];

  const visibleItems = useMemo(() => {
    if (activeTab === "attention") {
      return items.filter(
        (item) =>
          item.status === "open" ||
          (item.message &&
            !item.admin_reply &&
            item.feedback_type !== "rating"),
      );
    }
    return items;
  }, [items, activeTab]);

  const handleReply = async (feedbackId) => {
    const text = (replyDrafts[feedbackId] || "").trim();
    if (!text) {
      toast.error("Enter a reply first.");
      return;
    }
    try {
      await replyMut.mutateAsync({ feedbackId, admin_reply: text });
      toast.success("Reply published — students can see it on the material.");
      setReplyDrafts((prev) => ({ ...prev, [feedbackId]: "" }));
      refetch();
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Could not save reply."));
    }
  };

  const handleResolve = async (feedbackId) => {
    const text = (replyDrafts[feedbackId] || "").trim();
    try {
      await resolveMut.mutateAsync({
        feedbackId,
        admin_reply: text || undefined,
      });
      toast.success("Marked as resolved.");
      refetch();
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Could not resolve feedback."));
    }
  };

  const reportsLink = (
    <Link
      href="/admin/dashboards/admin-academic/materials/reports"
      className="inline-flex items-center justify-center w-full sm:w-auto px-4 py-2.5 rounded-xl text-sm font-semibold text-ds-action border border-ds-border bg-ds-surface hover:bg-ds-surface-hover transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-focus"
    >
      View access reports
    </Link>
  );

  if (isError) {
    return (
      <AdminDashboardPage
        title="Material Feedback Inbox"
        description="Review student comments, questions, and broken-file reports."
        action={reportsLink}
      >
        <div
          className="rounded-2xl border border-ds-error/30 bg-ds-surface p-8 text-center"
          role="alert"
        >
          <p className="text-ds-error font-medium">
            Failed to load material feedback.
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-4 px-4 py-2 rounded-xl bg-ds-action text-white text-sm font-semibold"
          >
            Try again
          </button>
        </div>
      </AdminDashboardPage>
    );
  }

  return (
    <AdminDashboardPage
      title="Material Feedback Inbox"
      description="Review student comments, questions, and broken-file reports. Replies are visible to students on the material page."
      action={reportsLink}
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {summaryLoading ? (
          [...Array(4)].map((_, i) => (
            <div
              key={i}
              className="h-24 rounded-2xl bg-ds-surface-secondary animate-pulse"
              aria-hidden="true"
            />
          ))
        ) : (
          <>
            <AdminMetricCard
              label="Open issues"
              value={summary.open_issues ?? 0}
              hint="Broken files & questions awaiting action"
            />
            <AdminMetricCard
              label="Awaiting reply"
              value={summary.awaiting_admin_reply ?? 0}
            />
            <AdminMetricCard
              label="Broken files"
              value={summary.broken_file_open ?? 0}
            />
            <AdminMetricCard
              label="Comments"
              value={summary.comments_total ?? 0}
            />
          </>
        )}
      </div>

      <div
        className="flex flex-wrap gap-2"
        role="tablist"
        aria-label="Feedback filters"
      >
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 sm:px-4 py-2 rounded-xl text-sm font-medium transition min-h-[40px] focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-focus ${
              activeTab === tab.id
                ? "bg-ds-action text-white"
                : "bg-ds-surface border border-ds-border text-ds-text-secondary hover:bg-ds-surface-hover"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <AdminSkeletonBlock lines={5} />
      ) : !visibleItems.length ? (
        <div className="rounded-2xl border border-dashed border-ds-border bg-ds-surface p-8 sm:p-12 text-center">
          <p className="text-sm text-ds-text-muted">
            No feedback in this view.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {isFetching && !isLoading ? (
            <p className="text-xs text-ds-text-muted" aria-live="polite">
              Refreshing…
            </p>
          ) : null}
          {visibleItems.map((item) => (
            <article
              key={item.id}
              className="rounded-2xl border border-ds-border bg-ds-surface overflow-hidden shadow-sm"
            >
              <div className="px-4 sm:px-5 py-4 border-b border-ds-border-subtle flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2 mb-1.5">
                    <span className="text-[11px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full bg-ds-action/10 text-ds-action">
                      {TYPE_LABELS[item.feedback_type] || item.feedback_type}
                    </span>
                    {item.status ? (
                      <span
                        className={`text-[11px] font-semibold uppercase ${
                          item.status === "open"
                            ? "text-ds-warning"
                            : "text-ds-success"
                        }`}
                      >
                        {item.status}
                      </span>
                    ) : null}
                    {item.rating ? (
                      <span className="text-amber-500 text-sm font-semibold">
                        ★ {item.rating}/5
                      </span>
                    ) : null}
                  </div>
                  <p className="font-semibold text-ds-text-primary break-words">
                    {item.material?.title || `Material #${item.material_id}`}
                  </p>
                  <p className="text-sm text-ds-text-muted mt-1 break-words">
                    <span className="text-ds-text-secondary">
                      {item.user?.full_name || item.user?.username || "Student"}
                    </span>
                    {item.created_at ? (
                      <>
                        {" "}
                        ·{" "}
                        <time dateTime={item.created_at}>
                          {new Date(item.created_at).toLocaleString()}
                        </time>
                      </>
                    ) : null}
                  </p>
                </div>
                <Link
                  href={`/admin/dashboards/admin-academic/materials/${item.material_id}`}
                  className="inline-flex items-center justify-center shrink-0 px-3 py-2 rounded-xl text-sm font-semibold text-ds-action border border-ds-border hover:bg-ds-surface-hover transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-focus"
                >
                  Open material
                </Link>
              </div>

              <div className="px-4 sm:px-5 py-4 space-y-4">
                {item.message ? (
                  <div>
                    <p className="text-xs font-semibold text-ds-text-muted uppercase mb-1">
                      Student message
                    </p>
                    <p className="text-sm text-ds-text-secondary whitespace-pre-wrap break-words">
                      {item.message}
                    </p>
                  </div>
                ) : null}

                {item.admin_reply ? (
                  <div className="rounded-xl bg-ds-surface-secondary border border-ds-border-subtle px-4 py-3">
                    <p className="text-xs font-semibold text-ds-action mb-1">
                      Your reply (visible to students)
                    </p>
                    <p className="text-sm text-ds-text-secondary whitespace-pre-wrap break-words">
                      {item.admin_reply}
                    </p>
                  </div>
                ) : null}

                {item.feedback_type !== "rating" ? (
                  <div className="space-y-3 pt-1">
                    <label className="sr-only" htmlFor={`reply-${item.id}`}>
                      Reply to feedback {item.id}
                    </label>
                    <textarea
                      id={`reply-${item.id}`}
                      value={replyDrafts[item.id] || ""}
                      onChange={(e) =>
                        setReplyDrafts((prev) => ({
                          ...prev,
                          [item.id]: e.target.value,
                        }))
                      }
                      rows={3}
                      placeholder="Write a public reply for the student..."
                      className="w-full rounded-xl border border-ds-border bg-ds-surface-input px-4 py-3 text-sm text-ds-text-primary placeholder:text-ds-text-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-focus"
                    />
                    <div className="flex flex-col sm:flex-row gap-2">
                      <button
                        type="button"
                        onClick={() => handleReply(item.id)}
                        disabled={replyMut.isPending}
                        className="w-full sm:w-auto px-4 py-2.5 min-h-[44px] rounded-xl bg-ds-surface-elevated text-ds-text-primary border border-ds-border text-sm font-semibold hover:bg-ds-surface-hover disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-focus"
                      >
                        Publish reply
                      </button>
                      {item.status === "open" ? (
                        <button
                          type="button"
                          onClick={() => handleResolve(item.id)}
                          disabled={resolveMut.isPending}
                          className="w-full sm:w-auto px-4 py-2.5 min-h-[44px] rounded-xl bg-ds-action text-white text-sm font-semibold hover:bg-ds-action-hover disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-focus"
                        >
                          Mark resolved
                        </button>
                      ) : null}
                    </div>
                  </div>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      )}
    </AdminDashboardPage>
  );
}
