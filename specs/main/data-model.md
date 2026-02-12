# Data Model: Planche.bg — AI Interior Design MVP

**Date**: 2026-02-12
**Source**: Feature spec + AI_Interior_Design_Full_Implementation_Plan.md

---

## Entity Relationship Diagram

```
┌─────────────────┐       ┌──────────────────┐
│    products      │──1:N──│  price_history    │
│                  │       │                   │
│ id (PK)          │       │ product_id (FK)   │
│ name             │       │ old_price         │
│ price            │       │ new_price         │
│ dimensions       │       │ changed_at        │
│ images (R2)      │       └──────────────────┘
│ vision_data      │
│ source_domain    │
└────────┬─────────┘
         │
         │ N:M (via designs.matched_products JSONB)
         │
┌────────▼─────────┐       ┌──────────────────┐
│    designs        │       │   scrape_jobs     │
│                   │       │                   │
│ id (PK)           │       │ id (PK)           │
│ sketch (R2)       │       │ url               │
│ room_analysis     │       │ status            │
│ matched_products  │       │ products_found    │
│ render (R2)       │       │ started_at        │
│ budget_eur        │       │ finished_at       │
└───────────────────┘       └──────────────────┘
```

---

## Entity: Product

The central entity. One row per scraped furniture item.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| **id** | TEXT (PK) | Yes | SHA256(domain + sku + name)[:16] — stable across re-scrapes |
| created_at | TIMESTAMPTZ | Auto | First scraped timestamp |
| updated_at | TIMESTAMPTZ | Auto | Last update timestamp |
| **name** | TEXT | Yes | Original language (Bulgarian). E.g., "Диван ъглов Марио" |
| brand | TEXT | No | Brand name if available |
| sku | TEXT | No | Store's product SKU |
| model | TEXT | No | Model name/number |
| **price** | DECIMAL(10,2) | Yes | Price in EUR |
| original_price | DECIMAL(10,2) | No | Price before discount (EUR) |
| currency | TEXT | Default 'EUR' | Always EUR (converted from BGN at scrape time) |
| on_sale | BOOLEAN | Default false | Whether currently discounted |
| **category** | TEXT | Yes | English. Values: sofa, table, chair, bed, wardrobe, cabinet, desk, lamp, rug, shelf, mirror, nightstand, dresser |
| subcategory | TEXT | No | English. E.g., corner sofa, coffee table, dining chair |
| **room_type** | TEXT | No | English. Values: living room, bedroom, kitchen, bathroom, office, kids room, dining room |
| **style** | TEXT | No | English. Values: modern, scandinavian, industrial, classic, minimalist, mid-century, bohemian, rustic, art-deco, traditional |
| width_cm | DECIMAL(8,2) | No | Width in centimeters |
| height_cm | DECIMAL(8,2) | No | Height in centimeters |
| depth_cm | DECIMAL(8,2) | No | Depth in centimeters |
| weight_kg | DECIMAL(8,2) | No | Weight in kilograms |
| seat_height_cm | DECIMAL(8,2) | No | Seat height (chairs, sofas) |
| diameter_cm | DECIMAL(8,2) | No | For round tables, lamps |
| dimensions_source | TEXT | No | 'website', 'website_verified', 'ai_estimated' |
| dimensions_confidence | TEXT | No | 'verified', 'estimated_high', 'estimated_low' |
| proportion_w_h | DECIMAL(6,3) | No | Width:height ratio (from vision enrichment) |
| proportion_w_d | DECIMAL(6,3) | No | Width:depth ratio (from vision enrichment) |
| **visual_description** | TEXT | No | AI-generated English description optimized for Nano Banana prompt. 2-3 sentences. |
| color | TEXT | No | English color name |
| color_hex | TEXT | No | Hex color code from image analysis |
| color_tone | TEXT | No | 'warm', 'cool', 'neutral' |
| available_colors | JSONB | No | Array of available color options |
| materials | JSONB | No | Array of material strings |
| primary_material | TEXT | No | Main material (English) |
| finish | TEXT | No | 'matte', 'gloss', 'textured', 'natural' |
| upholstery | TEXT | No | Fabric type if applicable |
| luxury_score | DECIMAL(3,2) | No | 0.00-1.00 from vision analysis |
| ai_category | TEXT | No | AI-detected category (if differs from scraped) |
| ai_subcategory | TEXT | No | AI-detected subcategory |
| suitable_rooms | JSONB | No | AI-detected room suitability array |
| image_type | TEXT | No | 'product_photo', 'lifestyle_shot', 'cgi_render', 'catalog' |
| **image_usable** | BOOLEAN | Default false | Good enough quality for render reference? |
| image_urls | JSONB | No | Original URLs from source site (backup) |
| main_image_url | TEXT | No | Original main image URL |
| **r2_image_keys** | JSONB | No | R2 keys array: ["products/videnov.bg/abc123/000.jpg"] |
| **r2_main_image_key** | TEXT | No | Primary R2 image key |
| r2_image_count | INTEGER | Default 0 | Number of images stored in R2 |
| description | TEXT | No | Original language product description |
| features | JSONB | No | Original language feature list |
| assembly_required | BOOLEAN | No | Needs assembly? |
| warranty | TEXT | No | Warranty info |
| max_load_kg | DECIMAL(8,2) | No | Maximum load capacity |
| seating_capacity | INTEGER | No | Number of seats |
| number_of_drawers | INTEGER | No | Drawer count |
| adjustable | BOOLEAN | No | Height/position adjustable? |
| foldable | BOOLEAN | No | Can fold? |
| outdoor_suitable | BOOLEAN | No | Suitable for outdoor use? |
| **in_stock** | BOOLEAN | Default true | Currently available? |
| delivery_info | TEXT | No | Delivery terms (original language) |
| delivery_days | INTEGER | No | Estimated delivery days |
| free_delivery | BOOLEAN | No | Free delivery available? |
| rating | DECIMAL(3,2) | No | Product rating (0-5) |
| review_count | INTEGER | No | Number of reviews |
| vision_data | JSONB | No | Full raw vision analysis JSON |
| vision_enriched | BOOLEAN | Default false | Has been through vision pipeline? |
| vision_enriched_at | TIMESTAMPTZ | No | Last vision analysis timestamp |
| **product_url** | TEXT | Yes | Link to product page on source store |
| **source_domain** | TEXT | Yes | E.g., 'videnov.bg', 'ikea.bg' |

### Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| idx_products_category | category | Filter by furniture type |
| idx_products_room | room_type | Filter by room |
| idx_products_style | style | Filter by design style |
| idx_products_price | price | Price range queries |
| idx_products_source | source_domain | Filter by store |
| idx_products_stock | in_stock | Stock filter |
| idx_products_enriched | vision_enriched | Find un-enriched products |
| idx_products_usable | image_usable | Find render-ready products |
| idx_products_luxury | luxury_score | Tier matching |
| idx_products_dims | (width_cm, depth_cm) | Spatial fitting |
| **idx_products_match** | (category, style, room_type, price) WHERE in_stock=TRUE | Primary matching query — partial composite index, equality cols first, range col last |

### Validation Rules

- `id`: Generated as SHA256(source_domain + ":" + sku + ":" + name)[:16]
- `price`: Must be > 0, stored in EUR. BGN conversion: price_bgn / 1.9558 (fixed rate)
- `category`: Must be one of the English category enum values
- `name`: Preserved in original language. Must not be empty.
- `product_url`: Must be a valid URL
- `source_domain`: Must match one of the configured target sites

---

## Entity: Design

A generated room design linking a sketch to matched products and render.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| **id** | TEXT (PK) | Yes | UUID[:12] |
| created_at | TIMESTAMPTZ | Auto | When design was generated |
| sketch_r2_key | TEXT | Yes | R2 key for uploaded sketch image |
| room_analysis | JSONB | Yes | Stage 2 output — room layout JSON |
| tier | TEXT | Yes | 'budget', 'standard', 'premium', 'luxury' |
| style | TEXT | Yes | Style preference used |
| budget_eur | DECIMAL(10,2) | Yes | Total budget in EUR |
| matched_products | JSONB | Yes | Stage 3 output — array of {slot, product_id, placement} |
| budget_spent | DECIMAL(10,2) | Yes | Total spent on matched products |
| budget_remaining | DECIMAL(10,2) | Yes | Remaining budget |
| render_r2_key | TEXT | No | R2 key for generated render |
| render_prompt | TEXT | No | The prompt sent to Nano Banana (for debugging) |
| user_id | TEXT | No | Optional user reference (post-MVP) |
| is_public | BOOLEAN | Default false | Publicly shareable? (post-MVP) |

