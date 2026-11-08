import { describe, expect, it } from "vitest";
import {
  fallbackUnit,
  formatSize,
  parseSize,
  suggestedName,
  unitsMatchingSize,
} from "./units";

const units = [
  { id: 1, name: "Piece" },
  { id: 2, name: "Can - 440g" },
  { id: 3, name: "Jar - 375g" },
  { id: 4, name: "Packet - 375g" },
  { id: 5, name: "Packet - 1kg" },
  { id: 6, name: "Bottle - 500ml" },
];

describe("parseSize", () => {
  it.each([
    ["400 g e", { amount: 400, kind: "mass" }],
    ["1kg", { amount: 1000, kind: "mass" }],
    ["1,5 kg", { amount: 1500, kind: "mass" }],
    ["Jar - 375g", { amount: 375, kind: "mass" }],
    ["500 mL", { amount: 500, kind: "volume" }],
    ["1.25 L", { amount: 1250, kind: "volume" }],
  ])("reads %j", (text, size) => {
    expect(parseSize(text)).toEqual(size);
  });

  it.each(["Piece", "6 x", "12 pack", ""])("finds no size in %j", (text) => {
    expect(parseSize(text)).toBeNull();
  });
});

describe("formatSize", () => {
  it.each([
    ["440 g", "440g"],
    ["1kg", "1kg"],
    ["1,5 L", "1.5l"],
    ["1.25 L", "1.25l"],
    ["500 mL", "500ml"],
  ])("writes %j as %j", (text, written) => {
    expect(formatSize(parseSize(text)!)).toBe(written);
  });
});

describe("unitsMatchingSize", () => {
  it("matches on the size whatever the container", () => {
    expect(unitsMatchingSize(units, "375 g").map((u) => u.id)).toEqual([3, 4]);
  });

  it("compares in the same measure", () => {
    expect(unitsMatchingSize(units, "1000 g").map((u) => u.id)).toEqual([5]);
    expect(unitsMatchingSize(units, "500 g")).toEqual([]);
    expect(unitsMatchingSize(units, "0.5 l").map((u) => u.id)).toEqual([6]);
  });

  it("matches nothing without a size", () => {
    expect(unitsMatchingSize(units, null)).toEqual([]);
    expect(unitsMatchingSize(units, "6 pack")).toEqual([]);
  });
});

describe("fallbackUnit", () => {
  it("prefers Piece", () => {
    expect(fallbackUnit(units)?.id).toBe(1);
    expect(fallbackUnit(units.slice(1))?.id).toBe(2);
    expect(fallbackUnit([])).toBeUndefined();
  });
});

describe("suggestedName", () => {
  it("adds the first brand", () => {
    expect(suggestedName("Apricot Halves", "SPC")).toBe("Apricot Halves - SPC");
    expect(suggestedName("Powerade", "Coca-Cola, Powerade")).toBe("Powerade");
    expect(suggestedName("Mountain Blast", "Coca-Cola, Powerade")).toBe(
      "Mountain Blast - Coca-Cola",
    );
  });

  it("leaves the name alone without a brand", () => {
    expect(suggestedName("Oats", null)).toBe("Oats");
    expect(suggestedName("Oats", " ")).toBe("Oats");
  });
});
