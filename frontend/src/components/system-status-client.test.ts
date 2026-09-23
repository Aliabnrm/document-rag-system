import { afterEach, describe, expect, it, vi } from "vitest";

import { getHealth } from "./system-status-client";

describe("getHealth", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("accepts the documented API contract", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      status: "ok",
      service: "document-qa-api",
      version: "0.1.0",
    }), { status: 200 })));

    await expect(getHealth()).resolves.toMatchObject({ status: "ok" });
  });

  it("rejects an incompatible API response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      status: "healthy",
    }), { status: 200 })));

    await expect(getHealth()).rejects.toThrow();
  });
});
