import { describe, expect, it } from "vitest";

import { csvCell, toCsv } from "./csv";

describe("csvCell", () => {
  it("rounds numbers to two decimals and leaves gaps empty", () => {
    expect(csvCell(1234.5678)).toBe("1234.57");
    expect(csvCell(-0.004)).toBe("0");
    expect(csvCell(null)).toBe("");
    expect(csvCell(undefined)).toBe("");
  });

  it("quotes cells containing commas, quotes or newlines", () => {
    expect(csvCell("2026-01-15T00:00:00Z")).toBe("2026-01-15T00:00:00Z");
    expect(csvCell("a,b")).toBe('"a,b"');
    expect(csvCell('say "hi"')).toBe('"say ""hi"""');
    expect(csvCell("two\nlines")).toBe('"two\nlines"');
  });
});

describe("toCsv", () => {
  it("writes the header then one line per row", () => {
    const csv = toCsv(
      ["start_time_utc", "forecast_mw", "actual_mw"],
      [
        ["2026-01-15T00:00:00Z", 11000, 10000.123],
        ["2026-01-15T00:30:00Z", null, 9950],
      ],
    );
    expect(csv.split("\n")).toEqual([
      "start_time_utc,forecast_mw,actual_mw",
      "2026-01-15T00:00:00Z,11000,10000.12",
      "2026-01-15T00:30:00Z,,9950",
    ]);
  });
});
