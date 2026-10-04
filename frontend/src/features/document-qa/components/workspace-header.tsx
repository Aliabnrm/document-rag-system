import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import type { Collection } from "@/schema/collection/collection.schema";

import styles from "../workspace.module.css";
import { DeleteConfirmation } from "./delete-confirmation";

type WorkspaceHeaderProps = {
  collection: Collection;
  onChangeCollection: () => void;
  onDeleteCollection: () => void;
  isDeletingCollection: boolean;
};

export function WorkspaceHeader({
  collection,
  onChangeCollection,
  onDeleteCollection,
  isDeletingCollection,
}: WorkspaceHeaderProps) {
  const t = useTranslations("Workspace");

  return (
    <header className={styles.workspaceHeader}>
      <div>
        <p className={styles.kicker}>{t("activeCollection")}</p>
        <h2 id="collection-heading" dir="auto">
          {collection.name}
        </h2>
        {collection.description ? <p dir="auto">{collection.description}</p> : null}
      </div>
      <div className={styles.workspaceHeaderActions}>
        <Button variant="quiet" size="compact" onClick={onChangeCollection}>
          {t("changeCollection")}
        </Button>
        <DeleteConfirmation
          label={t("deleteCollection")}
          confirmation={t("deleteCollectionConfirmation", { name: collection.name })}
          isPending={isDeletingCollection}
          onConfirm={onDeleteCollection}
        />
      </div>
    </header>
  );
}
