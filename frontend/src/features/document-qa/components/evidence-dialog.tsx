"use client";

import { useTranslations } from "next-intl";
import { type KeyboardEvent, useEffect, useRef } from "react";

import { Button } from "@/components/ui/button";
import type { Citation } from "@/schema/conversation/conversation.schema";

import styles from "../workspace.module.css";
import { CitationPageLabel } from "./citation-page-label";

type EvidenceDialogProps = {
  citation: Citation;
  returnFocusTo: HTMLButtonElement | null;
  onClose: () => void;
};

export function EvidenceDialog({
  citation,
  returnFocusTo,
  onClose,
}: EvidenceDialogProps) {
  const t = useTranslations("Workspace");
  const dialogRef = useRef<HTMLElement>(null);

  useEffect(() => {
    dialogRef.current?.querySelector<HTMLButtonElement>("button")?.focus();

    function handleEscape(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }

    window.addEventListener("keydown", handleEscape);
    return () => {
      window.removeEventListener("keydown", handleEscape);
      returnFocusTo?.focus();
    };
  }, [onClose, returnFocusTo]);

  function keepFocusInside(event: KeyboardEvent<HTMLElement>) {
    if (event.key !== "Tab") return;
    event.preventDefault();
    dialogRef.current?.querySelector<HTMLButtonElement>("button")?.focus();
  }

  return (
    <aside
      ref={dialogRef}
      className={styles.evidencePanel}
      aria-labelledby="evidence-heading"
      aria-modal="true"
      role="dialog"
      onKeyDown={keepFocusInside}
    >
      <header>
        <div>
          <p className={styles.kicker}>{citation.evidence_id}</p>
          <h3 id="evidence-heading" dir="auto">
            {citation.document_name}
          </h3>
          <p>
            <CitationPageLabel citation={citation} />
          </p>
        </div>
        <Button variant="quiet" size="compact" onClick={onClose}>
          {t("closeEvidence")}
        </Button>
      </header>
      <blockquote dir="auto">{citation.snippet}</blockquote>
      <p className={styles.evidenceNote}>{t("evidenceNote")}</p>
    </aside>
  );
}
