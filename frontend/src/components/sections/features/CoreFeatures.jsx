import {
  Download,
  FolderTree,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import SectionHeader from "@/components/sections/landing/SectionHeader";

const features = [
  {
    icon: FolderTree,
    title: "Smart Organization",
    description: "Faculty → Department → Semester → Course → Chapter.",
  },
  {
    icon: Sparkles,
    title: "JustClick AI Assistant",
    description:
      "Summarize a chapter, generate quiz questions, or ask about any uploaded material.",
  },
  {
    icon: ShieldCheck,
    title: "Verified Uploads",
    description:
      "Department admins publish official materials — one trusted source for students.",
  },
  {
    icon: Download,
    title: "Easy Downloads",
    description:
      "Download PDFs and files you need. Keep them on your device for later review.",
  },
];

const CoreFeatures = () => {
  return (
    <section id="features" className="bg-ds-page py-16 sm:py-20 lg:py-24">
      <div className="container">
        <SectionHeader
          eyebrow="Core features"
          title="Everything you need, nothing you don't"
          description="Clean, fast, and focused — centralized materials for your department with AI help when you need it."
        />

        <div className="grid gap-5 sm:grid-cols-2 lg:gap-6">
          {features.map(({ icon: Icon, title, description }) => (
            <article
              key={title}
              className="rounded-2xl border border-ds-border bg-ds-surface p-6 sm:p-7"
            >
              <span className="mb-5 flex h-11 w-11 items-center justify-center rounded-xl border border-ds-border bg-ds-surface-secondary text-ds-action">
                <Icon className="h-5 w-5" aria-hidden="true" />
              </span>
              <h3 className="text-lg font-semibold text-ds-text-primary sm:text-xl">
                {title}
              </h3>
              <p className="mt-2 text-ds-text-secondary leading-relaxed">
                {description}
              </p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
};

export default CoreFeatures;
