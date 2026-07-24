"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notificationsApi } from "./api";
import { notificationsKeys } from "./keys";

export function useNotificationBatches(params = {}, options = {}) {
  return useQuery({
    queryKey: notificationsKeys.batches(params),
    queryFn: () => notificationsApi.listBatches(params),
    ...options,
  });
}

export function useNotificationRecipients(params = {}, options = {}) {
  return useQuery({
    queryKey: notificationsKeys.recipients(params),
    queryFn: () => notificationsApi.listRecipients(params),
    ...options,
  });
}

export function useSendNotification() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload) => notificationsApi.send(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: notificationsKeys.all });
    },
  });
}

export function useResendNotificationEmail() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (batchId) => notificationsApi.resendEmail(batchId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: notificationsKeys.batches() });
    },
  });
}

export function useMyNotifications(params = {}, options = {}) {
  return useQuery({
    queryKey: notificationsKeys.mine(params),
    queryFn: () => notificationsApi.listMine(params),
    ...options,
  });
}

export function useUnreadNotificationCount(options = {}) {
  return useQuery({
    queryKey: notificationsKeys.unread(),
    queryFn: () => notificationsApi.unreadCount(),
    ...options,
  });
}
