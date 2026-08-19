"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";

import AsyncDropdown from "@/components/shared/inputs/AsyncDropdown";
import { useLogout } from "@/features/auth/hooks";
import { useRegisterStudent } from "@/features/signup/hooks";
import { getApiErrorMessage, isValidEmail } from "@/lib/apiErrors";
import { useDropdown } from "@/hooks/dropdown/useDropdown";
import { useSession } from "@/providers/SessionProvider";

const SignUpForm = () => {
  const router = useRouter();
  const registerMut = useRegisterStudent();
  const logoutMut = useLogout();
  const { user } = useSession();
  const clearedSessionRef = useRef(false);

  const [selectedFaculty, setSelectedFaculty] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [form, setForm] = useState({
    student_id: "",
    full_name: "",
    student_email: "",
    department_id: "",
    semester_id: "",
    accept_terms: false,
  });
  const [formError, setFormError] = useState("");

  useEffect(() => {
    if (!user || clearedSessionRef.current || logoutMut.isPending) return;
    clearedSessionRef.current = true;
    logoutMut.mutateAsync().catch(() => {});
  }, [user, logoutMut]);

  const onChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormError("");
    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const facultyDD = useDropdown({
    cacheKey: "public-faculties",
    endpoint: "/academic/public/faculties/dropdown",
    enabled: true,
    limit: 20,
  });

  const deptDD = useDropdown({
    cacheKey: `departments-faculty-${selectedFaculty || "none"}`,
    endpoint: "/academic/public/departments/by-faculty/dropdown",
    enabled: !!selectedFaculty,
    limit: 10,
    params: { faculty_id: selectedFaculty || "" },
  });

  const semesterDD = useDropdown({
    cacheKey: "public-semesters",
    endpoint: "/academic/public/semesters/dropdown",
    enabled: true,
    limit: 20,
  });

  const facultyOptions = useMemo(
    () => (Array.isArray(facultyDD.options) ? facultyDD.options : []),
    [facultyDD.options],
  );

  const departmentOptions = useMemo(
    () => (Array.isArray(deptDD.options) ? deptDD.options : []),
    [deptDD.options],
  );

  const semesterOptions = useMemo(
    () => (Array.isArray(semesterDD.options) ? semesterDD.options : []),
    [semesterDD.options],
  );

  const handleFacultyPick = (val) => {
    const facultyId = String(val || "");
    setFormError("");
    setSelectedFaculty(facultyId);
    setForm((prev) => ({
      ...prev,
      department_id: "",
    }));
    deptDD.reset?.();
  };

  const trimmedStudentId = form.student_id.trim();
  const trimmedFullName = form.full_name.trim();
  const trimmedEmail = form.student_email.trim();

  const isFormValid =
    !!trimmedStudentId &&
    !!trimmedFullName &&
    !!trimmedEmail &&
    isValidEmail(trimmedEmail) &&
    !!selectedFaculty &&
    !!form.department_id &&
    !!form.semester_id &&
    !!form.accept_terms;

  const isBusy = isSubmitting || registerMut.isPending;
  const isSubmitDisabled = !isFormValid || isBusy;

  const onSubmit = async (e) => {
    e.preventDefault();
    setFormError("");

    if (isBusy) return;

    const showError = (msg) => {
      setFormError(msg);
      toast.error(msg);
    };

    if (!form.accept_terms) {
      showError("Please accept terms.");
      return;
    }

    if (!trimmedStudentId || !trimmedFullName || !trimmedEmail) {
      showError("Please fill Student ID, Full name, and Email.");
      return;
    }

    if (!isValidEmail(trimmedEmail)) {
      showError("Please enter a valid email address.");
      return;
    }

    if (!selectedFaculty || !form.department_id) {
      showError("Please select Faculty and Department.");
      return;
    }

    if (!form.semester_id) {
      showError("Please select your current semester.");
      return;
    }

    setIsSubmitting(true);

    try {
      if (user) {
        try {
          await logoutMut.mutateAsync();
        } catch {
          /* still submit signup after a leftover session */
        }
      }

      const payload = {
        student_id: trimmedStudentId,
        email: trimmedEmail,
        full_name: trimmedFullName,
        faculty_id: Number(selectedFaculty),
        department_id: Number(form.department_id),
        semester_id: Number(form.semester_id),
      };

      const res = await registerMut.mutateAsync(payload);

      const msg =
        res?.message ||
        "Registration submitted. Please check your email to verify your address.";
      const d = res?.data || {};

      const qs = new URLSearchParams({
        message: msg,
        email: d.email || payload.email,
        status: d.status || "",
        student_id: d.student_id || payload.student_id,
      });

      router.replace(`/signup/success?${qs.toString()}`);
    } catch (err) {
      const msg = getApiErrorMessage(err, "Registration failed.");
      setFormError(msg);
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const labelCls =
    "block text-[12.5px] font-medium text-ds-text-secondary mb-1.5";

  const inputCls =
    "w-full min-w-0 h-11 rounded-lg border border-ds-border " +
    "bg-ds-surface-input px-3.5 text-sm text-ds-text-primary " +
    "placeholder:text-ds-text-muted " +
    "focus:outline-none focus:border-ds-action/50 focus:ring-4 focus:ring-ds-action/10 transition";

  const selectCls =
    "w-full min-w-0 h-11 rounded-lg border border-ds-border " +
    "bg-ds-surface-input px-3.5 pr-12 text-sm text-ds-text-primary " +
    "placeholder:text-ds-text-muted " +
    "focus:outline-none focus:border-ds-action/50 focus:ring-4 focus:ring-ds-action/10 transition";

  return (
    <div className="w-full min-w-0">
      <div className="mb-5">
        <h2 className="text-xl font-semibold text-ds-text-primary">
          Create account
        </h2>
        <p className="mt-1 text-sm text-ds-text-muted">
          Already registered?{" "}
          <Link
            href="/login"
            className="font-semibold text-ds-action hover:underline"
          >
            Sign in
          </Link>
        </p>
      </div>

      <div className="mb-5 rounded-xl border border-ds-action/25 bg-ds-action/10 px-4 py-3 text-sm text-ds-text-primary">
        No password yet. We will email a verification link so you can activate
        your student account.
      </div>

      {formError ? (
        <div
          role="alert"
          className="mb-4 rounded-xl border border-ds-error/30 bg-ds-error/10 px-4 py-3 text-sm text-ds-error"
        >
          {formError}
        </div>
      ) : null}

      <form onSubmit={onSubmit} className="space-y-3.5">
        <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2">
          <div className="min-w-0">
            <label className={labelCls} htmlFor="student_id">
              Student ID <span className="text-ds-error">*</span>
            </label>
            <input
              id="student_id"
              name="student_id"
              value={form.student_id}
              onChange={onChange}
              type="text"
              placeholder="C123456"
              className={inputCls}
              disabled={isBusy}
              autoComplete="username"
            />
          </div>

          <div className="min-w-0">
            <label className={labelCls} htmlFor="full_name">
              Full name <span className="text-ds-error">*</span>
            </label>
            <input
              id="full_name"
              name="full_name"
              value={form.full_name}
              onChange={onChange}
              type="text"
              placeholder="Falastiin Ahmed"
              className={inputCls}
              disabled={isBusy}
              autoComplete="name"
            />
          </div>
        </div>

        <div className="min-w-0">
          <label className={labelCls} htmlFor="student_email">
            Student email <span className="text-ds-error">*</span>
          </label>
          <input
            id="student_email"
            name="student_email"
            value={form.student_email}
            onChange={onChange}
            type="email"
            placeholder="student@university.edu"
            className={inputCls}
            disabled={isBusy}
            autoComplete="email"
          />
        </div>

        <div className="min-w-0">
          <label className={labelCls}>
            Faculty <span className="text-ds-error">*</span>
          </label>
          <AsyncDropdown
            value={selectedFaculty}
            onChange={handleFacultyPick}
            options={facultyOptions}
            isLoading={facultyDD.isLoading}
            hasMore={facultyDD.hasMore}
            onLoadMore={facultyDD.loadMore}
            onSearch={facultyDD.setSearch}
            placeholder="Select faculty"
            inputClassName={selectCls}
            disabled={isBusy}
          />
        </div>

        <div className="min-w-0">
          <label className={labelCls}>
            Department <span className="text-ds-error">*</span>
          </label>
          <AsyncDropdown
            key={`department-${selectedFaculty || "none"}`}
            value={form.department_id}
            onChange={(val) =>
              setForm((prev) => ({
                ...prev,
                department_id: String(val || ""),
              }))
            }
            options={departmentOptions}
            isLoading={deptDD.isLoading}
            hasMore={deptDD.hasMore}
            onLoadMore={deptDD.loadMore}
            onSearch={deptDD.setSearch}
            placeholder={
              selectedFaculty ? "Select department" : "Select faculty first"
            }
            inputClassName={selectCls}
            disabled={!selectedFaculty || isBusy}
          />
        </div>

        <div className="min-w-0">
          <label className={labelCls}>
            Current semester <span className="text-ds-error">*</span>
          </label>
          <AsyncDropdown
            value={form.semester_id}
            onChange={(val) => {
              setFormError("");
              setForm((prev) => ({
                ...prev,
                semester_id: String(val || ""),
              }));
            }}
            options={semesterOptions}
            isLoading={semesterDD.isLoading}
            hasMore={semesterDD.hasMore}
            onLoadMore={semesterDD.loadMore}
            onSearch={semesterDD.setSearch}
            placeholder="Select semester"
            inputClassName={selectCls}
            disabled={isBusy}
          />
        </div>

        <div className="flex items-start gap-3 pt-1">
          <input
            type="checkbox"
            id="terms"
            name="accept_terms"
            checked={form.accept_terms}
            onChange={onChange}
            className="mt-0.5 h-4 w-4 shrink-0 rounded border-ds-border text-ds-action focus:ring-ds-action/20"
            disabled={isBusy}
          />
          <label htmlFor="terms" className="text-sm text-ds-text-secondary">
            I agree to the{" "}
            <Link
              href="/terms"
              className="font-semibold text-ds-action hover:underline"
            >
              Terms
            </Link>{" "}
            and{" "}
            <Link
              href="/privacy"
              className="font-semibold text-ds-action hover:underline"
            >
              Privacy Policy
            </Link>
            .
          </label>
        </div>

        <button
          type="submit"
          disabled={isSubmitDisabled}
          aria-disabled={isSubmitDisabled}
          aria-busy={isBusy}
          className={
            "mt-1 flex w-full min-h-11 shrink-0 items-center justify-center rounded-lg text-sm font-semibold " +
            "visible opacity-100 focus:outline-none focus:ring-4 focus:ring-ds-action/20 " +
            (isSubmitDisabled
              ? "cursor-not-allowed border border-ds-border bg-ds-surface-hover text-ds-text-muted"
              : "border border-transparent bg-ds-action text-white hover:bg-ds-action-hover")
          }
        >
          {isBusy ? "Creating account..." : "Create account"}
        </button>
      </form>
    </div>
  );
};

export default SignUpForm;
