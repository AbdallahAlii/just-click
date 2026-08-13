"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { contactApi } from "./api";

export const contactKeys = {
  root: ["contact"],
  adminList: (params = {}) => [...contactKeys.root, "admin-list", params],
  adminDetail: (id) => [...contactKeys.root, "admin-detail", id],
};

export function useSubmitContact() {
  return useMutation({
    mutationFn: contactApi.submit,
  });
}

export function useAdminContactMessages(params = {}, options = {}) {
  return useQuery({
    queryKey: contactKeys.adminList(params),
    queryFn: () => contactApi.listAdmin(params),
    ...options,
  });
}

export function useHandleContactMessage(options = {}) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: contactApi.handleAdmin,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: contactKeys.root });
      if (options.onSuccess) options.onSuccess();
    },
    ...options,
  });
}
