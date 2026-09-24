import { describe, expect, it } from "vitest";

import { parseEventStreamBuffer } from "./api";

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

  it("rejects malformed citation payloads instead of trusting the stream", () => {
    const parsed = parseEventStreamBuffer(
      'event: citations\ndata: {"items":[{"evidence_id":"E1"}]}\n\n',
    );

    expect(parsed.events).toEqual([]);
  });
});
