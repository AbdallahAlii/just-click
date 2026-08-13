import Link from "next/link";
import ThemeController from "@/components/shared/others/ThemeController";

export default function LegalPageShell({ title, subtitle, children }) {
  return (
    <main className="bg-ds-page min-h-[70vh]">
      <ThemeController />
      <div className="mx-auto w-full max-w-3xl px-6 sm:px-8 py-12 md:py-16">
        <p className="text-sm font-semibold text-ds-action mb-2">JustClick</p>
        <h1 className="text-3xl font-semibold tracking-tight text-ds-text-primary">
          {title}
        </h1>
        {subtitle ? (
          <p className="mt-2 text-sm text-ds-text-muted">{subtitle}</p>
        ) : null}
        <div className="mt-8 space-y-5 text-[15px] leading-relaxed text-ds-text-secondary">
          {children}
        </div>
        <div className="mt-10 flex flex-wrap gap-4 text-sm font-semibold">
          <Link href="/privacy" className="text-ds-action hover:underline">
            Privacy
          </Link>
          <Link href="/terms" className="text-ds-action hover:underline">
            Terms
          </Link>
          <Link href="/contact" className="text-ds-action hover:underline">
            Contact
          </Link>
          <Link href="/" className="text-ds-text-muted hover:text-ds-action">
            Home
          </Link>
        </div>
      </div>
    </main>
  );
}
