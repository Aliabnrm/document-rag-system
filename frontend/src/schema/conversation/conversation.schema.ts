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

export const ConversationListPageSchema = z.object({
  items: z.array(ConversationSchema),
  next_cursor: z.string().nullable(),
});

export const PersistedMessageSchema = z.object({
  id: z.string().uuid(),
  position: z.number().int().nonnegative(),
  role: z.enum(["user", "assistant"]),
  content: z.string(),
  language: z.string(),
  created_at: z.string(),
  citations: CitationListSchema,
});

export const MessageListPageSchema = z.object({
  items: z.array(PersistedMessageSchema),
  next_position: z.number().int().nonnegative().nullable(),
});

export type Conversation = z.infer<typeof ConversationSchema>;
export type Citation = z.infer<typeof CitationSchema>;
export type ConversationListPage = z.infer<typeof ConversationListPageSchema>;
export type PersistedMessage = z.infer<typeof PersistedMessageSchema>;
export type MessageListPage = z.infer<typeof MessageListPageSchema>;
