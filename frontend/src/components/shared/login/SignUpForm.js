"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import toast from "react-hot-toast";
import { FiInfo, FiMail, FiUser } from "react-icons/fi";
import { HiOutlineIdentification } from "react-icons/hi";

import AsyncDropdown from "@/components/shared/inputs/AsyncDropdown";
import { useRegisterStudent } from "@/features/signup/hooks";
import { getApiErrorMessage, isValidEmail } from "@/lib/apiErrors";
import { useDropdown } from "@/hooks/dropdown/useDropdown";

const SignUpForm = () => {
  const router = useRouter();
  const registerMut = useRegisterStudent();

  const [selectedFaculty, setSelectedFaculty] = useState("");

  const [form, setForm] = useState({
    student_id: "",
    full_name: "",
    student_email: "",
    department_id: "",
    semester_id: "",
    accept_terms: false,
  });
  const [formError, setFormError] = useState("");

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
    !!selectedFaculty &&
    !!form.department_id &&
    !!form.semester_id &&
    !!form.accept_terms;

  const isSubmitting = registerMut.isPending;
  const isSubmitDisabled = !isFormValid || isSubmitting;

  const onSubmit = async (e) => {
    e.preventDefault();
    setFormError("");

    if (isSubmitting) return;

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

    try {
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
    }
  };

  const labelCls =
    "block text-[13px] font-semibold text-gray-700 dark:text-gray-300 mb-2";

  const inputWrap =
    "relative group rounded-2xl border border-gray-200 dark:border-gray-700 " +
    "bg-white/70 dark:bg-gray-900/40 " +
    "transition overflow-hidden " +
    "focus-within:border-primaryColor/40 focus-within:ring-4 focus-within:ring-primaryColor/10";

  const inputCls =
    "w-full h-12 pl-12 pr-4 text-sm bg-transparent outline-none " +
    "text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500";

  const iconCls =
    "absolute left-4 top-1/2 -translate-y-1/2 text-[20px] text-gray-400 " +
    "transition group-focus-within:text-primaryColor";

  const selectCls =
    "w-full h-12 px-4 text-sm rounded-2xl border border-gray-200 dark:border-gray-700 " +
    "bg-white/70 dark:bg-gray-900/40 text-gray-900 dark:text-white " +
    "focus:outline-none focus:border-primaryColor/40 focus:ring-4 focus:ring-primaryColor/10 transition appearance-none";

  return (
    <div className="transition-all duration-150 ease-linear">
      <div className="text-center mb-7">
        <h2 className="text-2xl md:text-3xl font-semibold text-gray-900 dark:text-white tracking-tight">
          Create account
        </h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Already registered?{" "}
          <Link
            href="/login"
            className="text-primaryColor font-semibold hover:underline"
          >
            Sign in
          </Link>
        </p>
      </div>

      <div className="mb-7 px-4 py-3 rounded-2xl border border-primaryColor/15 bg-primaryColor/5 flex items-start gap-3">
        <FiInfo className="text-primaryColor text-lg mt-0.5 flex-shrink-0" />
        <p className="text-sm text-gray-700 dark:text-gray-200">
          No password needed – we&apos;ll email you a secure link to activate
          your account.
        </p>
      </div>

      {formError ? (
        <div
          role="alert"
          className="mb-5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-300"
        >
          {formError}
        </div>
      ) : null}

      <form onSubmit={onSubmit} className="space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="md:col-span-2">
            <label className={labelCls}>
              Student ID <span className="text-red-400">*</span>
            </label>
            <div className={inputWrap}>
              <HiOutlineIdentification className={iconCls} />
              <input
                name="student_id"
                value={form.student_id}
                onChange={onChange}
                type="text"
                placeholder="C123456"
                className={inputCls}
                disabled={isSubmitting}
              />
            </div>
          </div>

          <div className="md:col-span-3">
            <label className={labelCls}>
              Full name <span className="text-red-400">*</span>
            </label>
            <div className={inputWrap}>
              <FiUser className={iconCls} />
              <input
                name="full_name"
                value={form.full_name}
                onChange={onChange}
                type="text"
                placeholder="Falastiin Ahmed"
                className={inputCls}
                disabled={isSubmitting}
              />
            </div>
          </div>
        </div>

        <div>
          <label className={labelCls}>
            Student email <span className="text-red-400">*</span>
          </label>
          <div className={inputWrap}>
            <FiMail className={iconCls} />
            <input
              name="student_email"
              value={form.student_email}
              onChange={onChange}
              type="email"
              placeholder="student@university.edu"
              className={inputCls}
              disabled={isSubmitting}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className={labelCls}>
              Faculty <span className="text-red-400">*</span>
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
              disabled={isSubmitting}
            />
          </div>

          <div>
            <label className={labelCls}>
              Department <span className="text-red-400">*</span>
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
              disabled={!selectedFaculty || isSubmitting}
            />
          </div>
        </div>

        <div>
          <label className={labelCls}>
            Current semester <span className="text-red-400">*</span>
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
            disabled={isSubmitting}
          />
        </div>

        <div className="flex items-start gap-3 pt-1">
          <input
            type="checkbox"
            id="terms"
            name="accept_terms"
            checked={form.accept_terms}
            onChange={onChange}
            className="w-5 h-5 mt-0.5 rounded-md border-gray-300 text-primaryColor focus:ring-primaryColor/20"
            disabled={isSubmitting}
          />
          <label
            htmlFor="terms"
            className="text-sm text-gray-600 dark:text-gray-400"
          >
            I agree to the{" "}
            <Link
              href="/terms"
              className="text-ds-action font-semibold hover:underline"
            >
              Terms
            </Link>{" "}
            and{" "}
            <Link
              href="/privacy"
              className="text-ds-action font-semibold hover:underline"
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
          className={
            "w-full h-12 rounded-2xl text-white text-sm font-semibold transition shadow-sm focus:outline-none focus:ring-4 " +
            (isSubmitDisabled
              ? "bg-gray-300 dark:bg-gray-700 cursor-not-allowed focus:ring-gray-200"
              : "bg-primaryColor hover:bg-primaryColor/90 focus:ring-primaryColor/20")
          }
        >
          {isSubmitting ? "Submitting..." : "Create account"}
        </button>
      </form>
    </div>
  );
};

export default SignUpForm;
