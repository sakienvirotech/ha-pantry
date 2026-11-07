/**
 * Credits Open Food Facts asks re-users to show: data under the ODbL and
 * pictures under CC BY-SA, each naming and linking Open Food Facts.
 */
const OPEN_FOOD_FACTS = "https://world.openfoodfacts.org";
const ODBL = "https://opendatacommons.org/licenses/odbl/1.0/";
const CC_BY_SA = "https://creativecommons.org/licenses/by-sa/3.0/";

/** Links open outside the Ingress frame, and never send its address as a referrer. */
function Link({ href, children }: { href: string; children: string }) {
  return (
    <a href={href} target="_blank" rel="noreferrer">
      {children}
    </a>
  );
}

export function DataCredit({ productUrl }: { productUrl?: string }) {
  return (
    <small class="credit">
      Data from <Link href={productUrl ?? OPEN_FOOD_FACTS}>Open Food Facts</Link>, under
      the <Link href={ODBL}>Open Database License</Link>
    </small>
  );
}

export function PictureCredit({ productUrl }: { productUrl?: string }) {
  return (
    <small class="credit">
      Picture from <Link href={productUrl ?? OPEN_FOOD_FACTS}>Open Food Facts</Link>,{" "}
      <Link href={CC_BY_SA}>CC BY-SA</Link>
    </small>
  );
}

/** HA-Pantry names the Open Food Facts pictures it saves to Grocy like this. */
export function isSavedOpenFoodFactsPicture(fileName: string): boolean {
  return fileName.startsWith("ha-pantry-");
}
