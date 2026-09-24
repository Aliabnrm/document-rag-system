"use client";

import { useTranslations } from "next-intl";

import { StatusBadge } from "@/components/ui/status-badge";
import type { Citation } from "@/schema/conversation/conversation.schema";

import type { ChatMessage } from "../model/chat-message";
import { errorMessageKey } from "../model/document-presentation";
import styles from "../workspace.module.css";
import { ChatMessageItem } from "./chat-message-item";
import { InlineError } from "./inline-error";
import { QuestionComposer } from "./question-composer";

type ChatPanelProps = {
  messages: ChatMessage[];
  readyDocumentCount: number;
  isAnswering: boolean;
  errorCode: string | null;
  canRetry: boolean;
  onSubmit: (question: string) => void;
  onCancel: () => void;
  onRetry: () => void;
  onDismissError: () => void;
  onCitationSelect: (
    citation: Citation,
    trigger: HTMLButtonElement,
  ) => void;
};

export function ChatPanel({
  messages,
  readyDocumentCount,
  isAnswering,
  errorCode,
  canRetry,
  onSubmit,
  onCancel,
  onRetry,
  onDismissError,
  onCitationSelect,
}: ChatPanelProps) {
  const t = useTranslations("Workspace");
  const canAsk = readyDocumentCount > 0;

  return (
    <main className={styles.chatPanel}>
      <div className={styles.chatHeader}>
        <div>
          <p className={styles.kicker}>{t("answerKicker")}</p>
          <h3>{t("chatTitle")}</h3>
        </div>
        <StatusBadge tone={canAsk ? "success" : "neutral"}>
          {canAsk
            ? t("readySources", { count: readyDocumentCount })
            : t("waitingForSource")}
        </StatusBadge>
      </div>

      <div className={styles.messages} aria-live="polite" aria-relevant="additions text">
        {errorCode ? (
          <InlineError
            message={t(errorMessageKey(errorCode))}
            onDismiss={onDismissError}
          />
        ) : null}
        {messages.length === 0 ? (
          <div className={styles.chatEmpty}>
            <div className={styles.chatEmptyMark} aria-hidden="true">
              “
            </div>
            <h4>{t("chatEmptyTitle")}</h4>
            <p>{canAsk ? t("chatEmptyReady") : t("chatEmptyWaiting")}</p>
          </div>
        ) : (
          messages.map((message) => (
            <ChatMessageItem
              key={message.id}
              message={message}
              onCitationSelect={onCitationSelect}
            />
          ))
        )}
      </div>

      <QuestionComposer
        canAsk={canAsk}
        isAnswering={isAnswering}
        canRetry={canRetry}
        onSubmit={onSubmit}
        onCancel={onCancel}
        onRetry={onRetry}
      />
    </main>
  );
}
