import { describe, expect, it } from "vitest";

import { addDays, clampDate, first, isCutoff } from "./dates";

describe("addDays", () => {
  it("crosses month and year boundaries", () => {
    expect(addDays("2026-01-31", 1)).toBe("2026-02-01");
    expect(addDays("2026-01-01", -1)).toBe("2025-12-31");
  });

  it("is not affected by clock changes", () => {
    expect(addDays("2026-03-28", 1)).toBe("2026-03-29");
    expect(addDays("2026-03-29", 1)).toBe("2026-03-30");
  });
});

describe("clampDate", () => {
  const [min, max] = ["2026-01-01", "2026-01-31"];

  it("keeps dates inside the window", () => {
    expect(clampDate("2026-01-15", min, max)).toBe("2026-01-15");
  });

  it("clamps out-of-range dates to the nearest bound", () => {
    expect(clampDate("2025-12-01", min, max)).toBe(min);
    expect(clampDate("2026-03-01", min, max)).toBe(max);
  });

  it("falls back to the latest date for missing or malformed input", () => {
    expect(clampDate(undefined, min, max)).toBe(max);
    expect(clampDate("15/01/2026", min, max)).toBe(max);
  });
});

describe("isCutoff", () => {
  it("accepts HH:MM in 24h time only", () => {
    expect(isCutoff("09:00")).toBe(true);
    expect(isCutoff("23:59")).toBe(true);
    expect(isCutoff("24:00")).toBe(false);
    expect(isCutoff("9:00")).toBe(false);
    expect(isCutoff(undefined)).toBe(false);
  });
});

describe("first", () => {
  it("takes the first value of repeated query params", () => {
    expect(first(["a", "b"])).toBe("a");
    expect(first("a")).toBe("a");
    expect(first(undefined)).toBeUndefined();
  });
});
