"use client";

import Link from "next/link";

const variants = {
  primary:
    "bg-ds-action text-white border-transparent hover:bg-ds-action-hover shadow-sm",
  secondary:
    "bg-ds-surface text-ds-text-primary border-ds-border hover:bg-ds-surface-hover",
  ghost:
    "bg-transparent text-ds-text-primary border-transparent hover:bg-ds-surface-hover",
};

const sizes = {
  sm: "min-h-10 px-4 text-sm",
  md: "min-h-11 px-5 text-sm sm:min-h-12 sm:px-6",
};

const ButtonPrimary = ({
  children,
  color,
  variant,
  type,
  path,
  arrow,
  width,
  onClick,
  disabled = false,
  className = "",
  size = "md",
}) => {
  const resolvedVariant =
    variant || (color === "secondary" ? "secondary" : "primary");

  const baseClasses = [
    "inline-flex items-center justify-center gap-2 rounded-xl border font-semibold",
    "transition-colors duration-200",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action focus-visible:ring-offset-2",
    "dark:focus-visible:ring-offset-ds-page",
    "disabled:pointer-events-none disabled:opacity-50",
    sizes[size] || sizes.md,
    variants[resolvedVariant] || variants.primary,
    width === "full" ? "w-full" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  const content = (
    <>
      {children}
      {arrow ? <i className="icofont-long-arrow-right" aria-hidden="true" /> : null}
    </>
  );

  if (type === "button" || type === "submit") {
    return (
      <button
        type={type === "submit" ? "submit" : "button"}
        onClick={onClick || undefined}
        disabled={disabled}
        className={baseClasses}
      >
        {content}
      </button>
    );
  }

  return (
    <Link className={baseClasses} href={path || "/"}>
      {content}
    </Link>
  );
};

export default ButtonPrimary;
