import Link from "next/link";
import ThemeController from "@/components/shared/others/ThemeController";

export const metadata = {
  title: "Registration submitted | JustClick",
  description: "Check your email to verify your JustClick student account.",
};

export default function SignupSuccessPage({ searchParams }) {
  const message =
    searchParams?.message ||
    "Registration submitted. Please check your university email.";
  const email = searchParams?.email || "";
  const status = searchParams?.status || "";
  const studentId = searchParams?.student_id || "";

  return (
    <main className="bg-ds-page">
      <ThemeController />
      <section className="mx-auto flex min-h-[calc(100vh-8rem)] w-full max-w-md flex-col justify-center px-6 py-12 sm:px-8 md:min-h-[calc(100vh-10rem)] md:py-16">
        <div className="mb-8 text-center">
          <Link
            href="/"
            className="inline-flex items-center justify-center rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action"
          >
            <span className="text-3xl font-bold tracking-tight">
              <span className="text-ds-text-primary">Just</span>
              <span className="text-ds-action">Click</span>
            </span>
          </Link>
        </div>

        <div className="rounded-2xl border border-ds-border bg-ds-surface p-6 sm:p-8 shadow-sm">
          <h1 className="text-xl font-semibold text-ds-text-primary">
            Check your email
          </h1>
          <p className="mt-2 text-sm text-ds-text-muted">{message}</p>

          <div className="mt-5 space-y-2 text-sm">
            {email ? (
              <div className="flex justify-between gap-3">
                <span className="text-ds-text-muted">Email</span>
                <span className="font-medium text-ds-text-primary">{email}</span>
              </div>
            ) : null}
            {studentId ? (
              <div className="flex justify-between gap-3">
                <span className="text-ds-text-muted">Student ID</span>
                <span className="font-medium text-ds-text-primary">{studentId}</span>
              </div>
            ) : null}
            {status ? (
              <div className="flex justify-between gap-3">
                <span className="text-ds-text-muted">Status</span>
                <span className="font-medium text-ds-text-primary">{status}</span>
              </div>
            ) : null}
          </div>

          <div className="mt-6 space-y-3">
            <Link
              href="/login"
              className="inline-flex h-11 w-full items-center justify-center rounded-lg bg-ds-action text-sm font-semibold text-white hover:bg-ds-action-hover transition"
            >
              Go to login
            </Link>
            <Link
              href="/"
              className="inline-flex h-11 w-full items-center justify-center rounded-lg border border-ds-border text-sm font-semibold text-ds-text-primary hover:bg-ds-surface-hover transition"
            >
              Back home
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
