export const materialsKeys = {
  root: ["materials"],

  lists: () => [...materialsKeys.root, "list"],
  list: (params = {}) => [...materialsKeys.lists(), params],

  adminLists: () => [...materialsKeys.root, "admin-list"],
  adminList: (params = {}) => [...materialsKeys.adminLists(), params],

  details: () => [...materialsKeys.root, "detail"],
  detail: (id) => [...materialsKeys.details(), id],

  adminDetails: () => [...materialsKeys.root, "admin-detail"],
  adminDetail: (id) => [...materialsKeys.adminDetails(), id],

  filterOptionsRoot: () => [...materialsKeys.root, "filter-options"],
  filterOptions: (params = {}) => [
    ...materialsKeys.filterOptionsRoot(),
    params,
  ],

  create: () => [...materialsKeys.root, "create"],
  update: (id) => [...materialsKeys.root, "update", id],
  delete: (id) => [...materialsKeys.root, "delete", id],
  bulkDelete: () => [...materialsKeys.root, "bulk-delete"],

  feedback: (materialId) => [...materialsKeys.root, "feedback", materialId],
  adminFeedback: (params = {}) => [...materialsKeys.root, "admin-feedback", params],
  accessReports: (params = {}) => [...materialsKeys.root, "access-reports", params],
  adminFeedbackSummary: () => [...materialsKeys.root, "admin-feedback-summary"],
};
