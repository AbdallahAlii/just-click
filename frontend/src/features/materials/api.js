import { fetchJSON } from "@/lib/http";

/**
 * Remove undefined, null, and empty string values
 */
function cleanParams(params = {}) {
  const cleaned = {};

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    cleaned[key] = value;
  });

  return cleaned;
}

/**
 * Convert params object to query string
 */
function toQueryString(params = {}) {
  const searchParams = new URLSearchParams();

  Object.entries(cleanParams(params)).forEach(([key, value]) => {
    searchParams.append(key, String(value));
  });

  const qs = searchParams.toString();
  return qs ? `?${qs}` : "";
}

/**
 * Always build FormData for material create/update.
 * Backend accepts multipart/form-data with:
 * - payload => JSON string
 * - file => optional uploaded file
 */
function buildMaterialFormData({ payload, file }) {
  const formData = new FormData();

  formData.append("payload", JSON.stringify(payload || {}));

  if (file) {
    formData.append("file", file);
  }

  return formData;
}

export const materialsApi = {
  /**
   * Create material
   */
  createMaterial: async ({ payload, file } = {}) => {
    const formData = buildMaterialFormData({ payload, file });

    return fetchJSON("/materials/create", {
      method: "POST",
      body: formData,
    });
  },

  /**
   * Update material
   */
  updateMaterial: async ({ id, payload, file } = {}) => {
    const formData = buildMaterialFormData({ payload, file });

    return fetchJSON(`/materials/${id}/update`, {
      method: "PUT",
      body: formData,
    });
  },

  /**
   * Student material detail
   */
  getMaterial: (id) =>
    fetchJSON(`/materials/get/${id}`, {
      method: "GET",
    }),

  /**
   * Admin material detail
   */
  getAdminMaterial: (id) =>
    fetchJSON(`/materials/get/${id}/admin`, {
      method: "GET",
    }),

  /**
   * Student list
   */
  getMaterialsList: (params = {}) =>
    fetchJSON(`/materials/list${toQueryString(params)}`, {
      method: "GET",
    }),

  /**
   * Admin list
   */
  getAdminMaterialsList: (params = {}) =>
    fetchJSON(`/materials/list/admin${toQueryString(params)}`, {
      method: "GET",
    }),

  /**
   * Filter options
   */
  getMaterialFilterOptions: (params = {}) =>
    fetchJSON(`/materials/filter-options${toQueryString(params)}`, {
      method: "GET",
    }),

  /**
   * Delete single material
   */
  deleteMaterial: (id) =>
    fetchJSON(`/materials/${id}/delete`, {
      method: "DELETE",
    }),

  /**
   * Bulk delete materials
   * Backend expects material_ids
   */
  bulkDeleteMaterials: ({ ids }) =>
    fetchJSON("/materials/bulk-delete", {
      method: "POST",
      body: JSON.stringify({ material_ids: ids }),
    }),

  /**
   * Favorites list
   */
  getFavoritesList: (params = {}) =>
    fetchJSON(`/materials/favorites${toQueryString(params)}`, {
      method: "GET",
    }),

  /**
   * Toggle favorite
   */
  setFavorite: ({ id, is_favorite }) =>
    fetchJSON(`/materials/${id}/favorite`, {
      method: "POST",
      body: JSON.stringify({ is_favorite }),
    }),

  /**
   * Track material view
   */
  trackView: (id, cooldown_seconds = 3600) =>
    fetchJSON(`/materials/${id}/view?cooldown_seconds=${cooldown_seconds}`, {
      method: "POST",
    }),

  /**
   * Track material download
   */
  trackDownload: (id) =>
    fetchJSON(`/materials/${id}/download`, {
      method: "POST",
    }),

  submitFeedback: ({ materialId, payload }) =>
    fetchJSON(`/materials/${materialId}/feedback`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getMaterialFeedback: (materialId, params = {}) =>
    fetchJSON(`/materials/${materialId}/feedback${toQueryString(params)}`, {
      method: "GET",
    }),

  getAdminFeedback: (params = {}) =>
    fetchJSON(`/materials/feedback/admin${toQueryString(params)}`, {
      method: "GET",
    }),

  replyFeedback: ({ feedbackId, admin_reply }) =>
    fetchJSON(`/materials/feedback/${feedbackId}/reply`, {
      method: "POST",
      body: JSON.stringify({ admin_reply }),
    }),

  resolveFeedback: ({ feedbackId, admin_reply }) =>
    fetchJSON(`/materials/feedback/${feedbackId}/resolve`, {
      method: "POST",
      body: JSON.stringify({ admin_reply: admin_reply || undefined }),
    }),

  getAccessReports: (params = {}) =>
    fetchJSON(`/materials/reports/access${toQueryString(params)}`, {
      method: "GET",
    }),

  getAdminFeedbackSummary: () =>
    fetchJSON("/materials/feedback/admin/summary", {
      method: "GET",
    }),
};
