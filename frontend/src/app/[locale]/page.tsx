import { getTranslations } from "next-intl/server";
import Link from "next/link";

import { SystemStatus } from "@/components/system-status";
import type { Locale } from "@/i18n/routing";

type HomePageProps = {
  params: Promise<{ locale: Locale }>;
};

export default async function HomePage({ params }: HomePageProps) {
  const { locale } = await params;
  const t = await getTranslations("Home");
  const otherLocale = locale === "fa" ? "en" : "fa";
  const steps = [
    { title: t("stepOneTitle"), body: t("stepOneBody") },
    { title: t("stepTwoTitle"), body: t("stepTwoBody") },
    { title: t("stepThreeTitle"), body: t("stepThreeBody") },
  ];

  return (
    <main>
      <nav className="nav shell" aria-label={t("brand")}>
        <Link className="brand" href={`/${locale}`}>
          <span className="brandMark" aria-hidden="true">D</span>
          <span>{t("brand")}</span>
        </Link>
        <Link className="languageSwitch" href={`/${otherLocale}`}>
          {t("languageLabel")}
        </Link>
      </nav>

      <section className="hero shell">
        <div className="heroCopy">
          <p className="eyebrow"><span aria-hidden="true" />{t("eyebrow")}</p>
          <h1>{t("title")}</h1>
          <p className="lead">{t("description")}</p>
          <div className="actions">
            <a className="button buttonPrimary" href="#foundation">{t("primaryAction")}</a>
            <a className="button buttonSecondary" href="#workflow">{t("secondaryAction")}</a>
          </div>
        </div>
        <div className="sourcePreview" aria-hidden="true">
          <div className="previewHeader"><span /><span /><span /></div>
          <div className="questionLine" />
          <div className="answerCard">
            <div className="answerAccent" />
            <div className="textLine wide" />
            <div className="textLine" />
            <div className="textLine short" />
          </div>
          <div className="citation"><span>01</span><div><i /><i /></div></div>
          <div className="citation"><span>02</span><div><i /><i /></div></div>
        </div>
      </section>

      <section className="workflow shell" id="workflow">
        <header>
          <p className="sectionLabel">RAG WORKFLOW</p>
          <h2>{t("workflowTitle")}</h2>
          <p>{t("workflowDescription")}</p>
        </header>
        <ol className="steps">
          {steps.map((step, index) => (
            <li key={step.title}>
              <span className="stepNumber">0{index + 1}</span>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="foundation shell" id="foundation">
        <div>
          <p className="sectionLabel">SPRINT 00</p>
          <h2>{t("foundation")}</h2>
          <p>{t("foundationBody")}</p>
        </div>
        <SystemStatus
          labels={{
            checking: t("statusChecking"),
            online: t("statusOnline"),
            offline: t("statusOffline"),
            hint: t("statusHint"),
          }}
        />
      </section>
    </main>
  );
}
