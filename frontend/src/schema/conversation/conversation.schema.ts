import { z } from "zod";

export const ConversationSchema = z.object({
  id: z.string().uuid(),
  collection_id: z.string().uuid(),
  title: z.string().nullable(),
  created_at: z.string(),
});

export const CitationSchema = z.object({
  evidence_id: z.string(),
  document_name: z.string(),
  page_start: z.number(),
  page_end: z.number(),
  snippet: z.string(),
});

export const CitationListSchema = z.array(CitationSchema);

export type Conversation = z.infer<typeof ConversationSchema>;
export type Citation = z.infer<typeof CitationSchema>;
