const SectionHeader = ({
  eyebrow,
  title,
  description,
  align = "center",
  className = "",
}) => {
  const alignment =
    align === "left" ? "text-left items-start" : "text-center items-center mx-auto";

  return (
    <div
      className={`mb-10 flex max-w-2xl flex-col md:mb-14 ${alignment} ${className}`}
    >
      {eyebrow ? (
        <span className="mb-3 inline-flex items-center rounded-lg border border-ds-border bg-ds-surface px-3 py-1 text-xs font-semibold uppercase tracking-wider text-ds-action">
          {eyebrow}
        </span>
      ) : null}
      <h2 className="text-3xl font-bold tracking-tight text-ds-text-primary sm:text-4xl">
        {title}
      </h2>
      {description ? (
        <p className="mt-4 text-base leading-relaxed text-ds-text-secondary sm:text-lg">
          {description}
        </p>
      ) : null}
    </div>
  );
};

export default SectionHeader;
