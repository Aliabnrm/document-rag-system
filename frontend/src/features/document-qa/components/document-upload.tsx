"use client";

import { useTranslations } from "next-intl";
import { type ChangeEvent, type DragEvent, useRef } from "react";

import { Button } from "@/components/ui/button";

import styles from "../workspace.module.css";

type DocumentUploadProps = {
  isUploading: boolean;
  progress: number | null;
  onUpload: (file: File) => void;
  onCancel: () => void;
};

export function DocumentUpload({
  isUploading,
  progress,
  onUpload,
  onCancel,
}: DocumentUploadProps) {
  const t = useTranslations("Workspace");
  const inputRef = useRef<HTMLInputElement>(null);

  function selectFirstFile(files: FileList | null) {
    const file = files?.item(0);
    if (file) onUpload(file);
    if (inputRef.current) inputRef.current.value = "";
  }

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    selectFirstFile(event.target.files);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    if (!isUploading) selectFirstFile(event.dataTransfer.files);
  }

  return (
    <div
      className={styles.dropzone}
      onDragOver={(event) => event.preventDefault()}
      onDrop={handleDrop}
    >
      <input
        ref={inputRef}
        className={styles.visuallyHidden}
        id="document-file"
        type="file"
        accept=".pdf,.txt,application/pdf,text/plain"
        onChange={handleChange}
        disabled={isUploading}
      />
      <div className={styles.uploadIcon} aria-hidden="true">
        ↑
      </div>
      <strong>{t("dropFile")}</strong>
      <span>{t("fileRequirements")}</span>
      <Button
        variant="secondary"
        size="compact"
        onClick={() => inputRef.current?.click()}
        disabled={isUploading}
      >
        {t("chooseFile")}
      </Button>

      {progress !== null ? (
        <div
          className={styles.uploadProgress}
          aria-live="polite"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progress}
          aria-label={t("uploading", { progress })}
        >
          <div className={styles.progressTrack}>
            <span style={{ inlineSize: `${progress}%` }} />
          </div>
          <div className={styles.progressMeta}>
            <span>{t("uploading", { progress })}</span>
            <button type="button" onClick={onCancel}>
              {t("cancel")}
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
