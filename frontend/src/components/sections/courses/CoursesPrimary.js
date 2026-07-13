"use client";

import CoursesGrid from "@/components/shared/courses/CoursesGrid";
import CoursesList from "@/components/shared/courses/CoursesList";
import NoData from "@/components/shared/others/NoData";
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
import useIntersectionLoadMore from "@/hooks/useIntersectionLoadMore";
import { useDebounce } from "@/hooks/dropdown/useDebounce";
import useTab from "@/hooks/useTab";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const sortInputs = [
  "Sort by New",
  "Most Viewed",
  "Most Downloaded",
  "Highest Rated",
  "Title Ascending",
];

const MATERIAL_TYPE_OPTIONS = [
  { value: "pdf", label: "PDF" },
  { value: "slides", label: "Slides / PPT" },
  { value: "doc", label: "Document" },
  { value: "video", label: "Video" },
  { value: "link", label: "Link" },
  { value: "other", label: "Other" },
];

/* -------------------------------------------------------------------------- */
/* Skeleton Loaders                                                           */
/* -------------------------------------------------------------------------- */

const GridCardSkeleton = () => (
  <div className="bg-white dark:bg-gray-800/40 rounded-2xl border border-gray-100 dark:border-gray-800 p-4 animate-pulse">
    <div className="w-full h-40 bg-gray-100 dark:bg-gray-700/50 rounded-xl mb-4" />
    <div className="space-y-3">
      <div className="h-5 bg-gray-100 dark:bg-gray-700/50 rounded w-full" />
      <div className="h-4 bg-gray-100 dark:bg-gray-700/50 rounded w-2/3" />
      <div className="h-4 bg-gray-100 dark:bg-gray-700/50 rounded w-1/2" />
      <div className="flex gap-2 pt-2">
        <div className="h-6 w-16 bg-gray-100 dark:bg-gray-700/50 rounded-full" />
        <div className="h-6 w-20 bg-gray-100 dark:bg-gray-700/50 rounded-full" />
      </div>
    </div>
  </div>
);

const ListRowSkeleton = () => (
  <div className="bg-white dark:bg-gray-800/40 rounded-2xl border border-gray-100 dark:border-gray-800 p-4 animate-pulse flex flex-col sm:flex-row gap-4 items-start sm:items-center">
    <div className="w-full sm:w-32 h-24 bg-gray-100 dark:bg-gray-700/50 rounded-xl shrink-0" />
    <div className="flex-1 space-y-3 w-full">
      <div className="h-5 bg-gray-100 dark:bg-gray-700/50 rounded w-3/4" />
      <div className="h-4 bg-gray-100 dark:bg-gray-700/50 rounded w-1/2" />
      <div className="h-4 bg-gray-100 dark:bg-gray-700/50 rounded w-1/3" />
      <div className="flex gap-2 pt-1">
        <div className="h-6 w-16 bg-gray-100 dark:bg-gray-700/50 rounded-full" />
        <div className="h-6 w-20 bg-gray-100 dark:bg-gray-700/50 rounded-full" />
      </div>
    </div>
  </div>
);

const GridSkeleton = ({ count = 6 }) => (
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
    {[...Array(count)].map((_, i) => (
      <GridCardSkeleton key={i} />
    ))}
  </div>
);

const ListSkeleton = ({ count = 5 }) => (
  <div className="space-y-4">
    {[...Array(count)].map((_, i) => (
      <ListRowSkeleton key={i} />
    ))}
  </div>
);

/* -------------------------------------------------------------------------- */
/* Filter Components                                                          */
/* -------------------------------------------------------------------------- */

const formatCount = (count) => (count < 10 ? `0${count}` : `${count}`);

