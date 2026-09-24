import { z } from "zod";

export const ApiErrorEnvelopeSchema = z.object({
  error: z.object({
    code: z.string(),
    message_key: z.string(),
    request_id: z.string(),
    details: z
      .array(
        z.object({
          field: z.string(),
          code: z.string(),
        }),
      )
      .optional(),
  }),
});

export type ApiErrorEnvelope = z.infer<typeof ApiErrorEnvelopeSchema>;
