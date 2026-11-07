import { useEffect, useState } from "preact/hooks";
import { listProducts } from "./api";
import type { Product, ProductQuery, Tag } from "./api";

interface Props {
  query: ProductQuery;
  tags: Tag[];
  run: (action: () => Promise<void>) => Promise<boolean>;
  onQueryChange: (query: ProductQuery) => void;
  onOpen: (product: Product) => void;
  onAdd: () => void;
  onManageTags: () => void;
}

const SEARCH_DELAY_MS = 200;

export function ProductList({
  query,
  tags,
  run,
  onQueryChange,
  onOpen,
  onAdd,
  onManageTags,
}: Props) {
  const [results, setResults] = useState<Product[]>();

  useEffect(() => {
    let current = true;
    const timer = setTimeout(() => {
      run(async () => {
        const products = await listProducts(query);
        if (current) setResults(products);
      });
    }, SEARCH_DELAY_MS);
    return () => {
      current = false;
      clearTimeout(timer);
    };
  }, [query]);

  const toggleTag = (tagId: number) =>
    onQueryChange({
      ...query,
      tagIds: query.tagIds.includes(tagId)
        ? query.tagIds.filter((id) => id !== tagId)
        : [...query.tagIds, tagId],
    });
  const filtered = query.text.trim() !== "" || query.tagIds.length > 0;

  return (
    <>
      <div class="actions">
        <button type="button" onClick={onAdd}>
          Add a product
        </button>
        <button type="button" onClick={onManageTags}>
          Tags
        </button>
      </div>
      <input
        class="search"
        type="search"
        aria-label="Search"
        placeholder="Search by name, brand, barcode or tag"
        value={query.text}
        onInput={(event) => onQueryChange({ ...query, text: event.currentTarget.value })}
      />
      {tags.length > 0 && (
        <div class="chips">
          {tags.map((tag) => (
            <button
              type="button"
              key={tag.id}
              aria-pressed={query.tagIds.includes(tag.id)}
              onClick={() => toggleTag(tag.id)}
            >
              {tag.name}
            </button>
          ))}
        </div>
      )}
      {results?.length === 0 && (
        <p>{filtered ? "No products match." : "No products yet. Scan one to start."}</p>
      )}
      <ul class="plain products">
        {results?.map((product) => (
          <li key={product.id}>
            <button type="button" onClick={() => onOpen(product)}>
              <span>{product.name}</span>
              <span>{product.quantity}</span>
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}
