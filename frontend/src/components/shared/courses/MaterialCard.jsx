// "use client";

// import {
//   useToggleMaterialFavorite,
//   useTrackMaterialDownload,
//   useTrackMaterialView,
// } from "@/features/materials/hooks";
// import { getFileIcon, getSemesterBg } from "@/utils/fileIcons";
// import Link from "next/link";

// const formatFileSize = (sizeMb) => {
//   if (sizeMb === null || sizeMb === undefined || Number.isNaN(Number(sizeMb))) {
//     return "—";
//   }

//   const num = Number(sizeMb);
//   return `${num % 1 === 0 ? num.toFixed(0) : num.toFixed(1)} MB`;
// };

// const getSafeFileName = (material) => {
//   const title = material?.title || "material";
//   const ext = material?.file?.extension || material?.materialType || "file";
//   const safeTitle = title.replace(/[<>:"/\\|?*\x00-\x1F]/g, "_").trim();

//   return `${safeTitle || "material"}.${String(ext).replace(/^\./, "")}`;
// };

// const normalizeUrl = (url) => {
//   if (!url) return "#";
//   return url.replace("http://127.0.0.1:7000", "http://localhost:7000");
// };

// const MaterialCard = ({ material, onToggleFavorite, onShareMaterial }) => {
//   const { mutate: toggleFavorite } = useToggleMaterialFavorite();
//   const { mutate: trackView } = useTrackMaterialView();
//   const { mutate: trackDownload } = useTrackMaterialDownload();

//   const id = material?.id;
//   const title = material?.title || "Untitled Material";
//   const chapterTitle = material?.chapterTitle || "No chapter info";
//   const semesterNumber = material?.semesterNumber;
//   const semesterName = material?.semesterName || "Semester";
//   const courseTitle = material?.courseTitle || "";
//   const materialType = material?.materialType || "file";

//   const fileExtension = material?.file?.extension || materialType;
//   const fileSize = formatFileSize(material?.file?.sizeMb);
//   const pageCount = material?.file?.pageCount;
//   const slideCount = material?.file?.slideCount;
//   const downloadUrl = material?.file?.downloadUrl || "#";
//   const readUrl = material?.file?.readUrl || "#";
//   const canPreviewInBrowser = material?.file?.canPreviewInBrowser ?? false;

//   const downloadCount = material?.stats?.downloadCount || 0;

//   const fileIconClass = getFileIcon(fileExtension);
//   const semesterBg = getSemesterBg(semesterNumber || 1);

//   const infoLabel =
//     slideCount != null
//       ? `${slideCount} slides`
//       : pageCount != null
//         ? `${pageCount} pages`
//         : materialType;

//   const handleViewClick = () => {
//     if (!id) return;
//     trackView({ id, cooldown_seconds: 3600 });
//   };

//   const handleDownloadClick = async (e) => {
//     e.preventDefault();
//     e.stopPropagation();

//     const finalDownloadUrl = normalizeUrl(downloadUrl);

//     if (!id || !finalDownloadUrl || finalDownloadUrl === "#") return;

//     try {
//       const token =
//         localStorage.getItem("token") ||
//         localStorage.getItem("access_token") ||
//         localStorage.getItem("authToken");

//       const response = await fetch(finalDownloadUrl, {
//         method: "GET",
//         credentials: "include",
//         headers: token ? { Authorization: `Bearer ${token}` } : {},
//       });

//       if (response.status === 401) {
//         alert("Your login session expired. Please login again.");
//         return;
//       }

//       if (!response.ok) {
//         alert("Download failed. Please try again.");
//         return;
//       }

//       const blob = await response.blob();
//       const blobUrl = window.URL.createObjectURL(blob);

//       const link = document.createElement("a");
//       link.href = blobUrl;
//       link.download = getSafeFileName(material);
//       document.body.appendChild(link);
//       link.click();
//       link.remove();

//       window.URL.revokeObjectURL(blobUrl);

