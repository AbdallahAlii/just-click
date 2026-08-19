// "use client";

// import Preloader from "@/components/shared/others/Preloader";

// import AcademicTable from "@/components/shared/dashboards/AcademicTable";
// import {
//   useBulkDeleteMaterials,
//   useMaterialsList,
// } from "@/features/materials/hooks";
// import useNotify from "@/hooks/useNotify";
// import { useRouter } from "next/navigation";
// import { useCallback, useMemo } from "react";

// const baseMaterialsColumns = [
//   { key: "title", label: "Title", width: "flex-1", linkRow: true },
//   { key: "course_code", label: "Course", width: "w-24", align: "center" },
//   { key: "material_type", label: "Type", width: "w-24" },
//   { key: "file_size_display", label: "Size", width: "w-24", align: "center" },
//   { key: "is_enabled_label", label: "Status", width: "w-24" },
// ];

// function extractListRows(res) {
//   return res?.data?.data?.data ?? res?.data?.data ?? res?.data ?? [];
// }

// const MaterialsMain = () => {
//   const router = useRouter();
//   const notify = useNotify();

//   const { data, isLoading, isError } = useMaterialsList({
//     mode: "scroll",
//     limit: 20,
//     is_enabled: 1,
//   });

//   const bulkDeleteMutation = useBulkDeleteMaterials();

//   const handleBulkDelete = useCallback(
//     (selectedIds) => {
//       if (!selectedIds?.length) return;

//       if (
//         confirm(
//           `Are you sure you want to delete ${selectedIds.length} materials?`
//         )
//       ) {
//         bulkDeleteMutation.mutate(
//           { ids: selectedIds },
//           {
//             onSuccess: () => {
//               notify.success("Materials deleted successfully");
//             },
//             onError: (err) => {
//               notify.error(err?.message || "Failed to delete materials");
//             },
//           }
//         );
//       }
//     },
//     [bulkDeleteMutation, notify]
//   );

//   const actions = useMemo(
//     () => [{ label: "Delete", action: "delete", onClick: handleBulkDelete }],
//     [handleBulkDelete]
//   );

//   const enrichedColumns = useMemo(() => {
//     return baseMaterialsColumns.map((col) => {
//       if (col.key === "material_type") {
//         return {
//           ...col,
//           filterDropdown: {
//             options: [
//               { label: "PDF Document", value: "pdf" },
//               { label: "Presentation (Slides)", value: "slides" },
//               { label: "Video", value: "video" },
//               { label: "Other", value: "other" },
//             ],
//             isLoading: false,
//             hasMore: false,
//           },
//         };
//       }
//       return col;
//     });
//   }, []);

//   const rawData = useMemo(() => {
//     const rows = extractListRows(data);
//     return Array.isArray(rows) ? rows : [];
//   }, [data]);

//   const materialsData = useMemo(() => {
//     return rawData.map((item) => ({
//       ...item,
//       course_code: item?.course?.code || item?.course_code || "—",
//       file_size_display:
//         item?.file_size_mb !== null && item?.file_size_mb !== undefined
//           ? `${item.file_size_mb} MB`
//           : "—",
//       is_enabled_label: item?.is_enabled ? "Active" : "Inactive",
//     }));
//   }, [rawData]);

//   const handleAddNew = useCallback(() => {
//     router.push("/admin/dashboards/admin-academic/materials/create");
//   }, [router]);

//   const handleRowClick = useCallback(
//     (row) => {
//       router.push(`/admin/dashboards/admin-academic/materials/${row.id}`);
//     },
//     [router]
//   );

//   if (isLoading) {
//     return <Preloader />;
//   }

//   if (isError) {
//     return (
//       <div className="p-10 text-center text-red-500">
//         Failed to load materials.
//       </div>
//     );
//   }

//   return (
//     <AcademicTable
//       title="Materials"
//       columns={enrichedColumns}
//       data={materialsData}
//       addNewLabel="Upload Material"
//       onAddNew={handleAddNew}
//       onRowClick={handleRowClick}
//       actions={actions}
//     />
//   );
// };

