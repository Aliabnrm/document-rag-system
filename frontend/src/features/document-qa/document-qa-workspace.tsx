"use client";

import { useCallback, useState } from "react";

import type { Locale } from "@/i18n/routing";
import type {
  Collection,
  CreateCollectionInput,
} from "@/schema/collection/collection.schema";
import type { Citation } from "@/schema/conversation/conversation.schema";
import { errorCodeOf } from "@/services/api/api-error";

import { ChatPanel } from "./components/chat-panel";
import { CollectionOnboarding } from "./components/collection-onboarding";
import { DocumentLibrary } from "./components/document-library";
import { EvidenceDialog } from "./components/evidence-dialog";
import { LoadingWorkspace } from "./components/loading-workspace";
import { WorkspaceHeader } from "./components/workspace-header";
import { useActiveCollection } from "./hooks/use-active-collection";
import { useDocumentChat } from "./hooks/use-document-chat";
import { useDocumentUpload } from "./hooks/use-document-upload";
import { useDocuments } from "./hooks/use-documents";
import { useRetryDocument } from "./hooks/use-retry-document";
import styles from "./workspace.module.css";

export function DocumentQaWorkspace({ locale }: { locale: Locale }) {
  const activeCollection = useActiveCollection();

  async function createCollection(input: CreateCollectionInput) {
    const collection = await activeCollection.createCollection.mutateAsync(input);
    activeCollection.activateCollection(collection);
  }

  if (activeCollection.isBooting) return <LoadingWorkspace />;

  if (!activeCollection.collection) {
    const errorCode = activeCollection.createCollection.error
      ? errorCodeOf(activeCollection.createCollection.error)
      : activeCollection.restoreErrorCode;

    return (
      <CollectionOnboarding
        errorCode={errorCode}
        isSubmitting={activeCollection.createCollection.isPending}
        onSubmit={createCollection}
      />
    );
  }

  return (
    <ActiveDocumentQaWorkspace
      key={activeCollection.collection.id}
      collection={activeCollection.collection}
      locale={locale}
      onChangeCollection={activeCollection.clearCollection}
    />
  );
}

type ActiveDocumentQaWorkspaceProps = {
  collection: Collection;
  locale: Locale;
  onChangeCollection: () => void;
};

function ActiveDocumentQaWorkspace({
  collection,
  locale,
  onChangeCollection,
}: ActiveDocumentQaWorkspaceProps) {
  const documentsQuery = useDocuments(collection.id);
  const upload = useDocumentUpload(collection.id);
  const retryDocument = useRetryDocument(collection.id);
  const readyDocumentCount = documentsQuery.documents.filter(
    (document) => document.status === "ready",
  ).length;
  const chat = useDocumentChat({
    collectionId: collection.id,
    locale,
    canAsk: readyDocumentCount > 0,
  });
  const [selectedEvidence, setSelectedEvidence] = useState<{
    citation: Citation;
    trigger: HTMLButtonElement;
  } | null>(null);

  const closeEvidence = useCallback(() => setSelectedEvidence(null), []);

  const documentErrorCode = upload.errorCode
    ?? (retryDocument.error ? errorCodeOf(retryDocument.error) : null)
    ?? (documentsQuery.error ? errorCodeOf(documentsQuery.error) : null);

  function dismissDocumentError() {
    upload.clearError();
    retryDocument.reset();
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
      />

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
          uploadProgress={upload.progress}
          isUploading={upload.isUploading}
          onUpload={(file) => void upload.upload(file)}
          onCancelUpload={upload.cancel}
          onRetryDocument={(documentId) => retryDocument.mutate(documentId)}
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
