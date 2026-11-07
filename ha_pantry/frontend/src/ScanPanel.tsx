import { useEffect, useRef, useState } from "preact/hooks";
import { createScanDetector } from "./scanner";

interface LogEntry {
  id: number;
  time: string;
  result: string;
  slowestGapMs: number;
}

const LOG_SIZE = 10;

/** Removes a scan from a text box it was typed into by mistake. */
function removeScannedText(code: string) {
  const active = document.activeElement;
  if (!(active instanceof HTMLInputElement) || active.readOnly) return;
  if (!active.value.endsWith(code)) return;
  active.value = active.value.slice(0, -code.length);
  active.dispatchEvent(new Event("input", { bubbles: true }));
}

export function ScanPanel() {
  const sentinel = useRef<HTMLInputElement>(null);
  const [focused, setFocused] = useState(document.hasFocus());
  const [log, setLog] = useState<LogEntry[]>([]);

  useEffect(() => {
    let nextId = 0;
    const addEntry = (result: string, slowestGapMs: number) => {
      const entry = {
        id: nextId++,
        time: new Date().toLocaleTimeString(),
        result,
        slowestGapMs: Math.round(slowestGapMs),
      };
      setLog((entries) => [entry, ...entries].slice(0, LOG_SIZE));
    };

    const detector = createScanDetector({
      onScan: (code, { slowestGapMs }) => {
        removeScannedText(code);
        addEntry(code, slowestGapMs);
      },
      onReject: (length, { slowestGapMs }) =>
        addEntry(`Too slow for a scan (${length} characters)`, slowestGapMs),
    });

    const onKeyDown = (event: KeyboardEvent) => {
      const modifier = event.ctrlKey || event.altKey || event.metaKey;
      if (detector.handleKey(event.key, event.timeStamp, modifier)) {
        event.preventDefault();
        event.stopPropagation();
      }
    };

    // Keystrokes reach this page only while its Ingress iframe has focus.
    const claimFocus = () => {
      if (document.activeElement === document.body || !document.activeElement) {
        sentinel.current?.focus({ preventScroll: true });
      }
      setFocused(document.hasFocus());
    };
    const onBlur = () => setFocused(false);
    const onFocusOut = (event: FocusEvent) => {
      if (!event.relatedTarget) setTimeout(claimFocus);
    };

    window.addEventListener("keydown", onKeyDown, true);
    window.addEventListener("focus", claimFocus);
    window.addEventListener("blur", onBlur);
    document.addEventListener("focusout", onFocusOut);
    document.addEventListener("visibilitychange", claimFocus);
    claimFocus();

    return () => {
      window.removeEventListener("keydown", onKeyDown, true);
      window.removeEventListener("focus", claimFocus);
      window.removeEventListener("blur", onBlur);
      document.removeEventListener("focusout", onFocusOut);
      document.removeEventListener("visibilitychange", claimFocus);
    };
  }, []);

  return (
    <section aria-label="Scanner test">
      {/* Read-only with no input mode, so a tablet keeps its on-screen keyboard closed. */}
      <input
        ref={sentinel}
        class="scan-sentinel"
        readOnly
        inputMode="none"
        tabIndex={-1}
        aria-hidden="true"
      />
      <button
        type="button"
        class={focused ? "scan-status ready" : "scan-status waiting"}
        onClick={() => sentinel.current?.focus({ preventScroll: true })}
      >
        {focused ? "Ready to scan" : "Tap here to scan"}
      </button>
      {log.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Result</th>
              <th>Slowest gap</th>
            </tr>
          </thead>
          <tbody>
            {log.map((entry) => (
              <tr key={entry.id}>
                <td>{entry.time}</td>
                <td>{entry.result}</td>
                <td>{entry.slowestGapMs} ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
