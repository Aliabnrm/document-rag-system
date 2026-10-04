"use client";

import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import type { Collection, CreateCollectionInput } from "@/schema/collection/collection.schema";

import styles from "../workspace.module.css";
import { CollectionOnboarding } from "./collection-onboarding";
import { DeleteConfirmation } from "./delete-confirmation";

type CollectionDashboardProps = {
  collections: Collection[];
  errorCode: string | null;
  isLoading: boolean;
  isSubmitting: boolean;
  hasNextPage: boolean;
  isLoadingMore: boolean;
  onCreate: (input: CreateCollectionInput) => Promise<void>;
  onOpen: (collection: Collection) => void;
  onDelete: (collectionId: string) => void;
  deletingCollectionId: string | null;
  onLoadMore: () => void;
};

export function CollectionDashboard({
  collections,
  errorCode,
  isLoading,
  isSubmitting,
  hasNextPage,
  isLoadingMore,
  onCreate,
  onOpen,
  onDelete,
  deletingCollectionId,
  onLoadMore,
}: CollectionDashboardProps) {
  const t = useTranslations("Workspace");
  return (
    <div className={styles.collectionDashboard}>
      {collections.length || isLoading ? (
        <section className={styles.collectionListPanel} aria-labelledby="collection-list-heading">
          <div>
            <p className={styles.kicker}>{t("yourCollectionsKicker")}</p>
            <h2 id="collection-list-heading">{t("yourCollections")}</h2>
          </div>
          {isLoading ? <p role="status">{t("loadingCollections")}</p> : (
            <div className={styles.collectionList}>
              {collections.map((collection) => (
                <article key={collection.id}>
                  <button type="button" onClick={() => onOpen(collection)}>
                    <strong dir="auto">{collection.name}</strong>
                    <span dir="auto">{collection.description || t("noCollectionDescription")}</span>
                  </button>
                  <DeleteConfirmation
                    label={t("deleteCollection")}
                    confirmation={t("deleteCollectionConfirmation", { name: collection.name })}
                    isPending={deletingCollectionId === collection.id}
                    onConfirm={() => onDelete(collection.id)}
                  />
                </article>
              ))}
            </div>
          )}
          {hasNextPage ? (
            <Button variant="secondary" onClick={onLoadMore} disabled={isLoadingMore}>
              {isLoadingMore ? t("loadingMore") : t("loadMoreCollections")}
            </Button>
          ) : null}
        </section>
      ) : null}
      <CollectionOnboarding
        errorCode={errorCode}
        isSubmitting={isSubmitting}
        onSubmit={onCreate}
      />
    </div>
  );
}
