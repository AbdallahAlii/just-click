export const notificationsKeys = {
  all: ["notifications"],
  batches: (params = {}) => ["notifications", "batches", params],
  recipients: (params = {}) => ["notifications", "recipients", params],
  mine: (params = {}) => ["notifications", "mine", params],
  unread: () => ["notifications", "unread"],
};