### Index

| Index | Columns | Purpose |
|-------|---------|---------|
| idx_designs_user | (user_id, created_at DESC) | User's design history |

### State Transitions

```
Created → Room Analyzed → Products Matched → Render Generated → [Swap → Re-rendered]*
```

---

## Entity: PriceHistory

Tracks price changes for products across re-scrapes.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| **id** | BIGSERIAL (PK) | Auto | Auto-increment |
| product_id | TEXT (FK → products.id) | Yes | Reference to product |
| old_price | DECIMAL(10,2) | Yes | Previous price (EUR) |
| new_price | DECIMAL(10,2) | Yes | New price (EUR) |
| currency | TEXT | Default 'EUR' | Currency |
| changed_at | TIMESTAMPTZ | Auto | When change was detected |

### Index

| Index | Columns | Purpose |
|-------|---------|---------|
| idx_price_history_product | (product_id, changed_at DESC) | Price history for a product |

---

## Entity: ScrapeJob

Records each scraping run for monitoring and debugging.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| **id** | TEXT (PK) | Yes | UUID for the scrape run |
| url | TEXT | Yes | Target URL scraped |
| status | TEXT | Default 'running' | 'running', 'done', 'failed' |
| products_found | INTEGER | Default 0 | Count of products extracted |
| pages_scraped | INTEGER | Default 0 | Pages processed |
| errors | TEXT | No | Error details if failed |
| started_at | TIMESTAMPTZ | Auto | Start time |
| finished_at | TIMESTAMPTZ | No | End time |
| duration_seconds | DECIMAL(10,2) | No | Total runtime |

---

## Cloudflare R2 Object Structure

Not a database entity, but documents the R2 key naming convention:

```
furniture-platform/
├── products/{source_domain}/{product_id}/{NNN}.webp     # Product images (WebP optimized)
├── sketches/{design_id}/sketch.{ext}                     # User uploads (original format)
├── renders/{design_id}/render_v{N}.jpg                   # Generated renders
└── thumbnails/products/{product_id}_thumb.webp           # Auto-generated (post-MVP)
```

**Notes**:
- Product images converted to WebP before upload (~60% smaller than JPEG)
- Public bucket with custom domain (e.g., `images.planche.bg`) for zero-cost CDN serving
- Set `ContentType` header on every upload

---

## Bulgarian Category Mapping

Internal reference for the BG→EN translation layer in `config.py`:

| Bulgarian (site) | English (DB) | Subcategories |
|-------------------|-------------|---------------|
| Дивани | sofa | ъглов диван → corner sofa, диван-легло → sofa bed |
| Маси | table | маса за хранене → dining table, журнална маса → coffee table |
| Столове | chair | трапезарен стол → dining chair, офис стол → office chair |
| Легла | bed | двойно легло → double bed, единично → single bed |
| Гардероби | wardrobe | |
| Шкафове | cabinet | скрин → dresser, нощно шкафче → nightstand |
| Бюра | desk | |
| Рафтове | shelf | етажерка → shelf unit, библиотека → bookcase |
| Осветление | lamp | настолна лампа → table lamp, подова лампа → floor lamp |
| Килими | rug | |
| Огледала | mirror | |
| Матраци | mattress | |
