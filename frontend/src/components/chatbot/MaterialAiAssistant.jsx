"use client";

import { useState } from "react";
import { useChatbotIndexStatus } from "@/features/chatbot/hooks";
import { Sparkles } from "lucide-react";
import AiChatPanel from "./AiChatPanel";

const INDEXABLE_TYPES = new Set(["pdf", "slides", "doc"]);

export default function MaterialAiAssistant({ materialId, rawMaterial }) {
  const [isOpen, setIsOpen] = useState(false);

  const hasFile = Boolean(rawMaterial?.file?.read_url || rawMaterial?.file_url);
  const materialType = String(rawMaterial?.material_type || "").toLowerCase();
  const isIndexableType = INDEXABLE_TYPES.has(materialType);

  const { data: indexStatusData } = useChatbotIndexStatus(materialId, {
    enabled: !!materialId && isIndexableType && hasFile,
  });

  const indexStatus = indexStatusData?.index_status;
  const showAi = isIndexableType && hasFile;
  const isReady = indexStatus === "indexed";
  const isPreparing = indexStatus === "pending" || indexStatus === "indexing";
  const isFailed = indexStatus === "failed";

  if (!showAi) return null;

  const openPanel = () => setIsOpen(true);
  const closePanel = () => setIsOpen(false);

  const label = isFailed
    ? "AI unavailable"
    : isPreparing
      ? "AI preparing…"
      : "Ask JustClick AI";

  return (
    <>
      <button
        type="button"
        onClick={openPanel}
        disabled={isFailed || isPreparing}
        className="inline-flex min-h-[40px] w-full items-center justify-center gap-2 rounded-lg bg-ds-action px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-ds-action-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:focus-visible:ring-offset-ds-page"
      >
        <Sparkles className="h-4 w-4" aria-hidden="true" />
        {label}
      </button>

      {!isOpen && isReady ? (
        <button
          type="button"
          onClick={openPanel}
          aria-label="Ask JustClick AI"
          className="fixed bottom-5 right-5 z-30 flex h-11 w-11 items-center justify-center rounded-full bg-ds-action text-white shadow-md transition-colors hover:bg-ds-action-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ds-action"
        >
          <Sparkles className="h-5 w-5" aria-hidden="true" />
        </button>
      ) : null}

      <AiChatPanel
        isOpen={isOpen}
        onClose={closePanel}
        materialId={materialId}
        rawMaterial={rawMaterial}
      />
    </>
  );
}
