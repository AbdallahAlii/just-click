"use client";

import {
  useMaterialFeedback,
  useSubmitMaterialFeedback,
  useReplyMaterialDiscussion,
} from "@/features/materials/hooks";
import { getApiErrorMessage } from "@/lib/apiErrors";
import { useMemo, useState } from "react";
import toast from "react-hot-toast";

const FEEDBACK_TABS = [
  { id: "comment", label: "Comment" },
  { id: "clarification", label: "Ask question" },
  { id: "broken_file", label: "Report issue" },
];

const TYPE_LABELS = {
  comment: "Comment",
  clarification: "Question",
  broken_file: "Issue report",
};

function initials(name) {
  const parts = String(name || "?")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (!parts.length) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
}

function formatWhen(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

function StarRating({ value, onChange, disabled }) {
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          disabled={disabled}
          onClick={() => onChange(star)}
          className={`text-2xl transition ${
            star <= value ? "text-amber-400" : "text-gray-300 dark:text-gray-600"
          } ${disabled ? "opacity-60 cursor-not-allowed" : "hover:scale-110"}`}
          aria-label={`Rate ${star} stars`}
        >
          ★
        </button>
      ))}
    </div>
  );
}

function AuthorRow({ name, when, badge }) {
  return (
    <div className="flex items-start gap-2.5">
      <div
        className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-ds-surface-secondary text-[11px] font-semibold text-ds-text-secondary"
        aria-hidden="true"
      >
        {initials(name)}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
          <span className="text-sm font-semibold text-ds-text-primary">
            {name}
          </span>
          {badge ? (
            <span className="text-[11px] uppercase tracking-wide text-ds-text-muted">
              {badge}
            </span>
          ) : null}
          {when ? (
            <span className="text-[11px] text-ds-text-muted">{when}</span>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function DiscussionItem({ item, onReply, replyPending }) {
  const [open, setOpen] = useState(false);
  const [replyText, setReplyText] = useState("");
  const name = item.user?.full_name || item.user?.username || "Student";
  const replies = Array.isArray(item.replies) ? item.replies : [];
  const canReply =
    item.feedback_type === "comment" ||
    item.feedback_type === "clarification" ||
    item.feedback_type === "broken_file";

  const submitReply = async (e) => {
    e.preventDefault();
    const text = replyText.trim();
    if (!text) {
      toast.error("Please enter a reply.");
      return;
    }
    await onReply(item.id, text);
    setReplyText("");
    setOpen(false);
  };

  return (
    <article className="border-b border-ds-border-subtle last:border-b-0 py-4">
      <AuthorRow
        name={name}
        when={formatWhen(item.created_at)}
        badge={TYPE_LABELS[item.feedback_type] || item.feedback_type}
      />
      {item.message ? (
        <p className="mt-2 pl-[42px] text-sm text-ds-text-secondary whitespace-pre-wrap">
          {item.message}
        </p>
      ) : null}
      {item.status ? (
        <p className="mt-1 pl-[42px] text-[11px] text-ds-text-muted">
          Status: {item.status}
        </p>
      ) : null}

      {replies.length > 0 ? (
        <div className="mt-3 ml-[42px] space-y-3 border-l border-ds-border pl-3">
          {replies.map((reply) => {
            const replyName =
              reply.user?.full_name || reply.user?.username || "User";
            return (
              <div key={reply.id}>
                <AuthorRow
                  name={replyName}
                  when={formatWhen(reply.created_at)}
                />
                <p className="mt-1.5 pl-[42px] text-sm text-ds-text-secondary whitespace-pre-wrap">
                  {reply.message}
                </p>
              </div>
            );
          })}
        </div>
      ) : null}

      {/* Legacy single admin_reply if somehow not migrated into replies */}
      {!replies.length && item.admin_reply ? (
        <div className="mt-3 ml-[42px] border-l border-ds-border pl-3">
          <p className="text-xs font-semibold text-ds-action mb-1">Admin reply</p>
          <p className="text-sm text-ds-text-secondary whitespace-pre-wrap">
            {item.admin_reply}
          </p>
        </div>
      ) : null}

      {canReply ? (
        <div className="mt-3 pl-[42px]">
          {!open ? (
            <button
              type="button"
              onClick={() => setOpen(true)}
              className="text-xs font-semibold text-ds-action hover:underline"
            >
              Reply
            </button>
          ) : (
            <form onSubmit={submitReply} className="space-y-2">
              <textarea
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                rows={2}
                placeholder="Write a reply..."
                className="w-full rounded-lg border border-ds-border bg-ds-surface-input px-3 py-2 text-sm text-ds-text-primary placeholder:text-ds-text-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-focus"
              />
              <div className="flex items-center gap-2">
                <button
                  type="submit"
                  disabled={replyPending}
                  className="px-3 py-1.5 rounded-lg bg-ds-action text-white text-xs font-semibold disabled:opacity-60 hover:bg-ds-action-hover min-h-[32px]"
                >
                  {replyPending ? "Posting..." : "Post reply"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setOpen(false);
                    setReplyText("");
                  }}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold text-ds-text-secondary hover:bg-ds-surface-secondary min-h-[32px]"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}
        </div>
      ) : null}
    </article>
  );
}

export default function MaterialFeedbackPanel({ materialId, stats = {} }) {
  const { data, isLoading, refetch } = useMaterialFeedback(materialId);
  const submitMut = useSubmitMaterialFeedback();
  const replyMut = useReplyMaterialDiscussion();

  const [activeTab, setActiveTab] = useState("comment");
  const [rating, setRating] = useState(0);
  const [message, setMessage] = useState("");

  const feedbackData = data?.data || {};
  const items = feedbackData?.items || [];
  const userRating = feedbackData?.user_rating ?? null;

  const displayRating = rating || userRating || 0;
  const ratingAvg = stats?.rating_avg ?? stats?.ratingAvg ?? 0;
  const ratingCount = stats?.rating_count ?? stats?.ratingCount ?? 0;

  const { publicItems, ownReports } = useMemo(() => {
    const pub = [];
    const reports = [];
    items.forEach((item) => {
      if (item.feedback_type === "broken_file") {
        reports.push(item);
      } else {
        pub.push(item);
      }
    });
    return { publicItems: pub, ownReports: reports };
  }, [items]);

  const handleRate = async (nextRating) => {
    setRating(nextRating);
    try {
      await submitMut.mutateAsync({
        materialId,
        payload: { feedback_type: "rating", rating: nextRating },
      });
      toast.success("Rating saved.");
      refetch();
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Could not save rating."));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const text = message.trim();
    if (!text) {
      toast.error("Please enter a message.");
      return;
    }

    try {
      await submitMut.mutateAsync({
        materialId,
        payload: {
          feedback_type: activeTab,
          message: text,
        },
      });
      setMessage("");
      toast.success(
        activeTab === "broken_file"
          ? "Issue reported. Admins will review it privately."
          : "Posted. Other students can see and reply.",
      );
      refetch();
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Could not submit feedback."));
    }
  };

  const handleReply = async (feedbackId, text) => {
    try {
      await replyMut.mutateAsync({ feedbackId, message: text });
      toast.success("Reply posted.");
      refetch();
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Could not post reply."));
      throw err;
    }
  };

  const renderThread = (list, emptyText) => {
    if (isLoading) {
      return <p className="text-sm text-ds-text-muted">Loading...</p>;
    }
    if (!list.length) {
      return <p className="text-sm text-ds-text-muted">{emptyText}</p>;
    }
    return (
      <div>
        {list.map((item) => (
          <DiscussionItem
            key={item.id}
            item={item}
            onReply={handleReply}
            replyPending={replyMut.isPending}
          />
        ))}
      </div>
    );
  };

  return (
    <section className="rounded-2xl border border-ds-border bg-ds-surface p-5 md:p-6 shadow-sm">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-4">
        <div>
          <h3 className="text-lg font-semibold text-ds-text-primary">
            Feedback & discussion
          </h3>
          <p className="text-sm text-ds-text-muted mt-1">
            Comments and questions are a shared class discussion. Broken-file
            reports stay private between you and admins.
          </p>
        </div>
        <div className="text-sm text-ds-text-muted">
          {ratingCount > 0 ? (
            <span>
              <span className="font-semibold text-amber-500">
                {Number(ratingAvg).toFixed(1)}
              </span>{" "}
              / 5 ({ratingCount} ratings)
            </span>
          ) : (
            <span>No ratings yet</span>
          )}
        </div>
      </div>

      <div className="mb-6">
        <p className="text-sm font-medium text-ds-text-secondary mb-2">
          How useful is this material?
        </p>
        <StarRating
          value={displayRating}
          onChange={handleRate}
          disabled={submitMut.isPending}
        />
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {FEEDBACK_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition min-h-[36px] focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-focus ${
              activeTab === tab.id
                ? "bg-ds-action text-white"
                : "bg-ds-surface-secondary text-ds-text-secondary hover:bg-ds-surface-hover"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="space-y-3 mb-8">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={3}
          placeholder={
            activeTab === "broken_file"
              ? "Describe what is wrong with the file (only admins see this)..."
              : activeTab === "clarification"
                ? "Ask a question other students can see and answer..."
                : "Leave a comment for the class..."
          }
          className="w-full rounded-xl border border-ds-border bg-ds-surface-input px-4 py-3 text-sm text-ds-text-primary placeholder:text-ds-text-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-focus"
        />
        <button
          type="submit"
          disabled={submitMut.isPending}
          className="px-4 py-2 rounded-xl bg-ds-action text-white text-sm font-semibold disabled:opacity-60 hover:bg-ds-action-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-focus min-h-[44px]"
        >
          {submitMut.isPending ? "Submitting..." : "Submit"}
        </button>
      </form>

      <div className="space-y-6">
        <div>
          <h4 className="font-semibold text-ds-text-primary mb-1">
            Comments & questions
          </h4>
          <p className="text-xs text-ds-text-muted mb-2">
            Shared with everyone who can access this material.
          </p>
          {renderThread(
            publicItems,
            "No comments yet. Be the first to start the discussion.",
          )}
        </div>

        {ownReports.length > 0 ? (
          <div>
            <h4 className="font-semibold text-ds-text-primary mb-1">
              Your issue reports
            </h4>
            <p className="text-xs text-ds-text-muted mb-2">
              Only visible to you and department admins.
            </p>
            {renderThread(ownReports, "")}
          </div>
        ) : null}
      </div>
    </section>
  );
}
