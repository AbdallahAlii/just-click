"use client";

import Preloader from "@/components/shared/others/Preloader";

import AcademicTable from "@/components/shared/dashboards/AcademicTable";
import {
  useBulkApproveStudents,
  useBulkResendStudentApprovalEmails,
  useStudentsList,
} from "@/features/people/hooks";
import { useRouter } from "next/navigation";
import useNotify from "@/hooks/useNotify";

const studentsColumns = [
  { key: "full_name", label: "Full Name", width: "flex-1", bold: true },
  { key: "student_id", label: "Student ID", width: "w-32" },
  { key: "department_name", label: "Department", width: "w-44" },
  { key: "status_label", label: "Status", width: "w-24" },
];

const StudentsMain = () => {
  const router = useRouter();
  const notify = useNotify();

  const { data, isLoading, isError } = useStudentsList({ limit: 20 });
  const bulkApproveMutation = useBulkApproveStudents();
  const bulkResendApprovalMutation = useBulkResendStudentApprovalEmails();

  if (isLoading) {
    return <Preloader />;
  }

  if (isError) {
    return <div className="p-10 text-center text-red-500">Failed to load students.</div>;
  }

  const rawData = data?.data?.data || data?.data || [];
  const tableData = rawData.map(item => ({
    ...item,
    full_name: item.profile?.full_name || "—",
    student_id: item.profile?.student_id || "—",
    department_name: item.context?.department?.name || "—",
    status_label: item.flags?.status_label || (item.flags?.is_enabled ? "Active" : "Inactive"),
    user_id: item.user?.id,
  }));

  const getSelectedUserIds = (selectedIds) => {
    return tableData
      .filter((row) => selectedIds.includes(row.id))
      .map((row) => row.user_id)
      .filter(Boolean);
  };

  const handleBulkApprove = (selectedIds) => {
    const userIds = getSelectedUserIds(selectedIds);

    if (userIds.length === 0) {
      notify.error("No student user IDs found for the selected rows");
      return;
    }

    if (confirm(`Are you sure you want to approve ${userIds.length} student(s)?`)) {
      bulkApproveMutation.mutate(
        { userIds },
        {
          onSuccess: () => notify.success("Student(s) approved successfully"),
          onError: (err) => notify.error(err?.message || "Failed to approve student(s)"),
        },
      );
    }
  };

  const handleBulkResendApprovalEmail = (selectedIds) => {
    const userIds = getSelectedUserIds(selectedIds);

    if (userIds.length === 0) {
      notify.error("No student user IDs found for the selected rows");
      return;
    }

    if (confirm(`Are you sure you want to resend approval emails for ${userIds.length} student(s)?`)) {
      bulkResendApprovalMutation.mutate(
        { userIds, sendNow: true },
        {
          onSuccess: () => notify.success("Approval emails resent successfully"),
          onError: (err) => notify.error(err?.message || "Failed to resend approval emails"),
        },
      );
    }
  };

  const actions = [
    { label: "Approve Students", action: "approve", onClick: handleBulkApprove },
    { label: "Resend Approval Email", action: "resend", onClick: handleBulkResendApprovalEmail },
  ];

  return (
    <AcademicTable
      title="Students"
      columns={studentsColumns}
      data={tableData}
      addNewLabel={null}
      onAddNew={null}
      onRowClick={(row) => router.push(`/admin/dashboards/admin-people/students/${row.id}`)}
      actions={actions}
    />
  );
};

export default StudentsMain;
