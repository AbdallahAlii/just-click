export function mapMaterialToCardModel(item) {
  return {
    id: item.id,
    title: item.title,
    description: item.description || "",
    materialType: item.material_type,
    createdAt: item.created_at,
    updatedAt: item.updated_at,

    semesterId: item.context?.semester?.id ?? null,
    semesterName: item.context?.semester?.name ?? "",
    semesterNumber: item.context?.semester?.number ?? null,

    courseId: item.context?.course?.id ?? null,
    courseTitle: item.context?.course?.title ?? "",
    courseCode: item.context?.course?.code ?? "",

    chapterId: item.context?.chapter?.id ?? null,
    chapterTitle: item.context?.chapter?.title ?? "",
    chapterNumber: item.context?.chapter?.number ?? null,

    academicYearId: item.context?.academic_year?.id ?? null,
    academicYearName: item.context?.academic_year?.name ?? "",

    departmentId: item.context?.department?.id ?? null,
    departmentName: item.context?.department?.name ?? "",

    file: {
      extension: item.file?.extension ?? "",
      sizeMb: item.file?.size_mb ?? 0,
      slideCount: item.file?.slide_count ?? null,
      pageCount: item.file?.page_count ?? null,
      downloadUrl: item.file?.download_url ?? "",
      readUrl: item.file?.read_url ?? "",
      canPreviewInBrowser: item.file?.can_preview_in_browser ?? false,
    },

    flags: {
      isDownloadable: item.flags?.is_downloadable ?? false,
      isEnabled: item.flags?.is_enabled ?? false,
    },

    stats: {
      viewCount: item.stats?.view_count ?? 0,
      downloadCount: item.stats?.download_count ?? 0,
      ratingCount: item.stats?.rating_count ?? 0,
      ratingAvg: item.stats?.rating_avg ?? 0,
    },

    userState: {
      isFavorite: item.user_state?.is_favorite ?? false,
      viewCount: item.user_state?.view_count ?? 0,
      downloadCount: item.user_state?.download_count ?? 0,
      lastViewedAt: item.user_state?.last_viewed_at ?? null,
      lastDownloadedAt: item.user_state?.last_downloaded_at ?? null,
    },
  };
}

export function flattenInfiniteMaterials(pages = []) {
  return pages.flatMap((page) => page?.data?.data || []);
}

export function sortMaterials(items = [], sort = "Sort by New") {
  const list = [...items];

  switch (sort) {
    case "Title Ascending":
      return list.sort((a, b) => a.title.localeCompare(b.title));

    case "Title Descending":
      return list.sort((a, b) => b.title.localeCompare(a.title));

    case "Most Viewed":
      return list.sort(
        (a, b) =>
          (b.stats?.viewCount ?? 0) - (a.stats?.viewCount ?? 0),
      );

    case "Most Downloaded":
      return list.sort(
        (a, b) =>
          (b.stats?.downloadCount ?? 0) - (a.stats?.downloadCount ?? 0),
      );

    case "Highest Rated":
      return list.sort(
        (a, b) =>
          (b.stats?.ratingAvg ?? 0) - (a.stats?.ratingAvg ?? 0),
      );

    case "Sort by New":
    default:
      return list.sort(
        (a, b) =>
          new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
      );
  }
}

export const SORT_TO_API = {
  "Sort by New": "recent",
  "Most Viewed": "most_viewed",
  "Most Downloaded": "most_downloaded",
  "Highest Rated": "highest_rated",
  "Title Ascending": "alphabetical",
  "Title Descending": "recent",
};
