import {
  BookOpen,
  FileText,
  MessageSquare,
  Search,
  Sparkles,
} from "lucide-react";

const navItems = [
  { label: "Semester 1", active: false },
  { label: "Computer Networks", active: true },
  { label: "Chapter 3 — Routing", active: false },
];

const materials = [
  { title: "Lecture 03 — Routing Basics.pdf", meta: "PDF · 2.4 MB" },
  { title: "Lab Sheet — OSPF Config.docx", meta: "DOC · 860 KB" },
  { title: "Week 3 Slides.pptx", meta: "PPT · 4.1 MB" },
];

const ProductPreview = () => {
  return (
    <div
      className="relative w-full overflow-hidden rounded-2xl border border-ds-border bg-ds-surface shadow-sm"
      aria-hidden="true"
    >
      {/* Browser chrome */}
      <div className="flex items-center gap-2 border-b border-ds-border bg-ds-surface-secondary px-4 py-3">
        <span className="h-2.5 w-2.5 rounded-full bg-ds-border" />
        <span className="h-2.5 w-2.5 rounded-full bg-ds-border" />
        <span className="h-2.5 w-2.5 rounded-full bg-ds-border" />
        <div className="ml-2 flex flex-1 items-center gap-2 rounded-lg border border-ds-border bg-ds-surface px-3 py-1.5 text-xs text-ds-text-muted">
          <Search className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">justclick.app / materials</span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-[140px_1fr] lg:grid-cols-[160px_1fr_150px]">
        {/* Sidebar nav */}
        <aside className="hidden border-r border-ds-border bg-ds-surface-secondary p-3 sm:block">
          <p className="mb-3 px-2 text-[10px] font-semibold uppercase tracking-wider text-ds-text-muted">
            Browse
          </p>
          <ul className="space-y-1">
            {navItems.map((item) => (
              <li key={item.label}>
                <div
                  className={`rounded-lg px-2.5 py-2 text-xs font-medium ${
                    item.active
                      ? "bg-ds-action/10 text-ds-action"
                      : "text-ds-text-secondary"
                  }`}
                >
                  {item.label}
                </div>
              </li>
            ))}
          </ul>
        </aside>

        {/* Materials list */}
        <div className="p-4">
          <div className="mb-4 flex items-center justify-between gap-2">
            <div>
              <p className="text-sm font-semibold text-ds-text-primary">
                Course materials
              </p>
              <p className="text-xs text-ds-text-muted">
                Faculty → Dept → Semester → Course
              </p>
            </div>
            <BookOpen className="h-4 w-4 text-ds-action" />
          </div>

          <ul className="space-y-2">
            {materials.map((item) => (
              <li
                key={item.title}
                className="flex items-center gap-3 rounded-xl border border-ds-border bg-ds-page px-3 py-2.5"
              >
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-ds-action/10 text-ds-action">
                  <FileText className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-semibold text-ds-text-primary sm:text-sm">
                    {item.title}
                  </p>
                  <p className="text-[11px] text-ds-text-muted">{item.meta}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        {/* AI panel */}
        <aside className="hidden border-l border-ds-border bg-ds-surface-secondary p-3 lg:block">
          <div className="mb-3 flex items-center gap-1.5 text-xs font-semibold text-ds-text-primary">
            <Sparkles className="h-3.5 w-3.5 text-ds-action" />
            JustClick AI
          </div>
          <div className="space-y-2">
            <div className="rounded-lg border border-ds-border bg-ds-surface p-2.5 text-[11px] leading-relaxed text-ds-text-secondary">
              Summarize Chapter 3 routing concepts.
            </div>
            <div className="rounded-lg bg-ds-action/10 p-2.5 text-[11px] leading-relaxed text-ds-text-primary">
              Routing forwards packets between networks using tables and
              protocols like OSPF…
            </div>
            <div className="flex items-center gap-1.5 rounded-lg border border-ds-border bg-ds-surface px-2.5 py-2 text-[11px] text-ds-text-muted">
              <MessageSquare className="h-3 w-3" />
              Ask about this material…
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
};

export default ProductPreview;
