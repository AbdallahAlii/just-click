"use client";

import Preloader from "@/components/shared/others/Preloader";
import FrappeForm from "@/components/shared/forms/FrappeForm";
import {
  useApproveStudent,
  useResendOutbox,
  useResetStudentPassword,
  useStudentDetail,
  useUpdateStudent,
} from "@/features/people/hooks";
import { useDepartmentsDropdown, useFacultiesDropdown, useSemestersDropdown } from "@/features/academic/hooks";
import useNotify from "@/hooks/useNotify";
import { useMemo, useState, useEffect, useRef } from "react";

const TRACKED_FIELDS = [
  "full_name",
  "student_id",
  "username",
  "email",
  "department_id",
  "faculty_id",
  "semester_id",
  "classroom_id",
  "profile_enabled",
  "account_enabled",
];

function extractDropdownRows(res) {
  return res?.data?.data?.data ?? res?.data?.data ?? res?.data ?? [];
}

function mapOptions(items = []) {
  return items.map((item) => ({
    label: item?.label || item?.name || item?.title || item?.display_name || `Option #${item?.id}`,
    value: String(item?.value ?? item?.id ?? ""),
    meta: item?.meta || { code: item?.code || item?.display_name || item?.name || "" },
  }));
}

function getChangedFields(initialValues, currentValues) {
  const changed = {};
  TRACKED_FIELDS.forEach((key) => {
    if (JSON.stringify(initialValues?.[key]) !== JSON.stringify(currentValues?.[key])) {
      changed[key] = currentValues[key];
    }
  });
  return changed;
}

function getVerificationOutboxId(studentData) {
  return (
    studentData?.email_verification_outbox?.id ||
    studentData?.verification_email_outbox?.id ||
    studentData?.email_outboxes?.verify_email?.id ||
    studentData?.email_outbox?.id ||
    null
  );
}

