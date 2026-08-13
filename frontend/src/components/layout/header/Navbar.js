"use client";

import { useEffect, useState } from "react";
import NavbarLogo from "./NavbarLogo";
import NavbarRight from "./NavbarRight";

const Navbar = () => {
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 24);
    };
    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <div
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-200 ${
        isScrolled
          ? "border-b border-ds-border bg-ds-surface/90 py-3 backdrop-blur-md"
          : "border-b border-transparent bg-transparent py-4"
      }`}
    >
      <div className="container">
        <div className="flex items-center justify-between gap-4">
          <NavbarLogo />
          <NavbarRight />
        </div>
      </div>
    </div>
  );
};

export default Navbar;
