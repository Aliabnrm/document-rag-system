"use client";

import { useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import type { CreateCollectionInput } from "@/schema/collection/collection.schema";

import { errorMessageKey } from "../model/document-presentation";
import styles from "../workspace.module.css";
import { InlineError } from "./inline-error";

type CollectionOnboardingProps = {
  errorCode: string | null;
  isSubmitting: boolean;
  onSubmit: (input: CreateCollectionInput) => Promise<void>;
};

export function CollectionOnboarding({
  errorCode,
  isSubmitting,
  onSubmit,
}: CollectionOnboardingProps) {
  const t = useTranslations("Workspace");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) return;

    try {
      await onSubmit({
        name: name.trim(),
        description: description.trim() || undefined,
      });
    } catch {
      // The mutation owns and exposes its safe error state to this form.
    }
  }

  return (
    <section className={styles.onboarding} aria-labelledby="workspace-heading">
      <div className={styles.onboardingIntro}>
        <p className={styles.kicker}>{t("startKicker")}</p>
        <h2 id="workspace-heading">{t("startTitle")}</h2>
        <p>{t("startDescription")}</p>
      </div>

      <form className={styles.collectionForm} onSubmit={handleSubmit}>
        <label htmlFor="collection-name">{t("collectionName")}</label>
        <input
          id="collection-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          maxLength={160}
          placeholder={t("collectionNamePlaceholder")}
          required
        />

        <label htmlFor="collection-description">{t("collectionDescription")}</label>
        <textarea
          id="collection-description"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          maxLength={1000}
          placeholder={t("collectionDescriptionPlaceholder")}
          rows={3}
        />

        {errorCode ? (
          <InlineError message={t(errorMessageKey(errorCode))} />
        ) : null}

        <Button type="submit" disabled={isSubmitting || !name.trim()}>
          {isSubmitting ? t("creatingCollection") : t("createCollection")}
        </Button>
      </form>
    </section>
  );
}