const StudentDetailMain = ({ id }) => {
  const notify = useNotify();

  const [values, setValues] = useState(null);
  const [initialValues, setInitialValues] = useState(null);
  const hasInitializedRef = useRef(false);

  const { data: response, isLoading, isError } = useStudentDetail(id);
  const studentData = useMemo(() => {
    return response?.data?.data ?? response?.data ?? null;
  }, [response]);

  const { data: deptsRes, isLoading: isLoadingDepts } = useDepartmentsDropdown({ limit: 20 });
  const { data: facsRes, isLoading: isLoadingFacs } = useFacultiesDropdown({ limit: 20 });
  const { data: semsRes, isLoading: isLoadingSems } = useSemestersDropdown({ limit: 20 });

  const departmentOptions = useMemo(() => mapOptions(extractDropdownRows(deptsRes)), [deptsRes]);
  const facultyOptions = useMemo(() => mapOptions(extractDropdownRows(facsRes)), [facsRes]);
  const semesterOptions = useMemo(() => mapOptions(extractDropdownRows(semsRes)), [semsRes]);

  const updateMutation = useUpdateStudent();
  const approveMutation = useApproveStudent();
  const resendVerificationMutation = useResendOutbox();
  const resetPasswordMutation = useResetStudentPassword();

  useEffect(() => {
    if (!studentData) return;

    const normalized = {
      full_name: studentData.profile?.full_name || "",
      student_id: studentData.profile?.student_id || "",
      username: studentData.user?.username || "",
      email: studentData.user?.email || "",
      manual_password: "",
      classroom_id: studentData.context?.classroom?.id ? String(studentData.context.classroom.id) : "",
      status_label: studentData.flags?.status_label || "",
      approval_status: studentData.flags?.approval_status || studentData.user?.status || "",
      profile_enabled: Boolean(studentData.flags?.profile_enabled ?? studentData.profile?.is_enabled),
      account_enabled: Boolean(studentData.flags?.account_enabled ?? studentData.user?.is_enabled),
      department_id: studentData.context?.department?.id ? String(studentData.context.department.id) : "",
      faculty_id: studentData.context?.faculty?.id ? String(studentData.context.faculty.id) : "",
      semester_id: studentData.context?.semester?.id ? String(studentData.context.semester.id) : "",
    };

    if (!hasInitializedRef.current || !initialValues) {
      setValues(normalized);
      setInitialValues(normalized);
      hasInitializedRef.current = true;
    }
  }, [studentData, initialValues]);

  const changedFields = useMemo(() => {
    if (!values || !initialValues) return {};
    return getChangedFields(initialValues, values);
  }, [initialValues, values]);

  const isDirty = Object.keys(changedFields).length > 0;

  const handleChange = (field, value) => {
    setValues((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = (e) => {
    e?.preventDefault?.();
    if (!values) return;
    if (!isDirty) {
      notify.warning("No changes in document");
      return;
    }

    const payload = {
      ...changedFields,
      ...(changedFields.department_id !== undefined ? { department_id: Number(changedFields.department_id) || null } : {}),
      ...(changedFields.faculty_id !== undefined ? { faculty_id: Number(changedFields.faculty_id) || null } : {}),
      ...(changedFields.semester_id !== undefined ? { semester_id: Number(changedFields.semester_id) || null } : {}),
      ...(changedFields.classroom_id !== undefined ? { classroom_id: Number(changedFields.classroom_id) || null } : {}),
    };

    updateMutation.mutate(
      { id, payload },
      {
        onSuccess: () => {
          notify.success("Student updated successfully");
          const nextValues = { ...values, ...changedFields };
          setValues(nextValues);
          setInitialValues(nextValues);
        },
        onError: (err) => {
          notify.error(err?.message || "Failed to update student");
        },
      },
    );
  };

  const handleApprove = () => {
    const userId = studentData?.user?.id;
    if (!userId) {
      notify.error("No student user ID found");
      return;
    }
    approveMutation.mutate(
      { userId, profileId: id },
      {
        onSuccess: () => notify.success("Student approved successfully"),
        onError: (err) => notify.error(err?.message || "Failed to approve student"),
      },
    );
  };

  const handleResendVerificationEmail = () => {
    const outboxId = getVerificationOutboxId(studentData);
    if (!outboxId) {
      notify.error("Verification email outbox ID is missing for this student");
      return;
    }
    resendVerificationMutation.mutate(outboxId, {
      onSuccess: () => notify.success("Verification email resent successfully"),
      onError: (err) => notify.error(err?.message || "Failed to resend verification email"),
    });
  };

  const handleResetPasswordEmail = () => {
    resetPasswordMutation.mutate(
      { id, mode: "email" },
      {
        onSuccess: (res) => notify.success(res?.message || "Password reset email queued"),
        onError: (err) => notify.error(err?.message || "Failed to reset password"),
      },
    );
  };

  const handleResetPasswordManual = () => {
    const pwd = (values?.manual_password || "").trim();
    if (!pwd) {
      notify.error("Enter a new password in the field below first");
      return;
    }
    resetPasswordMutation.mutate(
      { id, mode: "manual", newPassword: pwd },
      {
        onSuccess: (res) => {
          notify.success(res?.message || "Password updated");
          setValues((prev) => ({ ...prev, manual_password: "" }));
        },
        onError: (err) => notify.error(err?.message || "Failed to reset password"),
      },
    );
  };

  const formFields = useMemo(
    () => [
      { name: "full_name", label: "Full Name", type: "text", layout: "half" },
      { name: "student_id", label: "Student ID", type: "text", layout: "half" },
      { name: "username", label: "Username", type: "text", layout: "half" },
      { name: "email", label: "Email", type: "text", layout: "half" },
      { name: "status_label", label: "Account status", type: "text", layout: "half", readOnly: true },
      { name: "approval_status", label: "Approval stage", type: "text", layout: "half", readOnly: true },
      {
        name: "department_id",
        label: "Department",
        type: "async-dropdown",
        layout: "half",
        placeholder: "Select department",
        dropdownProps: {
          options: departmentOptions,
          isLoading: isLoadingDepts,
          getSublabel: (opt) => (opt?.meta?.code ? `Code: ${opt.meta.code}` : ""),
        },
      },
      {
        name: "faculty_id",
        label: "Faculty",
        type: "async-dropdown",
        layout: "half",
        placeholder: "Select faculty",
        dropdownProps: {
          options: facultyOptions,
          isLoading: isLoadingFacs,
          getSublabel: (opt) => (opt?.meta?.code ? `Code: ${opt.meta.code}` : ""),
        },
      },
      {
        name: "semester_id",
        label: "Semester",
        type: "async-dropdown",
        layout: "half",
        placeholder: "Select semester",
        dropdownProps: {
          options: semesterOptions,
          isLoading: isLoadingSems,
          getSublabel: (opt) => opt?.meta?.code || "",
        },
      },
      { name: "classroom_id", label: "Classroom ID", type: "text", layout: "half", placeholder: "Classroom record ID" },
      { name: "profile_enabled", label: "Profile enabled", type: "checkbox", checkboxLabel: "Student profile active", layout: "half" },
      { name: "account_enabled", label: "Login allowed", type: "checkbox", checkboxLabel: "User can sign in", layout: "half" },
      {
        name: "manual_password",
        label: "New password (manual)",
        type: "text",
        layout: "half",
        placeholder: "Type password, then use menu → Set manual password",
      },
    ],
    [departmentOptions, facultyOptions, semesterOptions, isLoadingDepts, isLoadingFacs, isLoadingSems],
  );

  const menuOptions = useMemo(
    () => [
      {
        label: resendVerificationMutation.isPending ? "Resending verification…" : "Resend verification email",
        action: handleResendVerificationEmail,
      },
      {
        label: resetPasswordMutation.isPending ? "Sending password…" : "Send new password by email",
        action: handleResetPasswordEmail,
      },
      {
        label: "Set manual password",
        action: handleResetPasswordManual,
      },
      {
        label: approveMutation.isPending ? "Approving…" : "Approve student",
        action: handleApprove,
      },
    ],
    [
      resendVerificationMutation.isPending,
      resetPasswordMutation.isPending,
      approveMutation.isPending,
      values?.manual_password,
      studentData,
    ],
  );

  if (isLoading || !values) {
    return <Preloader />;
  }

  if (isError) {
    return <div className="p-10 flex items-center justify-center text-red-500">Failed to load student details.</div>;
  }

  const formStatus = updateMutation.isPending ? "Saving..." : isDirty ? "Not Saved" : "Saved";

  return (
    <div className="max-w-7xl mx-auto w-full">
      <FrappeForm
        title={`Student: ${studentData?.profile?.full_name || ""}`}
        status={formStatus}
        fields={formFields}
        values={values}
        errors={{}}
        onChange={handleChange}
        onSave={handleSave}
        isSaving={updateMutation.isPending}
        menuOptions={menuOptions}
      />
    </div>
  );
};

export default StudentDetailMain;
