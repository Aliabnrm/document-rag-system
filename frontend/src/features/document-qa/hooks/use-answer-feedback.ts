"use client";

import { useMutation } from "@tanstack/react-query";

import { submitFeedbackApi } from "@/services/api/feedback/feedback.api";
import type { FeedbackReason } from "@/services/api/feedback/feedback.api";
import { coreApi } from "@/services/api/core-api";

export function useAnswerFeedback() {
  return useMutation({
    mutationFn: ({
      messageId,
      rating,
      reason,
      comment,
    }: {
      messageId: string;
      rating: -1 | 1;
      reason: FeedbackReason;
      comment?: string;
    }) =>
      submitFeedbackApi(
        coreApi,
        messageId,
        rating,
        reason,
        comment,
      ),
  });
}
