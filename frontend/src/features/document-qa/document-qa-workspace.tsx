"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";

import type { Locale } from "@/i18n/routing";
import type {
  Collection,
  CreateCollectionInput,
} from "@/schema/collection/collection.schema";
import type { Citation } from "@/schema/conversation/conversation.schema";
import { errorCodeOf } from "@/services/api/api-error";

import { ChatPanel } from "./components/chat-panel";
import { CollectionDashboard } from "./components/collection-dashboard";
import { DocumentLibrary } from "./components/document-library";
import { EvidenceDialog } from "./components/evidence-dialog";
import { LoadingWorkspace } from "./components/loading-workspace";
import { WorkspaceHeader } from "./components/workspace-header";
import { useActiveCollection } from "./hooks/use-active-collection";
import { useDocumentChat } from "./hooks/use-document-chat";
import { useDocumentUpload } from "./hooks/use-document-upload";
import { useDocuments } from "./hooks/use-documents";
import { useCollections } from "./hooks/use-collections";
import { useConversations } from "./hooks/use-conversations";
import { useRetryDocument } from "./hooks/use-retry-document";
import { useAnswerFeedback } from "./hooks/use-answer-feedback";
import { useDeleteCollection } from "./hooks/use-delete-collection";
import { useDeleteDocument } from "./hooks/use-delete-document";
import styles from "./workspace.module.css";

export function DocumentQaWorkspace({
  locale,
  initialCollectionId,
  initialConversationId,
}: {
  locale: Locale;
  initialCollectionId?: string;
  initialConversationId?: string;
}) {
  const router = useRouter();
  const activeCollection = useActiveCollection(initialCollectionId);
  const collections = useCollections();
  const deleteCollection = useDeleteCollection();

  async function createCollection(input: CreateCollectionInput) {
    const collection = await activeCollection.createCollection.mutateAsync(input);
    activeCollection.activateCollection(collection);
    router.push(`/${locale}/collections/${collection.id}`);
  }

  if (activeCollection.isBooting) return <LoadingWorkspace />;

  if (!activeCollection.collection) {
    const errorCode = activeCollection.createCollection.error
      ? errorCodeOf(activeCollection.createCollection.error)
      : activeCollection.restoreErrorCode;

    return <CollectionDashboard
      collections={collections.collections}
      errorCode={errorCode
        ?? (deleteCollection.error ? errorCodeOf(deleteCollection.error) : null)
        ?? (collections.error ? errorCodeOf(collections.error) : null)}
      isLoading={collections.isPending}
      isSubmitting={activeCollection.createCollection.isPending}
      hasNextPage={Boolean(collections.hasNextPage)}
      isLoadingMore={collections.isFetchingNextPage}
      onCreate={createCollection}
      onOpen={(collection) => router.push(`/${locale}/collections/${collection.id}`)}
      deletingCollectionId={deleteCollection.isPending ? deleteCollection.variables : null}
      onDelete={(collectionId) => deleteCollection.mutate(collectionId)}
      onLoadMore={() => void collections.fetchNextPage()}
    />;
  }

  return (
    <ActiveDocumentQaWorkspace
      key={`${activeCollection.collection.id}:${initialConversationId ?? "new"}`}
      collection={activeCollection.collection}
      locale={locale}
      initialConversationId={initialConversationId}
      onChangeCollection={() => {
        activeCollection.clearCollection();
        router.push(`/${locale}`);
      }}
      onDeleteCollection={async () => {
        await deleteCollection.mutateAsync(activeCollection.collection!.id);
        activeCollection.clearCollection();
        router.replace(`/${locale}`);
      }}
      isDeletingCollection={deleteCollection.isPending}
    />
  );
}

type ActiveDocumentQaWorkspaceProps = {
  collection: Collection;
  locale: Locale;
  initialConversationId?: string;
  onChangeCollection: () => void;
  onDeleteCollection: () => Promise<void>;
  isDeletingCollection: boolean;
};

