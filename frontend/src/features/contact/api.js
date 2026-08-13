import { fetchJSON } from "@/lib/http";

function toQueryString(params = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    searchParams.append(key, String(value));
  });
  const qs = searchParams.toString();
  return qs ? `?${qs}` : "";
}

export const contactApi = {
  submit: (payload) =>
    fetchJSON("/contact/submit", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listAdmin: (params = {}) =>
    fetchJSON(`/contact/admin/list${toQueryString(params)}`, {
      method: "GET",
    }),

  getAdmin: (contactId) =>
    fetchJSON(`/contact/admin/${contactId}`, {
      method: "GET",
    }),

  handleAdmin: ({ contactId, payload }) =>
    fetchJSON(`/contact/admin/${contactId}/handle`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
