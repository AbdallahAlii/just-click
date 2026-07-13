"use client";

import { Toaster } from "react-hot-toast";

export default function AppToaster() {
  return (
    <Toaster
      position="top-center"
      gutter={12}
      containerClassName="!top-20"
      toastOptions={{
        duration: 5000,
        className:
          "!text-sm !font-medium !rounded-xl !shadow-lg !bg-ds-surface !text-ds-text-primary !border !border-ds-border",
        success: {
          iconTheme: {
            primary: "#22c55e",
            secondary: "#fff",
          },
        },
        error: {
          iconTheme: {
            primary: "#ef4444",
            secondary: "#fff",
          },
        },
      }}
    />
  );
}
