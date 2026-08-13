"use client";

import MaterialAiAssistant from "@/components/chatbot/MaterialAiAssistant";
import MaterialFeedbackPanel from "@/components/materials/MaterialFeedbackPanel";
import {
  useMaterialDetail,
  useToggleMaterialFavorite,
  useTrackMaterialDownload,
  useTrackMaterialView,
} from "@/features/materials/hooks";
import { mapMaterialToCardModel } from "@/features/materials/utils";
import {
  downloadBlobFromUrl,
  formatFileSize,
  getFileTypeMeta,
  getMaterialsReturnUrl,
  getPagesOrSlidesLabel,
  getSafeFileName,
  normalizeMaterialUrl,
} from "@/utils/materialHelpers";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

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

const secondaryBtnClass =
  "inline-flex items-center justify-center gap-1.5 rounded-lg border border-ds-border bg-ds-surface px-3 py-2 text-sm font-semibold text-ds-text-primary transition-colors hover:bg-ds-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action focus-visible:ring-offset-2 dark:focus-visible:ring-offset-ds-page disabled:cursor-not-allowed disabled:opacity-50 min-h-[40px]";

const primaryBtnClass =
  "inline-flex items-center justify-center gap-1.5 rounded-lg bg-ds-action px-3.5 py-2 text-sm font-semibold text-white transition-colors hover:bg-ds-action-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action focus-visible:ring-offset-2 dark:focus-visible:ring-offset-ds-page disabled:cursor-not-allowed disabled:opacity-50 min-h-[40px]";

const DetailSkeleton = () => (
  <div className="min-h-screen bg-ds-page">
    <div className="container py-8 lg:py-12 animate-pulse">
      <div className="mb-8 h-4 w-36 rounded bg-ds-surface-secondary" />

      <div className="mb-3 h-5 w-16 rounded-lg bg-ds-surface-secondary" />
      <div className="mb-3 h-9 w-3/4 max-w-2xl rounded-lg bg-ds-surface-secondary" />
      <div className="mb-2 h-5 w-48 rounded bg-ds-surface-secondary" />
      <div className="mb-6 h-4 w-40 rounded bg-ds-surface-secondary" />
      <div className="mb-8 h-4 w-72 rounded bg-ds-surface-secondary" />

      <div className="mb-10 flex flex-wrap gap-2">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="h-11 w-28 rounded-xl bg-ds-surface-secondary"
          />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
        <div className="space-y-6 lg:col-span-8">
          <div className="h-40 rounded-2xl border border-ds-border bg-ds-surface" />
          <div className="h-32 rounded-2xl border border-ds-border bg-ds-surface" />
          <div className="h-48 rounded-2xl border border-ds-border bg-ds-surface" />
        </div>
        <div className="space-y-4 lg:col-span-4">
          <div className="h-48 rounded-2xl border border-ds-border bg-ds-surface" />
          <div className="h-40 rounded-2xl border border-ds-border bg-ds-surface" />
        </div>
      </div>
    </div>
  </div>
);

const ErrorState = ({ title, message, showRetry = true, backHref = "/materials" }) => (
  <div className="min-h-screen bg-ds-page">
    <div className="container py-16 lg:py-24">
      <div className="mx-auto max-w-lg text-center">
        <h1 className="mb-3 text-2xl font-bold tracking-tight text-ds-text-primary">
          {title}
        </h1>
        <p className="mb-8 text-ds-text-secondary leading-relaxed">{message}</p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link href={backHref} className={primaryBtnClass}>
            Back to materials
          </Link>
          {showRetry ? (
            <button
              type="button"
              onClick={() => window.location.reload()}
              className={secondaryBtnClass}
            >
              Try again
            </button>
          ) : null}
        </div>
      </div>
    </div>
  </div>
);

