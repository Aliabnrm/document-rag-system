import type { Locale } from "@/i18n/routing";

import { WorkspacePage } from "./workspace-page";

type HomePageProps = {
  params: Promise<{ locale: Locale }>;
};

export default async function HomePage({ params }: HomePageProps) {
  const { locale } = await params;
  return <WorkspacePage locale={locale} />;
}
