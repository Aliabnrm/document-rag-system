import { afterEach, describe, expect, it, vi } from "vitest";

import { parseEventStreamBuffer, streamAnswerApi } from "./answer-stream.api";

afterEach(() => {
  document.cookie = "docqa_csrf_dev=; Max-Age=0; path=/";
  vi.unstubAllGlobals();
});

describe("streamAnswerApi", () => {
  it("sends the session cookie and CSRF header with the streaming request", async () => {
    document.cookie = "docqa_csrf_dev=csrf-token; path=/";
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      body: null,
    });
    vi.stubGlobal("fetch", fetchMock);
    const controller = new AbortController();

    await expect(
      streamAnswerApi({
        conversationId: "conversation-1",
        question: "What is the policy?",
        language: "en",
        signal: controller.signal,
        onEvent: vi.fn(),
      }),
    ).rejects.toMatchObject({ code: "stream_unavailable" });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/conversations/conversation-1/messages:stream",
      {
        method: "POST",
        credentials: "include",
        headers: {
          Accept: "text/event-stream",
          "Content-Type": "application/json",
          "X-CSRF-Token": "csrf-token",
        },
        body: JSON.stringify({
          question: "What is the policy?",
          language: "en",
        }),
        signal: controller.signal,
      },
    );
  });
});

describe("parseEventStreamBuffer", () => {
  it("keeps incomplete frames and returns typed answer events", () => {
    const first = parseEventStreamBuffer(
      'event: retrieval_completed\ndata: {"evidence_count":2}\n\nevent: answer_delta\nda',
    );

    expect(first.events).toEqual([
      { event: "retrieval_completed", data: { evidence_count: 2 } },
    ]);
    expect(first.remaining).toBe("event: answer_delta\nda");

    const second = parseEventStreamBuffer(
      `${first.remaining}ta: {"text":"Grounded "}\n\n`,
    );
    expect(second.events).toEqual([
      { event: "answer_delta", data: { text: "Grounded " } },
    ]);
    expect(second.remaining).toBe("");
  });

  it("rejects malformed citation payloads", () => {
    const parsed = parseEventStreamBuffer(
      'event: citations\ndata: {"items":[{"evidence_id":"E1"}]}\n\n',
    );

    expect(parsed.events).toEqual([]);
  });
});
