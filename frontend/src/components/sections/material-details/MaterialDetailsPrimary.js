"use client";

import BalbImage from "@/components/shared/animaited-images/BalbImage";
import BookImage from "@/components/shared/animaited-images/BookImage";
import GlobImage from "@/components/shared/animaited-images/GlobImage";
import {
  useMaterialDetail,
  useToggleMaterialFavorite,
  useTrackMaterialDownload,
  useTrackMaterialView,
} from "@/features/materials/hooks";
import { mapMaterialToCardModel } from "@/features/materials/utils";
import { getFileIcon, getSemesterBg } from "@/utils/fileIcons";
import Link from "next/link";
import { useEffect, useRef } from "react";
import MaterialAiAssistant from "@/components/chatbot/MaterialAiAssistant";
import MaterialFeedbackPanel from "@/components/materials/MaterialFeedbackPanel";

const formatFileSize = (sizeMb) => {
  if (sizeMb === null || sizeMb === undefined || Number.isNaN(Number(sizeMb))) {
    return "—";
  }

  const num = Number(sizeMb);
  return `${num % 1 === 0 ? num.toFixed(0) : num.toFixed(1)} MB`;
};

const formatDate = (value) => {
  if (!value) return "—";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";

  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date);
};

const normalizeUrl = (url) => {
  if (!url) return "#";
  return String(url).replace("http://127.0.0.1:7000", "http://localhost:7000");
};

const getFilenameFromContentDisposition = (headerValue) => {
  if (!headerValue) return null;

  const utf8Match = headerValue.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1].replace(/["]/g, ""));
    } catch {
      return utf8Match[1].replace(/["]/g, "");
    }
  }

  const normalMatch = headerValue.match(/filename="?([^"]+)"?/i);
  if (normalMatch?.[1]) return normalMatch[1];

  return null;
};

