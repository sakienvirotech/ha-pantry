import { useEffect, useMemo, useState } from "preact/hooks";
import { lookupBarcode } from "./api";
import type { LookupResult, Product, ProductDetails } from "./api";
import { ProductForm } from "./ProductForm";

interface Props {
  code: string;
  products: Product[];
  onCreate: (details: ProductDetails) => void;
  onLink: (productId: number) => void;
  onCancel: () => void;
}

export function UnknownBarcode({ code, products, onCreate, onLink, onCancel }: Props) {
  const [productId, setProductId] = useState("");
  // Undefined while waiting. The form is usable throughout, as the lookup is only a help.
  const [lookup, setLookup] = useState<LookupResult>();

  useEffect(() => {
    let current = true;
    lookupBarcode(code)
      .catch((): LookupResult => ({ match: null, failed: true }))
      .then((result) => {
        if (current) setLookup(result);
      });
    return () => {
      current = false;
    };
  }, [code]);

  const match = lookup?.match;
  // Memoised so a re-render can't refill a field the user has just cleared.
  const suggestion = useMemo(
    () => (match ? { ...match, brand: match.brand ?? "" } : null),
    [match],
  );

  return (
    <article>
      <h2>New barcode</h2>
      <p class="code">{code}</p>

      <h3>Add a product</h3>
      <p role="status">
        {!lookup && "Looking this up online…"}
        {match && (
          <>
            Found on{" "}
            <a href={match.source_url} target="_blank" rel="noreferrer">
              {match.source}
            </a>
            . Check the details before saving.
          </>
        )}
        {lookup && !match && !lookup.failed && "No match online. Enter the details below."}
        {lookup &&
          !match &&
          lookup.failed &&
          "Online lookup isn't available right now. Enter the details below."}
      </p>
      <ProductForm
        suggestion={suggestion}
        submitLabel="Add product"
        onSubmit={onCreate}
        onCancel={onCancel}
      />

      {products.length > 0 && (
        <>
          <h3>Or add this barcode to a product</h3>
          <div class="actions">
            <select
              aria-label="Product"
              value={productId}
              onChange={(event) => setProductId(event.currentTarget.value)}
            >
              <option value="">Choose a product</option>
              {products.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.name}
                </option>
              ))}
            </select>
            <button
              type="button"
              disabled={!productId}
              onClick={() => onLink(Number(productId))}
            >
              Add barcode
            </button>
          </div>
        </>
      )}
    </article>
  );
}
