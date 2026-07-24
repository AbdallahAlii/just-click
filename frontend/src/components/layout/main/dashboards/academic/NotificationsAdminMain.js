"use client";

import AdminDashboardPage, {
  AdminMetricCard,
  AdminSkeletonBlock,
} from "@/components/shared/dashboards/AdminDashboardPage";
import {
  useNotificationBatches,
  useNotificationRecipients,
  useResendNotificationEmail,
  useSendNotification,
} from "@/features/notifications/hooks";
import { getApiErrorMessage } from "@/lib/apiErrors";
import { useMemo, useState } from "react";
import toast from "react-hot-toast";

const CHANNELS = [
  { id: "in_app", label: "In-app", hint: "Shows inside the web/mobile app notification list." },
  { id: "email", label: "Email", hint: "Queued to email_outbox and sent by email_worker.py." },
  { id: "push", label: "Mobile push", hint: "Firebase push for phones. Requires FIREBASE_SERVER_KEY + notification_worker.py." },
];

export default function NotificationsAdminMain() {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [recipientMode, setRecipientMode] = useState("all");
  const [selectedIds, setSelectedIds] = useState([]);
  const [channels, setChannels] = useState(["in_app", "email", "push"]);
  const [materialId, setMaterialId] = useState("");

  const { data: recipientsRes, isLoading: recipientsLoading } =
    useNotificationRecipients({ limit: 500 });
  const recipients = recipientsRes?.data?.recipients || [];

  const { data: batchesRes, isLoading: batchesLoading, refetch } =
    useNotificationBatches({ page: 1, per_page: 20 });
  const batches = batchesRes?.data?.data || [];

  const sendMut = useSendNotification();
  const resendMut = useResendNotificationEmail();

  const selectedCount = useMemo(
    () => (recipientMode === "all" ? recipients.length : selectedIds.length),
    [recipientMode, recipients.length, selectedIds.length],
  );

  const toggleChannel = (id) => {
    setChannels((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id],
    );
  };

  const toggleStudent = (userId) => {
    setSelectedIds((prev) =>
      prev.includes(userId)
        ? prev.filter((id) => id !== userId)
        : [...prev, userId],
    );
  };

  const handleSend = async () => {
    if (!title.trim() || !body.trim()) {
      toast.error("Title and message are required.");
      return;
    }
    if (!channels.length) {
      toast.error("Select at least one channel.");
      return;
    }
    if (recipientMode === "selected" && !selectedIds.length) {
      toast.error("Select at least one student.");
      return;
    }

    try {
      const res = await sendMut.mutateAsync({
        title: title.trim(),
        body: body.trim(),
        channels,
        recipient_mode: recipientMode,
        user_ids: recipientMode === "selected" ? selectedIds : undefined,
        material_id: materialId ? Number(materialId) : undefined,
      });
      toast.success(res?.message || "Notification sent.");
      setTitle("");
      setBody("");
      setSelectedIds([]);
      refetch();
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Failed to send notification."));
    }
  };

  const handleResend = async (batchId) => {
    try {
      const res = await resendMut.mutateAsync(batchId);
      toast.success(res?.message || "Emails queued for resend.");
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Failed to resend emails."));
    }
  };

  return (
    <AdminDashboardPage
      title="Notifications"
      subtitle="Send in-app, email, and push notifications to active verified students."
      metrics={
        <>
          <AdminMetricCard
            label="Eligible students"
            value={recipientsLoading ? "…" : recipients.length}
            hint="Active, approved, verified email"
          />
          <AdminMetricCard
            label="Selected"
            value={selectedCount}
            hint={recipientMode === "all" ? "All students" : "Custom selection"}
          />
          <AdminMetricCard
            label="Recent batches"
            value={batchesLoading ? "…" : batches.length}
            hint="Last 20 sends"
          />
        </>
      }
    >
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-ds-border dark:bg-ds-surface">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-ds-text">
            Compose notification
          </h2>

          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium">Title</label>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-ds-border dark:bg-ds-page"
                placeholder="e.g. New lecture slides available"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium">Message</label>
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                rows={5}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-ds-border dark:bg-ds-page"
                placeholder="Write the notification body students will see."
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium">
                Material ID (optional)
              </label>
              <input
                value={materialId}
                onChange={(e) => setMaterialId(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-ds-border dark:bg-ds-page"
                placeholder="Link notification to a material"
              />
            </div>

            <div>
              <p className="mb-2 text-sm font-medium">Channels</p>
              <div className="flex flex-wrap gap-2">
                {CHANNELS.map((ch) => (
                  <button
                    key={ch.id}
                    type="button"
                    title={ch.hint}
                    onClick={() => toggleChannel(ch.id)}
                    className={`rounded-full px-3 py-1 text-xs font-medium ${
                      channels.includes(ch.id)
                        ? "bg-primaryColor text-white"
                        : "bg-gray-100 text-gray-700 dark:bg-ds-page dark:text-ds-muted"
                    }`}
                  >
                    {ch.label}
                  </button>
                ))}
              </div>
              <p className="mt-2 text-xs text-gray-500 dark:text-ds-muted">
                Push = mobile app alerts only. It does not replace email or in-app notifications.
              </p>
            </div>

            <div>
              <p className="mb-2 text-sm font-medium">Recipients</p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setRecipientMode("all")}
                  className={`rounded-lg px-3 py-2 text-sm ${
                    recipientMode === "all"
                      ? "bg-primaryColor text-white"
                      : "bg-gray-100 dark:bg-ds-page"
                  }`}
                >
                  All eligible
                </button>
                <button
                  type="button"
                  onClick={() => setRecipientMode("selected")}
                  className={`rounded-lg px-3 py-2 text-sm ${
                    recipientMode === "selected"
                      ? "bg-primaryColor text-white"
                      : "bg-gray-100 dark:bg-ds-page"
                  }`}
                >
                  Select students
                </button>
              </div>
            </div>

            {recipientMode === "selected" && (
              <div className="max-h-56 overflow-y-auto rounded-lg border border-gray-200 p-2 dark:border-ds-border">
                {recipientsLoading ? (
                  <AdminSkeletonBlock rows={4} />
                ) : (
                  recipients.map((r) => (
                    <label
                      key={r.user_id}
                      className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 hover:bg-gray-50 dark:hover:bg-ds-page"
                    >
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(r.user_id)}
                        onChange={() => toggleStudent(r.user_id)}
                      />
                      <span className="text-sm">
                        {r.full_name} · {r.email}
                      </span>
                    </label>
                  ))
                )}
              </div>
            )}

            <button
              type="button"
              onClick={handleSend}
              disabled={sendMut.isPending}
              className="rounded-lg bg-primaryColor px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              {sendMut.isPending ? "Sending…" : "Send notification"}
            </button>
          </div>
        </section>

        <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-ds-border dark:bg-ds-surface">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-ds-text">
            Recent batches
          </h2>
          {batchesLoading ? (
            <AdminSkeletonBlock rows={6} />
          ) : batches.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-ds-muted">
              No notifications sent yet.
            </p>
          ) : (
            <div className="space-y-3">
              {batches.map((batch) => (
                <article
                  key={batch.id}
                  className="rounded-xl border border-gray-100 p-4 dark:border-ds-border"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="font-medium">{batch.title}</h3>
                      <p className="mt-1 text-sm text-gray-600 dark:text-ds-muted line-clamp-2">
                        {batch.body}
                      </p>
                      <p className="mt-2 text-xs text-gray-500 dark:text-ds-muted">
                        {batch.event_type} · {batch.recipient_count} recipients ·{" "}
                        {(batch.channels || []).join(", ")}
                      </p>
                      {batch.delivery && (
                        <p className="mt-1 text-xs">
                          <span
                            className={`inline-flex rounded-full px-2 py-0.5 font-medium ${
                              batch.delivery.overall_status === "sent"
                                ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
                                : batch.delivery.overall_status === "pending"
                                  ? "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300"
                                  : batch.delivery.overall_status === "failed"
                                    ? "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300"
                                    : "bg-gray-100 text-gray-700"
                            }`}
                          >
                            {batch.delivery.overall_status}
                          </span>
                          {batch.delivery.email && (
                            <span className="ml-2 text-gray-500 dark:text-ds-muted">
                              email: sent {batch.delivery.email.sent || 0}, failed{" "}
                              {batch.delivery.email.failed || 0}
                            </span>
                          )}
                          {(batch.delivery.push_skipped || 0) > 0 && (
                            <span className="ml-2 text-gray-500 dark:text-ds-muted">
                              push skipped {batch.delivery.push_skipped} (FCM not configured)
                            </span>
                          )}
                        </p>
                      )}
                      {batch.delivery?.email_last_error && (
                        <p className="mt-1 text-xs text-red-600 line-clamp-2">
                          {batch.delivery.email_last_error}
                        </p>
                      )}
                    </div>
                    {(batch.channels || []).includes("email") && (
                      <button
                        type="button"
                        onClick={() => handleResend(batch.id)}
                        disabled={resendMut.isPending}
                        className="shrink-0 rounded-lg border border-gray-300 px-3 py-1 text-xs dark:border-ds-border"
                      >
                        Resend email
                      </button>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </AdminDashboardPage>
  );
}
