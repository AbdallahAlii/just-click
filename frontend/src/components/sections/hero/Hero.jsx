import ButtonPrimary from "@/components/shared/buttons/ButtonPrimary";
import ProductPreview from "@/components/sections/hero/ProductPreview";
import { CheckCircle2, FolderOpen, Sparkles } from "lucide-react";

const benefits = [
  { icon: FolderOpen, text: "Department materials" },
  { icon: Sparkles, text: "AI study assistant" },
  { icon: CheckCircle2, text: "Admin-verified uploads" },
];

const Hero = () => {
  return (
    <section id="top" className="relative overflow-hidden bg-ds-page">
      <div className="container relative pt-28 pb-16 sm:pt-32 sm:pb-20 lg:pt-36 lg:pb-24">
        <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-14 xl:gap-16">
          <div>
            <span className="mb-4 inline-flex items-center rounded-lg border border-ds-border bg-ds-surface px-3 py-1 text-xs font-semibold uppercase tracking-wider text-ds-action">
              Centralized class materials portal
            </span>

            <h1 className="max-w-xl text-4xl font-bold tracking-tight text-ds-text-primary sm:text-5xl lg:text-[3.25rem] lg:leading-[1.15]">
              All your course materials. One place.
            </h1>

            <p className="mt-5 max-w-xl text-base leading-relaxed text-ds-text-secondary sm:text-lg">
              Slides, notes, and department resources organized by semester and
              course — with JustClick AI to summarize, quiz you, or explain any
              uploaded material. No more digging through chat groups.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <ButtonPrimary path="/signup">Create free account</ButtonPrimary>
              <ButtonPrimary variant="secondary" path="/login">
                Log in
              </ButtonPrimary>
            </div>

            <ul className="mt-8 flex flex-wrap gap-x-6 gap-y-3">
              {benefits.map(({ icon: Icon, text }) => (
                <li
                  key={text}
                  className="flex items-center gap-2 text-sm text-ds-text-secondary"
                >
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-ds-border bg-ds-surface text-ds-action">
                    <Icon className="h-4 w-4" aria-hidden="true" />
                  </span>
                  {text}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <ProductPreview />
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;
