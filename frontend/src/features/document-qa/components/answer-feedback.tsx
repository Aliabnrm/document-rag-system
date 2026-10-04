"use client";

import { useState, type FormEvent } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import type { FeedbackReason } from "@/services/api/feedback/feedback.api";

import styles from "../workspace.module.css";

const NEGATIVE_REASONS: FeedbackReason[] = [
  "incorrect",
  "unsupported",
  "citation_mismatch",
  "incomplete",
  "unclear_language",
  "should_have_abstained",
];

type AnswerFeedbackProps = {
  messageId: string;
  isPending: boolean;
  onSubmit: (
    messageId: string,
    rating: -1 | 1,
    reason: FeedbackReason,
    comment?: string,
  ) => Promise<void>;
};

export function AnswerFeedback({
  messageId,
  isPending,
  onSubmit,
}: AnswerFeedbackProps) {
  const t = useTranslations("Workspace");
  const [isExpanded, setIsExpanded] = useState(false);
  const [reason, setReason] = useState<FeedbackReason>("incorrect");
  const [comment, setComment] = useState("");
  const [status, setStatus] = useState<"idle" | "saved" | "error">("idle");

  async function submit(
    rating: -1 | 1,
    selectedReason: FeedbackReason,
    optionalComment?: string,
  ) {
    setStatus("idle");
    try {
      await onSubmit(messageId, rating, selectedReason, optionalComment);
      setStatus("saved");
      setIsExpanded(false);
    } catch {
      setStatus("error");
    }
  }

  function submitNegative(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submit(-1, reason, comment.trim() || undefined);
  }

  if (status === "saved") {
    return <p className={styles.feedbackStatus} role="status">{t("feedbackSaved")}</p>;
  }

  return (
    <div className={styles.feedbackBlock}>
      <div className={styles.feedbackActions} aria-label={t("answerFeedback")}>
        <span>{t("wasHelpful")}</span>
        <button
          type="button"
          disabled={isPending}
          onClick={() => void submit(1, "helpful")}
        >
          {t("helpful")}
        </button>
        <button
          type="button"
          disabled={isPending}
          aria-expanded={isExpanded}
          onClick={() => setIsExpanded((value) => !value)}
        >
          {t("notHelpful")}
        </button>
      </div>

      {isExpanded ? (
        <form className={styles.feedbackForm} onSubmit={submitNegative}>
          <label htmlFor={`feedback-reason-${messageId}`}>{t("feedbackReason")}</label>
          <select
            id={`feedback-reason-${messageId}`}
            value={reason}
            onChange={(event) => setReason(event.target.value as FeedbackReason)}
          >
            {NEGATIVE_REASONS.map((item) => (
              <option key={item} value={item}>
                {t(`feedbackReason_${item}`)}
              </option>
            ))}
          </select>
          <label htmlFor={`feedback-comment-${messageId}`}>{t("feedbackComment")}</label>
          <textarea
            id={`feedback-comment-${messageId}`}
            value={comment}
            maxLength={500}
            rows={2}
            onChange={(event) => setComment(event.target.value)}
            placeholder={t("feedbackCommentPlaceholder")}
          />
          <Button type="submit" size="compact" disabled={isPending}>
            {isPending ? t("savingFeedback") : t("sendFeedback")}
          </Button>
        </form>
      ) : null}

      {status === "error" ? (
        <p className={styles.feedbackError} role="alert">{t("feedbackError")}</p>
      ) : null}
    </div>
  );
}