//       trackDownload(id);
//     } catch (error) {
//       console.error("Download failed:", error);
//       alert("Download failed. Please check your connection.");
//     }
//   };

//   const handleFavoriteClick = async (e) => {
//     e.preventDefault();
//     e.stopPropagation();

//     if (!id) return;

//     if (typeof onToggleFavorite === "function") {
//       await onToggleFavorite(material);
//       return;
//     }

//     toggleFavorite({ id, is_favorite: !material?.isFavorite });
//   };

//   const handleShareClick = (e) => {
//     e.preventDefault();
//     e.stopPropagation();

//     if (typeof onShareMaterial === "function") {
//       onShareMaterial(material);
//       return;
//     }

//     const shareUrl =
//       typeof window !== "undefined"
//         ? `${window.location.origin}/materials/${id}`
//         : "";

//     if (!shareUrl) return;

//     const shareText = `New material uploaded: ${
//       material?.title || "Material"
//     }\n\nView here:\n${shareUrl}`;

//     if (navigator.share) {
//       navigator
//         .share({
//           title: material?.title || "Material",
//           text: "Check this material",
//           url: shareUrl,
//         })
//         .catch(() => {
//           const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(
//             shareText,
//           )}`;
//           window.open(whatsappUrl, "_blank", "noopener,noreferrer");
//         });
//       return;
//     }

//     const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(shareText)}`;
//     window.open(whatsappUrl, "_blank", "noopener,noreferrer");
//   };

//   return (
//     <div className="group bg-transparent border border-borderColor dark:border-borderColor-dark rounded-xl overflow-hidden hover:border-primaryColor dark:hover:border-primaryColor transition-all duration-300 flex flex-col h-full">
//       <div className="relative aspect-video bg-lightGrey7/30 dark:bg-whiteColor-dark/5 flex items-center justify-center overflow-hidden">
//         <i
//           className={`${fileIconClass} text-6xl text-primaryColor/80 group-hover:scale-110 transition-transform duration-500`}
//         ></i>

//         <div className="absolute top-3 left-3 flex gap-2 flex-wrap">
//           {semesterNumber ? (
//             <span
//               className={`text-[10px] uppercase font-bold px-2 py-1 rounded-md text-whiteColor ${semesterBg}`}
//             >
//               Sem {semesterNumber}
//             </span>
//           ) : semesterName ? (
//             <span
//               className={`text-[10px] uppercase font-bold px-2 py-1 rounded-md text-whiteColor ${semesterBg}`}
//             >
//               {semesterName}
//             </span>
//           ) : null}
//         </div>

//         <div className="absolute top-3 right-3 flex items-center gap-2">
//           <button
//             type="button"
//             onClick={handleShareClick}
//             className="w-8 h-8 rounded-full bg-white dark:bg-darkdeep3-dark shadow-sm flex items-center justify-center text-contentColor hover:text-primaryColor transition-colors"
//             aria-label="Share material"
//             title="Share material"
//           >
//             <i className="icofont-share"></i>
//           </button>

//           <button
//             type="button"
//             onClick={handleFavoriteClick}
//             className="w-8 h-8 rounded-full bg-white dark:bg-darkdeep3-dark shadow-sm flex items-center justify-center text-contentColor hover:text-red-500 transition-colors"
//             aria-label={
//               material?.isFavorite
//                 ? "Remove from favorites"
//                 : "Add to favorites"
//             }
//           >
//             <i
//               className={
//                 material?.isFavorite
//                   ? "icofont-heart text-red-500"
//                   : "icofont-heart-alt"
//               }
//             ></i>
//           </button>
//         </div>
//       </div>