const FilterChip = ({ label, active, count, onClick, disabled }) => (
  <button
    type="button"
    onClick={!disabled ? onClick : undefined}
    disabled={disabled}
    className={`
      w-full flex items-center justify-between px-4 py-2.5 rounded-xl text-sm transition-all mb-1
      ${
        active
          ? "bg-ds-action text-white shadow-sm"
          : "bg-ds-surface text-ds-text-secondary hover:bg-ds-surface-hover border border-ds-border"
      }
      ${disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}
    `}
  >
    <span className="font-medium truncate">{label}</span>
    {count !== undefined && (
      <span
        className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${
          active
            ? "bg-ds-surface-elevated text-white"
            : "bg-ds-surface-secondary text-ds-text-muted"
        }`}
      >
        {formatCount(count)}
      </span>
    )}
  </button>
);

const FilterSection = ({ title, children, disabled = false, badge }) => (
  <div className="mb-6">
    <div className="flex items-center justify-between px-1 mb-3">
      <span className="text-[10px] font-bold text-ds-text-muted uppercase tracking-widest">
        {title}
      </span>
      {badge && !disabled && (
        <span className="text-[9px] px-2 py-0.5 bg-ds-action/10 text-ds-action rounded-full font-bold">
          {badge}
        </span>
      )}
    </div>
    <div className={`space-y-1 ${disabled ? "opacity-50" : ""}`}>
      {children}
    </div>
  </div>
);

const ViewToggle = ({ currentIdx, onChange }) => (
  <div className="flex bg-white dark:bg-gray-800 p-1 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
    <button
      type="button"
      onClick={() => onChange(0)}
      className={`w-9 h-9 flex items-center justify-center rounded-lg transition-all ${
        currentIdx === 0
          ? "bg-ds-surface-hover text-ds-action shadow-sm"
          : "text-ds-text-muted hover:text-ds-text-secondary"
      }`}
      aria-label="Grid view"
    >
      <i className="icofont-layout text-lg" />
    </button>

    <button
      type="button"
      onClick={() => onChange(1)}
      className={`w-9 h-9 flex items-center justify-center rounded-lg transition-all ${
        currentIdx === 1
          ? "bg-ds-surface-hover text-ds-action shadow-sm"
          : "text-ds-text-muted hover:text-ds-text-secondary"
      }`}
      aria-label="List view"
    >
      <i className="icofont-listine-dots text-lg" />
    </button>
  </div>
);

const MaterialsSidebarFilters = ({
  mobile = false,
  currentIdx,
  onViewChange,
  searchString,
  onSearchChange,
  isSearchPending,
  isSearchFetching,
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
  isFilterOptionsFetching,
}) => (
  <div className="space-y-4">
    {mobile && (
      <FilterSection title="View">
        <ViewToggle currentIdx={currentIdx} onChange={onViewChange} />
      </FilterSection>
    )}

    <FilterSection title="Search">
      <div className="relative group">
        <input
          type="text"
          placeholder="Search materials..."
          value={searchString}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full px-4 py-3 pl-10 pr-10 bg-ds-surface-input border border-ds-border rounded-xl text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-focus transition-all text-ds-text-primary placeholder:text-ds-text-muted"
        />
        <i className="icofont-search-1 absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-primaryColor transition-colors" />
        {(isSearchPending || isSearchFetching) && (
          <span className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 border-2 border-primaryColor/30 border-t-primaryColor rounded-full animate-spin" />
        )}
      </div>
    </FilterSection>

    <FilterSection
      title="Semester"
      badge={semesters.length ? `${semesters.length}` : undefined}
    >
      {isFilterOptionsLoading ? (
        <div className="space-y-2">
          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className="h-11 rounded-xl bg-gray-100 dark:bg-gray-800/60 animate-pulse"
            />
          ))}
        </div>
      ) : (
        <div className="max-h-48 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
          {semesters.map((sem) => (
            <FilterChip
              key={sem.id}
              label={sem.label}
              count={sem.count}
              active={selectedSemester === sem.id}
              onClick={() => onSemesterChange(sem.id)}
            />
          ))}
        </div>
      )}
    </FilterSection>

    <FilterSection
      title="Course"
      disabled={!selectedSemester}
      badge={courses.length ? `${courses.length}` : undefined}
    >
      {!selectedSemester ? (
        <div className="text-center py-4 text-xs font-medium text-gray-400 bg-white/50 dark:bg-gray-800/30 rounded-xl border-2 border-dashed border-gray-100 dark:border-gray-700/50">
          Select a semester first
        </div>
      ) : isFilterOptionsFetching ? (
        <div className="space-y-2">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="h-11 rounded-xl bg-gray-100 dark:bg-gray-800/60 animate-pulse"
            />
          ))}
        </div>
      ) : (
        <div className="max-h-48 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
          {courses.length ? (
            courses.map((course) => (
              <FilterChip
                key={course.id}
                label={course.label}
                count={course.count}
                active={selectedCourse === course.id}
                onClick={() => onCourseChange(course.id)}
              />
            ))
          ) : (
            <div className="text-center py-4 text-xs font-medium text-gray-400 bg-white/50 dark:bg-gray-800/30 rounded-xl border-2 border-dashed border-gray-100 dark:border-gray-700/50">
              No courses found
            </div>
          )}
        </div>
      )}
    </FilterSection>

    <FilterSection
      title="Chapter"
      disabled={!selectedCourse}
      badge={chapters.length ? `${chapters.length}` : undefined}
    >
      {!selectedCourse ? (
        <div className="text-center py-4 text-xs font-medium text-gray-400 bg-white/50 dark:bg-gray-800/30 rounded-xl border-2 border-dashed border-gray-100 dark:border-gray-700/50">
          Select a course first
        </div>
      ) : isFilterOptionsFetching ? (
        <div className="space-y-2">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="h-11 rounded-xl bg-gray-100 dark:bg-gray-800/60 animate-pulse"
            />
          ))}
        </div>
      ) : (
        <div className="max-h-48 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
          {chapters.length ? (
            chapters.map((chapter) => (
              <FilterChip
                key={chapter.id}
                label={chapter.label}
                count={chapter.count}
                active={selectedChapter === chapter.id}
                onClick={() => onChapterChange(chapter.id)}
              />
            ))
          ) : (
            <div className="text-center py-4 text-xs font-medium text-gray-400 bg-white/50 dark:bg-gray-800/30 rounded-xl border-2 border-dashed border-gray-100 dark:border-gray-700/50">
              No chapters found
            </div>
          )}
        </div>
      )}
    </FilterSection>
  </div>
);

/* -------------------------------------------------------------------------- */
/* Main Component                                                             */
/* -------------------------------------------------------------------------- */

const CoursesPrimary = ({ isNotSidebar, isList }) => {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { currentIdx, setCurrentIdx } = useTab();

  const favoriteMutation = useToggleMaterialFavorite();

  const [isMobileFilterOpen, setIsMobileFilterOpen] = useState(false);
  const [favoriteOverrides, setFavoriteOverrides] = useState({});
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
  const debouncedSearch = useDebounce(searchString, 500);
  const [selectedMaterialType, setSelectedMaterialType] = useState(
    searchParams.get("type") || "",
  );
  const [sortInput, setSortInput] = useState(
    searchParams.get("sort") || "Sort by New",
  );

  useEffect(() => {
    if (isList) setCurrentIdx(1);
  }, [isList, setCurrentIdx]);

  const updateURL = useCallback(
    (updates) => {
      const params = new URLSearchParams(searchParams.toString());

      Object.entries(updates).forEach(([k, v]) => {
        if (v === null || v === undefined || v === "") {
          params.delete(k);
        } else {
          params.set(k, String(v));
        }
      });

      const qs = params.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  useEffect(() => {
    updateURL({
      sem: selectedSemester,
      course: selectedCourse,
      ch: selectedChapter,
      q: debouncedSearch || null,
      type: selectedMaterialType || null,
      sort: sortInput !== "Sort by New" ? sortInput : null,
      favorite: favoriteOnly ? "true" : null,
    });
  }, [
    selectedSemester,
    selectedCourse,
    selectedChapter,
    debouncedSearch,
    selectedMaterialType,
    sortInput,
    favoriteOnly,
    updateURL,
  ]);

  const filterOptionsParams = useMemo(
    () => ({
      semester_id: selectedSemester || undefined,
      course_id: selectedCourse || undefined,
      chapter_id: selectedChapter || undefined,
      material_type: selectedMaterialType || undefined,
    }),
    [
      selectedSemester,
      selectedCourse,
      selectedChapter,
      selectedMaterialType,
    ],
  );

  const {
    data: filterOptionsResponse,
    isLoading: isFilterOptionsLoading,
    isFetching: isFilterOptionsFetching,
  } = useMaterialFilterOptions(filterOptionsParams, {
    staleTime: 1000 * 60 * 5,
  });

  const semesters = filterOptionsResponse?.data?.options?.semesters || [];
  const courses = filterOptionsResponse?.data?.options?.courses || [];
  const chapters = filterOptionsResponse?.data?.options?.chapters || [];

  const materialsParams = useMemo(
    () => ({
      mode: "cursor",
      limit: 10,
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

    const mapped = raw.map((item) => {
      const base = mapMaterialToCardModel(item);

      const apiIsFavorite =
        item?.user_state?.is_favorite ??
        item?.is_favorite ??
        base?.isFavorite ??
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

    const visibleMaterials = favoriteOnly
      ? mapped.filter((item) => item.isFavorite)
      : mapped;

    return visibleMaterials;
  }, [data?.pages, favoriteOverrides, favoriteOnly]);

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

  const isSearchPending = searchString !== debouncedSearch;
  const isSearchFetching = isFetching && !isFetchingNextPage;
  const isInitialLoading = isLoading && !(data?.pages?.length);

  const handleSemesterChange = (semId) => {
    const nextValue = selectedSemester === semId ? null : semId;
    setSelectedSemester(nextValue);
    setSelectedCourse(null);
    setSelectedChapter(null);
  };

  const handleCourseChange = (courseId) => {
    const nextValue = selectedCourse === courseId ? null : courseId;
    setSelectedCourse(nextValue);
    setSelectedChapter(null);
  };

  const handleChapterChange = (chapterId) => {
    const nextValue = selectedChapter === chapterId ? null : chapterId;
    setSelectedChapter(nextValue);
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
    router.replace(pathname, { scroll: false });
  };

  const handleViewChange = (idx) => {
    setCurrentIdx(idx);
  };

  const handleToggleFavoriteFilter = () => {
    setFavoriteOnly((prev) => !prev);
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
          const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(
            shareText,
          )}`;
          window.open(whatsappUrl, "_blank", "noopener,noreferrer");
        });
      return;
    }

    const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(shareText)}`;
    window.open(whatsappUrl, "_blank", "noopener,noreferrer");
  }, []);

  const loadMoreRef = useIntersectionLoadMore({
    enabled: true,
    hasNextPage,
    isFetchingNextPage,
    onLoadMore: fetchNextPage,
  });

  const sidebarProps = {
    currentIdx,
    onViewChange: handleViewChange,
    searchString,
    onSearchChange: setSearchString,
    isSearchPending,
    isSearchFetching,
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
    isFilterOptionsFetching,
  };

  return (
    <div className="bg-gray-50/50 dark:bg-ds-page min-h-screen">
      <div className="container py-6 md:py-8 lg:py-10">
        <div className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-5 bg-transparent">
          <div>
            <h1 className="text-2xl font-bold text-ds-text-primary tracking-tight">
              Study Materials
            </h1>
            <div className="flex items-center gap-3 mt-2">
              <span className="inline-flex items-center justify-center px-2.5 py-1 rounded-md bg-ds-surface-secondary text-xs font-semibold text-ds-text-secondary">
                {totalCount} {totalCount === 1 ? "Result" : "Results"}
              </span>
              {hasActiveFilters && (
                <button
                  type="button"
                  onClick={clearAll}
                  className="text-[11px] font-bold text-gray-400 hover:text-red-500 uppercase tracking-wider transition-colors"
                >
                  Clear Filters
                </button>
              )}
            </div>
          </div>

          <div className="flex items-center flex-wrap gap-2">
            <button
              type="button"
              onClick={handleToggleFavoriteFilter}
              className={`px-4 py-2 rounded-xl border text-sm font-medium transition-all ${
                favoriteOnly
                  ? "bg-red-50 dark:bg-red-500/10 text-red-500 border-red-200 dark:border-red-500/20"
                  : "bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 border-gray-100 dark:border-gray-700 hover:text-red-500 hover:border-red-200 dark:hover:border-red-500/20"
              }`}
            >
              <span className="inline-flex items-center gap-2">
                <i className="icofont-heart-alt" />
                My Favorites
              </span>
            </button>

            <button
              type="button"
              onClick={() => setIsMobileFilterOpen(true)}
              className="lg:hidden flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 text-sm font-medium shadow-sm hover:shadow-md transition-all"
            >
              <i className="icofont-filter text-primaryColor" />
              <span className="text-gray-700 dark:text-gray-200">Filters</span>
              {activeFilterCount > 0 && (
                <span className="w-5 h-5 bg-primaryColor text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                  {activeFilterCount}
                </span>
              )}
            </button>

            <div className="flex bg-ds-surface p-1 rounded-xl shadow-sm border border-ds-border">
              <div className="hidden lg:flex items-center gap-1 border-r border-gray-100 dark:border-gray-700 pr-2 mr-2">
                <ViewToggle
                  currentIdx={currentIdx}
                  onChange={handleViewChange}
                />
              </div>

              <div className="relative flex items-center h-9 px-1 border-r border-gray-100 dark:border-gray-700 pr-2 mr-2">
                <select
                  value={selectedMaterialType}
                  onChange={(e) => setSelectedMaterialType(e.target.value)}
                  className="appearance-none text-sm font-medium bg-transparent text-gray-700 dark:text-gray-300 pl-3 pr-8 focus:outline-none cursor-pointer min-w-[120px]"
                  aria-label="Filter by material type"
                >
                  <option value="" className="dark:bg-gray-800">
                    All types
                  </option>
                  {MATERIAL_TYPE_OPTIONS.map((opt) => (
                    <option
                      key={opt.value}
                      value={opt.value}
                      className="dark:bg-gray-800"
                    >
                      {opt.label}
                    </option>
                  ))}
                </select>
                <i className="icofont-rounded-down absolute right-3 text-gray-400 pointer-events-none text-sm" />
              </div>

              <div className="relative flex items-center h-9 px-1">
                <select
                  value={sortInput}
                  onChange={(e) => setSortInput(e.target.value)}
                  className="appearance-none text-sm font-medium bg-transparent text-gray-700 dark:text-gray-300 pl-3 pr-8 focus:outline-none cursor-pointer"
                >
                  {sortInputs.map((s) => (
                    <option key={s} value={s} className="dark:bg-gray-800">
                      {s}
                    </option>
                  ))}
                </select>
                <i className="icofont-rounded-down absolute right-3 text-gray-400 pointer-events-none text-sm" />
              </div>
            </div>
          </div>
        </div>

        {hasActiveFilters && (
          <div className="flex flex-wrap gap-2 mb-6">
            {favoriteOnly && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700 shadow-sm text-xs text-gray-700 dark:text-gray-300">
                Favorites
                <button
                  type="button"
                  onClick={() => setFavoriteOnly(false)}
                  className="ml-1 text-gray-400 hover:text-red-500"
                >
                  <i className="icofont-close-line text-sm" />
                </button>
              </span>
            )}

            {selectedSemester && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700 shadow-sm text-xs text-gray-700 dark:text-gray-300">
                <span className="font-semibold text-primaryColor">
                  Semester
                </span>
                {semesters.find((s) => s.id === selectedSemester)?.label ||
                  selectedSemester}
                <button
                  type="button"
                  onClick={() => handleSemesterChange(selectedSemester)}
                  className="ml-1 text-gray-400 hover:text-red-500"
                >
                  <i className="icofont-close-line text-sm" />
                </button>
              </span>
            )}

            {selectedCourse && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700 shadow-sm text-xs text-gray-700 dark:text-gray-300">
                {courses.find((c) => c.id === selectedCourse)?.label ||
                  selectedCourse}
                <button
                  type="button"
                  onClick={() => handleCourseChange(selectedCourse)}
                  className="ml-1 text-gray-400 hover:text-red-500"
                >
                  <i className="icofont-close-line text-sm" />
                </button>
              </span>
            )}

            {selectedChapter && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700 shadow-sm text-xs text-gray-700 dark:text-gray-300">
                {chapters.find((c) => c.id === selectedChapter)?.label ||
                  selectedChapter}
                <button
                  type="button"
                  onClick={() => handleChapterChange(selectedChapter)}
                  className="ml-1 text-gray-400 hover:text-red-500"
                >
                  <i className="icofont-close-line text-sm" />
                </button>
              </span>
            )}

            {searchString && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700 shadow-sm text-xs text-gray-700 dark:text-gray-300">
                {searchString}
                <button
                  type="button"
                  onClick={() => setSearchString("")}
                  className="ml-1 text-gray-400 hover:text-red-500"
                >
                  <i className="icofont-close-line text-sm" />
                </button>
              </span>
            )}

            {selectedMaterialType && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700 shadow-sm text-xs text-gray-700 dark:text-gray-300">
                <span className="font-semibold text-primaryColor">Type</span>
                {MATERIAL_TYPE_OPTIONS.find((o) => o.value === selectedMaterialType)
                  ?.label || selectedMaterialType}
                <button
                  type="button"
                  onClick={() => setSelectedMaterialType("")}
                  className="ml-1 text-gray-400 hover:text-red-500"
                >
                  <i className="icofont-close-line text-sm" />
                </button>
              </span>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <aside className="hidden lg:block lg:col-span-3">
            <div className="sticky top-24 max-h-[calc(100vh-120px)] overflow-y-auto pr-2 custom-scrollbar">
              <MaterialsSidebarFilters {...sidebarProps} />
            </div>
          </aside>

          <main className="lg:col-span-9">
            {isInitialLoading ? (
              currentIdx === 0 ? (
                <GridSkeleton />
              ) : (
                <ListSkeleton />
              )
            ) : materials.length > 0 ? (
              <div className="space-y-8">
                <div className="tab-contents">
                  {currentIdx === 0 ? (
                    <CoursesGrid
                      isNotSidebar={isNotSidebar}
                      materials={materials}
                      onToggleFavorite={handleToggleFavorite}
                      onShareMaterial={handleShareMaterial}
                    />
                  ) : (
                    <CoursesList
                      materials={materials}
                      onToggleFavorite={handleToggleFavorite}
                      onShareMaterial={handleShareMaterial}
                    />
                  )}
                </div>

                <div ref={loadMoreRef} className="h-2 w-full" />

                {isFetchingNextPage &&
                  (currentIdx === 0 ? (
                    <GridSkeleton count={3} />
                  ) : (
                    <ListSkeleton count={3} />
                  ))}

                {!hasNextPage && materials.length > 0 && (
                  <div className="text-center text-sm text-gray-400 py-6">
                    You have reached the end.
                  </div>
                )}
              </div>
            ) : (
              <NoData
                message={
                  favoriteOnly
                    ? "No favorite materials found."
                    : "No materials found matching your filters."
                }
              />
            )}

            {isSearchFetching && !isInitialLoading && (
              <div className="mt-4 flex items-center gap-2 text-xs text-gray-400">
                <span className="w-3 h-3 border-2 border-primaryColor/30 border-t-primaryColor rounded-full animate-spin" />
                Updating results...
              </div>
            )}
          </main>
        </div>
      </div>

      <div
        className={`fixed inset-0 z-50 lg:hidden transition-all duration-300 ${
          isMobileFilterOpen ? "visible" : "invisible"
        }`}
      >
        <div
          className={`absolute inset-0 bg-black/40 backdrop-blur-sm transition-opacity duration-300 ${
            isMobileFilterOpen ? "opacity-100" : "opacity-0"
          }`}
          onClick={() => setIsMobileFilterOpen(false)}
        />
        <div
          className={`absolute right-0 top-0 h-full w-[85%] max-w-[360px] bg-gray-50 dark:bg-gray-900 shadow-2xl transform transition-transform duration-300 ease-out ${
            isMobileFilterOpen ? "translate-x-0" : "translate-x-full"
          }`}
        >
          <div className="sticky top-0 flex items-center justify-between p-5 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
            <div className="flex items-center gap-2">
              <i className="icofont-filter text-primaryColor" />
              <h3 className="font-bold text-gray-900 dark:text-white">
                Filters
              </h3>
            </div>
            <button
              type="button"
              onClick={() => setIsMobileFilterOpen(false)}
              className="w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-500 hover:text-gray-900 dark:hover:text-white transition-colors"
            >
              <i className="icofont-close" />
            </button>
          </div>

          <div className="p-5 overflow-y-auto h-[calc(100%-73px)]">
            <div className="mb-4">
              <button
                type="button"
                onClick={handleToggleFavoriteFilter}
                className={`w-full flex items-center justify-center gap-2 px-4 py-2 rounded-xl border text-sm font-medium transition-all ${
                  favoriteOnly
                    ? "bg-red-50 dark:bg-red-500/10 text-red-500 border-red-200 dark:border-red-500/20"
                    : "bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 border-gray-100 dark:border-gray-700"
                }`}
              >
                <i className="icofont-heart-alt" />
                <span>My Favorites</span>
              </button>
            </div>

            <MaterialsSidebarFilters {...sidebarProps} mobile />
            {hasActiveFilters && (
              <button
                type="button"
                onClick={() => {
                  clearAll();
                  setIsMobileFilterOpen(false);
                }}
                className="w-full mt-8 py-3 bg-red-50 dark:bg-red-500/10 text-red-500 hover:bg-red-100 dark:hover:bg-red-500/20 rounded-xl text-sm font-bold transition-colors"
              >
                Clear All Filters
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CoursesPrimary;