function ActiveDocumentQaWorkspace({
  collection,
  locale,
  initialConversationId,
  onChangeCollection,
  onDeleteCollection,
  isDeletingCollection,
}: ActiveDocumentQaWorkspaceProps) {
  const t = useTranslations("Workspace");
  const documentsQuery = useDocuments(collection.id);
  const router = useRouter();
  const conversations = useConversations(collection.id);
  const upload = useDocumentUpload(collection.id);
  const retryDocument = useRetryDocument(collection.id);
  const deleteDocument = useDeleteDocument(collection.id);
  const feedback = useAnswerFeedback();
  const readyDocumentCount = documentsQuery.documents.filter(
    (document) => document.status === "ready",
  ).length;
  const chat = useDocumentChat({
    collectionId: collection.id,
    locale,
    canAsk: readyDocumentCount > 0,
    initialConversationId,
    onConversationCreated: (conversationId) => {
      void conversations.refetch();
      router.replace(`/${locale}/collections/${collection.id}/conversations/${conversationId}`);
    },
  });
  const [selectedEvidence, setSelectedEvidence] = useState<{
    citation: Citation;
    trigger: HTMLButtonElement;
  } | null>(null);

  const closeEvidence = useCallback(() => setSelectedEvidence(null), []);

  const documentErrorCode = upload.errorCode
    ?? (retryDocument.error ? errorCodeOf(retryDocument.error) : null)
    ?? (deleteDocument.error ? errorCodeOf(deleteDocument.error) : null)
    ?? (documentsQuery.error ? errorCodeOf(documentsQuery.error) : null);

  function dismissDocumentError() {
    upload.clearError();
    retryDocument.reset();
    deleteDocument.reset();
    if (documentsQuery.error) void documentsQuery.refetch();
  }

  function changeCollection() {
    chat.reset();
    onChangeCollection();
  }

  return (
    <section className={styles.workspace} aria-labelledby="collection-heading">
      <WorkspaceHeader
        collection={collection}
        onChangeCollection={changeCollection}
        onDeleteCollection={() => void onDeleteCollection()}
        isDeletingCollection={isDeletingCollection}
      />

      <nav className={styles.conversationNav} aria-label={t("conversationHistory")}>
        <button
          type="button"
          aria-current={!initialConversationId ? "page" : undefined}
          onClick={() => router.push(`/${locale}/collections/${collection.id}`)}
        >
          {t("newConversation")}
        </button>
        {conversations.conversations.map((conversation, index) => (
          <button
            type="button"
            key={conversation.id}
            aria-current={conversation.id === initialConversationId ? "page" : undefined}
            onClick={() => router.push(
              `/${locale}/collections/${collection.id}/conversations/${conversation.id}`,
            )}
          >
            {conversation.title || t("conversationNumber", { number: conversations.conversations.length - index })}
          </button>
        ))}
        {conversations.hasNextPage ? (
          <button type="button" onClick={() => void conversations.fetchNextPage()}>
            {t("moreConversations")}
          </button>
        ) : null}
      </nav>

      <div className={styles.workspaceGrid}>
        <DocumentLibrary
          documents={documentsQuery.documents}
          locale={locale}
          errorCode={documentErrorCode}
          isLoading={documentsQuery.isPending}
          hasNextPage={Boolean(documentsQuery.hasNextPage)}
          isLoadingMore={documentsQuery.isFetchingNextPage}
          retryingDocumentId={
            retryDocument.isPending ? retryDocument.variables : null
          }
          deletingDocumentId={
            deleteDocument.isPending ? deleteDocument.variables : null
          }
          uploadProgress={upload.progress}
          isUploading={upload.isUploading}
          onUpload={(file) => void upload.upload(file)}
          onCancelUpload={upload.cancel}
          onRetryDocument={(documentId) => retryDocument.mutate(documentId)}
          onDeleteDocument={(documentId) => deleteDocument.mutate(documentId)}
          onLoadMore={() => void documentsQuery.fetchNextPage()}
          onDismissError={dismissDocumentError}
        />

        <ChatPanel
          messages={chat.messages}
          readyDocumentCount={readyDocumentCount}
          isAnswering={chat.isAnswering}
          errorCode={chat.errorCode}
          canRetry={
            Boolean(chat.lastQuestion) &&
            chat.messages.at(-1)?.status === "failed" &&
            !chat.isAnswering
          }
          onSubmit={(question) => void chat.submitQuestion(question)}
          onCancel={chat.cancelAnswer}
          onRetry={chat.retryLastQuestion}
          onDismissError={chat.clearError}
          onCitationSelect={(citation, trigger) =>
            setSelectedEvidence({ citation, trigger })
          }
          onFeedback={async (messageId, rating, reason, comment) => {
            await feedback.mutateAsync({ messageId, rating, reason, comment });
          }}
          feedbackPending={feedback.isPending}
        />
      </div>

      {selectedEvidence ? (
        <EvidenceDialog
          citation={selectedEvidence.citation}
          returnFocusTo={selectedEvidence.trigger}
          onClose={closeEvidence}
        />
      ) : null}
    </section>
  );
}