// export default MaterialsMain;
"use client";

import AcademicTable from "@/components/shared/dashboards/AcademicTable";
import Preloader from "@/components/shared/others/Preloader";
import {
  useAdminMaterialsList,
  useBulkDeleteMaterials,
} from "@/features/materials/hooks";
import useNotify from "@/hooks/useNotify";
import { useRouter } from "next/navigation";
import { useCallback, useMemo } from "react";

const baseMaterialsColumns = [
  { key: "title", label: "Title", width: "flex-1", linkRow: true },
  { key: "course_code", label: "Course", width: "w-24", align: "center" },
  { key: "material_type", label: "Type", width: "w-24" },
  { key: "file_size_display", label: "Size", width: "w-24", align: "center" },
  { key: "is_enabled_label", label: "Status", width: "w-24" },
];

function extractListRows(res) {
  return res?.data?.data?.data ?? res?.data?.data ?? res?.data ?? [];
}

const MaterialsMain = () => {
  const router = useRouter();
  const notify = useNotify();

  const { data, isLoading, isError } = useAdminMaterialsList({
    page: 1,
    limit: 20,
  });

  const bulkDeleteMutation = useBulkDeleteMaterials();

  const handleBulkDelete = useCallback(
    (selectedIds) => {
      if (!selectedIds?.length) return;

      if (
        confirm(
          `Are you sure you want to delete ${selectedIds.length} materials?`,
        )
      ) {
        bulkDeleteMutation.mutate(
          { ids: selectedIds },
          {
            onSuccess: () => {
              notify.success("Materials deleted successfully");
            },
            onError: (err) => {
              notify.error(err?.message || "Failed to delete materials");
            },
          },
        );
      }
    },
    [bulkDeleteMutation, notify],
  );

  const actions = useMemo(
    () => [{ label: "Delete", action: "delete", onClick: handleBulkDelete }],
    [handleBulkDelete],
  );

  const enrichedColumns = useMemo(() => {
    return baseMaterialsColumns.map((col) => {
      if (col.key === "material_type") {
        return {
          ...col,
          filterDropdown: {
            options: [
              { label: "PDF Document", value: "pdf" },
              { label: "Presentation (Slides)", value: "slides" },
              { label: "Document", value: "doc" },
              { label: "Video", value: "video" },
              { label: "Other", value: "other" },
            ],
            isLoading: false,
            hasMore: false,
          },
        };
      }

      return col;
    });
  }, []);

  const rawData = useMemo(() => {
    const rows = extractListRows(data);
    return Array.isArray(rows) ? rows : [];
  }, [data]);

  const materialsData = useMemo(() => {
    return rawData.map((item) => ({
      ...item,
      course_code:
        item?.course_code ||
        item?.course?.code ||
        item?.context?.course?.code ||
        "—",
      file_size_display:
        item?.file_size_mb !== null && item?.file_size_mb !== undefined
          ? `${item.file_size_mb} MB`
          : item?.file?.size_mb !== null && item?.file?.size_mb !== undefined
            ? `${item.file.size_mb} MB`
            : "—",
      is_enabled_label:
        (item?.is_enabled ?? item?.flags?.is_enabled) ? "Active" : "Inactive",
    }));
  }, [rawData]);

  const handleAddNew = useCallback(() => {
    router.push("/admin/dashboards/admin-academic/materials/create");
  }, [router]);

  const handleRowClick = useCallback(
    (row) => {
      router.push(`/admin/dashboards/admin-academic/materials/${row.id}`);
    },
    [router],
  );

  if (isLoading) {
    return <Preloader />;
  }

  if (isError) {
    return (
      <div className="p-10 text-center text-red-500">
        Failed to load materials.
      </div>
    );
  }

  return (
    <AcademicTable
      title="Materials"
      columns={enrichedColumns}
      data={materialsData}
      addNewLabel="Upload Material"
      onAddNew={handleAddNew}
      onRowClick={handleRowClick}
      actions={actions}
    />
  );
};

export default MaterialsMain;
