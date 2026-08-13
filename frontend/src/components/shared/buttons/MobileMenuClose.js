const MobileMenuClose = () => {
  return (
    <button
      type="button"
      aria-label="Close menu"
      className="close-mobile-menu absolute top-0 right-full hidden bg-ds-text-primary px-[11px] py-[6px] text-lg text-white transition-colors hover:bg-ds-action"
    >
      <i className="icofont icofont-close-line" aria-hidden="true"></i>
    </button>
  );
};

export default MobileMenuClose;