const getSafeFileName = (material, rawMaterial) => {
  const title = material?.title || rawMaterial?.title || "material";

  const ext =
    material?.file?.extension ||
    rawMaterial?.file?.extension ||
    material?.materialType ||
    rawMaterial?.material_type ||
    "file";

  const safeTitle = String(title)
    .replace(/[<>:"/\\|?*\x00-\x1F]/g, "_")
    .trim();

  return `${safeTitle || "material"}.${String(ext).replace(/^\./, "")}`;
};

const getAuthHeaders = () => {
  if (typeof window === "undefined") return {};

  const token =
    localStorage.getItem("token") ||
    localStorage.getItem("access_token") ||
    localStorage.getItem("authToken");

  return token ? { Authorization: `Bearer ${token}` } : {};
};

const downloadBlobFromUrl = async ({ url, filename }) => {
  const response = await fetch(url, {
    method: "GET",
    credentials: "include",
    headers: getAuthHeaders(),
  });

  if (response.status === 401) {
    throw new Error("Your login session expired. Please login again.");
  }

  if (response.status === 403) {
    throw new Error("You do not have permission to download this file.");
  }

  if (!response.ok) {
    throw new Error("Download failed. Please try again.");
  }

  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    const text = await response.text().catch(() => "");
    throw new Error(text || "Download failed. Server returned JSON.");
  }

  const blob = await response.blob();

  const responseFileName = getFilenameFromContentDisposition(
    response.headers.get("content-disposition"),
  );

  const blobUrl = window.URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = responseFileName || filename;
  link.style.display = "none";

  document.body.appendChild(link);
  link.click();
  link.remove();

  window.URL.revokeObjectURL(blobUrl);
};

const getPagesOrSlidesLabel = (material, rawMaterial) => {
  const mappedFile = material?.file || {};
  const rawFile = rawMaterial?.file || {};

  const slideCount = mappedFile.slideCount ?? rawFile.slide_count;
  const pageCount = mappedFile.pageCount ?? rawFile.page_count;

  if (slideCount != null) return `${slideCount} Slides`;
  if (pageCount != null) return `${pageCount} Pages`;

  return "—";
};

const HeroSkeleton = () => (
  <section className="relative overflow-hidden bg-blueDark py-16 lg:py-24 animate-pulse">
    <div className="container relative z-10">
      <div className="max-w-4xl">
        <div className="h-12 w-2/3 rounded bg-white/10 mb-4" />
        <div className="h-12 w-1/2 rounded bg-white/10 mb-6" />
        <div className="h-5 w-full max-w-2xl rounded bg-white/10 mb-3" />
      </div>
    </div>
  </section>
);

const ContentSkeleton = () => (
  <main className="container py-12 lg:py-20">
    <div className="h-96 rounded-2xl bg-gray-200 dark:bg-gray-800 animate-pulse" />
  </main>
);

const ErrorState = ({ title, message, showRetry = true }) => (
  <div className="container py-16 lg:py-24">
    <div className="max-w-2xl mx-auto text-center bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-3xl shadow-sm p-8 lg:p-10">
      <h1 className="text-2xl lg:text-3xl font-bold text-blackColor dark:text-white mb-4">
        {title}
      </h1>

      <p className="text-paragraphColor dark:text-gray-400 leading-relaxed mb-8">
        {message}
      </p>

      <div className="flex items-center justify-center gap-3 flex-wrap">
        <Link
          href="/materials"
          className="px-5 py-3 rounded-xl bg-primaryColor text-white font-bold hover:opacity-90 transition-all"
        >
          Back to Materials
        </Link>

        {showRetry ? (
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="px-5 py-3 rounded-xl border border-gray-200 dark:border-gray-700 text-blackColor dark:text-white font-bold hover:bg-gray-50 dark:hover:bg-gray-800 transition-all"
          >
            Try Again
          </button>
        ) : null}
      </div>
    </div>
  </div>
);

const MaterialDetailsPrimary = ({ id }) => {
  const numericId = Number(id);

  const { data, isLoading, isError, error } = useMaterialDetail(numericId, {
    retry: 1,
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60,
  });

  const { mutate: trackView } = useTrackMaterialView();
  const { mutate: trackDownload } = useTrackMaterialDownload();
  const { mutate: toggleFavorite } = useToggleMaterialFavorite();

  const hasTrackedViewRef = useRef(false);
  const rawMaterial = data?.data?.data;

  useEffect(() => {
    if (!numericId || !rawMaterial) return;
    if (hasTrackedViewRef.current) return;

    const sessionKey = `material_view_tracked_${numericId}`;
    if (typeof window !== "undefined" && sessionStorage.getItem(sessionKey)) {
      hasTrackedViewRef.current = true;
      return;
    }

    hasTrackedViewRef.current = true;
    if (typeof window !== "undefined") {
      sessionStorage.setItem(sessionKey, "1");
    }
    trackView({ id: numericId, cooldown_seconds: 3600 });
  }, [numericId, rawMaterial, trackView]);

  if (!id || Number.isNaN(numericId)) {
    return (
      <ErrorState
        title="Invalid material link"
        message="The material ID in the URL is not valid."
        showRetry={false}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-white dark:bg-gray-900">
        <HeroSkeleton />
        <ContentSkeleton />
      </div>
    );
  }

  if (isError) {
    const status =
      error?.status || error?.response?.status || error?.cause?.status || null;

    return (
      <ErrorState
        title={
          status === 404 ? "Material not found" : "Could not load material"
        }
        message={
          status === 404
            ? "The material you are looking for does not exist or may have been removed."
            : "We were unable to load this material right now."
        }
        showRetry={status !== 404}
      />
    );
  }

  if (!rawMaterial) {
    return (
      <ErrorState
        title="Material not found"
        message="No material data was returned from the server."
        showRetry={false}
      />
    );
  }

  const material = {
    ...mapMaterialToCardModel(rawMaterial),
    learningObjectives: rawMaterial?.learning_objectives || [],
  };

  const mappedFile = material?.file || {};
  const rawFile = rawMaterial?.file || {};

  const readHref = normalizeUrl(mappedFile.readUrl || rawFile.read_url || "");
  const downloadHref = normalizeUrl(
    mappedFile.downloadUrl || rawFile.download_url || "",
  );

  const canPreviewInBrowser =
    mappedFile.canPreviewInBrowser ?? rawFile.can_preview_in_browser ?? false;

  const isDownloadable =
    material?.flags?.isDownloadable ??
    rawMaterial?.flags?.is_downloadable ??
    false;

  const canPreviewFile =
    Boolean(readHref && readHref !== "#") && Boolean(canPreviewInBrowser);

  const canDownloadFile =
    Boolean(downloadHref && downloadHref !== "#") && Boolean(isDownloadable);

  const isFavorite =
    material?.isFavorite ?? rawMaterial?.user_state?.is_favorite ?? false;

  const fileIconClass = getFileIcon(
    mappedFile.extension || rawFile.extension || material?.materialType,
  );

  const semesterBg = getSemesterBg(material?.semesterNumber || 1);

  const shareUrl =
    typeof window !== "undefined"
      ? `${window.location.origin}/materials/${numericId}`
      : "";

  const shareText = `New material uploaded: ${
    material?.title || "Material"
  }\n\nView here:\n${shareUrl}`;

  const handleOpenPreview = () => {
    if (!canPreviewFile) return;
    window.open(readHref, "_blank", "noopener,noreferrer");
  };

  const handleOpenDownload = async () => {
    if (!canDownloadFile) {
      alert("This material is not available for download.");
      return;
    }

    try {
      await downloadBlobFromUrl({
        url: downloadHref,
        filename: getSafeFileName(material, rawMaterial),
      });

      trackDownload(numericId);
    } catch (error) {
      console.error("Download failed:", error);
      alert(error?.message || "Download failed. Please check your connection.");
    }
  };

  const handleCopyLink = async () => {
    if (!shareUrl) return;

    try {
      await navigator.clipboard.writeText(shareUrl);
      window.alert("Link copied successfully.");
    } catch {
      window.alert("Could not copy the link.");
    }
  };

  const handleShareWhatsApp = () => {
    if (!shareUrl) return;

    const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(shareText)}`;
    window.open(whatsappUrl, "_blank", "noopener,noreferrer");
  };

  const handleNativeShare = async () => {
    if (!shareUrl) return;

    if (navigator.share) {
      try {
        await navigator.share({
          title: material?.title || "Material",
          text: "Check this material",
          url: shareUrl,
        });
        return;
      } catch {}
    }

    handleShareWhatsApp();
  };

  const fileType =
    mappedFile.extension?.toUpperCase() ||
    rawFile.extension?.toUpperCase() ||
    "—";

  const fileSize = formatFileSize(mappedFile.sizeMb ?? rawFile.size_mb);

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900 transition-colors duration-300">
      <section className="relative overflow-hidden bg-blueDark py-16 lg:py-24">
        <div className="opacity-30">
          <BookImage />
          <GlobImage />
          <BalbImage />
        </div>

        <div className="container relative z-10">
          <div className="max-w-4xl" data-aos="fade-up">
            <div className="flex flex-wrap gap-2 mb-6">
              {material?.courseCode ? (
                <span className="px-4 py-1 bg-white/10 backdrop-blur-md border border-white/20 rounded-full text-xs font-bold text-white uppercase tracking-wider">
                  {material.courseCode}
                </span>
              ) : null}

              {material?.departmentName ? (
                <span className="px-4 py-1 bg-white/10 backdrop-blur-md border border-white/20 rounded-full text-xs font-bold text-white uppercase tracking-wider">
                  {material.departmentName}
                </span>
              ) : null}

              {material?.semesterName ? (
                <span
                  className={`px-4 py-1 rounded-full text-xs font-bold text-white uppercase tracking-wider ${semesterBg}`}
                >
                  {material.semesterName}
                </span>
              ) : null}

              {material?.flags?.isEnabled ? (
                <span className="px-4 py-1 bg-secondaryColor/20 border border-secondaryColor/30 text-secondaryColor rounded-full text-xs font-bold uppercase tracking-wider">
                  Enabled
                </span>
              ) : (
                <span className="px-4 py-1 bg-red-500/20 border border-red-400/30 text-red-300 rounded-full text-xs font-bold uppercase tracking-wider">
                  Disabled
                </span>
              )}
            </div>

            <div className="flex items-center gap-4 mb-6">
              <div className="w-16 h-16 rounded-2xl bg-white/10 border border-white/10 flex items-center justify-center text-white text-3xl shrink-0">
                <i className={fileIconClass}></i>
              </div>

              <div>
                <p className="text-sm text-white/70 uppercase tracking-widest font-bold">
                  {material?.materialType || "Material"}
                </p>
                <h1 className="text-4xl md:text-6xl font-bold text-white leading-tight">
                  {material?.title || "Untitled Material"}
                </h1>
              </div>
            </div>

            <p className="text-lg md:text-xl text-white/80 leading-relaxed max-w-3xl mb-10">
              {material?.description ||
                "No description was provided for this material."}
            </p>
          </div>
        </div>
      </section>

      <main className="container py-12 lg:py-20">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
          <div className="lg:col-span-8 space-y-12">
            <section data-aos="fade-up">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-1 h-8 bg-secondaryColor rounded-full"></div>
                <h2 className="text-3xl font-bold text-blackColor dark:text-white">
                  About this material
                </h2>
              </div>

              <div className="text-paragraphColor dark:text-gray-400 text-lg leading-relaxed space-y-6">
                <p>
                  {material?.description ||
                    "No detailed description is available for this material yet."}
                </p>

                <div className="bg-lightGrey11 dark:bg-gray-800 p-8 rounded-2xl border border-gray-100 dark:border-gray-700">
                  <h4 className="text-xl font-bold text-blackColor dark:text-white mb-4">
                    Learning Objectives
                  </h4>

                  {material.learningObjectives?.length ? (
                    <ul className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {material.learningObjectives.map((item, i) => (
                        <li
                          key={`${item}-${i}`}
                          className="flex items-start gap-2"
                        >
                          <i className="icofont-check-circled text-secondaryColor mt-1"></i>
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-paragraphColor dark:text-gray-400">
                      No learning objectives were added for this material.
                    </p>
                  )}
                </div>
              </div>
            </section>

            <section
              className="grid grid-cols-2 md:grid-cols-3 gap-8 p-8 border border-gray-100 dark:border-gray-800 rounded-2xl bg-white dark:bg-gray-900"
              data-aos="fade-up"
            >
              {[
                { label: "Department", value: material?.departmentName || "—" },
                { label: "Semester", value: material?.semesterName || "—" },
                { label: "Course", value: material?.courseTitle || "—" },
                { label: "Course Code", value: material?.courseCode || "—" },
                { label: "Chapter", value: material?.chapterTitle || "—" },
                {
                  label: "Academic Year",
                  value: material?.academicYearName || "—",
                },
                {
                  label: "File Type",
                  value: fileType,
                },
                {
                  label: "Size",
                  value: fileSize,
                },
                {
                  label: "Length",
                  value: getPagesOrSlidesLabel(material, rawMaterial),
                },
                { label: "Created", value: formatDate(material?.createdAt) },
                { label: "Updated", value: formatDate(material?.updatedAt) },
                {
                  label: "Downloads",
                  value: String(material?.stats?.downloadCount || 0),
                },
              ].map((info) => (
                <div key={info.label}>
                  <p className="text-xs font-bold text-secondaryColor uppercase tracking-widest mb-1">
                    {info.label}
                  </p>
                  <p className="font-bold text-blackColor dark:text-white break-words">
                    {info.value}
                  </p>
                </div>
              ))}
            </section>

            <MaterialFeedbackPanel
              materialId={numericId}
              stats={rawMaterial?.stats || material?.stats}
            />
          </div>

          <div className="lg:col-span-4">
            <div className="sticky top-28 space-y-6">
              <div
                className="bg-blueDark p-8 rounded-2xl shadow-2xl relative overflow-hidden"
                data-aos="fade-left"
              >
                <h3 className="text-xl font-bold text-white mb-6 relative z-10">
                  Quick Actions
                </h3>

                <div className="space-y-4 relative z-10">
                  <MaterialAiAssistant materialId={numericId} rawMaterial={rawMaterial} />

                  <button
                    type="button"
                    onClick={handleOpenPreview}
                    disabled={!canPreviewFile}
                    className={`w-full py-4 font-bold rounded-lg transition-all duration-300 flex items-center justify-center gap-2 ${
                      canPreviewFile
                        ? "bg-secondaryColor hover:bg-white text-white hover:text-secondaryColor"
                        : "bg-secondaryColor/40 text-white/60 cursor-not-allowed"
                    }`}
                  >
                    <i className="icofont-eye-alt"></i>
                    {canPreviewFile ? "Open Preview" : "Preview Unavailable"}
                  </button>

                  <button
                    type="button"
                    onClick={handleOpenDownload}
                    disabled={!canDownloadFile}
                    className={`w-full py-4 border font-bold rounded-lg transition-all duration-300 text-center block ${
                      canDownloadFile
                        ? "bg-white/10 hover:bg-white/20 text-white border-white/20"
                        : "bg-white/5 text-white/50 border-white/10 cursor-not-allowed"
                    }`}
                  >
                    Download File
                  </button>

                  <button
                    type="button"
                    onClick={handleNativeShare}
                    className="w-full py-4 font-bold rounded-lg transition-all duration-300 flex items-center justify-center gap-2 bg-white/5 text-white/80 border border-white/10 hover:bg-white/10"
                  >
                    <i className="icofont-share"></i>
                    Share Material
                  </button>

                  <button
                    type="button"
                    onClick={handleCopyLink}
                    className="w-full py-4 font-bold rounded-lg transition-all duration-300 flex items-center justify-center gap-2 bg-white/5 text-white/80 border border-white/10 hover:bg-white/10"
                  >
                    <i className="icofont-copy"></i>
                    Copy Link
                  </button>

                  <button
                    type="button"
                    onClick={handleShareWhatsApp}
                    className="w-full py-4 font-bold rounded-lg transition-all duration-300 flex items-center justify-center gap-2 bg-[#25D366]/20 text-[#25D366] border border-[#25D366]/30 hover:bg-[#25D366] hover:text-white"
                  >
                    <i className="icofont-brand-whatsapp"></i>
                    Share on WhatsApp
                  </button>

                  <button
                    type="button"
                    onClick={() =>
                      toggleFavorite({
                        id: numericId,
                        is_favorite: !isFavorite,
                      })
                    }
                    className={`w-full py-4 font-bold rounded-lg transition-all duration-300 flex items-center justify-center gap-2 ${
                      isFavorite
                        ? "bg-red-500/20 text-red-500 border border-red-500/30 hover:bg-red-500 hover:text-white"
                        : "bg-white/5 text-white/80 border border-white/10 hover:bg-white/10"
                    }`}
                  >
                    <i
                      className={
                        isFavorite ? "icofont-heart" : "icofont-heart-alt"
                      }
                    ></i>
                    {isFavorite ? "Saved to Favorites" : "Save to Favorites"}
                  </button>
                </div>

                <div className="absolute -bottom-10 -right-10 w-32 h-32 bg-secondaryColor/20 rounded-full blur-3xl"></div>
              </div>

              <div
                className="bg-lightGrey11 dark:bg-gray-800 p-8 rounded-2xl border border-secondaryColor/20"
                data-aos="fade-left"
                data-aos-delay="100"
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-12 h-12 bg-secondaryColor rounded-xl flex items-center justify-center text-white text-2xl">
                    <i className={fileIconClass}></i>
                  </div>

                  <div>
                    <h4 className="font-bold text-blackColor dark:text-white">
                      File Summary
                    </h4>
                    <p className="text-xs text-secondaryColor font-bold uppercase">
                      {material?.materialType || "Material"}
                    </p>
                  </div>
                </div>

                <div className="space-y-3 text-sm">
                  {[
                    ["Type", fileType],
                    ["Size", fileSize],
                    ["Length", getPagesOrSlidesLabel(material, rawMaterial)],
                    ["Views", material?.stats?.viewCount || 0],
                    ["Downloads", material?.stats?.downloadCount || 0],
                  ].map(([label, value]) => (
                    <div
                      key={label}
                      className="flex items-center justify-between gap-3"
                    >
                      <span className="text-paragraphColor dark:text-gray-400">
                        {label}
                      </span>
                      <span className="font-bold text-blackColor dark:text-white uppercase">
                        {value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="px-4 text-center">
                <Link
                  href="/materials"
                  className="inline-flex items-center gap-2 text-sm font-bold text-primaryColor hover:underline"
                >
                  <i className="icofont-long-arrow-left"></i>
                  Back to all materials
                </Link>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default MaterialDetailsPrimary;
