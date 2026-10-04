import { getTranslations } from "next-intl/server";
import Link from "next/link";

import { AuthBoundary } from "@/features/auth";
import { DocumentQaWorkspace } from "@/features/document-qa";
import type { Locale } from "@/i18n/routing";

export async function WorkspacePage({
  locale,
  collectionId,
  conversationId,
}: {
  locale: Locale;
  collectionId?: string;
  conversationId?: string;
}) {
  const t = await getTranslations("Home");
  const otherLocale = locale === "fa" ? "en" : "fa";
  const languageHref = collectionId && conversationId
    ? `/${otherLocale}/collections/${collectionId}/conversations/${conversationId}`
    : collectionId
    ? `/${otherLocale}/collections/${collectionId}`
    : `/${otherLocale}`;

  return (
    <main className="pageFrame">
      <nav className="nav shell" aria-label={t("navigationLabel")}>
        <Link className="brand" href={`/${locale}`}>
          <span className="brandMark" aria-hidden="true">D</span>
          <span>{t("brand")}</span>
        </Link>
        <Link className="languageSwitch" href={languageHref}>
          {t("languageLabel")}
        </Link>
      </nav>

      <header className="productIntro shell">
        <div>
          <p className="productEyebrow">{t("eyebrow")}</p>
          <h1>{t("title")}</h1>
        </div>
        <p className="productPromise">{t("description")}</p>
      </header>

      <div className="appShell shell">
        <AuthBoundary>
          <DocumentQaWorkspace
            locale={locale}
            initialCollectionId={collectionId}
            initialConversationId={conversationId}
          />
        </AuthBoundary>
      </div>
    </main>
  );
}