const MaterialDetailsPrimary = ({ id }) => {
  const numericId = Number(id);
  const [backHref, setBackHref] = useState("/materials");

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
    setBackHref(getMaterialsReturnUrl("/materials"));
  }, []);

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
        backHref={backHref}
      />
    );
  }

  if (isLoading) {
    return <DetailSkeleton />;
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
        backHref={backHref}
      />
    );
  }

  if (!rawMaterial) {
    return (
      <ErrorState
        title="Material not found"
        message="No material data was returned from the server."
        showRetry={false}
        backHref={backHref}
      />
    );
  }

  const material = {
    ...mapMaterialToCardModel(rawMaterial),
    learningObjectives: rawMaterial?.learning_objectives || [],
  };

  const mappedFile = material?.file || {};
  const rawFile = rawMaterial?.file || {};

  const readHref = normalizeMaterialUrl(
    mappedFile.readUrl || rawFile.read_url || "",
  );
  const downloadHref = normalizeMaterialUrl(
    mappedFile.downloadUrl || rawFile.download_url || "",
  );

  const canPreviewInBrowser =
    mappedFile.canPreviewInBrowser ?? rawFile.can_preview_in_browser ?? false;

  const isDownloadable =
    material?.flags?.isDownloadable ??
    rawMaterial?.flags?.is_downloadable ??
    false;

  const canPreviewFile = Boolean(readHref) && Boolean(canPreviewInBrowser);
  const canDownloadFile = Boolean(downloadHref) && Boolean(isDownloadable);

  const isFavorite =
    material?.isFavorite ?? rawMaterial?.user_state?.is_favorite ?? false;

  const fileExt =
    mappedFile.extension || rawFile.extension || material?.materialType;
  const { label: fileTypeLabel, Icon: FileTypeIcon } = getFileTypeMeta(fileExt);

  const pagesOrSlides =
    getPagesOrSlidesLabel({
      ...material,
      file: { ...rawFile, ...mappedFile },
    }) || null;

  const fileSize =
    formatFileSize(mappedFile.sizeMb ?? rawFile.size_mb) || null;

  const viewCount = material?.stats?.viewCount ?? 0;
  const downloadCount = material?.stats?.downloadCount ?? 0;

  const metaParts = [
    fileSize,
    pagesOrSlides,
    `${viewCount} views`,
    `${downloadCount} downloads`,
  ].filter(Boolean);

  const semesterChapter = [material?.semesterName, material?.chapterTitle]
    .filter(Boolean)
    .join(" · ");

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
        filename: getSafeFileName({
          ...material,
          file: { ...rawFile, ...mappedFile },
        }),
      });
      trackDownload(numericId);
    } catch (err) {
      console.error("Download failed:", err);
      alert(err?.message || "Download failed. Please check your connection.");
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

  const infoFields = [
    { label: "Department", value: material?.departmentName || "—" },
    { label: "Semester", value: material?.semesterName || "—" },
    { label: "Course", value: material?.courseTitle || "—" },
    { label: "Course Code", value: material?.courseCode || "—" },
    { label: "Chapter", value: material?.chapterTitle || "—" },
    { label: "Academic Year", value: material?.academicYearName || "—" },
    { label: "File Type", value: fileTypeLabel || "—" },
    { label: "Size", value: fileSize || "—" },
    { label: "Length", value: pagesOrSlides || "—" },
    { label: "Created", value: formatDate(material?.createdAt) },
    { label: "Updated", value: formatDate(material?.updatedAt) },
    { label: "Downloads", value: String(downloadCount) },
  ];

  return (
    <div className="min-h-screen bg-ds-page">
      <div className="container py-6 lg:py-8">
        <Link
          href={backHref}
          className="mb-5 inline-flex items-center gap-2 text-sm font-medium text-ds-text-secondary transition-colors hover:text-ds-action"
        >
          <i className="icofont-long-arrow-left" aria-hidden="true" />
          Back to materials
        </Link>

        <header className="mb-8">
          <span className="mb-2 inline-flex items-center gap-1.5 rounded-md border border-ds-border bg-ds-surface-secondary px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-ds-text-secondary">
            <FileTypeIcon className="h-3.5 w-3.5" aria-hidden="true" />
            {fileTypeLabel}
          </span>

          <h1 className="text-2xl font-bold tracking-tight text-ds-text-primary sm:text-3xl lg:text-[2.15rem] lg:leading-tight">
            {material?.title || "Untitled Material"}
          </h1>

          {material?.courseTitle ? (
            <p className="mt-1.5 text-base text-ds-text-secondary">
              {material.courseTitle}
              {material?.courseCode ? (
                <span className="text-ds-text-muted">
                  {" "}
                  ({material.courseCode})
                </span>
              ) : null}
            </p>
          ) : null}

          {semesterChapter ? (
            <p className="mt-1 text-sm text-ds-text-muted">{semesterChapter}</p>
          ) : null}

          {metaParts.length ? (
            <p className="mt-3 text-sm text-ds-text-muted">
              {metaParts.join(" · ")}
            </p>
          ) : null}

          <div className="mt-5 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={handleOpenDownload}
              disabled={!canDownloadFile}
              className={primaryBtnClass}
            >
              <i className="icofont-download" aria-hidden="true" />
              Download
            </button>

            <button
              type="button"
              onClick={handleOpenPreview}
              disabled={!canPreviewFile}
              className={secondaryBtnClass}
            >
              <i className="icofont-eye-alt" aria-hidden="true" />
              Preview
            </button>

            <button
              type="button"
              onClick={() =>
                toggleFavorite({
                  id: numericId,
                  is_favorite: !isFavorite,
                })
              }
              className={secondaryBtnClass}
              aria-pressed={isFavorite}
            >
              <i
                className={isFavorite ? "icofont-heart" : "icofont-heart-alt"}
                aria-hidden="true"
              />
              {isFavorite ? "Favorited" : "Favorite"}
            </button>

            <button
              type="button"
              onClick={handleCopyLink}
              className={secondaryBtnClass}
            >
              <i className="icofont-copy" aria-hidden="true" />
              Copy link
            </button>

            <button
              type="button"
              onClick={handleShareWhatsApp}
              className={secondaryBtnClass}
            >
              <i className="icofont-brand-whatsapp" aria-hidden="true" />
              WhatsApp
            </button>

            <button
              type="button"
              onClick={handleNativeShare}
              className={secondaryBtnClass}
            >
              <i className="icofont-share" aria-hidden="true" />
              Share
            </button>
          </div>
        </header>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:gap-8">
          <div className="space-y-6 lg:col-span-9">
            <section>
              <h2 className="mb-3 text-lg font-semibold text-ds-text-primary">
                About
              </h2>
              <p className="text-ds-text-secondary leading-relaxed">
                {material?.description ||
                  "No description was provided for this material."}
              </p>
            </section>

            {material.learningObjectives?.length ? (
              <section>
                <h2 className="mb-3 text-lg font-semibold text-ds-text-primary">
                  Learning objectives
                </h2>
                <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {material.learningObjectives.map((item, i) => (
                    <li
                      key={`${item}-${i}`}
                      className="flex items-start gap-2 text-ds-text-secondary"
                    >
                      <i
                        className="icofont-check-circled mt-0.5 text-ds-action"
                        aria-hidden="true"
                      />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            <section className="rounded-xl border border-ds-border bg-ds-surface p-5 sm:p-6">
              <h2 className="mb-4 text-lg font-semibold text-ds-text-primary">
                Details
              </h2>
              <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
                {infoFields.map((info) => (
                  <div key={info.label}>
                    <p className="mb-0.5 text-[11px] font-medium uppercase tracking-wide text-ds-text-muted">
                      {info.label}
                    </p>
                    <p className="break-words text-sm font-medium text-ds-text-primary">
                      {info.value}
                    </p>
                  </div>
                ))}
              </div>
            </section>

            <MaterialFeedbackPanel
              materialId={numericId}
              stats={rawMaterial?.stats || material?.stats}
            />
          </div>

          <aside className="lg:col-span-3">
            <div className="sticky top-24 space-y-3">
              <div className="rounded-xl border border-ds-border bg-ds-surface p-4">
                <MaterialAiAssistant
                  materialId={numericId}
                  rawMaterial={rawMaterial}
                />
              </div>

              <div className="rounded-xl border border-ds-border bg-ds-surface p-4">
                <div className="mb-4 flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-ds-border bg-ds-surface-secondary text-ds-action">
                    <FileTypeIcon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-ds-text-primary">
                      File summary
                    </h3>
                    <p className="text-xs text-ds-text-muted">
                      {material?.materialType || "Material"}
                    </p>
                  </div>
                </div>

                <dl className="space-y-2.5 text-sm">
                  {[
                    ["Type", fileTypeLabel],
                    ["Size", fileSize || "—"],
                    ["Length", pagesOrSlides || "—"],
                    ["Views", viewCount],
                    ["Downloads", downloadCount],
                  ].map(([label, value]) => (
                    <div
                      key={label}
                      className="flex items-center justify-between gap-3"
                    >
                      <dt className="text-ds-text-muted">{label}</dt>
                      <dd className="font-medium text-ds-text-primary">
                        {value}
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
};

export default MaterialDetailsPrimary;
