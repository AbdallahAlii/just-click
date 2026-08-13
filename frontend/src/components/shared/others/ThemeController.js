"use client";

import { useEffect } from "react";
import theme from "@/libs/theme";

const ThemeController = () => {
  useEffect(() => {
    theme();
  }, []);

  return (
    <div className="theme-controller fixed top-[100px] right-[-50px] z-xl transition-all duration-300 hover:right-0 3xl:top-[300px]">
      <button
        type="button"
        className="theme-controller flex h-10 w-90px items-center rounded-l-xl bg-ds-action px-10px text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="mr-10px block w-5 dark:hidden"
          viewBox="0 0 512 512"
          aria-hidden="true"
        >
          <path
            d="M160 136c0-30.62 4.51-61.61 16-88C99.57 81.27 48 159.32 48 248c0 119.29 96.71 216 216 216 88.68 0 166.73-51.57 200-128-26.39 11.49-57.38 16-88 16-119.29 0-216-96.71-216-216z"
            fill="none"
            stroke="currentColor"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="32"
          />
        </svg>
        <span className="block text-base dark:hidden">Dark</span>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="mr-10px hidden w-5 dark:block"
          viewBox="0 0 512 512"
          aria-hidden="true"
        >
          <path
            fill="none"
            stroke="currentColor"
            strokeLinecap="round"
            strokeMiterlimit="10"
            strokeWidth="32"
            d="M256 48v48M256 416v48M403.08 108.92l-33.94 33.94M142.86 369.14l-33.94 33.94M464 256h-48M96 256H48M403.08 403.08l-33.94-33.94M142.86 142.86l-33.94-33.94"
          />
          <circle
            cx="256"
            cy="256"
            r="80"
            fill="none"
            stroke="currentColor"
            strokeLinecap="round"
            strokeMiterlimit="10"
            strokeWidth="32"
          />
        </svg>
        <span className="hidden text-base dark:block">Light</span>
      </button>
    </div>
  );
};

export default ThemeController;
