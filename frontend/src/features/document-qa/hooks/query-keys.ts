export const documentQaKeys = {
  all: ["document-qa"] as const,
  collection: (collectionId: string) =>
    [...documentQaKeys.all, "collection", collectionId] as const,
  documents: (collectionId: string) =>
    [...documentQaKeys.all, "documents", collectionId] as const,
};
