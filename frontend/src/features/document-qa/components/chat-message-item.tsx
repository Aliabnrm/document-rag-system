import { useTranslations } from "next-intl";
import type { MouseEvent } from "react";

import { StatusBadge } from "@/components/ui/status-badge";
import type { Citation } from "@/schema/conversation/conversation.schema";

import type { ChatMessage } from "../model/chat-message";
import styles from "../workspace.module.css";
import { CitationPageLabel } from "./citation-page-label";

type ChatMessageItemProps = {
  message: ChatMessage;
  onCitationSelect: (
    citation: Citation,
    trigger: HTMLButtonElement,
  ) => void;
};

export function ChatMessageItem({
  message,
  onCitationSelect,
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
        {message.role === "user" ? t("you") : t("groundedAnswer")}
      </p>

      {message.status === "retrieving" && !message.content ? (
        <p className={styles.retrieving}>
          <span className={styles.spinner} aria-hidden="true" />
          {t("retrievingEvidence")}
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

      {message.abstained ? (
        <StatusBadge tone="warning">{t("insufficientEvidence")}</StatusBadge>
      ) : null}

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
    </article>
  );
}
