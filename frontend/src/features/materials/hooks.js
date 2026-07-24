"use client";

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { materialsApi } from "./api";
import { materialsKeys } from "./keys";

/**
 * Student detail
 */
export function useMaterialDetail(id, options = {}) {
  return useQuery({
    queryKey: materialsKeys.detail(id),
    queryFn: () => materialsApi.getMaterial(id),
    enabled: !!id,
    ...options,
  });
}

/**
 * Admin detail
 */
export function useAdminMaterialDetail(id, options = {}) {
  return useQuery({
    queryKey: materialsKeys.adminDetail(id),
    queryFn: () => materialsApi.getAdminMaterial(id),
    enabled: !!id,
    ...options,
  });
}

/**
 * Student paginated list
 */
export function useMaterialsList(params = {}, options = {}) {
  return useQuery({
    queryKey: materialsKeys.list(params),
    queryFn: () => materialsApi.getMaterialsList(params),
    ...options,
  });
}

/**
 * Admin paginated list
 */
export function useAdminMaterialsList(params = {}, options = {}) {
  return useQuery({
    queryKey: materialsKeys.adminList(params),
    queryFn: () => materialsApi.getAdminMaterialsList(params),
    ...options,
  });
}

/**
 * Student infinite / cursor list
 */
export function useInfiniteMaterialsList(baseParams = {}, options = {}) {
  return useInfiniteQuery({
    queryKey: materialsKeys.list({
      ...baseParams,
      mode: "cursor",
      infinite: true,
    }),
    queryFn: ({ pageParam = "" }) =>
      materialsApi.getMaterialsList({
        ...baseParams,
        mode: "cursor",
        limit: baseParams.limit || 10,
        cursor: pageParam || undefined,
      }),
    initialPageParam: "",
    getNextPageParam: (lastPage) => {
      const pagination = lastPage?.data?.pagination;
      if (pagination?.has_more && pagination?.next_cursor) {
        return pagination.next_cursor;
      }
      return undefined;
    },
    placeholderData: (previousData) => previousData,
    ...options,
  });
}

/**
 * Materials filter options
 */
export function useMaterialFilterOptions(params = {}, options = {}) {
  return useQuery({
    queryKey: materialsKeys.filterOptions(params),
    queryFn: () => materialsApi.getMaterialFilterOptions(params),
    ...options,
  });
}

/**
 * Create material
 */
export function useCreateMaterial(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: materialsApi.createMaterial,
    onSuccess: (data, variables, context) => {
      queryClient.invalidateQueries({ queryKey: materialsKeys.lists() });
      queryClient.invalidateQueries({ queryKey: materialsKeys.adminLists() });

      if (options.onSuccess) {
        options.onSuccess(data, variables, context);
      }
    },
    ...options,
  });
}

/**
 * Update material
 */
export function useUpdateMaterial(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: materialsApi.updateMaterial,
    onSuccess: (data, variables, context) => {
      const id = variables?.id;

      queryClient.invalidateQueries({ queryKey: materialsKeys.lists() });
      queryClient.invalidateQueries({ queryKey: materialsKeys.adminLists() });

      if (id) {
        queryClient.invalidateQueries({ queryKey: materialsKeys.detail(id) });
        queryClient.invalidateQueries({
          queryKey: materialsKeys.adminDetail(id),
        });
      }

      if (options.onSuccess) {
        options.onSuccess(data, variables, context);
      }
    },
    ...options,
  });
}

/**
 * Delete single material
 */
export function useDeleteMaterial(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: materialsApi.deleteMaterial,
    onSuccess: (data, id, context) => {
      queryClient.invalidateQueries({ queryKey: materialsKeys.lists() });
      queryClient.invalidateQueries({ queryKey: materialsKeys.adminLists() });

      if (id) {
        queryClient.removeQueries({ queryKey: materialsKeys.detail(id) });
        queryClient.removeQueries({ queryKey: materialsKeys.adminDetail(id) });
      }

      if (options.onSuccess) {
        options.onSuccess(data, id, context);
      }
    },
    ...options,
  });
}

/**
 * Bulk delete materials
 */
