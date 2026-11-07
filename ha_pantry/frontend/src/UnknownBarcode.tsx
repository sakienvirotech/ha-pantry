import { useState } from "preact/hooks";
import type { Product, ProductDetails } from "./api";
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

  return (
    <article>
      <h2>New barcode</h2>
      <p class="code">{code}</p>

      <h3>Add a product</h3>
      <ProductForm submitLabel="Add product" onSubmit={onCreate} onCancel={onCancel} />

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
