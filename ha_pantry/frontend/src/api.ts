export interface Barcode {
  id: number;
  code: string;
}

export type TagKind = "category" | "location";

export interface Tag {
  id: number;
  name: string;
  kind: TagKind;
}

export interface TagSummary extends Tag {
  product_count: number;
}

export interface Product {
  id: number;
  name: string;
  brand: string | null;
  quantity: number;
  image_url: string | null;
  barcodes: Barcode[];
  tags: Tag[];
}

export interface Suggestion {
  name: string;
  brand: string;
  image_url: string | null;
}

export interface ProductDetails extends Suggestion {
  tag_ids: number[];
}

export interface ProductQuery {
  text: string;
  tagIds: number[];
}

export interface LookupMatch extends Suggestion {
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

export function listProducts({ text, tagIds }: ProductQuery = { text: "", tagIds: [] }) {
  const params = new URLSearchParams();
  if (text) params.set("q", text);
  tagIds.forEach((id) => params.append("tag", String(id)));
  const query = params.toString();
  return request<Product[]>(query ? `products?${query}` : "products");
}

export const findByBarcode = (code: string) =>
  request<Product>(`barcodes/${encodeURIComponent(code)}`);

export const lookupBarcode = (code: string) =>
  request<LookupResult>(`lookup/${encodeURIComponent(code)}`);

export const createProduct = (details: ProductDetails, barcodes: string[]) =>
  request<Product>("products", "POST", { ...details, barcodes });

export const updateProduct = (id: number, details: ProductDetails) =>
  request<Product>(`products/${id}`, "PUT", details);

export const deleteProduct = (id: number) =>
  request<void>(`products/${id}`, "DELETE");

export const addStock = (id: number) =>
  request<Product>(`products/${id}/stock/add`, "POST");

export const removeStock = (id: number) =>
  request<Product>(`products/${id}/stock/remove`, "POST");

export const linkBarcode = (id: number, code: string) =>
  request<Product>(`products/${id}/barcodes`, "POST", { code });

export const unlinkBarcode = (id: number, barcodeId: number) =>
  request<Product>(`products/${id}/barcodes/${barcodeId}`, "DELETE");

export const listTags = () => request<TagSummary[]>("tags");

export const createTag = (name: string, kind: TagKind) =>
  request<Tag>("tags", "POST", { name, kind });

export const renameTag = (id: number, name: string) =>
  request<Tag>(`tags/${id}`, "PUT", { name });

export const deleteTag = (id: number) => request<void>(`tags/${id}`, "DELETE");
