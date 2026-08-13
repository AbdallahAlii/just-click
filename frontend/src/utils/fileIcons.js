// // utils/fileIcons.js
// export const getFileIcon = (fileType) => {
//   const icons = {
//     pdf: "icofont-file-pdf",
//     doc: "icofont-file-document",
//     docx: "icofont-file-document",
//     ppt: "icofont-file-powerpoint",
//     pptx: "icofont-file-powerpoint",
//     xls: "icofont-file-excel",
//     xlsx: "icofont-file-excel",
//     jpg: "icofont-file-image",
//     jpeg: "icofont-file-image",
//     png: "icofont-file-image",
//     gif: "icofont-file-image",
//     mp4: "icofont-file-video",
//     mov: "icofont-file-video",
//     avi: "icofont-file-video",
//     zip: "icofont-file-zip",
//     rar: "icofont-file-zip",
//     txt: "icofont-file-text",
//     default: "icofont-file-alt",
//   };
//   return icons[fileType?.toLowerCase()] || icons.default;
// };

// // Category background colors (matching original design) - NOW EXPORTED
// export const getCategoryBg = (category) => {
//   const categoryBgs = [
//     { category: "Programming", bg: "bg-secondaryColor" },
//     { category: "Algorithms", bg: "bg-blue" },
//     { category: "Data Structures", bg: "bg-secondaryColor2" },
//     { category: "Database", bg: "bg-greencolor2" },
//     { category: "Operating Systems", bg: "bg-orange" },
//     { category: "Web Development", bg: "bg-yellow" },
//     { category: "Networking", bg: "bg-secondaryColor" },
//     { category: "Security", bg: "bg-blue" },
//     { category: "AI", bg: "bg-secondaryColor2" },
//     { category: "Machine Learning", bg: "bg-greencolor2" },
//   ];
  
//   const found = categoryBgs.find(item => item.category === category);
//   return found ? found.bg : "bg-primaryColor";
// };
// utils/fileIcons.js
export const getFileIcon = (fileType) => {
  const icons = {
    pdf: "icofont-file-pdf",
    doc: "icofont-file-document",
    docx: "icofont-file-document",
    ppt: "icofont-file-powerpoint",
    pptx: "icofont-file-powerpoint",
    xls: "icofont-file-excel",
    xlsx: "icofont-file-excel",
    jpg: "icofont-file-image",
    jpeg: "icofont-file-image",
    png: "icofont-file-image",
    gif: "icofont-file-image",
    mp4: "icofont-file-video",
    mov: "icofont-file-video",
    avi: "icofont-file-video",
    zip: "icofont-file-zip",
    rar: "icofont-file-zip",
    txt: "icofont-file-text",
    default: "icofont-file-alt",
  };
  return icons[fileType?.toLowerCase()] || icons.default;
};

// Neutral semester badge (calm ds tokens — no neon accents)
export const getSemesterBg = () =>
  "bg-ds-surface-secondary text-ds-text-secondary";