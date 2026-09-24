import type { AxiosInstance } from "axios";
import { describe, expect, it, vi } from "vitest";

import { createCollectionApi } from "./collections.api";

describe("createCollectionApi", () => {
  it("uses the injected transport and validates the response", async () => {
    const payload = {
      id: "c86a2b1c-998e-4c87-9e34-1c7118dc96d3",
      name: "Policies",
      description: null,
      created_at: "2026-09-24T08:00:00Z",
      updated_at: "2026-09-24T08:00:00Z",
    };
    const post = vi.fn().mockResolvedValue({ data: payload });
    const api = { post } as unknown as AxiosInstance;

    await expect(
      createCollectionApi(api, { name: "Policies" }),
    ).resolves.toEqual(payload);
    expect(post).toHaveBeenCalledWith(
      "/api/v1/collections",
      { name: "Policies", description: null },
      { signal: undefined },
    );
  });

  it("converts incompatible contracts into a safe API error", async () => {
    const api = {
      post: vi.fn().mockResolvedValue({ data: { id: "not-a-uuid" } }),
    } as unknown as AxiosInstance;

    await expect(createCollectionApi(api, { name: "Policies" })).rejects.toEqual(
      expect.objectContaining({ code: "invalid_api_response" }),
    );
  });
});
