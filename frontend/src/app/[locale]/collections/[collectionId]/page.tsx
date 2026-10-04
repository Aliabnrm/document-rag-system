import type { Locale } from "@/i18n/routing";

import { WorkspacePage } from "../../workspace-page";

type CollectionPageProps = {
  params: Promise<{ locale: Locale; collectionId: string }>;
};

export default async function CollectionPage({ params }: CollectionPageProps) {
  const { locale, collectionId } = await params;
  return <WorkspacePage locale={locale} collectionId={collectionId} />;
}
