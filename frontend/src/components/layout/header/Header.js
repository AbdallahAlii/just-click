"use client";

import MobileMenu from "./MobileMenu";
import Navbar from "./Navbar";

const Header = () => {
  return (
    <header>
      <Navbar />
      <MobileMenu />
    </header>
  );
};

export default Header;
