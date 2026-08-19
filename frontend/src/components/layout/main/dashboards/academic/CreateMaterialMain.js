"use client";

import FrappeForm from "@/components/shared/forms/FrappeForm";
import Preloader from "@/components/shared/others/Preloader";
import {
  useCourseOfferingChaptersDropdown,
  useCourseOfferingsMaterialDropdown,
} from "@/features/academic/hooks";
import { useCreateMaterial } from "@/features/materials/hooks";
import useNotify from "@/hooks/useNotify";
import { useRouter } from "next/navigation";
import { useState } from "react";
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

const MATERIAL_TYPES = [
  { label: "Other / Setup Later", value: "other" },
  { label: "PDF Document", value: "pdf" },
  { label: "Presentation (Slides)", value: "slides" },
  { label: "Document", value: "doc" },
  { label: "Video", value: "video" },
];

const CreateMaterialMain = () => {
  const router = useRouter();
  const notify = useNotify();
  const createMutation = useCreateMaterial();

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
  });

  const [errors, setErrors] = useState({});
  const [offeringSearch, setOfferingSearch] = useState("");
  const [chapterSearch, setChapterSearch] = useState("");

  const normalizedOfferingId = normalizeDropdownValue(
    values.course_offering_id,
  );

  const {
    data: offeringsRes,
    isLoading: isLoadingOfferings,
    isFetching: isFetchingOfferings,
  } = useCourseOfferingsMaterialDropdown(
    {
      limit: 20,
      search: offeringSearch || undefined,
    },
    {
      staleTime: 60_000,
      placeholderData: (previousData) => previousData,
    },
  );

  const offeringOptions = Array.isArray(offeringsRes?.data)
    ? offeringsRes.data
    : offeringsRes?.data?.data || [];

  const {
    data: chaptersRes,
    isLoading: isLoadingChapters,
    isFetching: isFetchingChapters,
  } = useCourseOfferingChaptersDropdown(
    normalizedOfferingId,
    {
      search: chapterSearch || undefined,
    },
    {
      enabled: !!normalizedOfferingId,
      staleTime: 60_000,
      placeholderData: (previousData) => previousData,
    },
  );

  const chapterOptions = Array.isArray(chaptersRes?.data)
    ? chaptersRes.data
    : chaptersRes?.data?.data || [];

  const isInitialOfferingsLoading =
    isLoadingOfferings && !offeringsRes && !offeringSearch;

  const handleChange = (field, value) => {
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
        } else {
          next.file_size_mb = "";
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

    createMutation.mutate(
      {
        payload,
        file: values.file || null,
      },
      {
        onSuccess: (res) => {
          notify.success("Material created successfully!");

          const materialId = extractMaterialId(res);

          if (materialId) {
            router.push(
              `/admin/dashboards/admin-academic/materials/${materialId}`,
            );
            return;
          }

          router.push("/admin/dashboards/admin-academic/materials");
        },
        onError: (error) => {
          const msg =
            error?.info?.message ||
            error?.response?.data?.message ||
            error?.message ||
            "Failed to create material";

          notify.error(String(msg));
        },
      },
    );
  };

  const formFields = [
    {
      section: "Basic Information",
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
            isLoading: isLoadingOfferings || isFetchingOfferings,
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
            isLoading: isLoadingChapters || isFetchingChapters,
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
          label: "Upload File",
          type: "file",
          layout: "full",
          fileProps: {
            buttonLabel: "Choose File",
            helperText:
              "Optional. You can create the material now and upload the file later.",
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
  ];

  if (isInitialOfferingsLoading) return <Preloader />;

  return (
    <div className="max-w-7xl mx-auto w-full px-4 sm:px-6">
      <FrappeForm
        title="Create New Material"
        status="Draft"
        fields={formFields}
        values={values}
        errors={errors}
        onChange={handleChange}
        onSave={handleSave}
        isSaving={createMutation.isPending}
      />
    </div>
  );
};

export default CreateMaterialMain;
