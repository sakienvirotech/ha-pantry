import { useEffect, useState } from "preact/hooks";
import { lookupBarcode, similarProducts } from "./api";
import type { LookupResult, Named, NewProduct, Setup } from "./api";
import { NewProductForm } from "./NewProductForm";
import { ProductImage } from "./ProductImage";
import { ProductSearch } from "./ProductSearch";

interface Props {
  code: string;
  setup: Setup | undefined;
  run: (action: () => Promise<void>) => Promise<boolean>;
  onCreate: (product: Omit<NewProduct, "barcode">) => void;
  onLink: (product: Named) => void;
  onCancel: () => void;
}

export function UnknownBarcode({ code, setup, run, onCreate, onLink, onCancel }: Props) {
  // Undefined while waiting. Both paths work throughout, as the lookup is only a help.
  const [lookup, setLookup] = useState<LookupResult>();
  const [creating, setCreating] = useState(false);
  const [similar, setSimilar] = useState<Named[]>([]);

  useEffect(() => {
    let current = true;
    lookupBarcode(code)
      .catch((): LookupResult => ({ match: null, failed: true }))
      .then(async (result) => {
        if (!current) return;
        setLookup(result);
        if (!result.match) return;
        const { name, brand } = result.match;
        // Only a help, so a failure just leaves the search box.
        const found = await similarProducts(`${name} ${brand ?? ""}`).catch(() => []);
        if (current) setSimilar(found);
      });
    return () => {
      current = false;
    };
  }, [code]);

  const match = lookup?.match ?? null;

  return (
    <article>
      <h2>New barcode</h2>
      <p class="code">{code}</p>
      <p role="status">
        {!lookup && "Looking this up online…"}
        {match && (
          <>
            <a href={match.source_url} target="_blank" rel="noreferrer">
              {match.source}
            </a>{" "}
            says: <strong>{match.name}</strong>
            {match.brand && <>, {match.brand}</>}
            {match.quantity && <>, {match.quantity}</>}
          </>
        )}
        {lookup && !match && !lookup.failed && "No match online."}
        {lookup && !match && lookup.failed && "Online lookup isn't available right now."}
      </p>
      {match?.image_url && <ProductImage url={match.image_url} />}

      {creating && setup ? (
        <>
          <h3>Create a new product</h3>
          <NewProductForm
            setup={setup}
            match={match}
            onSubmit={onCreate}
            onCancel={() => setCreating(false)}
          />
        </>
      ) : (
        <>
          <h3>Add this barcode to a product already in Grocy</h3>
          {similar.length > 0 && (
            <>
              <p>Possible matches:</p>
              <ul class="plain products">
                {similar.map((product) => (
                  <li key={product.id}>
                    <button type="button" onClick={() => onLink(product)}>
                      <span>{product.name}</span>
                    </button>
                  </li>
                ))}
              </ul>
              <p>Or search:</p>
            </>
          )}
          <ProductSearch label="Search Grocy products" run={run} onPick={onLink} />
          <h3>Or create a new product</h3>
          <div class="actions">
            <button type="button" disabled={!setup} onClick={() => setCreating(true)}>
              Create a new product
            </button>
            <button type="button" onClick={onCancel}>
              Cancel
            </button>
          </div>
        </>
      )}
    </article>
  );
}
