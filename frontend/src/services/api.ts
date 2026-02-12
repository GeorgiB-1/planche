// ---------------------------------------------------------------------------
// Planche.bg Frontend API Client
// ---------------------------------------------------------------------------
// Typed functions wrapping the Planche.bg backend REST API.
// Uses the native `fetch` API -- no external HTTP libraries required.
// ---------------------------------------------------------------------------

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Type definitions matching the backend API responses
// ---------------------------------------------------------------------------

export interface ProductSummary {
  id: string;
  name: string;
  price: number | null;
  currency: string;
  category: string | null;
  room_type: string | null;
  style: string | null;
  r2_main_image_key: string | null;
  image_url: string | null;
  width_cm: number | null;
  height_cm: number | null;
  depth_cm: number | null;
  rating: number | null;
  source_domain: string | null;
  product_url: string | null;
  in_stock: boolean;
}

export interface SearchResult {
  products: ProductSummary[];
  total: number;
}

export interface SearchParams {
  q?: string;
  category?: string;
  room?: string;
  style?: string;
  min_price?: number;
  max_price?: number;
  source?: string;
  limit?: number;
}

export interface RoomData {
  rooms: any[];
  overall: {
    total_rooms: number;
    total_area_sqm: number;
    style_hints: string[];
    detected_labels: string[];
  };
}

export interface BuyLink {
  name: string;
  price: number;
  currency: string;
  url: string;
  source: string;
  image_url: string;
}

export interface DesignResult {
  design_id: string;
  render_url: string;
  sketch_url: string | null;
  products: BuyLink[];
  budget_spent: number;
  budget_remaining: number;
}

export interface SwapAlternative {
  id: string;
  name: string;
  price: number;
  image_url: string;
  visual_description: string | null;
}

export interface SwapAlternatives {
  alternatives: SwapAlternative[];
}

export interface SwapResult {
  design_id: string;
  render_url: string;
  swapped_slot: string;
  new_product: Record<string, any>;
}

export interface Stats {
  total_products: number;
  vision_enriched: number;
  usable_for_render: number;
  enrichment_pct: number;
}

export interface BudgetTier {
  label: string;
  description: string;
  per_sqm_eur: [number, number];
  preferred_sources: string[];
  max_single_item_pct: number;
  style_keywords: string[];
}

export interface TiersResponse {
  tiers: Record<string, BudgetTier>;
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Parse the JSON body of a response and throw a descriptive error when the
 * response status is not in the 2xx range.
 */
async function _handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let body: string;
    try {
      body = await res.text();
    } catch {
      body = "<unable to read response body>";
    }
    throw new Error(
      `API request failed with status ${res.status}: ${body}`
    );
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Public API functions
// ---------------------------------------------------------------------------

/**
 * Analyze a sketch / floor-plan image and return detected room data.
 *
 * POST /api/analyze  (multipart/form-data)
 */
export async function analyzeSketch(file: File): Promise<RoomData> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    body: form,
  });

  return _handleResponse<RoomData>(res);
}

/**
 * Generate a furnished design render for the given sketch / floor-plan.
 *
 * POST /api/furnish  (multipart/form-data)
 */
export async function furnishRoom(
  file: File,
  budget: number,
  tier: string,
  style: string,
  roomId?: string
): Promise<DesignResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("budget", String(budget));
  form.append("tier", tier);
  form.append("style", style);
  if (roomId !== undefined && roomId !== null) {
    form.append("room_id", roomId);
  }

  const res = await fetch(`${API_BASE}/api/furnish`, {
    method: "POST",
    body: form,
  });

  return _handleResponse<DesignResult>(res);
}

/**
 * Search the product catalogue.
 *
 * GET /api/products/search?q=...&category=...&...
 */
export async function searchProducts(
  params: SearchParams
): Promise<SearchResult> {
  const query = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      query.set(key, String(value));
    }
  }

  const qs = query.toString();
  const url = `${API_BASE}/api/products/search${qs ? `?${qs}` : ""}`;

  const res = await fetch(url, { method: "GET" });

  return _handleResponse<SearchResult>(res);
}

/**
 * Retrieve aggregate statistics about the product catalogue.
 *
 * GET /api/stats
 */
export async function getStats(): Promise<Stats> {
  const res = await fetch(`${API_BASE}/api/stats`, { method: "GET" });
  return _handleResponse<Stats>(res);
}

/**
 * Retrieve budget tier definitions.
 *
 * GET /api/tiers
 */
export async function getTiers(): Promise<TiersResponse> {
  const res = await fetch(`${API_BASE}/api/tiers`, { method: "GET" });
  return _handleResponse<TiersResponse>(res);
}

/**
 * Get alternative products for a specific slot in an existing design.
 *
 * POST /api/swap  (JSON body, without `product_id`)
 */
export async function getAlternatives(
  designId: string,
  slot: string
): Promise<SwapAlternatives> {
  const res = await fetch(`${API_BASE}/api/swap`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      design_id: designId,
      slot,
    }),
  });

  return _handleResponse<SwapAlternatives>(res);
}

/**
 * Swap a product in an existing design and receive an updated render.
 *
 * POST /api/swap  (JSON body, with `product_id`)
 */
export async function swapProduct(
  designId: string,
  slot: string,
  productId: string
): Promise<SwapResult> {
  const res = await fetch(`${API_BASE}/api/swap`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      design_id: designId,
      slot,
      product_id: productId,
    }),
  });

  return _handleResponse<SwapResult>(res);
}
