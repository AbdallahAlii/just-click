"use client";

import MobileMenuClose from "@/components/shared/buttons/MobileMenuClose";
import MobileMenuSimple from "./MobileMenuSimple";

const MobileMenu = () => {
  return (
    <div
      id="mobile-menu"
      className="
        mobile-menu
        fixed top-0 right-0 h-full
        w-[280px] md:w-[330px]
        bg-ds-surface
        border-l border-ds-border
        shadow-lg
        z-high
        transform translate-x-full
        transition-transform duration-300
        lg:hidden
      "
    >
      <MobileMenuClose />

      <div className="h-full overflow-y-auto px-5 pb-12 pt-5 md:px-8 md:pt-8">
        <MobileMenuSimple />
      </div>
    </div>
  );
};

export default MobileMenu;
