import {
  File,
  FileSpreadsheet,
  FileText,
  Link2,
  Presentation,
  Video,
} from "lucide-react";

export const MATERIALS_RETURN_KEY = "jc-materials-return";
export const MATERIALS_VIEW_KEY = "jc-materials-view";

export function formatFileSize(sizeMb) {
  if (sizeMb === null || sizeMb === undefined || Number.isNaN(Number(sizeMb))) {
    return null;
  }
  const num = Number(sizeMb);
  return `${num % 1 === 0 ? num.toFixed(0) : num.toFixed(1)} MB`;
}

export function normalizeMaterialUrl(url) {
  if (!url) return "";
  return String(url).replace("http://127.0.0.1:7000", "http://localhost:7000");
}

export function getMaterialFile(material) {
  return material?.file || material?.rawItem?.file || {};
}

export function getFileExtension(material) {
  const file = getMaterialFile(material);
  return String(file.extension || material?.materialType || "file").toLowerCase();
}

export function getDownloadUrl(material) {
  const file = getMaterialFile(material);
  return normalizeMaterialUrl(file.downloadUrl || file.download_url || "");
}

export function getReadUrl(material) {
  const file = getMaterialFile(material);
  return normalizeMaterialUrl(file.readUrl || file.read_url || "");
}

export function getCanPreviewInBrowser(material) {
  const file = getMaterialFile(material);
  return Boolean(
    file.canPreviewInBrowser ??
      file.can_preview_in_browser ??
      material?.rawItem?.file?.can_preview_in_browser ??
      false,
  );
}

export function getPagesOrSlidesLabel(material) {
  const file = getMaterialFile(material);
  const slideCount = file.slideCount ?? file.slide_count;
  const pageCount = file.pageCount ?? file.page_count;
  if (slideCount != null) return `${slideCount} slides`;
  if (pageCount != null) return `${pageCount} pages`;
  return null;
}

export function getSafeFileName(material) {
  const title = material?.title || "material";
  const ext = getFileExtension(material);
  const safeTitle = String(title)
    .replace(/[<>:"/\\|?*\x00-\x1F]/g, "_")
    .trim();
  return `${safeTitle || "material"}.${String(ext).replace(/^\./, "")}`;
}

export function getFileTypeMeta(extensionOrType) {
  const value = String(extensionOrType || "").toLowerCase();

  if (value === "pdf") {
    return { label: "PDF", Icon: FileText };
  }
  if (["ppt", "pptx", "slides"].includes(value)) {
    return { label: value === "slides" ? "Slides" : value.toUpperCase(), Icon: Presentation };
  }
  if (["doc", "docx", "document"].includes(value)) {
    return { label: value === "document" ? "Document" : value.toUpperCase(), Icon: FileSpreadsheet };
  }
  if (["mp4", "mov", "avi", "video"].includes(value)) {
    return { label: "Video", Icon: Video };
  }
  if (["link", "url"].includes(value)) {
    return { label: "Link", Icon: Link2 };
  }
  return { label: value ? value.toUpperCase() : "FILE", Icon: File };
}

export function buildFileMetaLine(material) {
  const ext = getFileExtension(material);
  const { label } = getFileTypeMeta(ext);
  const file = getMaterialFile(material);
  const size = formatFileSize(file.sizeMb ?? file.size_mb);
  const length = getPagesOrSlidesLabel(material);
  return [label, size, length].filter(Boolean).join(" · ");
}

export function getAuthHeaders() {
  if (typeof window === "undefined") return {};
  const token =
    localStorage.getItem("token") ||
    localStorage.getItem("access_token") ||
    localStorage.getItem("authToken");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function getFilenameFromContentDisposition(headerValue) {
  if (!headerValue) return null;
  const utf8Match = headerValue.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1].replace(/["']/g, ""));
    } catch {
      return utf8Match[1].replace(/["']/g, "");
    }
  }
  const normalMatch = headerValue.match(/filename="?([^"]+)"?/i);
  return normalMatch?.[1] || null;
}

export async function downloadBlobFromUrl({ url, filename }) {
  const response = await fetch(url, {
    method: "GET",
    credentials: "include",
    headers: getAuthHeaders(),
  });

  if (response.status === 401) {
    throw new Error("Your login session expired. Please login again.");
  }
  if (!response.ok) {
    throw new Error("Download failed. Please try again.");
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    const text = await response.text().catch(() => "");
    throw new Error(text || "Download failed. Server returned JSON instead of a file.");
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
}

export function saveMaterialsReturnUrl(url) {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(MATERIALS_RETURN_KEY, url);
  } catch {}
}

export function getMaterialsReturnUrl(fallback = "/materials") {
  if (typeof window === "undefined") return fallback;
  try {
    return sessionStorage.getItem(MATERIALS_RETURN_KEY) || fallback;
  } catch {
    return fallback;
  }
}

export function getStoredMaterialsView() {
  if (typeof window === "undefined") return "list";
  try {
    const value = localStorage.getItem(MATERIALS_VIEW_KEY);
    return value === "grid" ? "grid" : "list";
  } catch {
    return "list";
  }
}

export function setStoredMaterialsView(view) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(MATERIALS_VIEW_KEY, view === "grid" ? "grid" : "list");
  } catch {}
}
