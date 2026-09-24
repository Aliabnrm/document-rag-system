import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import messages from "../../../messages/en.json";
import { DocumentQaWorkspace } from "./workspace";

describe("DocumentQaWorkspace", () => {
  beforeEach(() => window.localStorage.clear());
  afterEach(() => vi.unstubAllGlobals());

  it("creates a collection and keeps chat disabled until evidence is ready", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "c86a2b1c-998e-4c87-9e34-1c7118dc96d3",
          name: "Product policies",
          description: null,
          created_at: "2026-09-24T08:00:00Z",
          updated_at: "2026-09-24T08:00:00Z",
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(
      <NextIntlClientProvider locale="en" messages={messages}>
        <DocumentQaWorkspace locale="en" />
      </NextIntlClientProvider>,
    );

    await user.type(await screen.findByLabelText("Collection name"), "Product policies");
    await user.click(screen.getByRole("button", { name: "Create collection" }));

    expect(await screen.findByRole("heading", { name: "Product policies" })).toBeVisible();
    expect(screen.getByLabelText("Your question")).toBeDisabled();
    expect(window.localStorage.getItem("document-qa.collection-id")).toBe(
      "c86a2b1c-998e-4c87-9e34-1c7118dc96d3",
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/collections",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
