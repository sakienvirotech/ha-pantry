import { PictureCredit } from "./credits";

const OPEN_FOOD_FACTS_HOST = "images.openfoodfacts.org";

/** No referrer, because the page's address contains the Ingress session path. */
export function ProductImage({ url, productUrl }: { url: string; productUrl?: string }) {
  const fromOpenFoodFacts = new URL(url).hostname === OPEN_FOOD_FACTS_HOST;
  return (
    <figure class="product-image">
      <img src={url} alt="" referrerPolicy="no-referrer" />
      {fromOpenFoodFacts && (
        <figcaption>
          <PictureCredit productUrl={productUrl} />
        </figcaption>
      )}
    </figure>
  );
}
