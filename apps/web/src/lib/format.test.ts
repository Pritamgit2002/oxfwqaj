import { describe, expect, it } from "vitest";

import { clock, gw, gwh, longDate, mw, pct } from "./format";

describe("unit formatting", () => {
  it("formats power and energy with one decimal in GW/GWh", () => {
    expect(gw(12_345)).toBe("12.3 GW");
    expect(gwh(267_230)).toBe("267.2 GWh");
    expect(mw(5_329.4)).toBe("5,329 MW");
    expect(pct(85.94)).toBe("85.9%");
  });

  it("renders missing values as a dash", () => {
    expect(gw(null)).toBe("–");
    expect(mw(undefined)).toBe("–");
  });
});

describe("UK market time", () => {
  it("shows GMT in winter and BST in summer, whatever the viewer's timezone", () => {
    expect(clock("2026-01-15T09:00:00Z")).toBe("09:00");
    expect(clock("2026-07-01T08:00:00Z")).toBe("09:00");
  });

  it("formats calendar dates without shifting the day", () => {
    expect(longDate("2026-01-15")).toContain("15 Jan 2026");
  });
});