//       <div className="p-5 flex flex-col flex-grow">
//         <div className="flex items-center gap-2 mb-2 flex-wrap">
//           <span className="text-[10px] font-bold text-primaryColor uppercase tracking-wider">
//             {fileExtension}
//           </span>
//           <span className="text-[10px] text-contentColor">•</span>
//           <span className="text-[10px] text-contentColor uppercase tracking-wider">
//             {fileSize}
//           </span>
//           {infoLabel ? (
//             <>
//               <span className="text-[10px] text-contentColor">•</span>
//               <span className="text-[10px] text-contentColor uppercase tracking-wider">
//                 {infoLabel}
//               </span>
//             </>
//           ) : null}
//         </div>

//         <Link href={`/materials/${id}`} className="block">
//           <h5 className="text-base font-bold text-blackColor dark:text-whiteColor leading-snug mb-2 group-hover:text-primaryColor transition-colors line-clamp-2 min-h-[2.8rem]">
//             {title}
//           </h5>
//         </Link>

//         <p className="text-xs text-contentColor dark:text-contentColor-dark mb-1 line-clamp-1 italic">
//           {chapterTitle}
//         </p>

//         {courseTitle ? (
//           <p className="text-[11px] text-contentColor/80 dark:text-contentColor-dark/80 mb-4 line-clamp-1">
//             {courseTitle}
//           </p>
//         ) : (
//           <div className="mb-4" />
//         )}

//         <div className="mt-auto pt-4 border-t border-borderColor/50 dark:border-borderColor-dark/50 flex items-center justify-between gap-3">
//           <div className="flex items-center gap-1 text-contentColor">
//             <i className="icofont-download text-sm"></i>
//             <span className="text-xs font-semibold">{downloadCount}</span>
//           </div>

//           <div className="flex gap-2">
//             <a
//               href={
//                 canPreviewInBrowser
//                   ? normalizeUrl(readUrl)
//                   : `/materials/${id}/view`
//               }
//               target={canPreviewInBrowser ? "_blank" : undefined}
//               rel={canPreviewInBrowser ? "noopener noreferrer" : undefined}
//               onClick={handleViewClick}
//               className="p-2 rounded-lg border border-borderColor dark:border-borderColor-dark text-contentColor hover:bg-primaryColor hover:text-whiteColor hover:border-primaryColor transition-all"
//               aria-label="View material"
//             >
//               <i className="icofont-eye-alt"></i>
//             </a>

//             <button
//               type="button"
//               onClick={handleDownloadClick}
//               className="px-4 py-2 rounded-lg bg-blackColor dark:bg-primaryColor text-whiteColor text-xs font-bold hover:opacity-90 transition-all"
//             >
//               Download
//             </button>
//           </div>
//         </div>
//       </div>
//     </div>
//   );
// };

// export default MaterialCard;
"use client";

import {
  useToggleMaterialFavorite,
  useTrackMaterialDownload,
  useTrackMaterialView,
} from "@/features/materials/hooks";
import { getFileIcon, getSemesterBg } from "@/utils/fileIcons";
import Link from "next/link";

const formatFileSize = (sizeMb) => {
  if (sizeMb === null || sizeMb === undefined || Number.isNaN(Number(sizeMb))) {
    return "—";
  }

  const num = Number(sizeMb);
  return `${num % 1 === 0 ? num.toFixed(0) : num.toFixed(1)} MB`;
};

const normalizeUrl = (url) => {
  if (!url) return "#";
  return String(url).replace("http://127.0.0.1:7000", "http://localhost:7000");
};

const getMaterialFile = (material) => {
  return material?.file || material?.rawItem?.file || {};
};

const getDownloadUrl = (material) => {
  const file = getMaterialFile(material);
  return normalizeUrl(file.downloadUrl || file.download_url || "");
};

const getReadUrl = (material) => {
  const file = getMaterialFile(material);
  return normalizeUrl(file.readUrl || file.read_url || "");
};

const getFileExtension = (material) => {
  const file = getMaterialFile(material);
  return file.extension || material?.materialType || "file";
};

const getCanPreviewInBrowser = (material) => {
  const file = getMaterialFile(material);

  return Boolean(
    file.canPreviewInBrowser ??
    file.can_preview_in_browser ??
    material?.rawItem?.file?.can_preview_in_browser ??
    false,
  );
};

