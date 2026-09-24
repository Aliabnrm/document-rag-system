import { describe, expect, it } from "vitest";

import { applyAnswerEvent, type ChatMessage } from "./chat-message";

const assistantMessage: ChatMessage = {
  id: "assistant-1",
  role: "assistant",
  content: "Grounded",
  status: "streaming",
};

describe("applyAnswerEvent", () => {
  it("appends streamed deltas without discarding prior content", () => {
    expect(
      applyAnswerEvent(assistantMessage, {
        event: "answer_delta",
        data: { text: " answer" },
      }),
    ).toMatchObject({ content: "Grounded answer", status: "streaming" });
  });

  it("records the backend abstention decision on completion", () => {
    expect(
      applyAnswerEvent(assistantMessage, {
        event: "completed",
        data: { abstained: true, rag_run_id: "run-1" },
      }),
    ).toMatchObject({ abstained: true, status: "complete" });
  });
});
