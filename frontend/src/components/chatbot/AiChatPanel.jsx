"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  useAskChatbot,
  useChatbotIndexStatus,
  useChatHistory,
  useCreateChatSession,
} from "@/features/chatbot/hooks";
import useNotify from "@/hooks/useNotify";
import AiChatSidebar from "./AiChatSidebar";
import AiComposer from "./AiComposer";
import AiIndexStatus from "./AiIndexStatus";
import AiMessageList from "./AiMessageList";
import AiQuickChips from "./AiQuickChips";
import {
  BotGlyph,
  IconButton,
  IconClose,
  IconExpand,
  IconHistory,
  IconPanelLeft,
  IconRestore,
} from "./AiChatIcons";
import {
  clearCurrentSessionId,
  loadSessionList,
  readCurrentSessionId,
  storeCurrentSessionId,
  titleFromQuestion,
  upsertSessionEntry,
} from "./chatSessionStorage";

function buildHeaderTitle(rawMaterial) {
  const title = rawMaterial?.title || "Material";
  const chapter = rawMaterial?.context?.chapter;
  if (chapter?.number) {
    return `${title} — Ch ${chapter.number}`;
  }
  return title;
}

function mergeSessionsForDisplay(sessionList, sessionId, messages) {
  if (!sessionId) return sessionList;
  if (sessionList.some((item) => item.sessionId === sessionId)) return sessionList;

  const firstUser = messages.find((item) => item.role === "user");
  return [
    {
      sessionId,
      title: firstUser ? titleFromQuestion(firstUser.content) : "Current chat",
      updatedAt: new Date().toISOString(),
    },
    ...sessionList,
  ];
}

