import { z } from "zod";

const RuntimeConfigSchema = z.object({
  apiBaseUrl: z.string().url(),
  csrfCookieName: z.string().min(1),
});

export const runtimeConfig = RuntimeConfigSchema.parse({
  apiBaseUrl: (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(
    /\/$/,
    "",
  ),
  csrfCookieName:
    process.env.NEXT_PUBLIC_CSRF_COOKIE_NAME ?? "docqa_csrf_dev",
});
