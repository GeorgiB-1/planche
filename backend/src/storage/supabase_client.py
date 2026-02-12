"""
Supabase client for Planche.bg — handles all database operations
for products, price history, scrape jobs, and designs.
"""

from supabase import create_client, Client
import hashlib
import json
import os

from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def generate_product_id(domain: str, sku: str, name: str) -> str:
    """Generate a stable, deterministic product ID from domain + sku + name."""
    raw = f"{domain}:{sku}:{name}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

def save_product(product: dict, domain: str) -> str:
    """
    Upsert a product into the products table.

    - Generates a stable product_id from domain + sku + name.
    - Detects price changes and records them in price_history.
    - Upserts the product row (insert or update on conflict).
    - Returns the product_id.
    """
    sku = product.get("sku", "")
    name = product.get("name", "")
    product_id = generate_product_id(domain, sku, name)

    # Check if product already exists (for price-change tracking)
    existing = (
        supabase.table("products")
        .select("id, price")
        .eq("id", product_id)
        .execute()
    )

    old_price = None
    if existing.data:
        old_price = existing.data[0].get("price")

    new_price = product.get("price")

    # Record price change if applicable
    if (
        old_price is not None
        and new_price is not None
        and float(old_price) != float(new_price)
    ):
        supabase.table("price_history").insert({
            "product_id": product_id,
            "old_price": float(old_price),
            "new_price": float(new_price),
        }).execute()

    # Build the row, filtering out None values
    row = {
        "id": product_id,
        "source_domain": domain,
        "updated_at": "now()",
    }
    for key, value in product.items():
        if value is not None:
            row[key] = value

    supabase.table("products").upsert(row).execute()

    return product_id


def get_product_by_id(product_id: str) -> dict | None:
    """Fetch a single product by its ID. Returns the row dict or None."""
    result = (
        supabase.table("products")
        .select("*")
        .eq("id", product_id)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


def get_unenriched_products(limit: int = 100) -> list[dict]:
    """
    Return products that have not yet been enriched by the vision pipeline
    and have a main image URL available.
    """
    result = (
        supabase.table("products")
        .select("*")
        .eq("vision_enriched", False)
        .not_.is_("main_image_url", "null")
        .limit(limit)
        .execute()
    )
    return result.data or []


def update_product(product_id: str, updates: dict) -> None:
    """Apply a partial update to an existing product row."""
    supabase.table("products").update(updates).eq("id", product_id).execute()


def query_products(
    categories: list[str] | None = None,
    room: str | None = None,
    style: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    max_width: int | None = None,
    preferred_sources: list[str] | None = None,
    require_usable_image: bool = False,
    require_proportions: bool = False,
    limit: int = 50,
) -> list[dict]:
    """
    Build a filtered Supabase query for product matching.

    All parameters are optional and applied as chained filters.
    Results are ordered by rating descending (nulls last) and
    always filtered to in_stock = True.
    """
    query = supabase.table("products").select("*")

    # Always filter for in-stock products
    query = query.eq("in_stock", True)

    if categories:
        query = query.in_("category", categories)

    if room:
        query = query.eq("room_type", room)

    # Style is used as a preference in ranking, not a hard filter,
    # so we don't filter by style here — the matcher's rank_candidates
    # will score style matches higher.

    if min_price is not None:
        # Include products with null prices (inquiry-based catalogs)
        query = query.or_(f"price.gte.{min_price},price.is.null")

    if max_price is not None:
        # Include products with null prices (inquiry-based catalogs)
        query = query.or_(f"price.lte.{max_price},price.is.null")

    if max_width is not None:
        # Include products with null dimensions (not yet measured)
        query = query.or_(f"width_cm.lte.{max_width},width_cm.is.null")

    # preferred_sources is used as a ranking signal in the matcher,
    # not a hard filter — we want to return products from all sources.

    if require_usable_image:
        query = query.eq("image_usable", True)

    if require_proportions:
        query = query.not_.is_("proportion_w_h", "null")

    # Order by rating descending, nulls last
    query = query.order("rating", desc=True, nullsfirst=False)

    query = query.limit(limit)

    result = query.execute()
    return result.data or []


# ---------------------------------------------------------------------------
# Scrape Jobs
# ---------------------------------------------------------------------------

def save_scrape_job(job_id: str, url: str) -> None:
    """Insert a new scrape job record with status 'running'."""
    supabase.table("scrape_jobs").insert({
        "id": job_id,
        "url": url,
        "status": "running",
    }).execute()


def update_scrape_job(
    job_id: str,
    status: str,
    products_found: int,
    pages_scraped: int,
    errors: str | None = None,
    duration_seconds: float | None = None,
) -> None:
    """Update a scrape job with its final results."""
    row: dict = {
        "status": status,
        "products_found": products_found,
        "pages_scraped": pages_scraped,
        "finished_at": "now()",
    }
    if errors is not None:
        row["errors"] = errors
    if duration_seconds is not None:
        row["duration_seconds"] = duration_seconds

    supabase.table("scrape_jobs").update(row).eq("id", job_id).execute()


# ---------------------------------------------------------------------------
# Designs
# ---------------------------------------------------------------------------

def save_design(design: dict) -> None:
    """Insert a new design record."""
    supabase.table("designs").insert(design).execute()


def get_design(design_id: str) -> dict | None:
    """Fetch a single design by its ID. Returns the row dict or None."""
    result = (
        supabase.table("designs")
        .select("*")
        .eq("id", design_id)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


def update_design(design_id: str, updates: dict) -> None:
    """Apply a partial update to an existing design row."""
    supabase.table("designs").update(updates).eq("id", design_id).execute()


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def get_product_stats() -> dict:
    """
    Return aggregate statistics about the product catalog:
    - total_products: total rows in products table
    - vision_enriched: count of products where vision_enriched = True
    - usable_for_render: count of products where image_usable = True
    """
    total_result = (
        supabase.table("products")
        .select("id", count="exact")
        .execute()
    )
    total_products = total_result.count or 0

    enriched_result = (
        supabase.table("products")
        .select("id", count="exact")
        .eq("vision_enriched", True)
        .execute()
    )
    vision_enriched = enriched_result.count or 0

    usable_result = (
        supabase.table("products")
        .select("id", count="exact")
        .eq("image_usable", True)
        .execute()
    )
    usable_for_render = usable_result.count or 0

    return {
        "total_products": total_products,
        "vision_enriched": vision_enriched,
        "usable_for_render": usable_for_render,
    }
