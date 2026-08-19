"use client";

import FrappeForm from "@/components/shared/forms/FrappeForm";
import Preloader from "@/components/shared/others/Preloader";
import {
  useCourseOfferingChaptersDropdown,
  useCourseOfferingsMaterialDropdown,
} from "@/features/academic/hooks";
import {
  useAdminMaterialDetail,
  useUpdateMaterial,
} from "@/features/materials/hooks";
import useNotify from "@/hooks/useNotify";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { z } from "zod";

const materialSchema = z.object({
  course_offering_id: z.number().min(1, "Please select a course offering"),
  chapter_id: z.number().optional().nullable(),
  title: z.string().min(1, "Title is required").max(200, "Title too long"),
  material_type: z.string().optional().nullable(),
  file_size_mb: z.number().optional().nullable(),
  page_count: z.number().optional().nullable(),
  slide_count: z.number().optional().nullable(),
  learning_objectives: z.array(z.string()).optional().default([]),
  description: z.string().optional(),
  is_downloadable: z.boolean().default(true),
  is_enabled: z.boolean().default(true),
});
function extractMaterialId(res) {
  return (
    res?.data?.material?.material_id ||
    res?.data?.material?.id ||
    res?.data?.material_id ||
    res?.material?.material_id ||
    res?.material?.id ||
    res?.material_id ||
    null
  );
}
function normalizeDropdownValue(value) {
  if (value == null) return "";
  if (typeof value === "string" || typeof value === "number")
    return String(value);

  if (typeof value === "object") {
    if (value.value != null) return String(value.value);
    if (value.id != null) return String(value.id);
  }

  return "";
}

function normalizeNullableNumber(value) {
  const normalized = normalizeDropdownValue(value);
  if (!normalized) return null;

  const n = Number(normalized);
  return Number.isFinite(n) && n > 0 ? n : null;
}

function normalizeOptionalNumber(value) {
  if (value === "" || value === null || value === undefined) return null;

  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? n : null;
}

function unwrapMaterial(res) {
  return res?.data?.data || res?.data?.material || res?.data || null;
}

function formatMaterialType(type) {
  const map = {
    other: "Other",
    pdf: "PDF",
    slides: "Slides",
    doc: "Document",
    video: "Video",
    link: "External Link",
  };

  return map[type] || type || "—";
}

function formatLength(material) {
  const type = material?.material_type || "other";
  const file = material?.file || {};

  if (type === "slides") {
    return file.slide_count ? `${file.slide_count} slides` : "—";
  }

  if (type === "pdf" || type === "doc") {
    return file.page_count ? `${file.page_count} pages` : "—";
  }

  return "—";
}

const MATERIAL_TYPES = [
  { label: "Other / Setup Later", value: "other" },
  { label: "PDF Document", value: "pdf" },
  { label: "Presentation (Slides)", value: "slides" },
  { label: "Document", value: "doc" },
  { label: "Video", value: "video" },
];

