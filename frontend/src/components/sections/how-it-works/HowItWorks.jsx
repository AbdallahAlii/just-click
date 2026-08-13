import { BookOpen, Sparkles, UserPlus } from "lucide-react";
import SectionHeader from "@/components/sections/landing/SectionHeader";

const steps = [
  {
    number: "01",
    icon: UserPlus,
    title: "Create your account",
    description:
      "Register with your student ID, verify your email, and wait for admin approval.",
  },
  {
    number: "02",
    icon: BookOpen,
    title: "Browse your materials",
    description:
      "Open your department portal — materials are filtered by semester and course.",
  },
  {
    number: "03",
    icon: Sparkles,
    title: "Study with JustClick AI",
    description:
      "Read, download, and ask AI to summarize, quiz you, or explain concepts from uploaded files.",
  },
];

const HowItWorks = () => {
  return (
    <section id="how" className="bg-ds-page py-16 sm:py-20 lg:py-24">
      <div className="container">
        <SectionHeader
          eyebrow="How it works"
          title="From signup to smarter studying"
          description="Three clear steps to get from registration to studying with JustClick AI."
        />

        <ol className="relative grid gap-6 md:grid-cols-3 md:gap-8">
          {steps.map(({ number, icon: Icon, title, description }) => (
            <li
              key={title}
              className="relative rounded-2xl border border-ds-border bg-ds-surface p-6 sm:p-7"
            >
              <div className="mb-5 flex items-center justify-between">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl border border-ds-border bg-ds-surface-secondary text-ds-action">
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </span>
                <span className="text-sm font-semibold tabular-nums text-ds-text-muted">
                  {number}
                </span>
              </div>
              <h3 className="text-lg font-semibold text-ds-text-primary sm:text-xl">
                {title}
              </h3>
              <p className="mt-2 text-ds-text-secondary leading-relaxed">
                {description}
              </p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
};

export default HowItWorks;
