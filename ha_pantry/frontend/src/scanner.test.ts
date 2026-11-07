import { describe, expect, it, vi } from "vitest";
import { createScanDetector } from "./scanner";

function setup() {
  const onScan = vi.fn();
  const onReject = vi.fn();
  const detector = createScanDetector({ onScan, onReject });
  let time = 1000;
  const type = (text: string, gapMs: number) => {
    let result = false;
    for (const key of [...text, "Enter"]) {
      time += gapMs;
      result = detector.handleKey(key, time, false);
    }
    return result;
  };
  const typeWithoutEnter = (text: string, gapMs: number) => {
    for (const key of text) {
      time += gapMs;
      detector.handleKey(key, time, false);
    }
  };
  const wait = (ms: number) => {
    time += ms;
  };
  return { onScan, onReject, type, typeWithoutEnter, wait, detector, now: () => time };
}

describe("createScanDetector", () => {
  it("detects a fast burst ending in Enter and suppresses the Enter", () => {
    const { onScan, onReject, type } = setup();
    expect(type("9300675024235", 10)).toBe(true);
    expect(onScan).toHaveBeenCalledWith("9300675024235", { slowestGapMs: 10 });
    expect(onReject).not.toHaveBeenCalled();
  });

  it("accepts the slowest scan measured on real hardware", () => {
    const { onScan, onReject, type } = setup();
    expect(type("9300675024235", 76)).toBe(true);
    expect(onScan).toHaveBeenCalledWith("9300675024235", { slowestGapMs: 76 });
    expect(onReject).not.toHaveBeenCalled();
  });

  it("leaves human typing alone but reports it as too slow", () => {
    const { onScan, onReject, type } = setup();
    expect(type("rolled oats", 120)).toBe(false);
    expect(onScan).not.toHaveBeenCalled();
    expect(onReject).toHaveBeenCalledWith(11, { slowestGapMs: 120 });
  });

  it("ignores a short fast entry", () => {
    const { onScan, onReject, type } = setup();
    expect(type("123", 10)).toBe(false);
    expect(onScan).not.toHaveBeenCalled();
    expect(onReject).not.toHaveBeenCalled();
  });

  it("finds a scan straight after typing", () => {
    const { onScan, type, typeWithoutEnter, wait } = setup();
    typeWithoutEnter("oats", 120);
    wait(200);
    expect(type("93006750", 10)).toBe(true);
    expect(onScan.mock.calls[0][0]).toBe("93006750");
  });

  it("forgets keystrokes from before a long pause", () => {
    const { onScan, type, typeWithoutEnter, wait } = setup();
    typeWithoutEnter("abc", 10);
    wait(1000);
    expect(type("93006750", 10)).toBe(true);
    expect(onScan.mock.calls[0][0]).toBe("93006750");
  });

  it("rejects a burst followed by a slow Enter", () => {
    const { onScan, onReject, typeWithoutEnter, detector, now } = setup();
    typeWithoutEnter("93006750", 10);
    expect(detector.handleKey("Enter", now() + 200, false)).toBe(false);
    expect(onScan).not.toHaveBeenCalled();
    expect(onReject).toHaveBeenCalledWith(8, { slowestGapMs: 200 });
  });

  it("does not let Shift break a code", () => {
    const { onScan, detector } = setup();
    let time = 1000;
    for (const key of ["A", "B", "Shift", "C", "1", "2", "3", "Enter"]) {
      time += 5;
      detector.handleKey(key, time, false);
    }
    expect(onScan.mock.calls[0][0]).toBe("ABC123");
  });

  it("discards input when a modifier shortcut is used", () => {
    const { onScan, detector } = setup();
    let time = 1000;
    for (const key of ["1", "2", "3", "4", "5", "6"]) {
      time += 5;
      detector.handleKey(key, time, false);
    }
    detector.handleKey("v", (time += 5), true);
    detector.handleKey("Enter", (time += 5), false);
    expect(onScan).not.toHaveBeenCalled();
  });
});
