const OPEN_FOOD_FACTS_HOST = "images.openfoodfacts.org";

/** No referrer, because the page's address contains the Ingress session path. */
export function ProductImage({ url }: { url: string }) {
  const fromOpenFoodFacts = new URL(url).hostname === OPEN_FOOD_FACTS_HOST;
  return (
    <figure class="product-image">
      <img src={url} alt="" referrerPolicy="no-referrer" />
      {fromOpenFoodFacts && (
        <figcaption>
          Image from Open Food Facts,{" "}
          <a
            href="https://creativecommons.org/licenses/by-sa/3.0/"
            target="_blank"
            rel="noreferrer"
          >
            CC BY-SA
          </a>
        </figcaption>
      )}
    </figure>
  );
}
