import { render } from "preact";
import { useEffect, useState } from "preact/hooks";
import { ScanPanel } from "./ScanPanel";
import "./styles.css";

interface Product {
  id: number;
  name: string;
}

// Relative on purpose: Ingress serves the app under a dynamic path.
const PRODUCTS_URL = "api/products";

function App() {
  const [products, setProducts] = useState<Product[]>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  async function refresh() {
    const response = await fetch(PRODUCTS_URL);
    if (!response.ok) throw new Error(`Loading failed (${response.status})`);
    setProducts(await response.json());
  }

  useEffect(() => {
    refresh().catch((e: Error) => setError(e.message));
  }, []);

  async function addProduct(event: Event) {
    event.preventDefault();
    setError("");
    try {
      const response = await fetch(PRODUCTS_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (!response.ok) throw new Error(`Saving failed (${response.status})`);
      setName("");
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <main>
      <h1>Pantry</h1>
      <ScanPanel />
      <form onSubmit={addProduct}>
        <input
          aria-label="Product name"
          value={name}
          onInput={(e) => setName(e.currentTarget.value)}
        />
        <button type="submit">Add</button>
      </form>
      {error && <p role="alert">{error}</p>}
      <ul>
        {products.map((product) => (
          <li key={product.id}>{product.name}</li>
        ))}
      </ul>
    </main>
  );
}

render(<App />, document.getElementById("app")!);