const EditMaterialMain = ({ id }) => {
  const router = useRouter();
  const notify = useNotify();

  const materialId = Number(id);

  const { data: detailRes, isLoading: isLoadingDetail } =
    useAdminMaterialDetail(materialId, {
      enabled: !!materialId,
    });

  const updateMutation = useUpdateMaterial();

  const [values, setValues] = useState({
    course_offering_id: "",
    chapter_id: "",
    title: "",
    material_type: "other",
    file_size_mb: "",
    page_count: "",
    slide_count: "",
    learning_objectives: [],
    description: "",
    is_downloadable: true,
    is_enabled: true,
    file: null,

    readonly_course: "",
    readonly_course_code: "",
    readonly_offering: "",
    readonly_department: "",
    readonly_semester: "",
    readonly_academic_year: "",
    readonly_chapter: "",
    readonly_credit_hours: "",

    readonly_file_type: "",
    readonly_file_size: "",
    readonly_file_length: "",
    readonly_views: "",
    readonly_downloads: "",
    readonly_file_url: "",
  });

  const [errors, setErrors] = useState({});
  const [offeringSearch, setOfferingSearch] = useState("");
  const [chapterSearch, setChapterSearch] = useState("");

  const material = unwrapMaterial(detailRes);

  useEffect(() => {
    if (!material) return;

    const file = material.file || {};
    const course = material.course || {};
    const offering = material.course_offering || {};
    const chapter = material.chapter || {};
    const department = material.department || {};
    const semester = material.semester || {};
    const academicYear = material.academic_year || {};
    const stats = material.stats || {};

    const chapterText = chapter.id
      ? chapter.number
        ? `Chapter ${chapter.number} — ${chapter.title}`
        : chapter.title
      : "General material";

    setValues({
      course_offering_id:
        offering.id !== null && offering.id !== undefined
          ? String(offering.id)
          : "",
      chapter_id:
        chapter.id !== null && chapter.id !== undefined
          ? String(chapter.id)
          : "",
      title: material.title || "",
      material_type: material.material_type || "other",
      file_size_mb: file.size_mb ?? "",
      page_count: file.page_count ?? "",
      slide_count: file.slide_count ?? "",
      learning_objectives: Array.isArray(material.learning_objectives)
        ? material.learning_objectives
        : [],
      description: material.description || "",
      is_downloadable: material.flags?.is_downloadable ?? true,
      is_enabled: material.flags?.is_enabled ?? true,
      file: null,

      readonly_course: course.title || "—",
      readonly_course_code: course.code || "—",
      readonly_offering: offering.custom_title || course.title || "—",
      readonly_department: department.name || "—",
      readonly_semester: semester.name
        ? semester.number
          ? `${semester.name} (${semester.number})`
          : semester.name
        : "—",
      readonly_academic_year: academicYear.name || "—",
      readonly_chapter: chapterText,
      readonly_credit_hours:
        offering.credit_hours !== null && offering.credit_hours !== undefined
          ? String(offering.credit_hours)
          : "—",

      readonly_file_type: formatMaterialType(material.material_type),
      readonly_file_size: file.size_mb ? `${file.size_mb} MB` : "—",
      readonly_file_length: formatLength(material),
      readonly_views:
        stats.view_count !== null && stats.view_count !== undefined
          ? String(stats.view_count)
          : "0",
      readonly_downloads:
        stats.download_count !== null && stats.download_count !== undefined
          ? String(stats.download_count)
          : "0",
      readonly_file_url: file.url || file.read_url || "—",
    });
  }, [material]);

  const normalizedOfferingId = normalizeDropdownValue(
    values.course_offering_id,
  );

  const { data: offeringsRes, isLoading: isLoadingOfferings } =
    useCourseOfferingsMaterialDropdown(
      {
        limit: 20,
        search: offeringSearch || undefined,
      },
      {
        staleTime: 60_000,
      },
    );

  const offeringOptions = useMemo(() => {
    const rows = Array.isArray(offeringsRes?.data)
      ? offeringsRes.data
      : offeringsRes?.data?.data || [];

    if (!material?.course_offering?.id) return rows;

    const exists = rows.some(
      (x) => String(x.value ?? x.id) === String(material.course_offering.id),
    );

    if (exists) return rows;

    return [
      {
        id: material.course_offering.id,
        value: material.course_offering.id,
        label:
          material.course_offering.custom_title ||
          material.course?.title ||
          `Offering ${material.course_offering.id}`,
        meta: {
          department_name: material.department?.name,
        },
      },
      ...rows,
    ];
  }, [offeringsRes, material]);

  const { data: chaptersRes, isLoading: isLoadingChapters } =
    useCourseOfferingChaptersDropdown(
      normalizedOfferingId,
      {
        search: chapterSearch || undefined,
      },
      {
        enabled: !!normalizedOfferingId,
        staleTime: 60_000,
      },
    );

  const chapterOptions = useMemo(() => {
    const rows = Array.isArray(chaptersRes?.data)
      ? chaptersRes.data
      : chaptersRes?.data?.data || [];

    if (!material?.chapter?.id) return rows;

    const exists = rows.some(
      (x) => String(x.value ?? x.id) === String(material.chapter.id),
    );

    if (exists) return rows;

    return [
      {
        id: material.chapter.id,
        value: material.chapter.id,
        label: material.chapter.number
          ? `Chapter ${material.chapter.number} — ${material.chapter.title}`
          : material.chapter.title,
        meta: {
          description: material.chapter.description,
          is_general: false,
        },
      },
      ...rows,
    ];
  }, [chaptersRes, material]);

  const handleChange = (field, value) => {
    if (field.startsWith("readonly_")) return;

    setValues((prev) => {
      const next = { ...prev, [field]: value };

      if (field === "course_offering_id") {
        next.chapter_id = "";
        setChapterSearch("");
      }

      if (field === "material_type") {
        const type = normalizeDropdownValue(value) || "other";

        if (type !== "slides") next.slide_count = "";
        if (type !== "pdf" && type !== "doc") next.page_count = "";
      }

      if (field === "file_upload") {
        next.file = value;

        if (value) {
          next.file_size_mb = Number((value.size / (1024 * 1024)).toFixed(2));
        }
      }

      return next;
    });

    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  const handleSave = async (e) => {
    e?.preventDefault();
    setErrors({});

    const materialType =
      normalizeDropdownValue(values.material_type) || "other";

    const testData = {
      ...values,
      course_offering_id: Number(
        normalizeDropdownValue(values.course_offering_id),
      ),
      chapter_id: normalizeNullableNumber(values.chapter_id),
      material_type: materialType,
      file_size_mb: normalizeOptionalNumber(values.file_size_mb),
      page_count: normalizeOptionalNumber(values.page_count),
      slide_count: normalizeOptionalNumber(values.slide_count),
      learning_objectives: Array.isArray(values.learning_objectives)
        ? values.learning_objectives
        : [],
    };

    const result = materialSchema.safeParse(testData);

    if (!result.success) {
      const fieldErrors = {};

      result.error.issues.forEach((issue) => {
        const key = issue.path[0];
        if (key) fieldErrors[key] = issue.message;
      });

      setErrors(fieldErrors);
      notify.error("Please fix the highlighted fields");
      return;
    }

    const payload = {
      course_offering_id: testData.course_offering_id,
      chapter_id: testData.chapter_id,
      title: testData.title.trim(),
      material_type: testData.material_type || "other",
      file_size_mb: testData.file_size_mb,
      page_count:
        testData.material_type === "pdf" || testData.material_type === "doc"
          ? testData.page_count
          : null,
      slide_count:
        testData.material_type === "slides" ? testData.slide_count : null,
      learning_objectives: testData.learning_objectives
        .map((x) => String(x).trim())
        .filter(Boolean),
      description: testData.description?.trim() || "",
      is_downloadable: testData.is_downloadable,
      is_enabled: testData.is_enabled,
    };

    updateMutation.mutate(
      {
        id: materialId,
        payload,
        file: values.file || null,
      },
      {
        onSuccess: () => {
          notify.success("Material updated successfully!");
          // Stay on the current detail page.
        },
        onError: (error) => {
          const msg =
            error?.info?.message ||
            error?.response?.data?.message ||
            error?.message ||
            "Failed to update material";

          notify.error(String(msg));
        },
      },
    );
  };

  const formFields = [
    {
      section: "Editable Information",
      fields: [
        {
          name: "course_offering_id",
          label: "Course Offering",
          type: "async-dropdown",
          required: true,
          layout: "half",
          placeholder: "Search or select course offering",
          dropdownProps: {
            options: offeringOptions,
            isLoading: isLoadingOfferings,
            hasMore: false,
            setSearch: setOfferingSearch,
            getSublabel: (opt) => {
              const dept = opt?.meta?.department_name;
              return dept ? `Department: ${dept}` : "";
            },
          },
        },
        {
          name: "chapter_id",
          label: "Chapter",
          type: "async-dropdown",
          required: false,
          layout: "half",
          placeholder: normalizedOfferingId
            ? "Search or select chapter"
            : "Select course offering first",
          dropdownProps: {
            options: chapterOptions,
            isLoading: isLoadingChapters,
            hasMore: false,
            setSearch: setChapterSearch,
            getSublabel: (opt) => {
              if (opt?.meta?.is_general) return "General material";
              return opt?.meta?.description || "";
            },
          },
        },
        {
          name: "title",
          label: "Title",
          type: "text",
          required: true,
          layout: "full",
          placeholder: "e.g., Database Architecture Slides",
        },
        {
          name: "material_type",
          label: "Material Type",
          type: "async-dropdown",
          required: false,
          layout: "half",
          placeholder: "Select type",
          dropdownProps: {
            options: MATERIAL_TYPES,
            isLoading: false,
            hasMore: false,
          },
        },
      ],
    },
    {
      section: "Material File",
      fields: [
        {
          name: "file_upload",
          label: "Replace File",
          type: "file",
          layout: "full",
          fileProps: {
            buttonLabel: "Choose File",
            currentFileName: material?.file?.url
              ? material.file.url.split("/").pop()
              : "",
            downloadUrl: material?.file?.url || material?.file?.read_url || "",
            helperText:
              "Optional. Select a new file only if you want to upload or replace the current file.",
          },
        },
        {
          name: "file_size_mb",
          label: "File Size (MB)",
          type: "number",
          layout: "half",
          placeholder: "Auto-filled when you select a file",
        },
      ],
    },
    {
      section: "Additional Details",
      fields: [
        {
          name: "slide_count",
          label: "Slide Count",
          type: "number",
          layout: "half",
          placeholder: "e.g., 45",
          condition: (vals) =>
            normalizeDropdownValue(vals.material_type) === "slides",
        },
        {
          name: "page_count",
          label: "Page Count",
          type: "number",
          layout: "half",
          placeholder: "e.g., 20",
          condition: (vals) => {
            const type = normalizeDropdownValue(vals.material_type);
            return type === "pdf" || type === "doc";
          },
        },
        {
          name: "learning_objectives",
          label: "Learning Objectives",
          type: "tags",
          layout: "full",
          placeholder: "Type objective and press Enter",
        },
        {
          name: "description",
          label: "Description",
          type: "textarea",
          layout: "full",
          placeholder: "Short summary of the material...",
        },
        {
          name: "is_downloadable",
          label: "Downloadable",
          type: "checkbox",
          layout: "half",
          checkboxLabel: "Allow students to download",
          checkboxDescription:
            "If unchecked, the material will be viewable only online.",
        },
        {
          name: "is_enabled",
          label: "Enabled",
          type: "checkbox",
          layout: "half",
          checkboxLabel: "Publish this material",
          checkboxDescription:
            "If unchecked, students will not see this material.",
        },
      ],
    },
    {
      section: "Academic Context",
      fields: [
        {
          name: "readonly_course",
          label: "Course",
          type: "text",
          layout: "half",
          readOnly: true,
        },
        {
          name: "readonly_course_code",
          label: "Course Code",
          type: "text",
          layout: "half",
          readOnly: true,
        },
        {
          name: "readonly_offering",
          label: "Offering",
          type: "text",
          layout: "half",
          readOnly: true,
        },
        {
          name: "readonly_department",
          label: "Department",
          type: "text",
          layout: "half",
          readOnly: true,
        },
        {
          name: "readonly_semester",
          label: "Semester",
          type: "text",
          layout: "half",
          readOnly: true,
        },
        {
          name: "readonly_academic_year",
          label: "Academic Year",
          type: "text",
          layout: "half",
          readOnly: true,
        },
        {
          name: "readonly_chapter",
          label: "Chapter",
          type: "text",
          layout: "full",
          readOnly: true,
        },
        {
          name: "readonly_credit_hours",
          label: "Credit Hours",
          type: "text",
          layout: "half",
          readOnly: true,
        },
      ],
    },
    {
      section: "File Summary",
      fields: [
        {
          name: "readonly_file_type",
          label: "Type",
          type: "text",
          layout: "half",
          readOnly: true,
        },
        {
          name: "readonly_file_size",
          label: "Size",
          type: "text",
          layout: "half",
          readOnly: true,
        },
        {
          name: "readonly_file_length",
          label: "Length",
          type: "text",
          layout: "half",
          readOnly: true,
        },
        {
          name: "readonly_views",
          label: "Views",
          type: "text",
          layout: "half",
          readOnly: true,
        },
        {
          name: "readonly_downloads",
          label: "Downloads",
          type: "text",
          layout: "half",
          readOnly: true,
        },
        {
          name: "readonly_file_url",
          label: "File URL",
          type: "text",
          layout: "full",
          readOnly: true,
        },
      ],
    },
  ];

  if (isLoadingDetail) return <Preloader />;

  return (
    <div className="max-w-7xl mx-auto w-full px-4 sm:px-6">
      <FrappeForm
        title="Edit Material"
        status={values.is_enabled ? "Published" : "Draft"}
        fields={formFields}
        values={values}
        errors={errors}
        onChange={handleChange}
        onSave={handleSave}
        isSaving={updateMutation.isPending}
      />
    </div>
  );
};

export default EditMaterialMain;
