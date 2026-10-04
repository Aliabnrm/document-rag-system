import { z } from "zod";

export const CollectionSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  description: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const CreateCollectionInputSchema = z.object({
  name: z.string().trim().min(1).max(160),
  description: z.string().trim().max(1000).optional(),
});

export const CollectionListPageSchema = z.object({
  items: z.array(CollectionSchema),
  next_cursor: z.string().nullable(),
});

export type Collection = z.infer<typeof CollectionSchema>;
export type CreateCollectionInput = z.infer<typeof CreateCollectionInputSchema>;
export type CollectionListPage = z.infer<typeof CollectionListPageSchema>;
