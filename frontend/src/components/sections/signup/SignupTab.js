"use client";

import Link from "next/link";
import SignUpForm from "@/components/shared/login/SignUpForm";

const SignupTab = () => {
  return (
    <section className="bg-ds-page">
      <div className="mx-auto flex min-h-[calc(100vh-8rem)] w-full max-w-lg flex-col justify-center px-6 py-12 sm:px-8 md:min-h-[calc(100vh-10rem)] md:py-16">
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
          <p className="mt-2 text-sm text-ds-text-muted">
            Create your student account to access class materials
          </p>
        </div>

        <div className="rounded-2xl border border-ds-border bg-ds-surface p-6 sm:p-8 shadow-sm">
          <SignUpForm />
        </div>

        <p className="mt-6 text-center text-xs text-ds-text-muted">
          By continuing you agree to our{" "}
          <Link href="/terms" className="font-semibold text-ds-action hover:underline">
            Terms
          </Link>{" "}
          and{" "}
          <Link href="/privacy" className="font-semibold text-ds-action hover:underline">
            Privacy
          </Link>
          .
        </p>
      </div>
    </section>
  );
};

export default SignupTab;
