"""Pydantic v2 models for furniture products."""

from pydantic import BaseModel


class ProductBase(BaseModel):
    """All product fields from the database."""

    model_config = {"from_attributes": True}

    # Identity
    name: str
    brand: str | None = None
    sku: str | None = None
    model: str | None = None

    # Pricing
    price: float | None = None
    original_price: float | None = None
    currency: str = "EUR"
    on_sale: bool = False

    # Classification
    category: str | None = None
    subcategory: str | None = None
    room_type: str | None = None
    style: str | None = None

    # Dimensions
    width_cm: float | None = None
    height_cm: float | None = None
    depth_cm: float | None = None
    weight_kg: float | None = None
    seat_height_cm: float | None = None
    diameter_cm: float | None = None

    # Materials & appearance
    materials: list[str] | None = None
    primary_material: str | None = None
    color: str | None = None
    available_colors: list[str] | None = None
    finish: str | None = None
    upholstery: str | None = None

    # Description
    description: str | None = None
    features: list[str] | None = None

    # Attributes
    assembly_required: bool | None = None
    warranty: str | None = None
    max_load_kg: float | None = None
    seating_capacity: int | None = None
    number_of_drawers: int | None = None
    adjustable: bool | None = None
    foldable: bool | None = None
    outdoor_suitable: bool | None = None

    # Availability & delivery
    in_stock: bool = True
    delivery_info: str | None = None
    delivery_days: int | None = None
    free_delivery: bool | None = None

    # Reviews
    rating: float | None = None
    review_count: int | None = None

    # Images & source
    image_urls: list[str] | None = None
    main_image_url: str | None = None
    product_url: str | None = None
    source_domain: str | None = None


class ProductCreate(ProductBase):
    """Scraper input model. Identical to ProductBase."""

    pass


class ProductDB(ProductBase):
    """Product as stored in the database, with system-managed fields."""

    id: str
    created_at: str | None = None
    updated_at: str | None = None

    # R2 image storage
    r2_image_keys: list[str] | None = None
    r2_main_image_key: str | None = None
    r2_image_count: int = 0

    # Dimension verification (from AI vision)
    dimensions_source: str | None = None
    dimensions_confidence: str | None = None

    # Proportion ratios
    proportion_w_h: float | None = None
    proportion_w_d: float | None = None

    # AI vision enrichment
    visual_description: str | None = None
    color_hex: str | None = None
    color_tone: str | None = None
    luxury_score: float | None = None
    ai_category: str | None = None
    ai_subcategory: str | None = None
    suitable_rooms: list[str] | None = None

    # Image quality assessment
    image_type: str | None = None
    image_usable: bool = False

    # Raw vision data
    vision_data: dict | None = None
    vision_enriched: bool = False
    vision_enriched_at: str | None = None


class ProductSummary(BaseModel):
    """Subset of product fields for API list responses."""

    model_config = {"from_attributes": True}

    id: str
    name: str
    price: float | None = None
    currency: str = "EUR"
    category: str | None = None
    room_type: str | None = None
    style: str | None = None
    r2_main_image_key: str | None = None
    width_cm: float | None = None
    height_cm: float | None = None
    depth_cm: float | None = None
    rating: float | None = None
    source_domain: str | None = None
    product_url: str | None = None
    in_stock: bool = True


class VisionEnrichment(BaseModel):
    """AI vision analysis result for a product image."""

    dimensions_verification: dict | None = None
    proportion_ratios: dict | None = None
    visual_description: str | None = None
    material_analysis: dict | None = None
    color_analysis: dict | None = None
    style_classification: dict | None = None
    category_verification: dict | None = None
    image_quality: dict | None = None
