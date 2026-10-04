import { z } from "zod";

import { CitationListSchema } from "./conversation.schema";

export const RetrievalStartedDataSchema = z.object({
  rag_run_id: z.string(),
});

export const RetrievalCompletedDataSchema = z.object({
  evidence_count: z.number(),
});

export const AnswerDeltaDataSchema = z.object({
  text: z.string(),
});

export const CitationsDataSchema = z.object({
  items: CitationListSchema,
});

export const AnswerCompletedDataSchema = z.object({
  abstained: z.boolean(),
  rag_run_id: z.string().default(""),
  answer_message_id: z.string().uuid(),
});

export const AnswerFailureDataSchema = z.object({
  code: z.string(),
  message_key: z.string().default(""),
});

export type AnswerStreamEvent =
  | { event: "retrieval_started"; data: z.infer<typeof RetrievalStartedDataSchema> }
  | { event: "retrieval_completed"; data: z.infer<typeof RetrievalCompletedDataSchema> }
  | { event: "answer_delta"; data: z.infer<typeof AnswerDeltaDataSchema> }
  | { event: "citations"; data: z.infer<typeof CitationsDataSchema> }
  | { event: "completed"; data: z.infer<typeof AnswerCompletedDataSchema> }
  | { event: "failure"; data: z.infer<typeof AnswerFailureDataSchema> };
