import { useEffect, useRef, useState } from "preact/hooks";
import { createScanDetector } from "./scanner";

/** Removes a scan from a text box it was typed into by mistake. */
function removeScannedText(code: string) {
  const active = document.activeElement;
  if (!(active instanceof HTMLInputElement) || active.readOnly) return;
  if (!active.value.endsWith(code)) return;
  active.value = active.value.slice(0, -code.length);
  active.dispatchEvent(new Event("input", { bubbles: true }));
}

/** Captures scans anywhere on the page and shows whether the page can receive them. */
export function ScanStatus({ onScan }: { onScan: (code: string) => void }) {
  const sentinel = useRef<HTMLInputElement>(null);
  const [focused, setFocused] = useState(document.hasFocus());
  const latestOnScan = useRef(onScan);
  latestOnScan.current = onScan;

  useEffect(() => {
    const detector = createScanDetector({
      onScan: (code) => {
        removeScannedText(code);
        latestOnScan.current(code);
      },
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
    <>
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
    </>
  );
}
