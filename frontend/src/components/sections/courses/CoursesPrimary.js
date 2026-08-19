"use client";

import CoursesGrid from "@/components/shared/courses/CoursesGrid";
import CoursesList from "@/components/shared/courses/CoursesList";
import {
  useInfiniteMaterialsList,
  useMaterialFilterOptions,
  useToggleMaterialFavorite,
} from "@/features/materials/hooks";
import {
  flattenInfiniteMaterials,
  mapMaterialToCardModel,
  SORT_TO_API,
} from "@/features/materials/utils";
import { useDebounce } from "@/hooks/dropdown/useDebounce";
import useIntersectionLoadMore from "@/hooks/useIntersectionLoadMore";
import {
  getStoredMaterialsView,
  saveMaterialsReturnUrl,
  setStoredMaterialsView,
} from "@/utils/materialHelpers";
import {
  Filter,
  Heart,
  LayoutGrid,
  List,
  Search,
  X,
} from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const SORT_OPTIONS = [
  "Sort by New",
  "Most Viewed",
  "Most Downloaded",
  "Title Ascending",
];

const MATERIAL_TYPE_OPTIONS = [
  { value: "pdf", label: "PDF" },
  { value: "slides", label: "Slides / PPT" },
  { value: "doc", label: "Document" },
  { value: "video", label: "Video" },
  { value: "other", label: "Other" },
];

const selectClass =
  "h-9 w-full appearance-none rounded-lg border border-ds-border bg-ds-surface-input px-2.5 pr-8 text-sm text-ds-text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-action disabled:cursor-not-allowed disabled:opacity-50";

/* -------------------------------------------------------------------------- */
/* Skeletons                                                                  */
/* -------------------------------------------------------------------------- */

const ListRowSkeleton = () => (
  <div className="flex flex-col gap-2 px-3 py-2.5 sm:flex-row sm:items-center sm:gap-3 sm:px-4 animate-pulse">
    <div className="flex min-w-0 flex-1 items-start gap-2.5 sm:items-center">
      <div className="h-9 w-9 shrink-0 rounded-lg bg-ds-surface-secondary" />
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="h-3.5 w-3/4 rounded bg-ds-surface-secondary" />
        <div className="h-3 w-1/2 rounded bg-ds-surface-secondary" />
      </div>
    </div>
    <div className="flex items-center gap-2">
      <div className="h-3 w-14 rounded bg-ds-surface-secondary" />
      <div className="h-8 w-20 rounded-lg bg-ds-surface-secondary" />
    </div>
  </div>
);

const ListSkeleton = ({ count = 5 }) => (
  <div className="overflow-hidden rounded-2xl border border-ds-border bg-ds-surface divide-y divide-ds-border">
    {[...Array(count)].map((_, i) => (
      <ListRowSkeleton key={i} />
    ))}
  </div>
);

const GridCardSkeleton = () => (
  <div className="rounded-xl border border-ds-border bg-ds-surface p-3 animate-pulse">
    <div className="mb-2 flex items-start justify-between">
      <div className="h-8 w-8 rounded-lg bg-ds-surface-secondary" />
      <div className="flex gap-1">
        <div className="h-7 w-7 rounded-md bg-ds-surface-secondary" />
        <div className="h-7 w-7 rounded-md bg-ds-surface-secondary" />
      </div>
    </div>
    <div className="mb-1.5 h-3.5 w-full rounded bg-ds-surface-secondary" />
    <div className="mb-1.5 h-3 w-2/3 rounded bg-ds-surface-secondary" />
    <div className="mb-2 h-3 w-1/2 rounded bg-ds-surface-secondary" />
    <div className="flex items-center justify-between border-t border-ds-border pt-2">
      <div className="h-3 w-14 rounded bg-ds-surface-secondary" />
      <div className="h-7 w-20 rounded-md bg-ds-surface-secondary" />
    </div>
  </div>
);

const GridSkeleton = ({ count = 6 }) => (
  <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
    {[...Array(count)].map((_, i) => (
      <GridCardSkeleton key={i} />
    ))}
  </div>
);

