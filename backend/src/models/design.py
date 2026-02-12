"""Pydantic v2 models for designs, matching, rendering, and swaps."""

from pydantic import BaseModel


class BuyLink(BaseModel):
    """A purchasable product link shown to the end user."""

    name: str
    price: float
    currency: str = "EUR"
    url: str
    source: str
    image_url: str


class ProductImageForRender(BaseModel):
    """Product image metadata needed by the render pipeline."""

    slot: str
    r2_key: str
    r2_url: str
    visual_description: str = ""
    width_cm: float | None = None
    height_cm: float | None = None
    depth_cm: float | None = None
    proportion_w_h: float | None = None
    proportion_w_d: float | None = None
    color: str | None = None
    primary_material: str | None = None


class MatchedProduct(BaseModel):
    """A product matched to a furniture slot in the room."""

    slot: str
    product: dict
    quantity: int = 1
    placement: dict | None = None


class MatchResult(BaseModel):
    """Result of the product-matching step for a single room and tier."""

    room: dict
    tier: str
    style: str | None = None
    budget_total: float
    budget_spent: float
    budget_remaining: float
    budget_utilization_pct: float
    products: list[MatchedProduct]
    product_count: int
    product_images_for_render: list[ProductImageForRender]
    buy_links: list[BuyLink]


class DesignResult(BaseModel):
    """Final design returned to the user after rendering."""

    design_id: str
    render_url: str
    sketch_url: str | None = None
    products: list[BuyLink]
    budget_spent: float
    budget_remaining: float


class SwapAlternative(BaseModel):
    """A single alternative product that can replace a slot."""

    id: str
    name: str
    price: float
    image_url: str
    visual_description: str | None = None


class SwapAlternatives(BaseModel):
    """List of alternatives for a given product slot."""

    alternatives: list[SwapAlternative]


class SwapResult(BaseModel):
    """Result after swapping a product in an existing design."""

    design_id: str
    render_url: str
    swapped_slot: str
    new_product: dict


class RefineResult(BaseModel):
    """Result of an iterative design refinement."""

    design_id: str
    render_url: str
    version: int
    refinement_description: str | None = None
    previous_render_url: str


class BudgetTier(BaseModel):
    """Definition of a budget tier (e.g. economy, mid-range, premium)."""

    label: str
    description: str
    per_sqm_eur: list[float]
    preferred_sources: list[str]
    max_single_item_pct: float
