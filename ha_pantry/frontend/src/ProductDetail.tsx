import { useState } from "preact/hooks";
import type { Product, ProductDetails, Tag, TagKind } from "./api";
import { ProductForm } from "./ProductForm";
import { ProductImage } from "./ProductImage";

interface Props {
  product: Product;
  tags: Tag[];
  onCreateTag: (name: string, kind: TagKind) => Promise<Tag | null>;
  onTagClick: (tagId: number) => void;
  onAddStock: () => Promise<boolean>;
  onRemoveStock: () => Promise<boolean>;
  onEdit: (details: ProductDetails) => Promise<boolean>;
  onUnlinkBarcode: (barcodeId: number) => void;
  onDelete: () => void;
  onBack: () => void;
}

export function ProductDetail({
  product,
  tags,
  onCreateTag,
  onTagClick,
  onAddStock,
  onRemoveStock,
  onEdit,
  onUnlinkBarcode,
  onDelete,
  onBack,
}: Props) {
  const [editing, setEditing] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [busy, setBusy] = useState(false);

  async function changeStock(change: () => Promise<boolean>) {
    setBusy(true);
    await change();
    setBusy(false);
  }

  if (editing) {
    return (
      <ProductForm
        initial={{
          ...product,
          brand: product.brand ?? "",
          tag_ids: product.tags.map((tag) => tag.id),
        }}
        tags={tags}
        onCreateTag={onCreateTag}
        submitLabel="Save"
        onSubmit={async (details) => {
          if (await onEdit(details)) setEditing(false);
        }}
        onCancel={() => setEditing(false)}
      />
    );
  }

  return (
    <article>
      <h2>{product.name}</h2>
      {product.brand && <p>{product.brand}</p>}
      {product.image_url && <ProductImage url={product.image_url} />}
      {product.tags.length > 0 && (
        <div class="chips">
          {product.tags.map((tag) => (
            <button type="button" key={tag.id} onClick={() => onTagClick(tag.id)}>
              {tag.name}
            </button>
          ))}
        </div>
      )}

      <div class="stock">
        <button
          type="button"
          aria-label="Remove 1"
          disabled={busy || product.quantity === 0}
          onClick={() => changeStock(onRemoveStock)}
        >
          −
        </button>
        <output aria-label="In stock">{product.quantity}</output>
        <button
          type="button"
          aria-label="Add 1"
          disabled={busy}
          onClick={() => changeStock(onAddStock)}
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

      <div class="actions">
        <button type="button" onClick={onBack}>
          Back
        </button>
        <button type="button" onClick={() => setEditing(true)}>
          Edit
        </button>
        {confirmingDelete ? (
          <button type="button" class="danger" onClick={onDelete}>
            Really delete?
          </button>
        ) : (
          <button type="button" onClick={() => setConfirmingDelete(true)}>
            Delete
          </button>
        )}
      </div>
    </article>
  );
}
