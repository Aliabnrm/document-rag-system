"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import type { Locale } from "@/i18n/routing";
import { errorCodeOf, isAbortError } from "@/services/api/api-error";
import {
  createConversationApi,
  listConversationMessagesApi,
} from "@/services/api/conversations/conversations.api";
import { streamAnswerApi } from "@/services/api/conversations/answer-stream.api";
import { coreApi } from "@/services/api/core-api";

import { applyAnswerEvent, type ChatMessage } from "../model/chat-message";
import { documentQaKeys } from "./query-keys";

type UseDocumentChatOptions = {
  collectionId: string;
  locale: Locale;
  canAsk: boolean;
  initialConversationId?: string;
  onConversationCreated?: (conversationId: string) => void;
};

export function useDocumentChat({
  collectionId,
  locale,
  canAsk,
  initialConversationId,
  onConversationCreated,
}: UseDocumentChatOptions) {
  const conversationIdRef = useRef<string | null>(initialConversationId ?? null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const answeringRef = useRef(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isAnswering, setIsAnswering] = useState(false);
  const [lastQuestion, setLastQuestion] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const history = useQuery({
    queryKey: documentQaKeys.messages(initialConversationId ?? "new"),
    queryFn: ({ signal }) =>
      listConversationMessagesApi(coreApi, initialConversationId!, undefined, signal),
    enabled: Boolean(initialConversationId),
  });

  const persistedMessages: ChatMessage[] = (history.data?.items ?? []).map((item) => ({
    id: item.id,
    role: item.role,
    content: item.content,
    status: item.role === "assistant" ? "complete" : undefined,
    citations: item.citations,
    abstained: item.abstained,
  }));

  const reset = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    conversationIdRef.current = null;
    answeringRef.current = false;
    setMessages([]);
    setIsAnswering(false);
    setLastQuestion(null);
    setErrorCode(null);
  }, []);

  useEffect(() => reset, [collectionId, reset]);

  async function submitQuestion(value: string) {
    const question = value.trim();
    if (!question || !canAsk || answeringRef.current) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
    };
    const assistantId = crypto.randomUUID();
    setMessages((current) => [
      ...(current.length ? current : persistedMessages),
      userMessage,
      {
        id: assistantId,
        role: "assistant",
        content: "",
        status: "retrieving",
      },
    ]);
    setLastQuestion(question);
    setErrorCode(null);
    setIsAnswering(true);
    answeringRef.current = true;

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      if (!conversationIdRef.current) {
        const conversation = await createConversationApi(
          coreApi,
          collectionId,
          controller.signal,
        );
        conversationIdRef.current = conversation.id;
        onConversationCreated?.(conversation.id);
      }

      await streamAnswerApi({
        conversationId: conversationIdRef.current,
        question,
        language: locale,
        signal: controller.signal,
        onEvent: (event) => {
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId
                ? applyAnswerEvent(message, event)
                : message,
            ),
          );
          if (event.event === "failure") setErrorCode(event.data.code);
        },
      });
    } catch (error: unknown) {
      const cancelled = isAbortError(error);
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId
            ? {
                ...message,
                status: cancelled ? "cancelled" : "failed",
              }
            : message,
        ),
      );
      if (!cancelled) setErrorCode(errorCodeOf(error));
    } finally {
      abortControllerRef.current = null;
      answeringRef.current = false;
      setIsAnswering(false);
    }
  }

  return {
    messages: messages.length ? messages : persistedMessages,
    isAnswering,
    lastQuestion,
    errorCode,
    submitQuestion,
    retryLastQuestion: () => {
      if (lastQuestion) void submitQuestion(lastQuestion);
    },
    cancelAnswer: () => abortControllerRef.current?.abort(),
    clearError: () => setErrorCode(null),
    reset,
  };
}
