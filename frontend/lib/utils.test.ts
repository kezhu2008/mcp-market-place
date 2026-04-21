import { describe, it, expect } from "vitest";
import { cn, relativeTime, shortId } from "./utils";

describe("cn", () => {
  it("merges tailwind classes", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
  });
});

describe("relativeTime", () => {
  it("returns — for null", () => {
    expect(relativeTime(null)).toBe("—");
  });
  it("formats seconds", () => {
    expect(relativeTime(Date.now() - 30_000)).toMatch(/s ago$/);
  });
  it("formats minutes", () => {
    expect(relativeTime(Date.now() - 5 * 60_000)).toMatch(/m ago$/);
  });
});

describe("shortId", () => {
  it("passes through short ids", () => {
    expect(shortId("abc")).toBe("abc");
  });
  it("shortens long ids", () => {
    const s = shortId("0123456789abcdef0123");
    expect(s).toContain("…");
  });
});
