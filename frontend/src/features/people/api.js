import { fetchJSON } from "@/lib/http";

function cleanParams(params = {}) {
  const cleaned = {};
  Object.entries(params).forEach(([key, value]) => {
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

export const peopleApi = {
  // --- Students ---
  getStudentsList: (params) => fetchJSON(`/admin/students/list${toQueryString(params)}`, { method: "GET" }),
  getStudent: (id) => fetchJSON(`/admin/students/${id}`, { method: "GET" }),
  updateStudent: ({ id, payload }) => fetchJSON(`/admin/students/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  resetStudentPassword: ({ id, mode = "email", newPassword }) =>
    fetchJSON(`/admin/students/${id}/reset-password`, {
      method: "POST",
      body: JSON.stringify({
        mode,
        ...(newPassword ? { new_password: newPassword } : {}),
      }),
    }),
  approveStudent: (userId) => fetchJSON(`/education_people/students/${userId}/approve`, { method: "POST" }),
  bulkApproveStudents: ({ userIds }) => fetchJSON(`/education_people/students/bulk-approve`, {
    method: "POST",
    body: JSON.stringify({ user_ids: userIds }),
  }),
  resendStudentApprovalEmail: ({ userId, sendNow = true }) => fetchJSON(`/education_people/students/${userId}/approval-email/resend`, {
    method: "POST",
    body: JSON.stringify({ send_now: sendNow }),
  }),
  bulkResendStudentApprovalEmails: ({ userIds, sendNow = true }) => fetchJSON(`/education_people/students/approval-email/resend-bulk`, {
    method: "POST",
    body: JSON.stringify({ user_ids: userIds, send_now: sendNow }),
  }),

  // --- Staff ---
  getStaffList: (params) => fetchJSON(`/admin/staff/list${toQueryString(params)}`, { method: "GET" }),
  getStaff: (id) => fetchJSON(`/admin/staff/${id}`, { method: "GET" }),
  updateStaff: ({ id, payload }) => fetchJSON(`/admin/staff/${id}`, { method: "PUT", body: JSON.stringify(payload) }),

  // --- Onboarding ---
  getOnboardingList: (params) => fetchJSON(`/education_people/onboarding/students/list${toQueryString(params)}`, { method: "GET" }),
  getOnboarding: (id) => fetchJSON(`/education_people/onboarding/students/${id}`, { method: "GET" }),
  resendOutbox: (outboxId) => fetchJSON(`/education_people/email/outbox/${outboxId}/resend`, { method: "POST" }),
};
