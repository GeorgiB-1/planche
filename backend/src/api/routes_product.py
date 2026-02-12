"""Product search, stats, and budget tier API routes for Planche.bg."""

from fastapi import APIRouter, Query, HTTPException

from src.storage.supabase_client import query_products, get_product_by_id, get_product_stats
from src.storage.r2_client import get_image_url
from src.config import BUDGET_TIERS

router = APIRouter(prefix="/api", tags=["products"])


def _resolve_image_url(r2_key: str | None) -> str | None:
    """Return a public URL for the given R2 key, or None if absent."""
    if r2_key:
        return get_image_url(r2_key)
    return None


# --------------------------------------------------------------------------- #
# 1. Product search
# --------------------------------------------------------------------------- #

@router.get("/products/search")
async def search_products(
    q: str | None = Query(default=None, description="Text search query (reserved for future use)"),
    category: str | None = Query(default=None, description="Filter by category (e.g. sofa, table)"),
    room: str | None = Query(default=None, description="Filter by room_type (e.g. living_room, bedroom)"),
    style: str | None = Query(default=None, description="Filter by style (e.g. modern, scandinavian)"),
    min_price: float | None = Query(default=None, description="Minimum price in EUR"),
    max_price: float | None = Query(default=None, description="Maximum price in EUR"),
    source: str | None = Query(default=None, description="Filter by source_domain (e.g. videnov.bg)"),
    limit: int = Query(default=20, description="Max results (capped at 100)"),
):
    """Search products with optional filters.

    Returns a list of ``ProductSummary``-shaped dicts enriched with a resolved
    ``image_url`` field.
    """
    limit = min(limit, 100)

    categories = [category] if category is not None else None
    preferred_sources = [source] if source is not None else None

    products = query_products(
        categories=categories,
        room=room,
        style=style,
        min_price=min_price,
        max_price=max_price,
        preferred_sources=preferred_sources,
        limit=limit,
    )

    for product in products:
        product["image_url"] = _resolve_image_url(product.get("r2_main_image_key"))

    return {"products": products, "total": len(products)}


# --------------------------------------------------------------------------- #
# 2. Single product by ID
# --------------------------------------------------------------------------- #

@router.get("/products/{product_id}")
async def get_product(product_id: str):
    """Return full product details (``ProductDB``) for the given ID.

    Raises 404 if the product does not exist.
    """
    product = get_product_by_id(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    product["image_url"] = _resolve_image_url(product.get("r2_main_image_key"))
    return product


# --------------------------------------------------------------------------- #
# 3. Product stats
# --------------------------------------------------------------------------- #

@router.get("/stats")
async def stats():
    """Return high-level product catalogue statistics."""
    data = get_product_stats()

    total = data.get("total_products", 0)
    enriched = data.get("vision_enriched", 0)

    enrichment_pct = (enriched / total * 100) if total > 0 else 0.0

    return {
        "total_products": total,
        "vision_enriched": enriched,
        "usable_for_render": data.get("usable_for_render", 0),
        "enrichment_pct": round(enrichment_pct, 2),
    }


# --------------------------------------------------------------------------- #
# 4. Budget tiers
# --------------------------------------------------------------------------- #

@router.get("/tiers")
async def tiers():
    """Return budget tier definitions for frontend consumption."""
    return {"tiers": BUDGET_TIERS}
