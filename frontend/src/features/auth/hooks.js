"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { authApi } from "./api";
import { authKeys } from "./keys";

export function useMyProfilePage(params = {}, opts = {}) {
  return useQuery({
    queryKey: [...authKeys.profilePage(), params],
    queryFn: () => authApi.getMyProfilePage(params),
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
    ...opts,
  });
}

export function useUpdateMyProfilePage(opts = {}) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: authApi.updateMyProfilePage,

    onSuccess: async (data, variables, context) => {
      const profile = data?.data?.profile;
      const loggedOut = Boolean(data?.data?.logged_out);

      if (profile) {
        qc.setQueriesData(
          {
            queryKey: authKeys.profilePage(),
            exact: false,
          },
          (old) => {
            if (!old) return old;

            return {
              ...old,
              data: {
                ...(old.data || {}),
                profile,
              },
            };
          },
        );
      }

      if (loggedOut) {
        qc.setQueryData(authKeys.me(), null);
        qc.removeQueries({ queryKey: authKeys.root });
      } else {
        await qc.invalidateQueries({ queryKey: authKeys.profilePage() });
        await qc.invalidateQueries({ queryKey: authKeys.me() });
      }

      if (typeof opts.onSuccess === "function") {
        opts.onSuccess(data, variables, context);
      }
    },

    onError: (error, variables, context) => {
      if (typeof opts.onError === "function") {
        opts.onError(error, variables, context);
      }
    },

    ...opts,
  });
}

export function useMe(opts = {}) {
  return useQuery({
    queryKey: authKeys.me(),
    queryFn: authApi.me,
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
    ...opts,
  });
}

export function useLogin() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: authApi.login,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: authKeys.me() });
      await qc.invalidateQueries({ queryKey: authKeys.profilePage() });
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: authApi.logout,
    onSuccess: async () => {
      qc.setQueryData(authKeys.me(), null);
      qc.removeQueries({ queryKey: authKeys.root });
      await qc.invalidateQueries();
    },
  });
}

export function useVerifyEmail() {
  return useMutation({
    mutationFn: authApi.verifyEmail,
  });
}

export function useForgotPassword() {
  return useMutation({
    mutationFn: authApi.forgotPassword,
  });
}

export function useResetPassword() {
  return useMutation({
    mutationFn: authApi.resetPassword,
  });
}
