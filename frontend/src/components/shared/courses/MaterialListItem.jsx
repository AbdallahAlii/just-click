"use client";

import {
  useToggleMaterialFavorite,
  useTrackMaterialDownload,
  useTrackMaterialView,
} from "@/features/materials/hooks";
import {
  buildFileMetaLine,
  downloadBlobFromUrl,
  getCanPreviewInBrowser,
  getDownloadUrl,
  getFileExtension,
  getFileTypeMeta,
  getReadUrl,
  getSafeFileName,
} from "@/utils/materialHelpers";
import { Download, Eye, Heart, Share2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

const iconBtnClass =
  "inline-flex h-8 w-8 items-center justify-center rounded-md text-ds-text-muted transition-colors hover:bg-ds-surface-hover hover:text-ds-text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-action";

const MaterialListItem = ({ material, onToggleFavorite, onShareMaterial }) => {
  const { mutate: toggleFavorite } = useToggleMaterialFavorite();
  const { mutate: trackView } = useTrackMaterialView();
  const { mutate: trackDownload } = useTrackMaterialDownload();
  const [isDownloading, setIsDownloading] = useState(false);

  const id = material?.id;
  const title = material?.title || "Untitled Material";
  const chapterTitle = material?.chapterTitle || "";
  const courseTitle = material?.courseTitle || "";
  const semesterNumber = material?.semesterNumber;
  const semesterName = material?.semesterName;

  const fileExtension = getFileExtension(material);
  const { Icon } = getFileTypeMeta(fileExtension);
  const metaLine = buildFileMetaLine(material);
  const downloadUrl = getDownloadUrl(material);
  const readUrl = getReadUrl(material);
  const canPreviewInBrowser = getCanPreviewInBrowser(material);

  const downloadCount = material?.stats?.downloadCount || 0;
  const viewCount = material?.stats?.viewCount || 0;
  const isFavorite = !!material?.isFavorite;

  const courseChapter = [courseTitle, chapterTitle].filter(Boolean).join(" · ");
  const semesterLabel = semesterNumber
    ? `Semester ${semesterNumber}`
    : semesterName || "";

  const detailHref = id ? `/materials/${id}` : "#";
  const previewHref =
    canPreviewInBrowser && readUrl ? readUrl : detailHref;

  const handleDetailClick = () => {
    if (!id) return;
    trackView({ id, cooldown_seconds: 3600 });
  };

  const handleFavoriteClick = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!id) return;

    if (typeof onToggleFavorite === "function") {
      await onToggleFavorite(material);
      return;
    }

    toggleFavorite({ id, is_favorite: !isFavorite });
  };

  const handleShareClick = (e) => {
    e.preventDefault();
    e.stopPropagation();

    if (typeof onShareMaterial === "function") {
      onShareMaterial(material);
      return;
    }

    const shareUrl =
      typeof window !== "undefined"
        ? `${window.location.origin}/materials/${id}`
        : "";
    if (!shareUrl) return;

    const shareText = `New material uploaded: ${title}\n\nView here:\n${shareUrl}`;

    if (navigator.share) {
      navigator
        .share({ title, text: "Check this material", url: shareUrl })
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
  };

  const handleDownloadClick = async (e) => {
    e.preventDefault();
    e.stopPropagation();

    if (!id || !downloadUrl) {
      alert("No download file is available.");
      return;
    }

    setIsDownloading(true);
    try {
      await downloadBlobFromUrl({
        url: downloadUrl,
        filename: getSafeFileName(material),
      });
      trackDownload(id);
    } catch (error) {
      console.error("Download failed:", error);
      alert(error?.message || "Download failed. Please check your connection.");
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="group flex flex-col gap-2 px-3 py-2.5 transition-colors hover:bg-ds-surface-hover sm:flex-row sm:items-center sm:gap-3 sm:px-4">
      <div className="flex min-w-0 flex-1 items-start gap-2.5 sm:items-center">
        <Link
          href={detailHref}
          onClick={handleDetailClick}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-ds-surface-secondary text-ds-action transition-colors hover:bg-ds-action/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-action"
          aria-label={`Open ${title}`}
        >
          <Icon className="h-4 w-4" aria-hidden="true" />
        </Link>

        <div className="min-w-0 flex-1">
          <Link
            href={detailHref}
            onClick={handleDetailClick}
            className="block text-sm font-semibold text-ds-text-primary transition-colors hover:text-ds-action focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-action rounded-sm line-clamp-1"
          >
            {title}
          </Link>

          <p className="mt-0.5 text-xs text-ds-text-muted line-clamp-1">
            {[courseChapter, metaLine, semesterLabel].filter(Boolean).join(" · ")}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 sm:flex-nowrap sm:justify-end sm:gap-3">
        <div className="flex items-center gap-2.5 text-xs text-ds-text-muted">
          <span
            className={`inline-flex items-center gap-1 ${
              viewCount === 0 ? "opacity-50" : ""
            }`}
            title={`${viewCount} views`}
          >
            <Eye className="h-3.5 w-3.5" aria-hidden="true" />
            <span>{viewCount}</span>
          </span>
          <span
            className={`inline-flex items-center gap-1 ${
              downloadCount === 0 ? "opacity-50" : ""
            }`}
            title={`${downloadCount} downloads`}
          >
            <Download className="h-3.5 w-3.5" aria-hidden="true" />
            <span>{downloadCount}</span>
          </span>
        </div>

        <div className="flex items-center gap-0.5">
          <button
            type="button"
            onClick={handleFavoriteClick}
            className={iconBtnClass}
            aria-label={isFavorite ? "Remove from favorites" : "Add to favorites"}
          >
            <Heart
              className={`h-4 w-4 ${
                isFavorite ? "fill-current text-ds-error" : ""
              }`}
              aria-hidden="true"
            />
          </button>

          <button
            type="button"
            onClick={handleShareClick}
            className={iconBtnClass}
            aria-label="Share material"
          >
            <Share2 className="h-4 w-4" aria-hidden="true" />
          </button>

          <a
            href={previewHref}
            target={canPreviewInBrowser ? "_blank" : undefined}
            rel={canPreviewInBrowser ? "noopener noreferrer" : undefined}
            onClick={handleDetailClick}
            className={iconBtnClass}
            aria-label="Preview material"
          >
            <Eye className="h-4 w-4" aria-hidden="true" />
          </a>

          <button
            type="button"
            onClick={handleDownloadClick}
            disabled={isDownloading}
            className="ml-1 inline-flex h-8 items-center gap-1 rounded-md bg-ds-action px-2.5 text-xs font-semibold text-white transition-colors hover:bg-ds-action-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-action disabled:opacity-60"
            aria-label="Download material"
          >
            <Download className="h-3.5 w-3.5" aria-hidden="true" />
            {isDownloading ? "…" : "Download"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default MaterialListItem;