export default function AiChatPanel({ isOpen, onClose, materialId, rawMaterial }) {
  const notify = useNotify();
  const headerTitle = buildHeaderTitle(rawMaterial);
  const [mounted, setMounted] = useState(false);

  const [sessionId, setSessionId] = useState(null);
  const [sessionList, setSessionList] = useState([]);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);
  const historyLoadedRef = useRef(false);

  const { data: indexStatusData } = useChatbotIndexStatus(materialId, { enabled: isOpen && !!materialId });
  const indexStatus = indexStatusData?.index_status || "pending";
  const isIndexed = indexStatus === "indexed";
  const isChatDisabled = !isIndexed;

  const createSession = useCreateChatSession();
  const askChatbot = useAskChatbot();
  const { data: historyRows = [] } = useChatHistory(sessionId, {
    enabled: isOpen && !!sessionId,
  });

  const isLoading = createSession.isPending || askChatbot.isPending;

  const displaySessions = useMemo(
    () => mergeSessionsForDisplay(sessionList, sessionId, messages),
    [sessionList, sessionId, messages],
  );

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!isOpen || !materialId) return;

    const storedSessionId = readCurrentSessionId(materialId);
    let list = loadSessionList(materialId);

    if (storedSessionId && !list.some((item) => item.sessionId === storedSessionId)) {
      list = upsertSessionEntry(materialId, { sessionId: storedSessionId, title: "Current chat" });
    }

    setSessionList(list);
    setSessionId(storedSessionId);
    if (!storedSessionId) {
      setMessages([]);
    }
    historyLoadedRef.current = false;
    setHistoryDrawerOpen(false);
  }, [isOpen, materialId]);

  useEffect(() => {
    if (!isOpen) return undefined;

    document.body.classList.add("chat-panel-open");
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.body.classList.remove("chat-panel-open", "chat-panel-fullscreen");
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    if (isFullscreen) {
      document.body.classList.add("chat-panel-fullscreen");
    } else {
      document.body.classList.remove("chat-panel-fullscreen");
    }
  }, [isOpen, isFullscreen]);

  useEffect(() => {
    if (!isOpen) {
      setIsFullscreen(false);
      setSidebarOpen(true);
      setHistoryDrawerOpen(false);
    }
  }, [isOpen]);

  useEffect(() => {
    if (isFullscreen) {
      document.body.classList.add("chat-panel-fullscreen");
    } else {
      document.body.classList.remove("chat-panel-fullscreen");
    }
  }, [isFullscreen]);

  useEffect(() => {
    if (!isOpen) return undefined;

    const handleEscape = (event) => {
      if (event.key !== "Escape") return;
      if (historyDrawerOpen) {
        setHistoryDrawerOpen(false);
        return;
      }
      if (isFullscreen) {
        setIsFullscreen(false);
        return;
      }
      onClose();
    };

    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [isOpen, isFullscreen, historyDrawerOpen, onClose]);

  useEffect(() => {
    if (!sessionId || !historyRows.length || historyLoadedRef.current) return;
    setMessages(
      historyRows.map((row) => ({
        role: row.role,
        content: row.content,
      })),
    );
    historyLoadedRef.current = true;

    const firstUser = historyRows.find((row) => row.role === "user");
    if (firstUser && materialId) {
      const next = upsertSessionEntry(materialId, {
        sessionId,
        title: titleFromQuestion(firstUser.content),
      });
      setSessionList(next);
    }
  }, [sessionId, historyRows, materialId]);


  const ensureSession = async () => {
    if (sessionId) return sessionId;
    const response = await createSession.mutateAsync({
      material_id: materialId,
      scope: "material",
    });
    const newSessionId = response?.data?.session_id || response?.session_id;
    if (!newSessionId) throw new Error("Could not start AI session.");
    setSessionId(newSessionId);
    storeCurrentSessionId(materialId, newSessionId);
    const next = upsertSessionEntry(materialId, { sessionId: newSessionId, title: "New chat" });
    setSessionList(next);
    return newSessionId;
  };

  const sendQuestion = async (question) => {
    const trimmed = (question || "").trim();
    if (!trimmed || isChatDisabled || isLoading) return;

    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setInputValue("");

    try {
      const activeSessionId = await ensureSession();
      const next = upsertSessionEntry(materialId, {
        sessionId: activeSessionId,
        title: titleFromQuestion(trimmed),
      });
      setSessionList(next);

      const response = await askChatbot.mutateAsync({
        session_id: activeSessionId,
        question: trimmed,
      });
      const payload = response?.data ?? response;
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: payload?.answer || "No answer returned.",
          sources: payload?.sources || [],
        },
      ]);
      setSessionList(
        upsertSessionEntry(materialId, {
          sessionId: activeSessionId,
          title: titleFromQuestion(trimmed),
        }),
      );
    } catch (error) {
      notify.error(error?.message || "Could not get an AI answer.");
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I could not answer that right now. Please try again in a moment.",
          isError: true,
        },
      ]);
    }
  };

  const handleNewChat = () => {
    clearCurrentSessionId(materialId);
    setSessionId(null);
    setMessages([]);
    historyLoadedRef.current = false;
    setHistoryDrawerOpen(false);
  };

  const handleSelectSession = (nextSessionId) => {
    if (!nextSessionId || nextSessionId === sessionId) {
      setHistoryDrawerOpen(false);
      return;
    }
    setSessionId(nextSessionId);
    storeCurrentSessionId(materialId, nextSessionId);
    setMessages([]);
    historyLoadedRef.current = false;
    setHistoryDrawerOpen(false);
  };

  if (!isOpen || !mounted) return null;

  const shellClass = isFullscreen
    ? "fixed inset-0 z-[9999] flex bg-ds-page"
    : "fixed top-14 right-0 bottom-0 z-[200] flex w-full max-w-[480px] flex-col border-l border-ds-border bg-ds-page shadow-xl sm:max-w-[520px]";

  const panel = (
    <>
      {!isFullscreen && (
        <div
          className="fixed inset-0 z-[199] bg-black/20 dark:bg-black/40"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <div className={shellClass}>
        {isFullscreen && sidebarOpen && (
          <AiChatSidebar
            sessions={displaySessions}
            activeSessionId={sessionId}
            onSelectSession={handleSelectSession}
            onNewChat={handleNewChat}
            onCollapse={() => setSidebarOpen(false)}
            showCollapse
            materialTitle={headerTitle}
          />
        )}

        {isFullscreen && !sidebarOpen && (
          <div className="flex w-11 flex-shrink-0 flex-col items-center border-r border-ds-border bg-ds-surface-secondary py-3">
            <IconButton label="Show chat history" onClick={() => setSidebarOpen(true)}>
              <IconPanelLeft />
            </IconButton>
          </div>
        )}

        <div className="relative flex min-h-0 min-w-0 flex-1 flex-col bg-ds-page">
          {!isFullscreen && historyDrawerOpen && (
            <>
              <button
                type="button"
                className="absolute inset-0 z-20 bg-black/20 dark:bg-black/40"
                onClick={() => setHistoryDrawerOpen(false)}
                aria-label="Close chat history"
              />
              <div className="absolute inset-y-0 left-0 z-30 shadow-xl">
                <AiChatSidebar
                  sessions={displaySessions}
                  activeSessionId={sessionId}
                  onSelectSession={handleSelectSession}
                  onNewChat={handleNewChat}
                  materialTitle={headerTitle}
                />
              </div>
            </>
          )}

          <header className="flex h-12 flex-shrink-0 items-center gap-2 border-b border-ds-border bg-ds-surface px-3">
            <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md bg-ds-action/10 text-ds-action">
              <BotGlyph className="h-3.5 w-3.5" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-ds-text-primary">
                {headerTitle}
              </p>
              <p className="truncate text-[11px] text-ds-text-muted">JustClick AI</p>
            </div>

            <div className="flex flex-shrink-0 items-center gap-0.5">
              <button
                type="button"
                onClick={handleNewChat}
                className="mr-1 hidden h-8 items-center rounded-md border border-ds-border px-2.5 text-xs font-semibold text-ds-text-secondary transition-colors hover:bg-ds-surface-hover sm:inline-flex"
              >
                New chat
              </button>

              {!isFullscreen && (
                <IconButton
                  label="Chat history"
                  onClick={() => setHistoryDrawerOpen((prev) => !prev)}
                  active={historyDrawerOpen}
                >
                  <IconHistory />
                </IconButton>
              )}

              {isFullscreen ? (
                <IconButton label="Exit full screen" onClick={() => setIsFullscreen(false)}>
                  <IconRestore />
                </IconButton>
              ) : (
                <IconButton
                  label="Open full screen"
                  onClick={() => {
                    setIsFullscreen(true);
                    setSidebarOpen(true);
                  }}
                >
                  <IconExpand />
                </IconButton>
              )}

              <IconButton label="Close assistant" onClick={onClose}>
                <IconClose />
              </IconButton>
            </div>
          </header>

          <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-ds-page">
            {!isIndexed && (
              <div className="flex-shrink-0 px-3 pt-3">
                <AiIndexStatus status={indexStatus} />
              </div>
            )}

            <AiMessageList messages={messages} isLoading={isLoading} isWide={isFullscreen} />

            {messages.length === 0 && isIndexed && (
              <AiQuickChips
                onSelect={sendQuestion}
                disabled={isChatDisabled || isLoading}
                isWide={isFullscreen}
              />
            )}
          </div>

          <AiComposer
            value={inputValue}
            onChange={setInputValue}
            onSend={() => sendQuestion(inputValue)}
            disabled={isChatDisabled}
            isSending={isLoading}
            isWide={isFullscreen}
          />
        </div>
      </div>
    </>
  );

  return createPortal(panel, document.body);
}
