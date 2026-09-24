import { useTranslations } from "next-intl";

import type { Citation } from "@/schema/conversation/conversation.schema";

export function CitationPageLabel({ citation }: { citation: Citation }) {
  const t = useTranslations("Workspace");

  return citation.page_start === citation.page_end
    ? t("page", { page: citation.page_start })
    : t("pageRange", {
        start: citation.page_start,
        end: citation.page_end,
      });
}
