import { Fragment } from "preact";
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
        {product.userfields?.map((field) => (
          <Fragment key={field.caption}>
            <dt>{field.caption}</dt>
            <dd>{field.value}</dd>
          </Fragment>
        ))}
      </dl>

      {/* Before the buttons, as the date applies to stock added after it's picked. */}
      <label class="due-date">
        Due date for added stock
        <input
          type="date"
          value={dueDate}
          onInput={(event) => setDueDate(event.currentTarget.value)}
        />
        <small>Leave blank for never overdue.</small>
      </label>
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

      {product.edit_url ? (
        <p>
          <GrocyLink url={product.edit_url} />
        </p>
      ) : (
        <p>Edit other details, or delete the product, in Grocy.</p>
      )}
      <div class="actions">
        <button type="button" onClick={onBack}>
          Back
        </button>
      </div>
    </article>
  );
}

/**
 * A Home Assistant route such as /app/a0d7b954_grocy is absolute on purpose:
 * it's a page of Home Assistant's own UI, not a call to this app's API
 * through Ingress. It opens in the whole Home Assistant window rather than
 * inside this app's frame, at Grocy's front page, as Home Assistant can't
 * open an App at a page of its own. A Grocy outside Home Assistant opens at
 * the product, in a new tab.
 */
function GrocyLink({ url }: { url: string }) {
  return url.startsWith("/") ? (
    <>
      <a href={url} target="_top">
        Open Grocy
      </a>{" "}
      to edit or delete this product.
    </>
  ) : (
    <a href={url} target="_blank" rel="noopener noreferrer">
      Edit or delete this product in Grocy
    </a>
  );
}
