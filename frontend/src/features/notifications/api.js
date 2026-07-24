import { fetchJSON } from "@/lib/http";

function toQueryString(params = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    searchParams.append(key, String(value));
  });
  const qs = searchParams.toString();
  return qs ? `?${qs}` : "";
}

export const notificationsApi = {
  listBatches: (params = {}) =>
    fetchJSON(`/notifications/admin/batches${toQueryString(params)}`),

  listRecipients: (params = {}) =>
    fetchJSON(`/notifications/admin/recipients${toQueryString(params)}`),

  send: (payload = {}) =>
    fetchJSON("/notifications/admin/send", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  resendEmail: (batchId) =>
    fetchJSON(`/notifications/admin/batches/${batchId}/resend-email`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  listMine: (params = {}) =>
    fetchJSON(`/notifications/list${toQueryString(params)}`),

  unreadCount: () => fetchJSON("/notifications/unread-count"),

  markRead: (notificationId) =>
    fetchJSON("/notifications/read", {
      method: "POST",
      body: JSON.stringify({ notification_id: notificationId }),
    }),

  markAllRead: () =>
    fetchJSON("/notifications/read-all", {
      method: "POST",
      body: JSON.stringify({}),
    }),

  registerDevice: (payload) =>
    fetchJSON("/notifications/devices/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
