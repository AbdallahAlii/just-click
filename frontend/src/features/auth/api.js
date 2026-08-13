import { fetchJSON } from "@/lib/http";

function cleanParams(params = {}) {
  const cleaned = {};

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    cleaned[key] = value;
  });

  return cleaned;
}

function toQueryString(params = {}) {
  const searchParams = new URLSearchParams();

  Object.entries(cleanParams(params)).forEach(([key, value]) => {
    searchParams.append(key, String(value));
  });

  const qs = searchParams.toString();
  return qs ? `?${qs}` : "";
}

export const authApi = {
  login: (payload) =>
    fetchJSON("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  logout: () =>
    fetchJSON("/auth/logout", {
      method: "POST",
    }),

  me: () => fetchJSON("/auth/me"),

  verifyEmail: ({ username, token }) =>
    fetchJSON(
      `/auth/verify-email?username=${encodeURIComponent(
        username,
      )}&token=${encodeURIComponent(token)}`,
    ),

  forgotPassword: (payload) =>
    fetchJSON("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  resetPassword: (payload) =>
    fetchJSON("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getMyProfilePage: (params = {}) =>
    fetchJSON(`/auth/me/profile-page${toQueryString(params)}`),

  updateMyProfilePage: (payload) =>
    fetchJSON("/auth/me/profile-page/update", {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
};
