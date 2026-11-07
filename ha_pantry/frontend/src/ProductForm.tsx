import { useEffect, useState } from "preact/hooks";
import type { ProductDetails, Suggestion, Tag, TagKind } from "./api";
import { ProductImage } from "./ProductImage";
import { TagPicker } from "./TagPicker";

interface Props {
  initial?: ProductDetails;
  /** Fills in whatever is still empty, so a slow lookup can't overwrite typing. */
  suggestion?: Suggestion | null;
  tags: Tag[];
  onCreateTag: (name: string, kind: TagKind) => Promise<Tag | null>;
  submitLabel: string;
  onSubmit: (details: ProductDetails) => void;
  onCancel: () => void;
}

/**
 * Enter never saves. A scan that lands in a text box ends in Enter, which
 * would otherwise save the digits, for example when a tablet's on-screen
 * keyboard is open. No autofocus either, as that would open the keyboard.
 */
export function ProductForm({
  initial,
  suggestion,
  tags,
  onCreateTag,
  submitLabel,
  onSubmit,
  onCancel,
}: Props) {
  const [name, setName] = useState(initial?.name ?? "");
  const [brand, setBrand] = useState(initial?.brand ?? "");
  const [imageUrl, setImageUrl] = useState(initial?.image_url ?? null);
  const [tagIds, setTagIds] = useState(initial?.tag_ids ?? []);

  useEffect(() => {
    if (!suggestion) return;
    setName((current) => current || suggestion.name);
    setBrand((current) => current || suggestion.brand);
    setImageUrl((current) => current ?? suggestion.image_url);
  }, [suggestion]);

  return (
    <form
      class="stacked"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit({ name, brand, image_url: imageUrl, tag_ids: tagIds });
      }}
      onKeyDown={(event) => {
        if (event.key === "Enter" && event.target instanceof HTMLInputElement) {
          event.preventDefault();
        }
      }}
    >
      <label>
        Name
        <input
          required
          maxLength={200}
          value={name}
          onInput={(event) => setName(event.currentTarget.value)}
        />
      </label>
      <label>
        Brand
        <input
          maxLength={200}
          value={brand}
          onInput={(event) => setBrand(event.currentTarget.value)}
        />
      </label>
      <TagPicker
        tags={tags}
        selected={tagIds}
        onChange={setTagIds}
        onCreate={onCreateTag}
      />
      {imageUrl && (
        <div>
          <ProductImage url={imageUrl} />
          <button type="button" onClick={() => setImageUrl(null)}>
            Remove image
          </button>
        </div>
      )}
      <div class="actions">
        <button type="submit">{submitLabel}</button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
