import { render } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import * as api from "./api";
import type { Product, ProductDetails } from "./api";
import { ProductDetail } from "./ProductDetail";
import { ProductForm } from "./ProductForm";
import { ScanStatus } from "./ScanStatus";
import { UnknownBarcode } from "./UnknownBarcode";
import "./styles.css";

type View =
  | { kind: "list" }
  | { kind: "new" }
  | { kind: "product"; product: Product }
  | { kind: "unknown"; code: string };

const LIST: View = { kind: "list" };

function App() {
  const [products, setProducts] = useState<Product[]>([]);
  const [view, setView] = useState<View>(LIST);
  const [error, setError] = useState("");
  const latestScan = useRef(0);

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

  const refresh = async () => setProducts(await api.listProducts());

  useEffect(() => {
    run(refresh);
  }, []);

  function showProduct(product: Product) {
    setView({ kind: "product", product });
    return refresh();
  }

  function handleScan(code: string) {
    // Scans can arrive faster than lookups return, and the last one should win.
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

  function create(details: ProductDetails, barcodes: string[]) {
    return run(async () => showProduct(await api.createProduct(details, barcodes)));
  }

  function renderView() {
    switch (view.kind) {
      case "list":
        return (
          <>
            <button type="button" onClick={() => setView({ kind: "new" })}>
              Add a product
            </button>
            <ul class="plain products">
              {products.map((product) => (
                <li key={product.id}>
                  <button
                    type="button"
                    onClick={() => setView({ kind: "product", product })}
                  >
                    <span>{product.name}</span>
                    <span>{product.quantity}</span>
                  </button>
                </li>
              ))}
            </ul>
          </>
        );
      case "new":
        return (
          <ProductForm
            submitLabel="Add product"
            onSubmit={(details) => create(details, [])}
            onCancel={() => setView(LIST)}
          />
        );
      case "unknown":
        return (
          <UnknownBarcode
            key={view.code}
            code={view.code}
            products={products}
            onCreate={(details) => create(details, [view.code])}
            onLink={(id) =>
              run(async () => showProduct(await api.linkBarcode(id, view.code)))
            }
            onCancel={() => setView(LIST)}
          />
        );
      case "product": {
        const { id } = view.product;
        return (
          <ProductDetail
            key={id}
            product={view.product}
            onAddStock={() => run(async () => showProduct(await api.addStock(id)))}
            onRemoveStock={() =>
              run(async () => showProduct(await api.removeStock(id)))
            }
            onEdit={(details) =>
              run(async () => showProduct(await api.updateProduct(id, details)))
            }
            onUnlinkBarcode={(barcodeId) =>
              run(async () => showProduct(await api.unlinkBarcode(id, barcodeId)))
            }
            onDelete={() =>
              run(async () => {
                await api.deleteProduct(id);
                setView(LIST);
                await refresh();
              })
            }
            onBack={() => setView(LIST)}
          />
        );
      }
    }
  }

  return (
    <main>
      <h1>Pantry</h1>
      <ScanStatus onScan={handleScan} />
      {error && <p role="alert">{error}</p>}
      {renderView()}
    </main>
  );
}

render(<App />, document.getElementById("app")!);
