"use client";

import Link from "next/link";
import { useState } from "react";
import toast from "react-hot-toast";
import ThemeController from "@/components/shared/others/ThemeController";
import { useSubmitContact } from "@/features/contact/hooks";
import { getApiErrorMessage } from "@/lib/apiErrors";

const labelCls =
  "block text-[12.5px] font-medium text-ds-text-secondary mb-1.5";
const inputCls =
  "w-full h-11 rounded-lg border border-ds-border " +
  "bg-ds-surface-input px-3.5 text-sm text-ds-text-primary " +
  "placeholder:text-ds-text-muted " +
  "focus:outline-none focus:border-ds-action/50 focus:ring-4 focus:ring-ds-action/10 transition";

export default function ContactPage() {
  const submitMut = useSubmitContact();
  const [form, setForm] = useState({
    name: "",
    email: "",
    subject: "",
    message: "",
  });
  const [formError, setFormError] = useState("");
  const [sent, setSent] = useState(false);

  const onChange = (e) => {
    const { name, value } = e.target;
    setFormError("");
    setForm((p) => ({ ...p, [name]: value }));
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setFormError("");

    if (!form.name.trim() || !form.email.trim() || !form.subject.trim() || !form.message.trim()) {
      setFormError("Please complete all fields.");
      return;
    }

    try {
      await submitMut.mutateAsync({
        name: form.name.trim(),
        email: form.email.trim(),
        subject: form.subject.trim(),
        message: form.message.trim(),
      });
      setSent(true);
      toast.success("Message sent.");
    } catch (err) {
      const msg = getApiErrorMessage(err, "Could not send your message.");
      setFormError(msg);
      toast.error(msg);
    }
  };

  return (
    <main className="bg-ds-page min-h-[70vh]">
      <ThemeController />
      <div className="mx-auto w-full max-w-xl px-6 sm:px-8 py-12 md:py-16">
        <p className="text-sm font-semibold text-ds-action mb-2">JustClick</p>
        <h1 className="text-3xl font-semibold tracking-tight text-ds-text-primary">
          Contact us
        </h1>
        <p className="mt-2 text-sm text-ds-text-muted">
          Send a message to the JustClick team. You can also email{" "}
          <a
            href="mailto:justclick.cmc@gmail.com"
            className="font-semibold text-ds-action hover:underline"
          >
            justclick.cmc@gmail.com
          </a>
          .
        </p>

        {sent ? (
          <div className="mt-8 space-y-4">
            <div className="rounded-xl border border-ds-action/25 bg-ds-action/10 px-4 py-3 text-sm text-ds-text-primary">
              Thanks — your message has been received. We will get back to you
              when we can.
            </div>
            <Link
              href="/"
              className="inline-flex h-11 items-center justify-center rounded-lg bg-ds-action px-5 text-sm font-semibold text-white hover:bg-ds-action-hover"
            >
              Back to home
            </Link>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="mt-8 space-y-3.5">
            {formError ? (
              <div
                role="alert"
                className="rounded-xl border border-ds-error/30 bg-ds-error/10 px-4 py-3 text-sm text-ds-error"
              >
                {formError}
              </div>
            ) : null}

            <div>
              <label className={labelCls} htmlFor="name">
                Name <span className="text-ds-error">*</span>
              </label>
              <input
                id="name"
                name="name"
                value={form.name}
                onChange={onChange}
                className={inputCls}
                disabled={submitMut.isPending}
              />
            </div>

            <div>
              <label className={labelCls} htmlFor="email">
                Email <span className="text-ds-error">*</span>
              </label>
              <input
                id="email"
                name="email"
                type="email"
                value={form.email}
                onChange={onChange}
                className={inputCls}
                disabled={submitMut.isPending}
              />
            </div>

            <div>
              <label className={labelCls} htmlFor="subject">
                Subject <span className="text-ds-error">*</span>
              </label>
              <input
                id="subject"
                name="subject"
                value={form.subject}
                onChange={onChange}
                className={inputCls}
                disabled={submitMut.isPending}
              />
            </div>

            <div>
              <label className={labelCls} htmlFor="message">
                Message <span className="text-ds-error">*</span>
              </label>
              <textarea
                id="message"
                name="message"
                rows={5}
                value={form.message}
                onChange={onChange}
                className="w-full rounded-lg border border-ds-border bg-ds-surface-input px-3.5 py-3 text-sm text-ds-text-primary placeholder:text-ds-text-muted focus:outline-none focus:border-ds-action/50 focus:ring-4 focus:ring-ds-action/10 transition"
                disabled={submitMut.isPending}
              />
            </div>

            <button
              type="submit"
              disabled={submitMut.isPending}
              className={`w-full h-11 rounded-lg text-white text-sm font-semibold transition ${
                submitMut.isPending
                  ? "bg-ds-action/60 cursor-not-allowed"
                  : "bg-ds-action hover:bg-ds-action-hover"
              }`}
            >
              {submitMut.isPending ? "Sending..." : "Send message"}
            </button>
          </form>
        )}
      </div>
    </main>
  );
}