export function useBulkDeleteMaterials(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: materialsApi.bulkDeleteMaterials,
    onSuccess: (data, variables, context) => {
      queryClient.invalidateQueries({ queryKey: materialsKeys.lists() });
      queryClient.invalidateQueries({ queryKey: materialsKeys.adminLists() });

      const ids = variables?.ids || [];
      ids.forEach((id) => {
        queryClient.removeQueries({ queryKey: materialsKeys.detail(id) });
        queryClient.removeQueries({ queryKey: materialsKeys.adminDetail(id) });
      });

      if (options.onSuccess) {
        options.onSuccess(data, variables, context);
      }
    },
    ...options,
  });
}

/**
 * Favorites list
 */
export function useMaterialsFavoritesList(params = {}, options = {}) {
  return useQuery({
    queryKey: materialsKeys.list({ ...params, type: "favorites" }),
    queryFn: () => materialsApi.getFavoritesList(params),
    ...options,
  });
}

/**
 * Toggle favorite
 */
export function useToggleMaterialFavorite(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: materialsApi.setFavorite,
    onSuccess: (data, variables, context) => {
      queryClient.invalidateQueries({ queryKey: materialsKeys.lists() });

      if (variables?.id) {
        queryClient.invalidateQueries({
          queryKey: materialsKeys.detail(variables.id),
        });
      }

      if (options.onSuccess) {
        options.onSuccess(data, variables, context);
      }
    },
    ...options,
  });
}

/**
 * Track material view
 */
export function useTrackMaterialView(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, cooldown_seconds }) =>
      materialsApi.trackView(id, cooldown_seconds),
    onSuccess: (data, variables, context) => {
      queryClient.invalidateQueries({ queryKey: materialsKeys.lists() });

      if (variables?.id) {
        queryClient.invalidateQueries({
          queryKey: materialsKeys.detail(variables.id),
        });
      }

      if (options.onSuccess) {
        options.onSuccess(data, variables, context);
      }
    },
    ...options,
  });
}

/**
 * Track material download
 */
export function useTrackMaterialDownload(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: materialsApi.trackDownload,
    onSuccess: (data, id, context) => {
      queryClient.invalidateQueries({ queryKey: materialsKeys.lists() });

      if (id) {
        queryClient.invalidateQueries({ queryKey: materialsKeys.detail(id) });
      }

      if (options.onSuccess) {
        options.onSuccess(data, id, context);
      }
    },
    ...options,
  });
}

export function useMaterialFeedback(materialId, options = {}) {
  return useQuery({
    queryKey: materialsKeys.feedback(materialId),
    queryFn: () => materialsApi.getMaterialFeedback(materialId),
    enabled: !!materialId,
    ...options,
  });
}

export function useSubmitMaterialFeedback(options = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: materialsApi.submitFeedback,
    onSuccess: (data, variables, context) => {
      const id = variables?.materialId;
      if (id) {
        queryClient.invalidateQueries({ queryKey: materialsKeys.feedback(id) });
        queryClient.invalidateQueries({ queryKey: materialsKeys.detail(id) });
        queryClient.invalidateQueries({ queryKey: materialsKeys.lists() });
      }
      if (options.onSuccess) options.onSuccess(data, variables, context);
    },
    ...options,
  });
}

export function useAdminMaterialFeedback(params = {}, options = {}) {
  return useQuery({
    queryKey: materialsKeys.adminFeedback(params),
    queryFn: () => materialsApi.getAdminFeedback(params),
    ...options,
  });
}

export function useReplyMaterialFeedback(options = {}) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: materialsApi.replyFeedback,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: materialsKeys.root });
      if (options.onSuccess) options.onSuccess();
    },
    ...options,
  });
}

export function useResolveMaterialFeedback(options = {}) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: materialsApi.resolveFeedback,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: materialsKeys.root });
      if (options.onSuccess) options.onSuccess();
    },
    ...options,
  });
}

export function useMaterialAccessReports(params = {}, options = {}) {
  return useQuery({
    queryKey: materialsKeys.accessReports(params),
    queryFn: () => materialsApi.getAccessReports(params),
    staleTime: 10 * 1000,
    refetchInterval: 15 * 1000,
    refetchIntervalInBackground: false,
    ...options,
  });
}

export function useMaterialFeedbackAdminSummary(options = {}) {
  return useQuery({
    queryKey: materialsKeys.adminFeedbackSummary(),
    queryFn: () => materialsApi.getAdminFeedbackSummary(),
    staleTime: 30 * 1000,
    ...options,
  });
}
