"use client";

import {
  useMaterialFeedback,
  useSubmitMaterialFeedback,
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

export default function MaterialFeedbackPanel({ materialId, stats = {} }) {
  const { data, isLoading, refetch } = useMaterialFeedback(materialId);
  const submitMut = useSubmitMaterialFeedback();

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
          : "Posted. Other students and admins can see it.",
      );
      refetch();
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Could not submit feedback."));
    }
  };

  const renderThread = (list, emptyText) => {
    if (isLoading) {
      return <p className="text-sm text-ds-text-muted">Loading...</p>;
    }
    if (!list.length) {
      return (
        <p className="text-sm text-ds-text-muted">{emptyText}</p>
      );
    }
    return (
      <div className="space-y-4">
        {list.map((item) => (
          <div
            key={item.id}
            className="rounded-xl border border-ds-border p-4 bg-ds-surface-secondary"
          >
            <div className="flex items-center justify-between gap-3 mb-2">
              <span className="text-sm font-semibold text-ds-text-primary">
                {item.user?.full_name || item.user?.username || "Student"}
              </span>
              <span className="text-[11px] uppercase tracking-wide text-ds-text-muted">
                {TYPE_LABELS[item.feedback_type] || item.feedback_type}
                {item.status ? ` · ${item.status}` : ""}
              </span>
            </div>
            {item.message ? (
              <p className="text-sm text-ds-text-secondary whitespace-pre-wrap">
                {item.message}
              </p>
            ) : null}
            {item.admin_reply ? (
              <div className="mt-3 rounded-lg bg-ds-surface-elevated border border-ds-border-subtle px-3 py-2">
                <p className="text-xs font-semibold text-ds-action mb-1">
                  Admin reply
                </p>
                <p className="text-sm text-ds-text-secondary whitespace-pre-wrap">
                  {item.admin_reply}
                </p>
              </div>
            ) : null}
          </div>
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
            Comments and questions are visible to all students. Broken-file
            reports are private — only you and admins see them.
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
                ? "Ask a question other students can see..."
                : "Leave a comment..."
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
          <h4 className="font-semibold text-ds-text-primary mb-3">
            Comments & questions
          </h4>
          {renderThread(
            publicItems,
            "No comments yet. Be the first to ask a question.",
          )}
        </div>

        {ownReports.length > 0 ? (
          <div>
            <h4 className="font-semibold text-ds-text-primary mb-1">
              Your issue reports
            </h4>
            <p className="text-xs text-ds-text-muted mb-3">
              Only visible to you and department admins.
            </p>
            {renderThread(ownReports, "")}
          </div>
        ) : null}
      </div>
    </section>
  );
}
