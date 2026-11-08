import { render } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import * as api from "./api";
import type { Product, Setup, Status } from "./api";
import { ProductDetail } from "./ProductDetail";
import { ProductSearch } from "./ProductSearch";
import { ScanStatus } from "./ScanStatus";
import { UnknownBarcode } from "./UnknownBarcode";
import "./styles.css";

type View =
  | { kind: "home" }
  | { kind: "product"; product: Product }
  | { kind: "unknown"; code: string };

const HOME: View = { kind: "home" };
// Focus and visibility changes come in pairs, so one refresh covers both.
const REFRESH_GAP_MS = 2000;

function App() {
  const [view, setView] = useState<View>(HOME);
  const [status, setStatus] = useState<Status>();
  const [setup, setSetup] = useState<Setup>();
  const [error, setError] = useState("");
  const latestScan = useRef(0);
  const connected = useRef(false);
  const setupRefresh = useRef({ running: false, finished: 0 });

  async function run(action: () => Promise<void>) {
    setError("");
    try {
      await action();
      return true;
    } catch (e) {
      setError((e as Error).message);
      return false;
    }
  }

  async function connect() {
    const result = await api.getStatus();
    setStatus(result);
    connected.current = result.connected;
    if (result.connected) setSetup(await api.getSetup());
  }

  /**
   * Picks up units, locations, groups and userfields added in Grocy since the
   * app loaded, for example in another tab. A failure keeps the lists already
   * shown, as they still work for creating a product.
   */
  async function refreshSetup(force = false) {
    const state = setupRefresh.current;
    if (!connected.current || state.running) return;
    if (!force && Date.now() - state.finished < REFRESH_GAP_MS) return;
    state.running = true;
    try {
      setSetup(await api.getSetup());
    } catch {
      // Keep the lists already shown.
    } finally {
      state.running = false;
      state.finished = Date.now();
    }
  }

  useEffect(() => {
    run(connect);
    const onVisible = () => {
      if (document.visibilityState === "visible") refreshSetup();
    };
    const onFocus = () => refreshSetup();
    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener("focus", onFocus);
    return () => {
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("focus", onFocus);
    };
  }, []);

  function handleScan(code: string) {
    // Scans can arrive faster than Grocy answers, and the last one should win.
    const scan = ++latestScan.current;
    run(async () => {
      try {
        const product = await api.findByBarcode(code);
        if (scan === latestScan.current) setView({ kind: "product", product });
      } catch (e) {
        if (!(e instanceof api.ApiError && e.status === 404)) throw e;
        if (scan === latestScan.current) setView({ kind: "unknown", code });
      }
    });
  }

  const openProduct = (id: number) =>
    run(async () => setView({ kind: "product", product: await api.getProduct(id) }));

  const update = (change: () => Promise<Product>) =>
    run(async () => {
      const product = await change();
      setView({ kind: "product", product });
      if (product.warning) setError(product.warning);
    });

  function renderView() {
    switch (view.kind) {
      case "home":
        return (
          <>
            <p>Scan a barcode, or find a product in Grocy.</p>
            <ProductSearch
              label="Search Grocy products"
              run={run}
              onPick={(product) => openProduct(product.id)}
            />
          </>
        );
      case "unknown":
        return (
          <UnknownBarcode
            key={view.code}
            code={view.code}
            setup={setup}
            run={run}
            onCreate={(product) =>
              update(() => api.createProduct({ ...product, barcode: view.code }))
            }
            onLink={(product) => update(() => api.linkBarcode(product.id, view.code))}
            onUnitCreated={(unit) =>
              setSetup((current) => current && { ...current, units: [...current.units, unit] })
            }
            onRefreshSetup={refreshSetup}
            onCancel={() => setView(HOME)}
          />
        );
      case "product": {
        const { id } = view.product;
        return (
          <ProductDetail
            key={id}
            product={view.product}
            onAddStock={(date) => update(() => api.addStock(id, date))}
            onRemoveStock={() => update(() => api.removeStock(id))}
            onUnlinkBarcode={(barcodeId) => update(() => api.unlinkBarcode(id, barcodeId))}
            onBack={() => setView(HOME)}
          />
        );
      }
    }
  }

  return (
    <main>
      <h1>Pantry</h1>
      <ScanStatus onScan={handleScan} />
      {status && !status.connected && (
        <div role="alert" class="problem">
          <p>{status.message}</p>
          <button type="button" onClick={() => run(connect)}>
            Try again
          </button>
        </div>
      )}
      {error && <p role="alert">{error}</p>}
      {renderView()}
    </main>
  );
}

render(<App />, document.getElementById("app")!);
