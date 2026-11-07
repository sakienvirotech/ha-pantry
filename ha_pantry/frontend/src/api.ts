export interface Named {
  id: number;
  name: string;
}

export interface Barcode {
  id: number;
  code: string;
}

/** A Grocy product, with its stock in the product's stock unit. */
export interface Product {
  id: number;
  name: string;
  stock_amount: number;
  unit: string;
  location: string | null;
  group: string | null;
  barcodes: Barcode[];
}

export interface Setup {
  locations: Named[];
  units: Named[];
  groups: Named[];
  default_location_id: number | null;
}

export interface Status {
  connected: boolean;
  message: string | null;
  grocy_version: string | null;
}

export interface NewProduct {
  name: string;
  unit_id: number;
  location_id: number;
  group_id: number | null;
  barcode?: string;
}

export interface LookupMatch {
  name: string;
  brand: string | null;
  image_url: string | null;
  quantity: string | null;
  source: string;
  source_url: string;
}

export interface LookupResult {
  match: LookupMatch | null;
  failed: boolean;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

// Relative on purpose: Ingress serves the app under a dynamic path.
async function request<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  const response = await fetch(`api/${path}`, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    const detail = typeof error?.detail === "string" ? error.detail : null;
    throw new ApiError(detail ?? `Request failed (${response.status})`, response.status);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export const getStatus = () => request<Status>("status");

export const getSetup = () => request<Setup>("setup");

export const searchProducts = (text: string) =>
  request<Named[]>(`products?q=${encodeURIComponent(text)}`);

export const similarProducts = (name: string) =>
  request<Named[]>(`similar-products?name=${encodeURIComponent(name)}`);

export const getProduct = (id: number) => request<Product>(`products/${id}`);

export const findByBarcode = (code: string) =>
  request<Product>(`barcodes/${encodeURIComponent(code)}`);

export const lookupBarcode = (code: string) =>
  request<LookupResult>(`lookup/${encodeURIComponent(code)}`);

export const createProduct = (product: NewProduct) =>
  request<Product>("products", "POST", product);

export const addStock = (id: number, bestBeforeDate: string | null) =>
  request<Product>(`products/${id}/stock/add`, "POST", {
    amount: 1,
    best_before_date: bestBeforeDate,
  });

export const removeStock = (id: number) =>
  request<Product>(`products/${id}/stock/remove`, "POST");

export const linkBarcode = (id: number, code: string) =>
  request<Product>(`products/${id}/barcodes`, "POST", { code });

export const unlinkBarcode = (id: number, barcodeId: number) =>
  request<Product>(`products/${id}/barcodes/${barcodeId}`, "DELETE");
