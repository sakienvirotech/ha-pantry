import { useState } from "preact/hooks";
import type { ProductDetails } from "./api";

interface Props {
  initial?: ProductDetails;
  submitLabel: string;
  onSubmit: (details: ProductDetails) => void;
  onCancel: () => void;
}

/**
 * Enter never saves. A scan that lands in a text box ends in Enter, which
 * would otherwise save the digits, for example when a tablet's on-screen
 * keyboard is open. No autofocus either, as that would open the keyboard.
 */
export function ProductForm({ initial, submitLabel, onSubmit, onCancel }: Props) {
  const [name, setName] = useState(initial?.name ?? "");
  const [brand, setBrand] = useState(initial?.brand ?? "");

  return (
    <form
      class="stacked"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit({ name, brand });
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
      <div class="actions">
        <button type="submit">{submitLabel}</button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
