import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import messages from "../../../../messages/en.json";

import { ChatMessageItem } from "./chat-message-item";

describe("ChatMessageItem", () => {
  it("does not leave an empty card while waiting for displayable model text", () => {
    render(
      <NextIntlClientProvider locale="en" messages={messages}>
        <ChatMessageItem
          message={{
            id: "answer-streaming",
            role: "assistant",
            content: "",
            status: "streaming",
          }}
          onCitationSelect={vi.fn()}
          onFeedback={vi.fn()}
          feedbackPending={false}
        />
      </NextIntlClientProvider>,
    );

    expect(
      screen.getByText("Checking whether the evidence is sufficient…"),
    ).toBeVisible();
  });

  it("renders a useful abstention state even when the answer text is empty", () => {
    render(
      <NextIntlClientProvider locale="en" messages={messages}>
        <ChatMessageItem
          message={{
            id: "answer-1",
            role: "assistant",
            content: "",
            status: "complete",
            abstained: true,
            citations: [],
          }}
          onCitationSelect={vi.fn()}
          onFeedback={vi.fn()}
          feedbackPending={false}
        />
      </NextIntlClientProvider>,
    );

    expect(screen.getByRole("status")).toHaveTextContent(
      "No answer found in the documents",
    );
    expect(screen.getByText("Document check result")).toBeVisible();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Try exact names, dates, or terms",
    );
    expect(screen.queryByText("Grounded answer text from the backend")).not.toBeInTheDocument();
  });
});
