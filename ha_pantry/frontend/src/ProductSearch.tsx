import { useEffect, useState } from "preact/hooks";
import { searchProducts } from "./api";
import type { Named } from "./api";

interface Props {
  label: string;
  run: (action: () => Promise<void>) => Promise<boolean>;
  onPick: (product: Named) => void;
}

const SEARCH_DELAY_MS = 200;

/** Searches Grocy's products by name. No autofocus, so a tablet keeps its keyboard closed. */
export function ProductSearch({ label, run, onPick }: Props) {
  const [text, setText] = useState("");
  const [results, setResults] = useState<Named[]>();

  useEffect(() => {
    let current = true;
    const timer = setTimeout(() => {
      run(async () => {
        const products = await searchProducts(text);
        if (current) setResults(products);
      });
    }, SEARCH_DELAY_MS);
    return () => {
      current = false;
      clearTimeout(timer);
    };
  }, [text]);

  return (
    <>
      <input
        class="search"
        type="search"
        aria-label={label}
        placeholder={label}
        value={text}
        onInput={(event) => setText(event.currentTarget.value)}
      />
      {results?.length === 0 && <p>No products match.</p>}
      <ul class="plain products">
        {results?.map((product) => (
          <li key={product.id}>
            <button type="button" onClick={() => onPick(product)}>
              <span>{product.name}</span>
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}