const getSafeFileName = (material) => {
  const title = material?.title || "material";
  const ext = getFileExtension(material);
  const safeTitle = title.replace(/[<>:"/\\|?*\x00-\x1F]/g, "_").trim();

  return `${safeTitle || "material"}.${String(ext).replace(/^\./, "")}`;
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

  if (!response.ok) {
    throw new Error("Download failed. Please try again.");
  }

  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    const text = await response.text().catch(() => "");
    throw new Error(
      text || "Download failed. Server returned JSON instead of a file.",
    );
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

const MaterialCard = ({ material, onToggleFavorite, onShareMaterial }) => {
  const { mutate: toggleFavorite } = useToggleMaterialFavorite();
  const { mutate: trackView } = useTrackMaterialView();
  const { mutate: trackDownload } = useTrackMaterialDownload();

  const id = material?.id;
  const title = material?.title || "Untitled Material";
  const chapterTitle = material?.chapterTitle || "No chapter info";
  const semesterNumber = material?.semesterNumber;
  const semesterName = material?.semesterName || "Semester";
  const courseTitle = material?.courseTitle || "";
  const materialType = material?.materialType || "file";

  const file = getMaterialFile(material);
  const fileExtension = getFileExtension(material);
  const fileSize = formatFileSize(file.sizeMb ?? file.size_mb);
  const pageCount = file.pageCount ?? file.page_count;
  const slideCount = file.slideCount ?? file.slide_count;
  const downloadUrl = getDownloadUrl(material);
  const readUrl = getReadUrl(material);
  const canPreviewInBrowser = getCanPreviewInBrowser(material);

  const downloadCount = material?.stats?.downloadCount || 0;
  const viewCount = material?.stats?.viewCount || 0;

  const fileIconClass = getFileIcon(fileExtension);
  const semesterBg = getSemesterBg(semesterNumber || 1);

  const infoLabel =
    slideCount != null
      ? `${slideCount} slides`
      : pageCount != null
        ? `${pageCount} pages`
        : materialType;

  const handleViewClick = () => {
    if (!id) return;
    trackView({ id, cooldown_seconds: 3600 });
  };

  const handleDownloadClick = async (e) => {
    e.preventDefault();
    e.stopPropagation();

    if (!id || !downloadUrl || downloadUrl === "#") {
      alert("No download file is available.");
      return;
    }

    try {
      await downloadBlobFromUrl({
        url: downloadUrl,
        filename: getSafeFileName(material),
      });

      trackDownload(id);
    } catch (error) {
      console.error("Download failed:", error);
      alert(error?.message || "Download failed. Please check your connection.");
    }
  };

  const handleFavoriteClick = async (e) => {
    e.preventDefault();
    e.stopPropagation();

    if (!id) return;

    if (typeof onToggleFavorite === "function") {
      await onToggleFavorite(material);
      return;
    }

    toggleFavorite({ id, is_favorite: !material?.isFavorite });
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
  };

  const viewHref =
    canPreviewInBrowser && readUrl && readUrl !== "#"
      ? readUrl
      : `/materials/${id}`;

  return (
    <div className="group bg-transparent border border-borderColor dark:border-borderColor-dark rounded-xl overflow-hidden hover:border-primaryColor dark:hover:border-primaryColor transition-all duration-300 flex flex-col h-full">
      <div className="relative aspect-video bg-lightGrey7/30 dark:bg-whiteColor-dark/5 flex items-center justify-center overflow-hidden">
        <i
          className={`${fileIconClass} text-6xl text-primaryColor/80 group-hover:scale-110 transition-transform duration-500`}
        ></i>

        <div className="absolute top-3 left-3 flex gap-2 flex-wrap">
          {semesterNumber ? (
            <span
              className={`text-[10px] uppercase font-bold px-2 py-1 rounded-md text-whiteColor ${semesterBg}`}
            >
              Sem {semesterNumber}
            </span>
          ) : semesterName ? (
            <span
              className={`text-[10px] uppercase font-bold px-2 py-1 rounded-md text-whiteColor ${semesterBg}`}
            >
              {semesterName}
            </span>
          ) : null}
        </div>

        <div className="absolute top-3 right-3 flex items-center gap-2">
          <button
            type="button"
            onClick={handleShareClick}
            className="w-8 h-8 rounded-full bg-white dark:bg-darkdeep3-dark shadow-sm flex items-center justify-center text-contentColor hover:text-primaryColor transition-colors"
            aria-label="Share material"
            title="Share material"
          >
            <i className="icofont-share"></i>
          </button>

          <button
            type="button"
            onClick={handleFavoriteClick}
            className="w-8 h-8 rounded-full bg-white dark:bg-darkdeep3-dark shadow-sm flex items-center justify-center text-contentColor hover:text-red-500 transition-colors"
            aria-label={
              material?.isFavorite
                ? "Remove from favorites"
                : "Add to favorites"
            }
          >
            <i
              className={
                material?.isFavorite
                  ? "icofont-heart text-red-500"
                  : "icofont-heart-alt"
              }
            ></i>
          </button>
        </div>
      </div>

      <div className="p-5 flex flex-col flex-grow">
        <div className="flex items-center gap-2 mb-2 flex-wrap">
          <span className="text-[10px] font-bold text-primaryColor uppercase tracking-wider">
            {fileExtension}
          </span>
          <span className="text-[10px] text-contentColor">•</span>
          <span className="text-[10px] text-contentColor uppercase tracking-wider">
            {fileSize}
          </span>
          {infoLabel ? (
            <>
              <span className="text-[10px] text-contentColor">•</span>
              <span className="text-[10px] text-contentColor uppercase tracking-wider">
                {infoLabel}
              </span>
            </>
          ) : null}
        </div>

        <Link href={`/materials/${id}`} className="block">
          <h5 className="text-base font-bold text-blackColor dark:text-whiteColor leading-snug mb-2 group-hover:text-primaryColor transition-colors line-clamp-2 min-h-[2.8rem]">
            {title}
          </h5>
        </Link>

        <p className="text-xs text-contentColor dark:text-contentColor-dark mb-1 line-clamp-1 italic">
          {chapterTitle}
        </p>

        {courseTitle ? (
          <p className="text-[11px] text-contentColor/80 dark:text-contentColor-dark/80 mb-4 line-clamp-1">
            {courseTitle}
          </p>
        ) : (
          <div className="mb-4" />
        )}

        <div className="mt-auto pt-4 border-t border-borderColor/50 dark:border-borderColor-dark/50 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 text-contentColor">
            <div className="flex items-center gap-1">
              <i className="icofont-eye-alt text-sm"></i>
              <span className="text-xs font-semibold">{viewCount}</span>
            </div>
            <div className="flex items-center gap-1">
              <i className="icofont-download text-sm"></i>
              <span className="text-xs font-semibold">{downloadCount}</span>
            </div>
          </div>

          <div className="flex gap-2">
            <a
              href={viewHref}
              target={canPreviewInBrowser ? "_blank" : undefined}
              rel={canPreviewInBrowser ? "noopener noreferrer" : undefined}
              onClick={handleViewClick}
              className="p-2 rounded-lg border border-borderColor dark:border-borderColor-dark text-contentColor hover:bg-primaryColor hover:text-whiteColor hover:border-primaryColor transition-all"
              aria-label="View material"
            >
              <i className="icofont-eye-alt"></i>
            </a>

            <button
              type="button"
              onClick={handleDownloadClick}
              className="px-4 py-2 rounded-lg bg-blackColor dark:bg-primaryColor text-whiteColor text-xs font-bold hover:opacity-90 transition-all"
            >
              Download
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MaterialCard;
