import { getTranslations } from "next-intl/server";
import Link from "next/link";

import { DocumentQaWorkspace } from "@/features/document-qa/workspace";
import type { Locale } from "@/i18n/routing";

type HomePageProps = {
  params: Promise<{ locale: Locale }>;
};

export default async function HomePage({ params }: HomePageProps) {
  const { locale } = await params;
  const t = await getTranslations("Home");
  const otherLocale = locale === "fa" ? "en" : "fa";

  return (
    <main>
      <nav className="nav shell" aria-label={t("navigationLabel")}>
        <Link className="brand" href={`/${locale}`}>
          <span className="brandMark" aria-hidden="true">D</span>
          <span>{t("brand")}</span>
        </Link>
        <Link className="languageSwitch" href={`/${otherLocale}`}>
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
        <DocumentQaWorkspace locale={locale} />
      </div>
    </main>
  );
}
