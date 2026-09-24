import { z } from "zod";

const RuntimeConfigSchema = z.object({
  apiBaseUrl: z.string().url(),
});

export const runtimeConfig = RuntimeConfigSchema.parse({
  apiBaseUrl: (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(
    /\/$/,
    "",
  ),
});
