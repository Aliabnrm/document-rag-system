import type { Locale } from "@/i18n/routing";

import { WorkspacePage } from "../../../../workspace-page";

type ConversationPageProps = {
  params: Promise<{
    locale: Locale;
    collectionId: string;
    conversationId: string;
  }>;
};

export default async function ConversationPage({ params }: ConversationPageProps) {
  const { locale, collectionId, conversationId } = await params;
  return (
    <WorkspacePage
      locale={locale}
      collectionId={collectionId}
      conversationId={conversationId}
    />
  );
}
