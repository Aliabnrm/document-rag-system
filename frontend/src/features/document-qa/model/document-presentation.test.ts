import { describe, expect, it } from "vitest";

import { validateDocumentFile } from "./document-presentation";

describe("validateDocumentFile", () => {
  it("accepts the supported extensions", () => {
    expect(validateDocumentFile(new File(["text"], "guide.TXT"))).toBeNull();
    expect(validateDocumentFile(new File(["%PDF"], "guide.pdf"))).toBeNull();
  });

  it("rejects empty and unsupported files before upload", () => {
    expect(validateDocumentFile(new File([], "guide.txt"))).toBe("empty_file");
    expect(validateDocumentFile(new File(["data"], "guide.docx"))).toBe(
      "unsupported_file_type",
    );
  });
});
