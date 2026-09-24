"use client";

import { useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";

import styles from "../workspace.module.css";

type QuestionComposerProps = {
  canAsk: boolean;
  isAnswering: boolean;
  canRetry: boolean;
  onSubmit: (question: string) => void;
  onCancel: () => void;
  onRetry: () => void;
};

export function QuestionComposer({
  canAsk,
  isAnswering,
  canRetry,
  onSubmit,
  onCancel,
  onRetry,
}: QuestionComposerProps) {
  const t = useTranslations("Workspace");
  const [question, setQuestion] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = question.trim();
    if (!value || !canAsk || isAnswering) return;
    setQuestion("");
    onSubmit(value);
  }

  return (
    <form className={styles.composer} onSubmit={handleSubmit}>
      <label className={styles.visuallyHidden} htmlFor="question">
        {t("questionLabel")}
      </label>
      <textarea
        id="question"
        value={question}
        onChange={(event) => setQuestion(event.target.value)}
        placeholder={canAsk ? t("questionPlaceholder") : t("questionDisabled")}
        disabled={!canAsk || isAnswering}
        rows={2}
        maxLength={4000}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            event.currentTarget.form?.requestSubmit();
          }
        }}
      />

      <div className={styles.composerFooter}>
        <span>{t("composerHint")}</span>
        {isAnswering ? (
          <Button type="button" variant="danger" size="compact" onClick={onCancel}>
            {t("stopAnswer")}
          </Button>
        ) : (
          <Button type="submit" disabled={!question.trim() || !canAsk}>
            {t("askQuestion")}
          </Button>
        )}
      </div>

      {canRetry ? (
        <button type="button" className={styles.retryAnswer} onClick={onRetry}>
          {t("retryLastQuestion")}
        </button>
      ) : null}
    </form>
  );
}
