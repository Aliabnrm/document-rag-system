import { z } from "zod";

const healthResponseSchema = z.object({
  status: z.literal("ok"),
  service: z.literal("document-qa-api"),
  version: z.string().min(1),
});

export type HealthResponse = z.infer<typeof healthResponseSchema>;

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const response = await fetch(`${baseUrl}/api/v1/health`, {
    signal,
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error(`Health request failed with status ${response.status}`);
  }

  return healthResponseSchema.parse(await response.json());
}
