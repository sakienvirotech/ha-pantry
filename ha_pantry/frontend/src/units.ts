import type { Named } from "./api";

const GRAMS_PER_UNIT: Record<string, number> = { g: 1, kg: 1000, ml: 1, l: 1000 };
const KIND: Record<string, string> = { g: "mass", kg: "mass", ml: "volume", l: "volume" };

interface Size {
  amount: number;
  kind: string;
}

/** Reads the first size in text such as "400 g e", "1kg" or "Jar - 375g". */
export function parseSize(text: string): Size | null {
  const match = /(\d+(?:[.,]\d+)?)\s*(kg|g|ml|l)\b/i.exec(text);
  if (!match) return null;
  const unit = match[2].toLowerCase();
  const amount = Number(match[1].replace(",", ".")) * GRAMS_PER_UNIT[unit];
  return { amount: Math.round(amount), kind: KIND[unit] };
}

/** Grocy units whose name includes the same pack size, such as "Can - 440g". */
export function unitsMatchingSize(units: Named[], quantity: string | null): Named[] {
  const size = quantity ? parseSize(quantity) : null;
  if (!size) return [];
  return units.filter((unit) => {
    const unitSize = parseSize(unit.name);
    return unitSize?.kind === size.kind && unitSize.amount === size.amount;
  });
}

export function fallbackUnit(units: Named[]): Named | undefined {
  return units.find((unit) => unit.name.toLowerCase() === "piece") ?? units[0];
}

/** Follows the "Name - Brand" pattern used in this household's Grocy. */
export function suggestedName(name: string, brand: string | null): string {
  const brands = (brand ?? "").split(",").map((b) => b.trim()).filter(Boolean);
  const lowerName = name.toLowerCase();
  if (brands.length === 0 || brands.some((b) => lowerName.includes(b.toLowerCase()))) {
    return name;
  }
  return `${name} - ${brands[0]}`;
}
