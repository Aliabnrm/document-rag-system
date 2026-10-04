import { useTranslations } from "next-intl";
import type { MouseEvent } from "react";

import { StatusBadge } from "@/components/ui/status-badge";
import type { Citation } from "@/schema/conversation/conversation.schema";

import type { ChatMessage } from "../model/chat-message";
import type { FeedbackReason } from "@/services/api/feedback/feedback.api";
import styles from "../workspace.module.css";
import { AnswerFeedback } from "./answer-feedback";
import { CitationPageLabel } from "./citation-page-label";

type ChatMessageItemProps = {
  message: ChatMessage;
  onCitationSelect: (
    citation: Citation,
    trigger: HTMLButtonElement,
  ) => void;
  onFeedback: (
    messageId: string,
    rating: -1 | 1,
    reason: FeedbackReason,
    comment?: string,
  ) => Promise<void>;
  feedbackPending: boolean;
};

export function ChatMessageItem({
  message,
  onCitationSelect,
  onFeedback,
  feedbackPending,
}: ChatMessageItemProps) {
  const t = useTranslations("Workspace");

  function selectCitation(
    event: MouseEvent<HTMLButtonElement>,
    citation: Citation,
  ) {
    onCitationSelect(citation, event.currentTarget);
  }

  return (
    <article className={`${styles.message} ${styles[message.role]}`}>
      <p className={styles.messageRole}>
        {message.role === "user"
          ? t("you")
          : message.abstained
            ? t("evidenceCheckResult")
            : t("groundedAnswer")}
      </p>

      {message.abstained ? (
        <div className={styles.abstention} role="status">
          <StatusBadge tone="warning">{t("insufficientEvidence")}</StatusBadge>
          <strong>{t("answerNotFoundTitle")}</strong>
          <p>{t("answerNotFoundDescription")}</p>
          <p className={styles.abstentionHint}>{t("answerNotFoundHint")}</p>
        </div>
      ) : message.status === "retrieving" && !message.content ? (
        <p className={styles.retrieving}>
          <span className={styles.spinner} aria-hidden="true" />
          {t("retrievingEvidence")}
        </p>
      ) : message.status === "streaming" && !message.content ? (
        <p className={styles.retrieving}>
          <span className={styles.spinner} aria-hidden="true" />
          {t("checkingEvidence")}
        </p>
      ) : (
        <p className={styles.messageContent} dir="auto">
          {message.content ||
            (message.status === "failed"
              ? t("answerFailed")
              : message.status === "cancelled"
                ? t("answerCancelled")
                : "")}
        </p>
      )}

      {message.citations?.length ? (
        <div className={styles.citations}>
          <p>{t("evidenceUsed")}</p>
          {message.citations.map((citation) => (
            <button
              type="button"
              key={citation.evidence_id}
              className={styles.citationButton}
              onClick={(event) => selectCitation(event, citation)}
              aria-label={t("openCitation", {
                document: citation.document_name,
                page: citation.page_start,
              })}
            >
              <span>{citation.evidence_id}</span>
              <strong dir="auto">{citation.document_name}</strong>
              <small>
                <CitationPageLabel citation={citation} />
              </small>
            </button>
          ))}
        </div>
      ) : null}

      {message.role === "assistant" && message.status === "complete" ? (
        <AnswerFeedback
          messageId={message.id}
          isPending={feedbackPending}
          onSubmit={onFeedback}
        />
      ) : null}
    </article>
  );
}
