import Link from "next/link";
import { Check, GraduationCap, Shield } from "lucide-react";
import SectionHeader from "@/components/sections/landing/SectionHeader";

const studentItems = [
  "Materials organized for your semester and department",
  "Search and filter by course or chapter",
  "Save favorites for quick access",
  "Download files you need",
  "Ask JustClick AI about any material",
];

const adminItems = [
  "Upload materials (PDF, PPT, DOC, video, links)",
  "Organize by semester, course, and chapter",
  "Manage faculty and department structure",
  "Review and approve student registrations",
  "Keep one official source for your department",
];

const RoleCard = ({ icon: Icon, title, items, href, linkLabel }) => (
  <article className="flex h-full flex-col rounded-2xl border border-ds-border bg-ds-surface p-6 sm:p-8">
    <div className="mb-6 flex items-center gap-3">
      <span className="flex h-11 w-11 items-center justify-center rounded-xl border border-ds-border bg-ds-surface-secondary text-ds-action">
        <Icon className="h-5 w-5" aria-hidden="true" />
      </span>
      <h3 className="text-xl font-semibold text-ds-text-primary sm:text-2xl">
        {title}
      </h3>
    </div>

    <ul className="flex-1 space-y-3.5">
      {items.map((text) => (
        <li key={text} className="flex items-start gap-3">
          <Check
            className="mt-0.5 h-4 w-4 shrink-0 text-ds-action"
            aria-hidden="true"
          />
          <span className="text-ds-text-secondary">{text}</span>
        </li>
      ))}
    </ul>

    <div className="mt-8">
      <Link
        href={href}
        className="inline-flex items-center gap-1.5 text-sm font-semibold text-ds-action transition-colors hover:text-ds-action-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action focus-visible:ring-offset-2 rounded-md"
      >
        {linkLabel}
        <span aria-hidden="true">→</span>
      </Link>
    </div>
  </article>
);

const UserRoles = () => {
  return (
    <section id="roles" className="bg-ds-surface-secondary py-16 sm:py-20 lg:py-24">
      <div className="container">
        <SectionHeader
          eyebrow="Who it's for"
          title="Built for students and department admins"
          description="Students get organized materials and AI help. Admins upload and manage resources for their university department."
        />

        <div className="grid gap-6 lg:grid-cols-2 lg:gap-8">
          <RoleCard
            icon={GraduationCap}
            title="For Students"
            items={studentItems}
            href="/signup"
            linkLabel="Create student account"
          />
          <RoleCard
            icon={Shield}
            title="For Admins"
            items={adminItems}
            href="/login"
            linkLabel="Admin sign in"
          />
        </div>
      </div>
    </section>
  );
};

export default UserRoles;
