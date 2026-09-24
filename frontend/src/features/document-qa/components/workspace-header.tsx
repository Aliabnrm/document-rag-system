import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import type { Collection } from "@/schema/collection/collection.schema";

import styles from "../workspace.module.css";

type WorkspaceHeaderProps = {
  collection: Collection;
  onChangeCollection: () => void;
};

export function WorkspaceHeader({
  collection,
  onChangeCollection,
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
      <Button variant="quiet" size="compact" onClick={onChangeCollection}>
        {t("changeCollection")}
      </Button>
    </header>
  );
}
