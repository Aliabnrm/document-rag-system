import type { AxiosInstance } from "axios";
import { z } from "zod";

import { requestAndParse } from "@/services/api/core-api";

const FeedbackResponseSchema = z.object({ id: z.string().uuid() });

export type FeedbackReason =
  | "helpful"
  | "incorrect"
  | "unsupported"
  | "citation_mismatch"
  | "incomplete"
  | "unclear_language"
  | "should_have_abstained";

export function submitFeedbackApi(
  api: AxiosInstance,
  answerMessageId: string,
  rating: -1 | 1,
  reason: FeedbackReason,
  comment?: string,
): Promise<{ id: string }> {
  return requestAndParse(
    api.post(`/api/v1/messages/${answerMessageId}/feedback`, {
      rating,
      reason,
      comment: comment || null,
    }),
    FeedbackResponseSchema,
  );
}
