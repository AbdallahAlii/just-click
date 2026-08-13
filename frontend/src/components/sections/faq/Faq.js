"use client";

import { ChevronDown } from "lucide-react";
import { useState } from "react";
import SectionHeader from "@/components/sections/landing/SectionHeader";

const faqs = [
  {
    question: "Is it really free for students?",
    answer:
      "Yes. Students can create an account and access approved materials published by their department admin.",
  },
  {
    question: "Do I need internet all the time?",
    answer:
      "Yes — you need internet to browse the portal and use JustClick AI. If you download a file, you can open that saved copy offline later.",
  },
  {
    question: "How does JustClick AI work?",
    answer:
      "Open any material and use the AI assistant to summarize content, generate quiz questions, or ask about what you are reading. Answers are based on that material's uploaded files.",
  },
  {
    question: "Who uploads the materials?",
    answer:
      "Department admins upload and organize official materials for their faculty and department. Students access what is published for their semester.",
  },
  {
    question: "How do I get access after registering?",
    answer:
      "After you verify your email, a department admin reviews and approves your account. Once approved, you can sign in and browse materials.",
  },
];

const Faq = () => {
  const [openIndex, setOpenIndex] = useState(0);

  return (
    <section id="faq" className="bg-ds-surface-secondary py-16 sm:py-20 lg:py-24">
      <div className="container">
        <div className="mx-auto max-w-3xl">
          <SectionHeader
            eyebrow="FAQ"
            title="Common questions"
            description="Quick answers about access, materials, and JustClick AI."
          />

          <div className="space-y-3">
            {faqs.map((faq, index) => {
              const isOpen = openIndex === index;
              const panelId = `faq-panel-${index}`;
              const buttonId = `faq-button-${index}`;

              return (
                <div
                  key={faq.question}
                  className="overflow-hidden rounded-xl border border-ds-border bg-ds-surface"
                >
                  <button
                    id={buttonId}
                    type="button"
                    aria-expanded={isOpen}
                    aria-controls={panelId}
                    onClick={() => setOpenIndex(isOpen ? null : index)}
                    className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition-colors hover:bg-ds-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ds-action sm:px-6 sm:py-5"
                  >
                    <span className="text-base font-semibold text-ds-text-primary sm:text-lg">
                      {faq.question}
                    </span>
                    <ChevronDown
                      className={`h-5 w-5 shrink-0 text-ds-text-muted transition-transform duration-200 ${
                        isOpen ? "rotate-180" : ""
                      }`}
                      aria-hidden="true"
                    />
                  </button>

                  <div
                    id={panelId}
                    role="region"
                    aria-labelledby={buttonId}
                    className={`grid transition-[grid-template-rows] duration-200 ease-out ${
                      isOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
                    }`}
                  >
                    <div className="overflow-hidden">
                      <p className="px-5 pb-5 text-ds-text-secondary leading-relaxed sm:px-6">
                        {faq.answer}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
};

export default Faq;
