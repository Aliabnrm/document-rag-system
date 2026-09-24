"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { errorCodeOf, isAbortError } from "@/services/api/api-error";
import { coreApi } from "@/services/api/core-api";
import { uploadDocumentApi } from "@/services/api/documents/documents.api";

import { validateDocumentFile } from "../model/document-presentation";
import { documentQaKeys } from "./query-keys";

export function useDocumentUpload(collectionId: string) {
  const queryClient = useQueryClient();
  const abortControllerRef = useRef<AbortController | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);

  const uploadMutation = useMutation({
    mutationFn: ({ file, signal }: { file: File; signal: AbortSignal }) =>
      uploadDocumentApi(coreApi, collectionId, file, {
        signal,
        onProgress: setProgress,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: documentQaKeys.documents(collectionId),
      }),
  });

  useEffect(
    () => () => {
      abortControllerRef.current?.abort();
    },
    [],
  );

  async function upload(file: File) {
    const validationError = validateDocumentFile(file);
    if (validationError) {
      setErrorCode(validationError);
      return;
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;
    setProgress(0);
    setErrorCode(null);

    try {
      await uploadMutation.mutateAsync({ file, signal: controller.signal });
    } catch (error: unknown) {
      if (!isAbortError(error)) setErrorCode(errorCodeOf(error));
    } finally {
      abortControllerRef.current = null;
      setProgress(null);
    }
  }

  return {
    upload,
    cancel: () => abortControllerRef.current?.abort(),
    progress,
    isUploading: uploadMutation.isPending,
    errorCode,
    clearError: () => setErrorCode(null),
  };
}
