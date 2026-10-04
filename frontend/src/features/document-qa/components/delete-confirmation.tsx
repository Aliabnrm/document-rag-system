"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";

import styles from "../workspace.module.css";

type DeleteConfirmationProps = {
  label: string;
  confirmation: string;
  isPending: boolean;
  onConfirm: () => void;
};

export function DeleteConfirmation({
  label,
  confirmation,
  isPending,
  onConfirm,
}: DeleteConfirmationProps) {
  const t = useTranslations("Workspace");
  const [isOpen, setIsOpen] = useState(false);

  if (!isOpen) {
    return (
      <Button variant="quiet" size="compact" onClick={() => setIsOpen(true)}>
        {label}
      </Button>
    );
  }

  return (
    <div className={styles.deleteConfirmation} role="group" aria-label={confirmation}>
      <p>{confirmation}</p>
      <div>
        <Button
          variant="danger"
          size="compact"
          disabled={isPending}
          onClick={onConfirm}
        >
          {isPending ? t("deleting") : t("confirmDelete")}
        </Button>
        <Button
          variant="quiet"
          size="compact"
          disabled={isPending}
          onClick={() => setIsOpen(false)}
        >
          {t("cancel")}
        </Button>
      </div>
    </div>
  );
}
