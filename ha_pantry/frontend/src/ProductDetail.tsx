import { useState } from "preact/hooks";
import type { Product } from "./api";
import { isSavedOpenFoodFactsPicture, PictureCredit } from "./credits";

interface Props {
  product: Product;
  onAddStock: (bestBeforeDate: string | null) => Promise<boolean>;
  onRemoveStock: () => Promise<boolean>;
  onUnlinkBarcode: (barcodeId: number) => void;
  onBack: () => void;
}

export function ProductDetail({
  product,
  onAddStock,
  onRemoveStock,
  onUnlinkBarcode,
  onBack,
}: Props) {
  const [busy, setBusy] = useState(false);
  const [dueDate, setDueDate] = useState("");

  async function changeStock(change: () => Promise<boolean>) {
    setBusy(true);
    await change();
    setBusy(false);
  }

  return (
    <article>
      <h2>{product.name}</h2>
      {product.picture && (
        <figure class="product-image">
          <img
            class="grocy-picture"
            // The file name changes with the picture, so a new one is never cached as the old.
            src={`api/products/${product.id}/picture?v=${encodeURIComponent(product.picture)}`}
            alt=""
          />
          {isSavedOpenFoodFactsPicture(product.picture) && (
            <figcaption>
              <PictureCredit />
            </figcaption>
          )}
        </figure>
      )}
      <dl class="facts">
        <dt>Unit</dt>
        <dd>{product.unit}</dd>
        <dt>Location</dt>
        <dd>{product.location ?? "Not set"}</dd>
        <dt>Group</dt>
        <dd>{product.group ?? "None"}</dd>
      </dl>

      <div class="stock">
        <button
          type="button"
          aria-label="Remove 1"
          disabled={busy || product.stock_amount < 1}
          onClick={() => changeStock(onRemoveStock)}
        >
          −
        </button>
        <output aria-label="In stock">{product.stock_amount}</output>
        <button
          type="button"
          aria-label="Add 1"
          disabled={busy}
          onClick={() => changeStock(() => onAddStock(dueDate || null))}
        >
          +
        </button>
      </div>
      <label class="due-date">
        Due date for added stock
        <input
          type="date"
          value={dueDate}
          onInput={(event) => setDueDate(event.currentTarget.value)}
        />
        <small>Leave blank for never overdue.</small>
      </label>

      <h3>Barcodes</h3>
      {product.barcodes.length === 0 && <p>None yet.</p>}
      <ul class="plain">
        {product.barcodes.map((barcode) => (
          <li key={barcode.id}>
            <span>{barcode.code}</span>
            <button type="button" onClick={() => onUnlinkBarcode(barcode.id)}>
              Remove
            </button>
          </li>
        ))}
      </ul>

      <p>Edit other details, or delete the product, in Grocy.</p>
      <div class="actions">
        <button type="button" onClick={onBack}>
          Back
        </button>
      </div>
    </article>
  );
}
