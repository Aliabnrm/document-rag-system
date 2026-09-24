import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import messages from "../../../messages/en.json";
import { createCollectionApi } from "@/services/api/collections/collections.api";
import { listDocumentsApi } from "@/services/api/documents/documents.api";

import { DocumentQaWorkspace } from "./document-qa-workspace";

vi.mock("@/services/api/collections/collections.api", () => ({
  createCollectionApi: vi.fn(),
  getCollectionApi: vi.fn(),
}));

vi.mock("@/services/api/documents/documents.api", () => ({
  listDocumentsApi: vi.fn(),
  uploadDocumentApi: vi.fn(),
  retryDocumentApi: vi.fn(),
}));

const collection = {
  id: "c86a2b1c-998e-4c87-9e34-1c7118dc96d3",
  name: "Product policies",
  description: null,
  created_at: "2026-09-24T08:00:00Z",
  updated_at: "2026-09-24T08:00:00Z",
};

function TestProviders({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return (
    <NextIntlClientProvider locale="en" messages={messages}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </NextIntlClientProvider>
  );
}

describe("DocumentQaWorkspace", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.mocked(createCollectionApi).mockResolvedValue(collection);
    vi.mocked(listDocumentsApi).mockResolvedValue({
      items: [],
      next_cursor: null,
    });
  });

  afterEach(() => vi.clearAllMocks());

  it("creates a collection and keeps chat disabled until evidence is ready", async () => {
    const user = userEvent.setup();

    render(<DocumentQaWorkspace locale="en" />, {
      wrapper: TestProviders,
    });

    await user.type(await screen.findByLabelText("Collection name"), "Product policies");
    await user.click(screen.getByRole("button", { name: "Create collection" }));

    expect(await screen.findByRole("heading", { name: "Product policies" })).toBeVisible();
    expect(screen.getByLabelText("Your question")).toBeDisabled();
    expect(window.localStorage.getItem("document-qa.collection-id")).toBe(collection.id);
    expect(createCollectionApi).toHaveBeenCalledWith(
      expect.anything(),
      { name: "Product policies", description: undefined },
    );
  });
});
