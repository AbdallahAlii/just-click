import { Check, X } from "lucide-react";
import SectionHeader from "@/components/sections/landing/SectionHeader";

const pain = [
  "Materials buried in chat history",
  "Different versions, no single source",
  "Hard to find the right file when exams approach",
];

const gain = [
  "One verified repository for your department",
  "Organized by semester → course → chapter",
  "Searchable materials with AI-assisted learning",
];

const ProblemFix = () => {
  return (
    <section id="problem" className="bg-ds-surface-secondary py-16 sm:py-20 lg:py-24">
      <div className="container">
        <SectionHeader
          eyebrow="Problem & solution"
          title="From chat-group chaos to one trusted portal"
          description="JustClick replaces scattered WhatsApp files with a structured learning hub — built for your department, with AI help on every material."
        />

        <div className="grid gap-6 lg:grid-cols-2 lg:gap-8">
          <div className="rounded-2xl border border-ds-border bg-ds-surface p-6 sm:p-8">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-ds-error">
              The problem
            </p>
            <h3 className="mb-6 text-xl font-semibold text-ds-text-primary sm:text-2xl">
              WhatsApp chaos ends here.
            </h3>
            <ul className="space-y-4">
              {pain.map((text) => (
                <li key={text} className="flex items-start gap-3">
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-ds-error/10 text-ds-error">
                    <X className="h-3.5 w-3.5" aria-hidden="true" />
                  </span>
                  <span className="text-ds-text-secondary">{text}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-2xl border border-ds-border bg-ds-surface p-6 sm:p-8">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-ds-success">
              The fix
            </p>
            <h3 className="mb-6 text-xl font-semibold text-ds-text-primary sm:text-2xl">
              One portal, all materials.
            </h3>
            <ul className="space-y-4">
              {gain.map((text) => (
                <li key={text} className="flex items-start gap-3">
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-ds-success/10 text-ds-success">
                    <Check className="h-3.5 w-3.5" aria-hidden="true" />
                  </span>
                  <span className="text-ds-text-secondary">{text}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
};

export default ProblemFix;
