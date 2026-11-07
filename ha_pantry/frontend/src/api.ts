export interface Barcode {
  id: number;
  code: string;
}

export interface Product {
  id: number;
  name: string;
  brand: string | null;
  quantity: number;
  barcodes: Barcode[];
}

export interface ProductDetails {
  name: string;
  brand: string;
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

export const listProducts = () => request<Product[]>("products");

export const findByBarcode = (code: string) =>
  request<Product>(`barcodes/${encodeURIComponent(code)}`);

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
