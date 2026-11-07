export interface ScanTiming {
  /** Slowest gap between keystrokes, including the final Enter. */
  slowestGapMs: number;
}

export interface DetectorOptions {
  onScan: (code: string, timing: ScanTiming) => void;
  /** A code-length entry ended in Enter, but too slowly to count as a scan. */
  onReject: (length: number, timing: ScanTiming) => void;
  minLength?: number;
  maxGapMs?: number;
}

/** A longer pause than this means the keystrokes are unrelated. */
const UNRELATED_GAP_MS = 500;

interface Keystroke {
  char: string;
  gapMs: number;
}

/**
 * Tells scanner input from typing. Scanners act as keyboards, so the only
 * difference is speed: a scan is a fast burst of characters ending in Enter.
 */
export function createScanDetector({
  onScan,
  onReject,
  minLength = 6,
  maxGapMs = 100,
}: DetectorOptions) {
  let keystrokes: Keystroke[] = [];
  let lastTime = 0;

  /** Returns true when the key completed a scan and must not act as Enter. */
  function handleKey(key: string, time: number, hasModifier: boolean): boolean {
    const gapMs = time - lastTime;
    lastTime = time;

    if (key === "Enter") {
      const entered = keystrokes;
      keystrokes = [];
      return finish(entered, gapMs);
    }
    if (hasModifier) {
      keystrokes = [];
    } else if (key.length === 1) {
      if (gapMs > UNRELATED_GAP_MS) keystrokes = [];
      const first = keystrokes.length === 0;
      keystrokes.push({ char: key, gapMs: first ? 0 : gapMs });
    }
    return false;
  }

  function finish(entered: Keystroke[], enterGapMs: number): boolean {
    // Only the final fast run counts, so typing just before a scan doesn't spoil it.
    // Each keystroke holds the gap before it, so the run starts at the last slow gap.
    let start = Math.max(entered.length - 1, 0);
    while (start > 0 && entered[start].gapMs <= maxGapMs) start -= 1;
    const run = entered.slice(start);

    const slowestOf = (items: Keystroke[]) =>
      Math.max(enterGapMs, ...items.slice(1).map((item) => item.gapMs));

    if (run.length >= minLength && enterGapMs <= maxGapMs) {
      const code = run.map((item) => item.char).join("");
      onScan(code, { slowestGapMs: slowestOf(run) });
      return true;
    }
    if (entered.length >= minLength) {
      onReject(entered.length, { slowestGapMs: slowestOf(entered) });
    }
    return false;
  }

  return { handleKey };
}