/* -------------------------------------------------------------------------- */
/* Small UI pieces                                                            */
/* -------------------------------------------------------------------------- */

const FilterChip = ({ label, onRemove }) => (
  <span className="inline-flex items-center gap-1.5 rounded-lg border border-ds-border bg-ds-surface px-3 py-1.5 text-xs text-ds-text-secondary">
    {label}
    <button
      type="button"
      onClick={onRemove}
      className="rounded text-ds-text-muted transition-colors hover:text-ds-error focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-action"
      aria-label={`Remove ${label}`}
    >
      <X className="h-3.5 w-3.5" aria-hidden="true" />
    </button>
  </span>
);

const CascadingFilterFields = ({
  semesters,
  courses,
  chapters,
  selectedSemester,
  selectedCourse,
  selectedChapter,
  onSemesterChange,
  onCourseChange,
  onChapterChange,
  isFilterOptionsLoading,
  idPrefix = "",
}) => (
  <>
    <div>
      <label
        htmlFor={`${idPrefix}semester`}
        className="mb-1 block text-[11px] font-medium text-ds-text-muted"
      >
        Semester
      </label>
      <div className="relative">
        <select
          id={`${idPrefix}semester`}
          value={selectedSemester ?? ""}
          onChange={(e) =>
            onSemesterChange(e.target.value ? Number(e.target.value) : null)
          }
          disabled={isFilterOptionsLoading}
          className={selectClass}
        >
          <option value="">All semesters</option>
          {semesters.map((sem) => (
            <option key={sem.id} value={sem.id}>
              {sem.label}
              {sem.count != null ? ` (${sem.count})` : ""}
            </option>
          ))}
        </select>
        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ds-text-muted text-xs">
          ▾
        </span>
      </div>
    </div>

    <div>
      <label
        htmlFor={`${idPrefix}course`}
        className="mb-1 block text-[11px] font-medium text-ds-text-muted"
      >
        Course
      </label>
      <div className="relative">
        <select
          id={`${idPrefix}course`}
          value={selectedCourse ?? ""}
          onChange={(e) =>
            onCourseChange(e.target.value ? Number(e.target.value) : null)
          }
          disabled={!selectedSemester}
          className={selectClass}
        >
          <option value="">
            {selectedSemester ? "All courses" : "Select semester first"}
          </option>
          {courses.map((course) => (
            <option key={course.id} value={course.id}>
              {course.label}
              {course.count != null ? ` (${course.count})` : ""}
            </option>
          ))}
        </select>
        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ds-text-muted text-xs">
          ▾
        </span>
      </div>
    </div>

    <div>
      <label
        htmlFor={`${idPrefix}chapter`}
        className="mb-1 block text-[11px] font-medium text-ds-text-muted"
      >
        Chapter
      </label>
      <div className="relative">
        <select
          id={`${idPrefix}chapter`}
          value={selectedChapter ?? ""}
          onChange={(e) =>
            onChapterChange(e.target.value ? Number(e.target.value) : null)
          }
          disabled={!selectedCourse}
          className={selectClass}
        >
          <option value="">
            {selectedCourse ? "All chapters" : "Select course first"}
          </option>
          {chapters.map((chapter) => (
            <option key={chapter.id} value={chapter.id}>
              {chapter.label}
              {chapter.count != null ? ` (${chapter.count})` : ""}
            </option>
          ))}
        </select>
        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ds-text-muted text-xs">
          ▾
        </span>
      </div>
    </div>
  </>
);

/* -------------------------------------------------------------------------- */
/* Main                                                                       */
/* -------------------------------------------------------------------------- */

