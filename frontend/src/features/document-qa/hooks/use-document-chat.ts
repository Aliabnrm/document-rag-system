"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { Locale } from "@/i18n/routing";
import { errorCodeOf, isAbortError } from "@/services/api/api-error";
import { createConversationApi } from "@/services/api/conversations/conversations.api";
import { streamAnswerApi } from "@/services/api/conversations/answer-stream.api";
import { coreApi } from "@/services/api/core-api";

import { applyAnswerEvent, type ChatMessage } from "../model/chat-message";

type UseDocumentChatOptions = {
  collectionId: string;
  locale: Locale;
  canAsk: boolean;
};

export function useDocumentChat({
  collectionId,
  locale,
  canAsk,
}: UseDocumentChatOptions) {
  const conversationIdRef = useRef<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const answeringRef = useRef(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isAnswering, setIsAnswering] = useState(false);
  const [lastQuestion, setLastQuestion] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);

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
      ...current,
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
    messages,
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