const CoursesPrimary = ({ isNotSidebar, isList }) => {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const favoriteMutation = useToggleMaterialFavorite();
  const lastUrlRef = useRef("");

  const [isMobileFilterOpen, setIsMobileFilterOpen] = useState(false);
  const [favoriteOverrides, setFavoriteOverrides] = useState({});

  const [viewMode, setViewMode] = useState(() => {
    if (isList) return "list";
    const fromUrl = searchParams.get("view");
    if (fromUrl === "grid" || fromUrl === "list") return fromUrl;
    return getStoredMaterialsView();
  });

  const [favoriteOnly, setFavoriteOnly] = useState(
    searchParams.get("favorite") === "true",
  );
  const [selectedSemester, setSelectedSemester] = useState(
    searchParams.get("sem") ? Number(searchParams.get("sem")) : null,
  );
  const [selectedCourse, setSelectedCourse] = useState(
    searchParams.get("course") ? Number(searchParams.get("course")) : null,
  );
  const [selectedChapter, setSelectedChapter] = useState(
    searchParams.get("ch") ? Number(searchParams.get("ch")) : null,
  );
  const [searchString, setSearchString] = useState(searchParams.get("q") || "");
  const debouncedSearch = useDebounce(searchString, 300);
  const [selectedMaterialType, setSelectedMaterialType] = useState(
    searchParams.get("type") || "",
  );
  const [sortInput, setSortInput] = useState(() => {
    const fromUrl = searchParams.get("sort");
    if (fromUrl && SORT_OPTIONS.includes(fromUrl)) return fromUrl;
    return "Sort by New";
  });

  useEffect(() => {
    if (isList) setViewMode("list");
  }, [isList]);

  useEffect(() => {
    if (!isList) setStoredMaterialsView(viewMode);
  }, [viewMode, isList]);

  const buildQueryString = useCallback(() => {
    const params = new URLSearchParams();

    if (selectedSemester != null) params.set("sem", String(selectedSemester));
    if (selectedCourse != null) params.set("course", String(selectedCourse));
    if (selectedChapter != null) params.set("ch", String(selectedChapter));
    if (debouncedSearch) params.set("q", debouncedSearch);
    if (selectedMaterialType) params.set("type", selectedMaterialType);
    if (sortInput && sortInput !== "Sort by New") params.set("sort", sortInput);
    if (favoriteOnly) params.set("favorite", "true");
    if (viewMode && viewMode !== "list") params.set("view", viewMode);

    return params.toString();
  }, [
    selectedSemester,
    selectedCourse,
    selectedChapter,
    debouncedSearch,
    selectedMaterialType,
    sortInput,
    favoriteOnly,
    viewMode,
  ]);

  useEffect(() => {
    const qs = buildQueryString();
    const nextUrl = qs ? `${pathname}?${qs}` : pathname;
    saveMaterialsReturnUrl(nextUrl);

    if (qs === searchParams.toString() || lastUrlRef.current === nextUrl) {
      lastUrlRef.current = nextUrl;
      return;
    }

    lastUrlRef.current = nextUrl;
    router.replace(nextUrl, { scroll: false });
  }, [buildQueryString, pathname, router, searchParams]);

  const filterOptionsParams = useMemo(
    () => ({
      semester_id: selectedSemester || undefined,
      course_id: selectedCourse || undefined,
    }),
    [selectedSemester, selectedCourse],
  );

  const {
    data: filterOptionsResponse,
    isLoading: isFilterOptionsLoading,
  } = useMaterialFilterOptions(filterOptionsParams, {
    staleTime: 1000 * 60 * 5,
  });

  const semesters = filterOptionsResponse?.data?.options?.semesters || [];
  const courses = filterOptionsResponse?.data?.options?.courses || [];
  const chapters = filterOptionsResponse?.data?.options?.chapters || [];

  const materialsParams = useMemo(
    () => ({
      mode: "cursor",
      limit: 20,
      semester_id: selectedSemester || undefined,
      course_id: selectedCourse || undefined,
      chapter_id: selectedChapter || undefined,
      material_type: selectedMaterialType || undefined,
      search: debouncedSearch || undefined,
      sort_by:
        SORT_TO_API[sortInput] && SORT_TO_API[sortInput] !== "recent"
          ? SORT_TO_API[sortInput]
          : undefined,
      is_enabled: true,
      is_favorite: favoriteOnly || undefined,
    }),
    [
      selectedSemester,
      selectedCourse,
      selectedChapter,
      selectedMaterialType,
      debouncedSearch,
      sortInput,
      favoriteOnly,
    ],
  );

  const {
    data,
    isLoading,
    isFetching,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
  } = useInfiniteMaterialsList(materialsParams, {
    staleTime: 1000 * 30,
  });

  const materials = useMemo(() => {
    const raw = flattenInfiniteMaterials(data?.pages || []);

    return raw.map((item) => {
      const base = mapMaterialToCardModel(item);
      const apiIsFavorite =
        item?.user_state?.is_favorite ??
        item?.is_favorite ??
        base?.userState?.isFavorite ??
        false;

      const finalIsFavorite =
        favoriteOverrides[item.id] !== undefined
          ? favoriteOverrides[item.id]
          : apiIsFavorite;

      return {
        ...base,
        id: item.id,
        isFavorite: finalIsFavorite,
        userState: item?.user_state || null,
        rawItem: item,
      };
    });
  }, [data?.pages, favoriteOverrides]);

  const totalCount =
    data?.pages?.[0]?.data?.meta?.total_count ??
    data?.pages?.[0]?.data?.pagination?.total_count ??
    materials.length;

  const hasActiveFilters =
    !!selectedSemester ||
    !!selectedCourse ||
    !!selectedChapter ||
    !!selectedMaterialType ||
    !!debouncedSearch ||
    !!favoriteOnly;

  const activeFilterCount = [
    selectedSemester,
    selectedCourse,
    selectedChapter,
    selectedMaterialType,
    debouncedSearch,
    favoriteOnly ? "favorite" : null,
  ].filter(Boolean).length;

  const isInitialLoading = isLoading && !data?.pages?.length;
  const showUpdating =
    isFetching && !isFetchingNextPage && !isInitialLoading;
  const isListView = isList || viewMode === "list";

  const handleSemesterChange = (semId) => {
    setSelectedSemester(semId);
    setSelectedCourse(null);
    setSelectedChapter(null);
  };

  const handleCourseChange = (courseId) => {
    setSelectedCourse(courseId);
    setSelectedChapter(null);
  };

  const handleChapterChange = (chapterId) => {
    setSelectedChapter(chapterId);
  };

  const clearAll = () => {
    setSelectedSemester(null);
    setSelectedCourse(null);
    setSelectedChapter(null);
    setSelectedMaterialType("");
    setSearchString("");
    setSortInput("Sort by New");
    setFavoriteOnly(false);
    setIsMobileFilterOpen(false);
  };

  const handleViewChange = (next) => {
    if (isList) return;
    setViewMode(next);
  };

  const handleToggleFavorite = useCallback(
    async (material) => {
      if (!material?.id) return;

      const currentFavorite = !!material.isFavorite;
      const nextFavorite = !currentFavorite;

      setFavoriteOverrides((prev) => ({
        ...prev,
        [material.id]: nextFavorite,
      }));

      try {
        if (typeof favoriteMutation?.mutateAsync === "function") {
          await favoriteMutation.mutateAsync({
            id: material.id,
            is_favorite: nextFavorite,
          });
        } else if (typeof favoriteMutation?.mutate === "function") {
          favoriteMutation.mutate({
            id: material.id,
            is_favorite: nextFavorite,
          });
        }
      } catch (error) {
        setFavoriteOverrides((prev) => ({
          ...prev,
          [material.id]: currentFavorite,
        }));
        console.error("Favorite toggle failed:", error);
      }
    },
    [favoriteMutation],
  );

  const handleShareMaterial = useCallback((material) => {
    if (!material?.id) return;

    const shareUrl =
      typeof window !== "undefined"
        ? `${window.location.origin}/materials/${material.id}`
        : "";
    if (!shareUrl) return;

    const shareText = `New material uploaded: ${
      material?.title || "Material"
    }\n\nView here:\n${shareUrl}`;

    if (navigator.share) {
      navigator
        .share({
          title: material?.title || "Material",
          text: "Check this material",
          url: shareUrl,
        })
        .catch(() => {
          window.open(
            `https://wa.me/?text=${encodeURIComponent(shareText)}`,
            "_blank",
            "noopener,noreferrer",
          );
        });
      return;
    }

    window.open(
      `https://wa.me/?text=${encodeURIComponent(shareText)}`,
      "_blank",
      "noopener,noreferrer",
    );
  }, []);

  const loadMoreRef = useIntersectionLoadMore({
    enabled: true,
    hasNextPage,
    isFetchingNextPage,
    onLoadMore: fetchNextPage,
  });

  const cascadingProps = {
    semesters,
    courses,
    chapters,
    selectedSemester,
    selectedCourse,
    selectedChapter,
    onSemesterChange: handleSemesterChange,
    onCourseChange: handleCourseChange,
    onChapterChange: handleChapterChange,
    isFilterOptionsLoading,
  };

  return (
    <div className="min-h-screen bg-ds-page">
      <div className="container py-5 md:py-6 lg:py-8">
        {/* Header */}
        <div className="mb-4 flex flex-col gap-1.5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-ds-text-primary sm:text-2xl">
              Study Materials
            </h1>
            <p className="mt-0.5 text-sm text-ds-text-secondary">
              Browse notes, slides, and course files in one place.
            </p>
          </div>
          <span className="inline-flex w-fit items-center rounded-md bg-ds-surface-secondary px-2 py-0.5 text-xs font-semibold text-ds-text-secondary">
            {totalCount} {totalCount === 1 ? "result" : "results"}
          </span>
        </div>

        {/* Toolbar */}
        <div className="mb-4 space-y-2.5">
          <div className="relative">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ds-text-muted"
              aria-hidden="true"
            />
            <input
              type="search"
              placeholder="Search materials..."
              value={searchString}
              onChange={(e) => setSearchString(e.target.value)}
              className="h-9 w-full rounded-lg border border-ds-border bg-ds-surface-input py-2 pl-9 pr-3 text-sm text-ds-text-primary placeholder:text-ds-text-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-action"
              aria-label="Search materials"
            />
          </div>

          <div className="hidden grid-cols-2 gap-2 md:grid lg:grid-cols-5">
            <CascadingFilterFields {...cascadingProps} idPrefix="desk-" />

            <div>
              <label
                htmlFor="desk-type"
                className="mb-1 block text-[11px] font-medium text-ds-text-muted"
              >
                Type
              </label>
              <div className="relative">
                <select
                  id="desk-type"
                  value={selectedMaterialType}
                  onChange={(e) => setSelectedMaterialType(e.target.value)}
                  className={selectClass}
                >
                  <option value="">All types</option>
                  {MATERIAL_TYPE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ds-text-muted text-xs">
                  ▾
                </span>
              </div>
            </div>

            <div>
              <label
                htmlFor="desk-sort"
                className="mb-1 block text-[11px] font-medium text-ds-text-muted"
              >
                Sort
              </label>
              <div className="relative">
                <select
                  id="desk-sort"
                  value={sortInput}
                  onChange={(e) => setSortInput(e.target.value)}
                  className={selectClass}
                >
                  {SORT_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
                <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ds-text-muted text-xs">
                  ▾
                </span>
              </div>
            </div>
          </div>

          {/* Mobile type + sort */}
          <div className="grid grid-cols-2 gap-2 md:hidden">
            <div>
              <label
                htmlFor="mob-type"
                className="mb-1 block text-[11px] font-medium text-ds-text-muted"
              >
                Type
              </label>
              <div className="relative">
                <select
                  id="mob-type"
                  value={selectedMaterialType}
                  onChange={(e) => setSelectedMaterialType(e.target.value)}
                  className={selectClass}
                >
                  <option value="">All types</option>
                  {MATERIAL_TYPE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ds-text-muted text-xs">
                  ▾
                </span>
              </div>
            </div>
            <div>
              <label
                htmlFor="mob-sort"
                className="mb-1 block text-[11px] font-medium text-ds-text-muted"
              >
                Sort
              </label>
              <div className="relative">
                <select
                  id="mob-sort"
                  value={sortInput}
                  onChange={(e) => setSortInput(e.target.value)}
                  className={selectClass}
                >
                  {SORT_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
                <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ds-text-muted text-xs">
                  ▾
                </span>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setFavoriteOnly((prev) => !prev)}
              className={`inline-flex h-9 items-center gap-1.5 rounded-lg border px-3 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-action ${
                favoriteOnly
                  ? "border-ds-error/30 bg-ds-error/10 text-ds-error"
                  : "border-ds-border bg-ds-surface text-ds-text-secondary hover:bg-ds-surface-hover"
              }`}
              aria-pressed={favoriteOnly}
            >
              <Heart
                className={`h-4 w-4 ${favoriteOnly ? "fill-current" : ""}`}
                aria-hidden="true"
              />
              Favorites
            </button>

            {!isList ? (
              <div
                className="inline-flex rounded-lg border border-ds-border bg-ds-surface p-0.5"
                role="group"
                aria-label="View mode"
              >
                <button
                  type="button"
                  onClick={() => handleViewChange("list")}
                  className={`inline-flex h-8 w-8 items-center justify-center rounded-md transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-action ${
                    isListView
                      ? "bg-ds-action/10 text-ds-action"
                      : "text-ds-text-muted hover:text-ds-text-secondary"
                  }`}
                  aria-label="List view"
                  aria-pressed={isListView}
                >
                  <List className="h-4 w-4" aria-hidden="true" />
                </button>
                <button
                  type="button"
                  onClick={() => handleViewChange("grid")}
                  className={`inline-flex h-8 w-8 items-center justify-center rounded-md transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-action ${
                    !isListView
                      ? "bg-ds-action/10 text-ds-action"
                      : "text-ds-text-muted hover:text-ds-text-secondary"
                  }`}
                  aria-label="Grid view"
                  aria-pressed={!isListView}
                >
                  <LayoutGrid className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
            ) : null}

            <button
              type="button"
              onClick={() => setIsMobileFilterOpen(true)}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-ds-border bg-ds-surface px-3 text-sm font-medium text-ds-text-secondary transition-colors hover:bg-ds-surface-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-action md:hidden"
            >
              <Filter className="h-4 w-4 text-ds-action" aria-hidden="true" />
              Filters
              {activeFilterCount > 0 ? (
                <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-ds-action px-1.5 text-[10px] font-bold text-white">
                  {activeFilterCount}
                </span>
              ) : null}
            </button>

            {showUpdating ? (
              <span className="ml-auto text-xs text-ds-text-muted">
                Updating…
              </span>
            ) : null}
          </div>

          {hasActiveFilters ? (
            <div className="flex flex-wrap items-center gap-2">
              {favoriteOnly ? (
                <FilterChip
                  label="Favorites"
                  onRemove={() => setFavoriteOnly(false)}
                />
              ) : null}
              {selectedSemester ? (
                <FilterChip
                  label={
                    semesters.find((s) => s.id === selectedSemester)?.label ||
                    `Semester ${selectedSemester}`
                  }
                  onRemove={() => handleSemesterChange(null)}
                />
              ) : null}
              {selectedCourse ? (
                <FilterChip
                  label={
                    courses.find((c) => c.id === selectedCourse)?.label ||
                    "Course"
                  }
                  onRemove={() => handleCourseChange(null)}
                />
              ) : null}
              {selectedChapter ? (
                <FilterChip
                  label={
                    chapters.find((c) => c.id === selectedChapter)?.label ||
                    "Chapter"
                  }
                  onRemove={() => handleChapterChange(null)}
                />
              ) : null}
              {selectedMaterialType ? (
                <FilterChip
                  label={
                    MATERIAL_TYPE_OPTIONS.find(
                      (o) => o.value === selectedMaterialType,
                    )?.label || selectedMaterialType
                  }
                  onRemove={() => setSelectedMaterialType("")}
                />
              ) : null}
              {debouncedSearch ? (
                <FilterChip
                  label={`“${debouncedSearch}”`}
                  onRemove={() => setSearchString("")}
                />
              ) : null}
              <button
                type="button"
                onClick={clearAll}
                className="text-xs font-medium text-ds-text-muted transition-colors hover:text-ds-error focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-action rounded"
              >
                Clear all
              </button>
            </div>
          ) : null}
        </div>

        {/* Results */}
        <main>
          {isInitialLoading ? (
            isListView ? (
              <ListSkeleton />
            ) : (
              <GridSkeleton />
            )
          ) : materials.length > 0 ? (
            <div className="space-y-6">
              {isListView ? (
                <CoursesList
                  materials={materials}
                  onToggleFavorite={handleToggleFavorite}
                  onShareMaterial={handleShareMaterial}
                />
              ) : (
                <CoursesGrid
                  isNotSidebar={isNotSidebar !== false}
                  materials={materials}
                  onToggleFavorite={handleToggleFavorite}
                  onShareMaterial={handleShareMaterial}
                />
              )}

              <div ref={loadMoreRef} className="h-2 w-full" />

              {isFetchingNextPage
                ? isListView
                  ? <ListSkeleton count={3} />
                  : <GridSkeleton count={3} />
                : null}

              {!hasNextPage && materials.length > 0 ? (
                <p className="py-4 text-center text-sm text-ds-text-muted">
                  You’ve reached the end.
                </p>
              ) : null}
            </div>
          ) : (
            <div className="rounded-2xl border border-ds-border bg-ds-surface px-6 py-20 text-center">
              <p className="text-base font-medium text-ds-text-primary">
                {favoriteOnly
                  ? "No favorites yet"
                  : "No materials found"}
              </p>
              <p className="mt-2 text-sm text-ds-text-muted">
                {favoriteOnly
                  ? "Save materials with the heart icon to see them here."
                  : "Try adjusting your search or filters."}
              </p>
              {hasActiveFilters ? (
                <button
                  type="button"
                  onClick={clearAll}
                  className="mt-5 inline-flex items-center rounded-xl border border-ds-border bg-ds-surface-secondary px-4 py-2 text-sm font-medium text-ds-text-secondary transition-colors hover:bg-ds-surface-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-action"
                >
                  Clear filters
                </button>
              ) : null}
            </div>
          )}
        </main>
      </div>

      {/* Mobile filters sheet */}
      <div
        className={`fixed inset-0 z-50 md:hidden ${
          isMobileFilterOpen ? "pointer-events-auto" : "pointer-events-none"
        }`}
        aria-hidden={!isMobileFilterOpen}
      >
        <button
          type="button"
          className={`absolute inset-0 bg-black/40 transition-opacity ${
            isMobileFilterOpen ? "opacity-100" : "opacity-0"
          }`}
          onClick={() => setIsMobileFilterOpen(false)}
          aria-label="Close filters"
        />
        <div
          className={`absolute bottom-0 left-0 right-0 max-h-[85vh] overflow-y-auto rounded-t-2xl border-t border-ds-border bg-ds-surface p-5 shadow-xl transition-transform duration-300 ${
            isMobileFilterOpen ? "translate-y-0" : "translate-y-full"
          }`}
          role="dialog"
          aria-modal="true"
          aria-labelledby="mobile-filters-title"
        >
          <div className="mb-4 flex items-center justify-between">
            <h2
              id="mobile-filters-title"
              className="text-base font-semibold text-ds-text-primary"
            >
              Filters
            </h2>
            <button
              type="button"
              onClick={() => setIsMobileFilterOpen(false)}
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-ds-text-muted hover:bg-ds-surface-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-action"
              aria-label="Close filters"
            >
              <X className="h-5 w-5" aria-hidden="true" />
            </button>
          </div>

          <div className="space-y-3">
            <CascadingFilterFields {...cascadingProps} idPrefix="mob-" />
          </div>

          <div className="mt-6 flex gap-2">
            {hasActiveFilters ? (
              <button
                type="button"
                onClick={clearAll}
                className="flex-1 rounded-xl border border-ds-border px-4 py-2.5 text-sm font-medium text-ds-text-secondary hover:bg-ds-surface-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-action"
              >
                Clear all
              </button>
            ) : null}
            <button
              type="button"
              onClick={() => setIsMobileFilterOpen(false)}
              className="flex-1 rounded-xl bg-ds-action px-4 py-2.5 text-sm font-semibold text-white hover:bg-ds-action-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-action"
            >
              Show results
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CoursesPrimary;
