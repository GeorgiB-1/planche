# AI Interior Design Platform — Full Implementation Plan v2
## Sketch → Furnished Room with Real Purchasable Products
### Bulgaria/Europe Market • Firecrawl • Nano Banana • Budget-Aware
### Storage: Supabase (Postgres) + Cloudflare R2 (Images)

---

## Overview

A platform where a user uploads a hand-drawn sketch or floor plan, sets a budget and style preference, and gets back a **photorealistic room render filled with real furniture products** from Bulgarian and European stores — with links to buy everything.

The render is built using **actual product photos** from the database as visual references, so Nano Banana knows exactly what each piece of furniture looks like and renders it at the correct proportions relative to the room.

```
User draws sketch on paper → photographs it → uploads
                ↓
Selects: Room type, Style (luxury/standard/budget), Budget (€500–€50,000)
                ↓
AI reads the sketch → understands room layout, dimensions, windows, doors
                ↓
Backend queries Supabase → picks real products that fit the space AND budget
                ↓
Product photos are fetched from Cloudflare R2
                ↓
Nano Banana receives: sketch + ALL product reference photos + room dimensions + product dimensions
                ↓
Generates photorealistic render with proportionally accurate real furniture
                ↓
User sees the room + product cards with names, prices, "Buy" links
                ↓
User can swap individual pieces → product photo swapped → re-renders
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                    │
│  Next.js / React                                                      │
│                                                                       │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────────────┐  │
│  │ Upload   │  │ Budget &     │  │ Rendered Room +                │  │
│  │ Sketch   │  │ Style Panel  │  │ Product Cards + Buy Links      │  │
│  └────┬─────┘  └──────┬───────┘  └───────────────▲────────────────┘  │
│       │               │                           │                   │
└───────┼───────────────┼───────────────────────────┼───────────────────┘
        │               │                           │
        ▼               ▼                           │
┌──────────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                              │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ STAGE 2: Room Analyzer (Gemini 2.5 Flash Vision)            │    │
│  │ Reads sketch → extracts rooms, dimensions, features          │    │
│  │ Output: structured JSON of room layout                       │    │
│  └───────────────────────┬──────────────────────────────────────┘    │
│                          ▼                                           │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ STAGE 3: Furniture Matcher (Budget Engine)                   │    │
│  │ Takes room layout + budget + style preference                │    │
│  │ Queries Supabase → selects real products that:               │    │
│  │   • Fit the room dimensions (verified by AI vision)          │    │
│  │   • Match the style preference                               │    │
│  │   • Stay within budget (distributes € across pieces)         │    │
│  │   • Are in stock                                             │    │
│  │   • Have AI-verified dimensions & visual descriptions        │    │
│  │ Output: list of real products + their R2 image URLs          │    │
│  └───────────────────────┬──────────────────────────────────────┘    │
│                          ▼                                           │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ STAGE 4: Design Generator (Nano Banana)                      │    │
│  │ AUTO-ASSEMBLES the prompt:                                   │    │
│  │   1. User's sketch image                                     │    │
│  │   2. Room dimensions from Stage 2                            │    │
│  │   3. EACH matched product's photo (from R2)        ← KEY    │    │
│  │   4. EACH product's verified dimensions            ← KEY    │    │
│  │   5. Placement instructions (where in room)                  │    │
│  │   6. Style/tier rendering instructions                       │    │
│  │ Nano Banana sees the actual furniture → renders it in room   │    │
│  │ Output: photorealistic render with proportionally correct    │    │
│  │         real furniture                                       │    │
│  └───────────────────────┬──────────────────────────────────────┘    │
│                          │                                           │
│  ┌───────────────────────┴──────────────────────────────────────┐    │
│  │ STAGE 1: Furniture Database                                  │    │
│  │                                                              │    │
│  │  ┌─────────────┐    ┌──────────────┐    ┌────────────────┐  │    │
│  │  │ 1A: Scraper │───▶│ 1B: Vision   │───▶│ 1C: Storage    │  │    │
│  │  │ (Firecrawl) │    │ Enrichment   │    │                │  │    │
│  │  │             │    │ (Gemini      │    │ Supabase (DB)  │  │    │
│  │  │ Scrapes     │    │  Flash)      │    │ Cloudflare R2  │  │    │
│  │  │ product     │    │             │    │ (images)       │  │    │
│  │  │ pages       │    │ Analyzes     │    │                │  │    │
│  │  │             │    │ each product │    │ Stores         │  │    │
│  │  │ Extracts    │    │ image to:    │    │ everything     │  │    │
│  │  │ raw data    │    │ • Verify     │    │ with R2 URLs   │  │    │
│  │  │             │    │   dimensions │    │                │  │    │
│  │  └─────────────┘    │ • Detect     │    └────────────────┘  │    │
│  │                      │   materials  │                        │    │
│  │                      │ • Classify   │                        │    │
│  │                      │   style      │                        │    │
│  │                      │ • Visual     │                        │    │
│  │                      │   description│                        │    │
│  │                      │   for Nano   │                        │    │
│  │                      │   Banana     │                        │    │
│  │                      │ • Proportion │                        │    │
│  │                      │   ratios     │                        │    │
│  │                      └──────────────┘                        │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## STAGE 1A: Furniture Scraper (Firecrawl)

**Status: Built ✅** (the .tar file you have)

### What it does
- Scrapes any furniture website URL using Firecrawl
- Extracts 40+ fields per product (name, price, dimensions, materials, images, colors, etc.)
- Bulgarian language-aware (keeps names in BG, translates categories to English)
- All prices in EUR

### Files (from .tar)
- `config.py` — schemas, extraction prompt, target sites
- `database.py` — storage layer (will be migrated to Supabase)
- `scraper.py` — Firecrawl engine + CLI
- `scheduler.py` — 24/7 VPS daemon

### Target sites to scrape first
| Site | URL | Priority | Products |
|------|-----|----------|----------|
| Мебели Виденов | videnov.bg | HIGH | Sofas, beds, tables, chairs, wardrobes |
| IKEA България | ikea.bg | HIGH | Full catalog |
| AIKO | aiko-bg.com | HIGH | Full catalog |
| JYSK | jysk.bg | MEDIUM | Sofas, beds, tables |
| eMAG | emag.bg | MEDIUM | Furniture section |
| Wayfair UK | wayfair.co.uk | LOW | Premium/luxury items |
| IKEA UK | ikea.com/gb | LOW | Additional range |

### Setup
```bash
pip install firecrawl-py pydantic requests
export FIRECRAWL_API_KEY="fc-your-key"
python scraper.py "https://videnov.bg/mebeli/divani"
python scraper.py --all    # scrape all configured sites
```

---

## STAGE 1B: Vision Enrichment Pipeline

**Status: Needs to be built — runs after every scrape**

### Why this is critical
Bulgarian furniture sites often have incomplete data. A sofa listing might show a photo but no dimensions, or say "дърво" (wood) but not specify what kind. Worse — without verified dimensions, we can't guarantee the furniture will look proportionally correct in the Nano Banana render.

This stage runs **every product image through Gemini 2.5 Flash Vision** to:
1. **Verify or extract dimensions** — if the site says 275×88×180cm, confirm. If dimensions are missing, estimate from the image using reference objects (cushions ~50cm, standard doors ~200cm tall)
2. **Calculate proportion ratios** — width:height:depth ratio so Nano Banana renders the furniture at correct proportions even if exact cm are slightly off
3. **Classify style accurately** — the site might say nothing about style, but the image clearly shows "scandinavian" or "industrial"
4. **Identify actual materials and colors** — from the photo, not just the text (which may be vague)
5. **Generate a visual description** — a detailed text description of what the furniture looks like, optimized for Nano Banana's prompt. This is stored in the DB and sent with every render request
6. **Detect furniture type** — confirm the category (is this actually a corner sofa or a regular 3-seater?)
7. **Flag quality issues** — blurry images, lifestyle shots where the product is hard to see, CGI renders vs real photos

### Implementation

```python
# vision_enrichment.py

from google import genai
import json
from supabase_client import supabase
from r2_client import get_r2_image_bytes

client = genai.Client(api_key=GEMINI_API_KEY)

PRODUCT_VISION_PROMPT = """You are an expert furniture analyst and interior designer.

Analyze this product image and extract the following information.
Be as precise as possible — your analysis will be used to:
  (a) place this furniture in room renders at correct proportions
  (b) match it with appropriate rooms and styles

EXISTING DATA FROM THE WEBSITE (may be incomplete or inaccurate):
Name: {name}
Category: {category}
Listed dimensions: {dimensions}
Listed materials: {materials}
Listed color: {color}
Listed style: {style}
Price: €{price}

ANALYZE THE IMAGE AND RETURN:

1. DIMENSIONS VERIFICATION:
   - If website lists dimensions, verify them against the image. Are they plausible?
   - If dimensions are MISSING, estimate from the image:
     * Use reference objects: seat cushions (~50cm deep), standard pillows (~40×60cm),
       door handles (~100cm from floor), typical seat height (~45cm)
     * Give estimated width_cm, height_cm, depth_cm
   - Confidence level: "verified", "estimated_high", "estimated_low"

2. PROPORTION RATIOS (critical for rendering):
   - width_to_height_ratio (e.g., a sofa might be 3.1:1)
   - width_to_depth_ratio (e.g., 1.5:1)
   - These ratios ensure the furniture looks correct in the render even if
     exact centimeters are slightly off

3. VISUAL DESCRIPTION FOR RENDERING:
   Write a detailed description (2-3 sentences) of what this furniture looks like,
   written specifically to help an AI image generator recreate it accurately.
   Focus on: shape, silhouette, leg style, arm style, cushion arrangement,
   distinctive features, texture, pattern, color tones.
   Example: "Low-profile 3-seat sofa with wide track arms and deep cushions.
   Upholstered in heathered grey linen-look fabric with visible stitching.
   Tapered dark wood legs, approximately 12cm tall. Clean Scandinavian silhouette."

4. MATERIAL ANALYSIS:
   - primary_material: what is the main material visible?
   - secondary_materials: other materials visible
   - finish: matte/gloss/textured/natural
   - fabric_type: if upholstered — linen, velvet, leather, microfiber, etc.

5. COLOR ANALYSIS:
   - primary_color: dominant color (in English)
   - color_hex: approximate hex code of the primary color
   - secondary_colors: accent colors
   - color_tone: warm/cool/neutral

6. STYLE CLASSIFICATION:
   - style: modern / scandinavian / industrial / classic / minimalist / mid-century /
     bohemian / rustic / art-deco / traditional / transitional
   - style_confidence: 0.0–1.0
   - luxury_score: 0.0–1.0 (how premium/luxurious does this look?)

7. CATEGORY VERIFICATION:
   - detected_category: what type of furniture is this actually?
   - detected_subcategory: more specific type
   - suitable_rooms: which rooms would this work in?

8. IMAGE QUALITY:
   - image_type: "product_photo" / "lifestyle_shot" / "cgi_render" / "catalog"
   - product_visible: 0.0–1.0 (how clearly can you see the actual product?)
   - background: "white" / "room_setting" / "transparent" / "other"
   - usable_for_reference: true/false (good enough to use as Nano Banana reference?)

Return as JSON.
"""


async def enrich_product(product: dict) -> dict:
    """Run vision analysis on a single product image."""

    # Get the product image from R2
    image_url = product.get("main_image_url") or (product.get("image_urls") or [None])[0]
    if not image_url:
        return {"error": "no_image", "product_id": product["id"]}

    # Fetch image bytes from R2 (already uploaded by scraper)
    r2_key = product.get("r2_image_key")
    if r2_key:
        image_bytes = get_r2_image_bytes(r2_key)
    else:
        # Fallback: download from original URL
        image_bytes = download_image(image_url)

    if not image_bytes:
        return {"error": "image_download_failed", "product_id": product["id"]}

    # Build the prompt with existing product data
    dims = ""
    if product.get("width_cm"):
        dims = f"{product.get('width_cm', '?')}W × {product.get('height_cm', '?')}H × {product.get('depth_cm', '?')}D cm"

    prompt = PRODUCT_VISION_PROMPT.format(
        name=product.get("name", "Unknown"),
        category=product.get("category", "Unknown"),
        dimensions=dims or "NOT LISTED",
        materials=", ".join(product.get("materials", [])) or "NOT LISTED",
        color=product.get("color", "NOT LISTED"),
        style=product.get("style", "NOT LISTED"),
        price=product.get("price", "?"),
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            {"role": "user", "parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": image_bytes}},
                {"text": prompt}
            ]}
        ],
        generation_config={"response_mime_type": "application/json"}
    )

    vision_data = json.loads(response.text)

    # Update the product in Supabase with enriched data
    updates = {}

    # Dimensions — use AI-verified/estimated if site didn't provide
    if vision_data.get("dimensions_verification"):
        dv = vision_data["dimensions_verification"]
        if not product.get("width_cm") and dv.get("estimated_width_cm"):
            updates["width_cm"] = dv["estimated_width_cm"]
            updates["height_cm"] = dv.get("estimated_height_cm")
            updates["depth_cm"] = dv.get("estimated_depth_cm")
            updates["dimensions_source"] = "ai_estimated"
            updates["dimensions_confidence"] = dv.get("confidence", "estimated_low")
        elif product.get("width_cm"):
            updates["dimensions_source"] = "website_verified" if dv.get("verified") else "website"
            updates["dimensions_confidence"] = dv.get("confidence", "verified")

    # Proportion ratios — always store these
    if vision_data.get("proportion_ratios"):
        pr = vision_data["proportion_ratios"]
        updates["proportion_w_h"] = pr.get("width_to_height_ratio")
        updates["proportion_w_d"] = pr.get("width_to_depth_ratio")

    # Visual description — critical for Nano Banana prompts
    if vision_data.get("visual_description"):
        updates["visual_description"] = vision_data["visual_description"]

    # Materials — override if AI is more specific
    if vision_data.get("material_analysis"):
        ma = vision_data["material_analysis"]
        if ma.get("primary_material") and not product.get("primary_material"):
            updates["primary_material"] = ma["primary_material"]
        if ma.get("fabric_type"):
            updates["upholstery"] = ma["fabric_type"]
        if ma.get("finish") and not product.get("finish"):
            updates["finish"] = ma["finish"]

    # Color — more accurate from image
    if vision_data.get("color_analysis"):
        ca = vision_data["color_analysis"]
        if not product.get("color"):
            updates["color"] = ca.get("primary_color")
        updates["color_hex"] = ca.get("color_hex")
        updates["color_tone"] = ca.get("color_tone")

    # Style — AI is often more accurate than site labels
    if vision_data.get("style_classification"):
        sc = vision_data["style_classification"]
        if sc.get("style_confidence", 0) > 0.6:
            updates["style"] = sc["style"]
        updates["luxury_score"] = sc.get("luxury_score", 0)

    # Category verification
    if vision_data.get("category_verification"):
        cv = vision_data["category_verification"]
        if cv.get("detected_category") != product.get("category"):
            updates["ai_category"] = cv["detected_category"]
            updates["ai_subcategory"] = cv.get("detected_subcategory")
        updates["suitable_rooms"] = json.dumps(cv.get("suitable_rooms", []))

    # Image quality
    if vision_data.get("image_quality"):
        iq = vision_data["image_quality"]
        updates["image_type"] = iq.get("image_type")
        updates["image_usable"] = iq.get("usable_for_reference", False)

    # Store full vision analysis as JSON
    updates["vision_data"] = json.dumps(vision_data)
    updates["vision_enriched"] = True
    updates["vision_enriched_at"] = "now()"

    # Write to Supabase
    if updates:
        supabase.table("products").update(updates).eq("id", product["id"]).execute()

    return {"product_id": product["id"], "updates": updates}


async def enrich_all_unenriched():
    """Run vision enrichment on all products that haven't been analyzed yet."""

    # Query Supabase for products with images but no vision data
    result = supabase.table("products") \
        .select("*") \
        .eq("vision_enriched", False) \
        .not_.is_("main_image_url", "null") \
        .limit(100) \
        .execute()

    products = result.data
    print(f"Enriching {len(products)} products...")

    enriched = 0
    errors = 0
    for product in products:
        try:
            result = await enrich_product(product)
            if "error" not in result:
                enriched += 1
            else:
                errors += 1
            # Rate limit — Gemini Flash free tier
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Error enriching {product['id']}: {e}")
            errors += 1

    print(f"Done: {enriched} enriched, {errors} errors")
    return {"enriched": enriched, "errors": errors}
```

### New DB Fields Added by Vision Enrichment

These columns get added to the Supabase `products` table:

| Field | Type | Purpose |
|-------|------|---------|
| `visual_description` | text | 2-3 sentence visual description optimized for Nano Banana prompt |
| `proportion_w_h` | float | Width:height ratio for proportionally correct rendering |
| `proportion_w_d` | float | Width:depth ratio for proportionally correct rendering |
| `dimensions_source` | text | "website", "website_verified", "ai_estimated" |
| `dimensions_confidence` | text | "verified", "estimated_high", "estimated_low" |
| `color_hex` | text | Hex color code from image analysis |
| `color_tone` | text | "warm", "cool", "neutral" |
| `luxury_score` | float | 0.0–1.0 how premium the product looks |
| `ai_category` | text | AI-detected category (if differs from scraped) |
| `ai_subcategory` | text | AI-detected subcategory |
| `suitable_rooms` | jsonb | AI-detected room suitability |
| `image_type` | text | "product_photo", "lifestyle_shot", "cgi_render" |
| `image_usable` | boolean | Good enough quality for Nano Banana reference? |
| `vision_data` | jsonb | Full raw vision analysis JSON |
| `vision_enriched` | boolean | Has this product been analyzed? |
| `vision_enriched_at` | timestamp | When was it last analyzed? |

### When vision enrichment runs
- **After every scrape batch** — scheduler runs `enrich_all_unenriched()` after `scrape_all_targets()`
- **On demand** — `python vision_enrichment.py --all` or `--product-id X`
- **Priority queue** — products with images but no dimensions get enriched first (most valuable)

---

## STAGE 1C: Storage Layer (Supabase + Cloudflare R2)

**Status: Needs to be built — replaces SQLite + local filesystem**

### Why this stack

| Need | Solution | Why |
|------|----------|-----|
| Structured product data | **Supabase (Postgres)** | Relational queries, JSONB for flexible fields, REST API, auth built in, real-time subscriptions for live updates |
| Product images | **Cloudflare R2** | S3-compatible, no egress fees (critical — images served to Nano Banana + frontend), you already have a Cloudflare account |
| Generated renders | **Cloudflare R2** | Same bucket, different prefix, served to frontend |
| User uploads (sketches) | **Cloudflare R2** | Temporary storage for processing |

### Supabase Schema

```sql
-- products table — one row per scraped furniture product
CREATE TABLE products (
    id TEXT PRIMARY KEY,                    -- SHA256(domain + sku + name)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Identity
    name TEXT NOT NULL,                     -- original language (Bulgarian OK)
    brand TEXT,
    sku TEXT,
    model TEXT,

    -- Pricing (EUR)
    price DECIMAL(10,2),
    original_price DECIMAL(10,2),
    currency TEXT DEFAULT 'EUR',
    on_sale BOOLEAN DEFAULT FALSE,

    -- Classification
    category TEXT,                          -- English: sofa, table, chair, bed...
    subcategory TEXT,                       -- English: corner sofa, coffee table...
    room_type TEXT,                         -- English: living room, bedroom...
    style TEXT,                             -- English: modern, scandinavian...

    -- Dimensions (cm/kg) — from scraping OR AI vision
    width_cm DECIMAL(8,2),
    height_cm DECIMAL(8,2),
    depth_cm DECIMAL(8,2),
    weight_kg DECIMAL(8,2),
    seat_height_cm DECIMAL(8,2),
    diameter_cm DECIMAL(8,2),

    -- AI Vision Enrichment (Stage 1B)
    dimensions_source TEXT,                 -- 'website', 'website_verified', 'ai_estimated'
    dimensions_confidence TEXT,             -- 'verified', 'estimated_high', 'estimated_low'
    proportion_w_h DECIMAL(6,3),            -- width:height ratio
    proportion_w_d DECIMAL(6,3),            -- width:depth ratio
    visual_description TEXT,                -- AI-generated description for Nano Banana
    color_hex TEXT,                          -- '#8B7355'
    color_tone TEXT,                         -- 'warm', 'cool', 'neutral'
    luxury_score DECIMAL(3,2),              -- 0.00–1.00
    ai_category TEXT,                       -- AI-detected category if differs
    ai_subcategory TEXT,
    suitable_rooms JSONB,                   -- ["living room", "office"]
    image_type TEXT,                         -- 'product_photo', 'lifestyle_shot', 'cgi_render'
    image_usable BOOLEAN DEFAULT FALSE,     -- good enough for Nano Banana reference?
    vision_data JSONB,                      -- full raw vision analysis
    vision_enriched BOOLEAN DEFAULT FALSE,
    vision_enriched_at TIMESTAMPTZ,

    -- Materials & Appearance
    materials JSONB,                        -- ["oak", "fabric", "foam"]
    primary_material TEXT,
    color TEXT,                             -- English: grey, white, oak...
    available_colors JSONB,                 -- ["grey", "blue", "beige"]
    finish TEXT,
    upholstery TEXT,

    -- Images — Cloudflare R2
    image_urls JSONB,                       -- original URLs from site (backup)
    main_image_url TEXT,                    -- original main URL
    r2_image_keys JSONB,                    -- ["products/videnov/abc123/000.jpg", ...]
    r2_main_image_key TEXT,                 -- "products/videnov/abc123/000.jpg"
    r2_image_count INTEGER DEFAULT 0,

    -- Details
    description TEXT,                       -- original language
    features JSONB,                         -- original language
    assembly_required BOOLEAN,
    warranty TEXT,
    care_instructions TEXT,
    max_load_kg DECIMAL(8,2),
    seating_capacity INTEGER,
    number_of_drawers INTEGER,
    adjustable BOOLEAN,
    foldable BOOLEAN,
    outdoor_suitable BOOLEAN,
    eco_certified BOOLEAN,

    -- Availability
    in_stock BOOLEAN,
    delivery_info TEXT,
    delivery_days INTEGER,
    free_delivery BOOLEAN,
    stock_quantity INTEGER,

    -- Reviews
    rating DECIMAL(3,2),
    review_count INTEGER,

    -- Source
    product_url TEXT,
    source_domain TEXT
);

-- Indexes for fast matching queries
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_room ON products(room_type);
CREATE INDEX idx_products_style ON products(style);
CREATE INDEX idx_products_price ON products(price);
CREATE INDEX idx_products_source ON products(source_domain);
CREATE INDEX idx_products_stock ON products(in_stock);
CREATE INDEX idx_products_enriched ON products(vision_enriched);
CREATE INDEX idx_products_usable ON products(image_usable);
CREATE INDEX idx_products_luxury ON products(luxury_score);
CREATE INDEX idx_products_dims ON products(width_cm, depth_cm);

-- Composite index for the most common matching query
CREATE INDEX idx_products_match ON products(category, in_stock, image_usable, price)
    WHERE in_stock = TRUE AND image_usable = TRUE;


-- price_history — tracks price changes over time
CREATE TABLE price_history (
    id BIGSERIAL PRIMARY KEY,
    product_id TEXT REFERENCES products(id),
    old_price DECIMAL(10,2),
    new_price DECIMAL(10,2),
    currency TEXT DEFAULT 'EUR',
    changed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_price_history_product ON price_history(product_id, changed_at DESC);


-- scrape_jobs — tracks each scrape run
CREATE TABLE scrape_jobs (
    id TEXT PRIMARY KEY,
    url TEXT,
    status TEXT DEFAULT 'running',          -- 'running', 'done', 'failed'
    products_found INTEGER DEFAULT 0,
    pages_scraped INTEGER DEFAULT 0,
    errors TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    duration_seconds DECIMAL(10,2)
);


-- designs — stores generated room designs
CREATE TABLE designs (
    id TEXT PRIMARY KEY,                    -- UUID
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Input
    sketch_r2_key TEXT,                     -- R2 key for uploaded sketch
    room_analysis JSONB,                    -- Stage 2 output
    tier TEXT,                              -- 'budget', 'standard', 'premium', 'luxury'
    style TEXT,
    budget_eur DECIMAL(10,2),

    -- Matched products
    matched_products JSONB,                 -- Stage 3 output (product IDs + placements)
    budget_spent DECIMAL(10,2),
    budget_remaining DECIMAL(10,2),

    -- Output
    render_r2_key TEXT,                     -- R2 key for generated render
    render_prompt TEXT,                     -- the prompt sent to Nano Banana (for debugging)

    -- User
    user_id TEXT,                           -- optional, for saved designs
    is_public BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_designs_user ON designs(user_id, created_at DESC);
```

### Cloudflare R2 Structure

```
furniture-platform-r2/
│
├── products/                           # Product images from scraping
│   ├── videnov.bg/
│   │   ├── {product_id}/
│   │   │   ├── 000.jpg                 # Main product image
│   │   │   ├── 001.jpg                 # Additional angles
│   │   │   └── 002.jpg
│   │   └── {product_id}/
│   │       └── 000.jpg
│   ├── ikea.bg/
│   │   └── ...
│   └── jysk.bg/
│       └── ...
│
├── sketches/                           # User-uploaded sketches
│   └── {design_id}/
│       └── sketch.jpg
│
├── renders/                            # Nano Banana generated renders
│   └── {design_id}/
│       ├── render_v1.jpg
│       ├── render_v2.jpg              # After swap
│       └── render_v3.jpg
│
└── thumbnails/                         # Auto-generated for frontend
    └── products/
        └── {product_id}_thumb.jpg
```

### R2 Client

```python
# r2_client.py

import boto3
from botocore.config import Config
import os

R2_ACCOUNT_ID = os.environ["CF_ACCOUNT_ID"]
R2_ACCESS_KEY = os.environ["R2_ACCESS_KEY"]
R2_SECRET_KEY = os.environ["R2_SECRET_KEY"]
R2_BUCKET = os.environ.get("R2_BUCKET", "furniture-platform")
R2_PUBLIC_URL = os.environ.get("R2_PUBLIC_URL", f"https://pub-xxx.r2.dev")

s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(signature_version="s3v4"),
    region_name="auto",
)


def upload_image(image_bytes: bytes, r2_key: str, content_type: str = "image/jpeg") -> str:
    """Upload image to R2 and return public URL."""
    s3.put_object(
        Bucket=R2_BUCKET,
        Key=r2_key,
        Body=image_bytes,
        ContentType=content_type,
    )
    return f"{R2_PUBLIC_URL}/{r2_key}"


def get_image_url(r2_key: str) -> str:
    """Get public URL for an R2 image."""
    return f"{R2_PUBLIC_URL}/{r2_key}"


def get_r2_image_bytes(r2_key: str) -> bytes:
    """Download image bytes from R2 (used by vision enrichment + Nano Banana prompt)."""
    response = s3.get_object(Bucket=R2_BUCKET, Key=r2_key)
    return response["Body"].read()


def delete_image(r2_key: str):
    """Delete an image from R2."""
    s3.delete_object(Bucket=R2_BUCKET, Key=r2_key)


def upload_product_images(product_id: str, domain: str, image_urls: list) -> list:
    """Download product images from URLs and upload to R2. Returns R2 keys."""
    import requests
    r2_keys = []

    for i, url in enumerate(image_urls[:10]):  # max 10 images per product
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                ext = "jpg"  # default
                ct = resp.headers.get("content-type", "")
                if "png" in ct: ext = "png"
                elif "webp" in ct: ext = "webp"

                r2_key = f"products/{domain}/{product_id}/{i:03d}.{ext}"
                upload_image(resp.content, r2_key, ct or "image/jpeg")
                r2_keys.append(r2_key)

                import time; time.sleep(0.3)
        except Exception as e:
            print(f"Failed to upload image {url}: {e}")

    return r2_keys
```

### Supabase Client

```python
# supabase_client.py

from supabase import create_client
import os

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]  # service role key for backend

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def save_product(product: dict, domain: str) -> str:
    """Upsert a product into Supabase. Returns product ID."""
    import hashlib

    # Generate stable product ID
    id_string = f"{domain}:{product.get('sku', '')}:{product.get('name', '')}"
    product_id = hashlib.sha256(id_string.encode()).hexdigest()[:16]

    # Check if product exists (for price tracking)
    existing = supabase.table("products").select("id, price").eq("id", product_id).execute()

    if existing.data:
        old_price = existing.data[0].get("price")
        new_price = product.get("price")
        if old_price and new_price and float(old_price) != float(new_price):
            # Track price change
            supabase.table("price_history").insert({
                "product_id": product_id,
                "old_price": float(old_price),
                "new_price": float(new_price),
            }).execute()

    # Upsert product
    row = {
        "id": product_id,
        "source_domain": domain,
        "updated_at": "now()",
        **{k: v for k, v in product.items() if v is not None}
    }
    supabase.table("products").upsert(row, on_conflict="id").execute()

    return product_id
```

### Scraper → R2 → Supabase Flow

The updated scraper pipeline:

```
Firecrawl scrapes page
       ↓
Extracts product data (name, price, dimensions, image_urls, etc.)
       ↓
Downloads product images from image_urls
       ↓
Uploads images to Cloudflare R2 → gets r2_keys
       ↓
Saves product to Supabase with r2_image_keys + r2_main_image_key
       ↓
Vision enrichment runs (async) → reads image from R2
       ↓
Updates Supabase with visual_description, proportions, verified dims, etc.
```

---

## STAGE 2: Room Analyzer

**Status: Needs to be built**

### What it does
Takes a sketch/photo of a floor plan and uses Gemini 2.5 Flash Vision to understand it.

### Input
- Photo of a hand-drawn sketch, scan, or digital floor plan image
- User-selected room type (optional — AI can detect it)

### Output — structured JSON
```json
{
  "rooms": [
    {
      "id": "room_1",
      "type": "living room",
      "estimated_width_cm": 450,
      "estimated_depth_cm": 380,
      "estimated_area_sqm": 17.1,
      "features": {
        "windows": [
          {"wall": "north", "width_cm": 180, "position": "center"}
        ],
        "doors": [
          {"wall": "east", "width_cm": 90, "type": "standard", "connects_to": "hallway"}
        ],
        "balcony_access": false,
        "fireplace": false
      },
      "usable_walls": [
        {"wall": "south", "free_length_cm": 350, "suitable_for": ["sofa", "shelving", "TV unit"]},
        {"wall": "west", "free_length_cm": 280, "suitable_for": ["bookcase", "desk"]}
      ],
      "furniture_zones": [
        {"zone": "seating_area", "position": "center-south", "area_cm": [300, 250]},
        {"zone": "dining_corner", "position": "north-east", "area_cm": [200, 150]}
      ]
    }
  ],
  "overall": {
    "total_rooms": 2,
    "total_area_sqm": 27.6,
    "style_hints": ["open plan", "modern proportions"],
    "detected_labels": ["хол", "спалня"]
  }
}
```

### Implementation

```python
# room_analyzer.py

from google import genai

client = genai.Client(api_key=GEMINI_API_KEY)

ROOM_ANALYSIS_PROMPT = """You are an expert interior designer and architect.

Analyze this floor plan sketch/drawing and extract:

1. Each distinct room:
   - Type (living room, bedroom, kitchen, bathroom, office, dining room, kids room, hallway)
   - Estimated dimensions in centimeters (width × depth)
   - Approximate area in square meters
   - Windows: which wall, approximate width, position
   - Doors: which wall, width, what they connect to
   - Special features: balcony, fireplace, built-in storage, etc.

2. For each room, identify:
   - Usable wall sections (free wall space where furniture can go)
   - What type of furniture would fit against each wall, and maximum dimensions
   - Open floor zones where furniture groupings should go
   - Traffic paths that must stay clear (minimum 80cm walkways)

3. If the sketch has labels in Bulgarian (хол, спалня, кухня, баня, etc.),
   translate them to English for the room type but note the original label.

4. Estimate real-world dimensions even from rough sketches.
   Use door widths (standard ~80-90cm) as reference scale.

CRITICAL: Be specific about centimeter measurements. They will be compared against
real furniture product dimensions to ensure nothing is too big for the room.
For each usable wall, state the maximum furniture width that can fit there.

Return as structured JSON matching the schema provided.
"""


async def analyze_room(sketch_image: bytes, mime_type: str = "image/jpeg") -> dict:
    """Send sketch to Gemini Vision → get structured room layout."""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            {"role": "user", "parts": [
                {"inline_data": {"mime_type": mime_type, "data": sketch_image}},
                {"text": ROOM_ANALYSIS_PROMPT}
            ]}
        ],
        generation_config={"response_mime_type": "application/json"}
    )

    return json.loads(response.text)
```

### Key decisions
- Use **Gemini 2.5 Flash** for room analysis (fast, cheap, good vision)
- Save **Nano Banana (Gemini Image model)** for the final render only
- The room analyzer doesn't generate images — it just reads the sketch and outputs data
- Wall measurements include max furniture width → directly compared against product `width_cm` from DB

---

## STAGE 3: Furniture Matcher (Budget Engine)

**Status: Needs to be built — this is the core business logic**

### What it does
Takes the room analysis + user preferences → queries Supabase → returns real products that:
1. **Fit the physical space** — product width_cm ≤ wall's max width (uses AI-verified dimensions)
2. **Match the style** — luxury, modern, scandinavian, budget-friendly, etc.
3. **Stay within budget** — smart allocation across furniture pieces
4. **Are in stock** and available for delivery
5. **Have usable images** — `image_usable = TRUE` (from vision enrichment)
6. **Have proportion data** — so Nano Banana renders them correctly

### Budget Tiers

```python
BUDGET_TIERS = {
    "budget": {
        "label": "Бюджетен / Budget",
        "description": "Functional, affordable furniture from JYSK, IKEA, eMAG",
        "per_sqm_eur": (30, 60),
        "preferred_sources": ["jysk.bg", "ikea.bg", "emag.bg"],
        "max_single_item_pct": 0.35,
        "style_keywords": ["budget", "basic", "functional", "minimalist"],
    },
    "standard": {
        "label": "Стандартен / Standard",
        "description": "Good quality mid-range from Videnov, IKEA, AIKO",
        "per_sqm_eur": (60, 150),
        "preferred_sources": ["videnov.bg", "ikea.bg", "aiko-bg.com"],
        "max_single_item_pct": 0.30,
        "style_keywords": ["modern", "scandinavian", "contemporary"],
    },
    "premium": {
        "label": "Премиум / Premium",
        "description": "High-quality designer furniture",
        "per_sqm_eur": (150, 350),
        "preferred_sources": ["wayfair.co.uk", "ikea.com", "videnov.bg"],
        "max_single_item_pct": 0.25,
        "style_keywords": ["premium", "designer", "high-end"],
    },
    "luxury": {
        "label": "Луксозен / Luxury",
        "description": "Top-tier luxury furniture, premium materials",
        "per_sqm_eur": (350, 1000),
        "preferred_sources": ["wayfair.co.uk"],
        "max_single_item_pct": 0.25,
        "style_keywords": ["luxury", "premium", "designer", "exclusive"],
    },
}
```

### Budget Allocation Logic

```python
ROOM_BUDGET_ALLOCATION = {
    "living room": {
        "seating":      (0.30, 0.40),
        "tables":       (0.08, 0.15),
        "storage":      (0.10, 0.20),
        "lighting":     (0.05, 0.10),
        "rugs":         (0.05, 0.10),
        "decor":        (0.05, 0.10),
    },
    "bedroom": {
        "bed":          (0.35, 0.45),
        "storage":      (0.20, 0.30),
        "nightstands":  (0.08, 0.12),
        "lighting":     (0.05, 0.10),
        "rugs":         (0.03, 0.08),
        "decor":        (0.03, 0.08),
    },
    "kitchen": {
        "dining_table": (0.25, 0.35),
        "chairs":       (0.20, 0.30),
        "storage":      (0.15, 0.25),
        "lighting":     (0.05, 0.10),
        "accessories":  (0.05, 0.10),
    },
    "dining room": {
        "dining_table": (0.30, 0.40),
        "chairs":       (0.25, 0.35),
        "storage":      (0.10, 0.20),
        "lighting":     (0.05, 0.10),
        "decor":        (0.05, 0.10),
    },
    "office": {
        "desk":         (0.30, 0.40),
        "chair":        (0.20, 0.30),
        "storage":      (0.15, 0.25),
        "lighting":     (0.05, 0.10),
        "accessories":  (0.05, 0.10),
    },
    "kids room": {
        "bed":          (0.30, 0.40),
        "desk":         (0.15, 0.20),
        "storage":      (0.20, 0.30),
        "lighting":     (0.05, 0.10),
        "decor":        (0.05, 0.10),
    },
}

ROOM_FURNITURE_REQUIREMENTS = {
    "living room": {
        "required": [
            {"slot": "sofa", "categories": ["sofa", "corner sofa", "sofa bed"], "quantity": 1},
            {"slot": "coffee_table", "categories": ["coffee table", "table"], "quantity": 1},
        ],
        "optional": [
            {"slot": "tv_unit", "categories": ["TV stand", "wall unit", "shelving"], "quantity": 1},
            {"slot": "armchair", "categories": ["armchair", "chair"], "quantity": (0, 2)},
            {"slot": "bookcase", "categories": ["bookcase", "shelf unit", "shelving"], "quantity": (0, 1)},
            {"slot": "floor_lamp", "categories": ["lamp", "floor lamp"], "quantity": (0, 2)},
            {"slot": "rug", "categories": ["rug", "carpet"], "quantity": (0, 1)},
            {"slot": "side_table", "categories": ["side table", "table"], "quantity": (0, 2)},
        ],
    },
    "bedroom": {
        "required": [
            {"slot": "bed", "categories": ["bed", "double bed"], "quantity": 1},
            {"slot": "wardrobe", "categories": ["wardrobe", "cabinet"], "quantity": 1},
        ],
        "optional": [
            {"slot": "nightstand", "categories": ["nightstand", "bedside table"], "quantity": (0, 2)},
            {"slot": "dresser", "categories": ["dresser", "chest of drawers"], "quantity": (0, 1)},
            {"slot": "mirror", "categories": ["mirror"], "quantity": (0, 1)},
            {"slot": "lamp", "categories": ["lamp", "table lamp"], "quantity": (0, 2)},
            {"slot": "rug", "categories": ["rug"], "quantity": (0, 1)},
        ],
    },
    "kitchen": {
        "required": [
            {"slot": "dining_table", "categories": ["dining table", "kitchen table", "table"], "quantity": 1},
            {"slot": "chairs", "categories": ["dining chair", "chair"], "quantity": (2, 6)},
        ],
        "optional": [
            {"slot": "storage", "categories": ["cabinet", "shelf unit"], "quantity": (0, 1)},
        ],
    },
    "office": {
        "required": [
            {"slot": "desk", "categories": ["desk", "office desk"], "quantity": 1},
            {"slot": "chair", "categories": ["office chair", "chair"], "quantity": 1},
        ],
        "optional": [
            {"slot": "bookcase", "categories": ["bookcase", "shelf unit"], "quantity": (0, 2)},
            {"slot": "lamp", "categories": ["desk lamp", "lamp"], "quantity": (0, 1)},
        ],
    },
}
```

### The Matching Algorithm

```python
# furniture_matcher.py

def match_furniture_for_room(
    room: dict,
    budget_eur: float,
    tier: str,
    style: str = None,
) -> dict:
    """
    Find real products from Supabase that fit, match style, stay within budget,
    and have usable images + proportion data for accurate rendering.
    """

    room_type = room["type"]
    room_width = room["estimated_width_cm"]
    room_depth = room["estimated_depth_cm"]

    tier_config = BUDGET_TIERS[tier]
    allocations = ROOM_BUDGET_ALLOCATION.get(room_type, {})
    requirements = ROOM_FURNITURE_REQUIREMENTS.get(room_type, {})

    selected_products = []
    remaining_budget = budget_eur
    total_spent = 0

    # --- Step 1: Fill required furniture slots ---
    for slot in requirements.get("required", []):
        slot_name = slot["slot"]
        categories = slot["categories"]
        quantity = slot["quantity"] if isinstance(slot["quantity"], int) else slot["quantity"][1]

        alloc = allocations.get(slot_name.split("_")[0], allocations.get(slot_name, (0.15, 0.25)))
        slot_budget = remaining_budget * alloc[1]
        per_item_budget = slot_budget / quantity

        # Get max dimension from room analysis
        max_width = get_max_dimension_for_slot(slot_name, room)

        # Query Supabase — ONLY products with usable images
        candidates = query_supabase_for_matching(
            categories=categories,
            room=room_type,
            style=style,
            min_price=per_item_budget * 0.3,
            max_price=per_item_budget,
            max_width=max_width,
            preferred_sources=tier_config["preferred_sources"],
            require_usable_image=True,
            require_proportions=True,
            limit=5,
        )

        if candidates:
            best = rank_candidates(candidates, target_price=per_item_budget, tier=tier)
            for i in range(quantity):
                selected_products.append({
                    "slot": slot_name,
                    "product": best,
                    "quantity": 1,
                    "placement": get_placement_for_slot(slot_name, room),
                })
                total_spent += best["price"]
                remaining_budget -= best["price"]

    # --- Step 2: Fill optional slots with remaining budget ---
    for slot in requirements.get("optional", []):
        if remaining_budget <= 0:
            break

        slot_name = slot["slot"]
        categories = slot["categories"]

        alloc = allocations.get(slot_name, (0.03, 0.08))
        slot_budget = min(remaining_budget * 0.4, budget_eur * alloc[1])

        if slot_budget < 15:
            continue

        max_width = get_max_dimension_for_slot(slot_name, room)

        candidates = query_supabase_for_matching(
            categories=categories,
            max_price=slot_budget,
            style=style,
            max_width=max_width,
            preferred_sources=tier_config["preferred_sources"],
            require_usable_image=True,
            limit=3,
        )

        if candidates:
            best = rank_candidates(candidates, target_price=slot_budget * 0.7, tier=tier)
            selected_products.append({
                "slot": slot_name,
                "product": best,
                "quantity": 1,
                "placement": get_placement_for_slot(slot_name, room),
            })
            total_spent += best["price"]
            remaining_budget -= best["price"]

    # --- Step 3: Build result with R2 image URLs ---
    return {
        "room": room,
        "tier": tier,
        "style": style,
        "budget_total": budget_eur,
        "budget_spent": round(total_spent, 2),
        "budget_remaining": round(remaining_budget, 2),
        "budget_utilization_pct": round((total_spent / budget_eur) * 100, 1),
        "products": selected_products,
        "product_count": len(selected_products),

        # Product images for Nano Banana prompt — auto-included
        "product_images_for_render": [
            {
                "slot": p["slot"],
                "r2_key": p["product"]["r2_main_image_key"],
                "r2_url": get_image_url(p["product"]["r2_main_image_key"]),
                "visual_description": p["product"].get("visual_description", ""),
                "width_cm": p["product"].get("width_cm"),
                "height_cm": p["product"].get("height_cm"),
                "depth_cm": p["product"].get("depth_cm"),
                "proportion_w_h": p["product"].get("proportion_w_h"),
                "proportion_w_d": p["product"].get("proportion_w_d"),
                "color": p["product"].get("color"),
                "primary_material": p["product"].get("primary_material"),
            }
            for p in selected_products
            if p["product"].get("r2_main_image_key")
        ],

        # Buy links for frontend
        "buy_links": [
            {
                "name": p["product"]["name"],
                "price": p["product"]["price"],
                "currency": p["product"]["currency"],
                "url": p["product"]["product_url"],
                "source": p["product"]["source_domain"],
                "image_url": get_image_url(p["product"]["r2_main_image_key"]),
            }
            for p in selected_products
        ],
    }


def get_max_dimension_for_slot(slot: str, room: dict) -> int:
    """Get max furniture width for this slot from room analysis."""
    room_width = room["estimated_width_cm"]
    room_depth = room["estimated_depth_cm"]

    # Try to use wall measurements from room analysis
    usable_walls = room.get("usable_walls", [])
    for wall in usable_walls:
        if slot in wall.get("suitable_for", []):
            return int(wall.get("free_length_cm", room_width * 0.6))

    # Fallback proportional limits
    limits = {
        "sofa": room_width * 0.75,
        "coffee_table": room_width * 0.35,
        "bed": min(room_width * 0.7, 220),
        "wardrobe": room_width * 0.6,
        "desk": min(room_width * 0.5, 180),
        "dining_table": min(room_width * 0.6, room_depth * 0.5),
        "tv_unit": room_width * 0.5,
        "bookcase": room_width * 0.4,
        "nightstand": 60,
        "dresser": room_width * 0.4,
        "lamp": 50,
        "rug": room_width * 0.7,
        "chair": 80,
        "armchair": 100,
        "side_table": 60,
        "mirror": room_width * 0.3,
    }
    return int(limits.get(slot, room_width * 0.5))


def query_supabase_for_matching(
    categories: list = None,
    room: str = None,
    style: str = None,
    min_price: float = None,
    max_price: float = None,
    max_width: int = None,
    preferred_sources: list = None,
    require_usable_image: bool = True,
    require_proportions: bool = False,
    limit: int = 10,
) -> list:
    """Query Supabase for matching products."""

    query = supabase.table("products").select("*")

    if categories:
        # category IN (list) OR subcategory IN (list)
        cat_filter = ",".join(categories)
        query = query.or_(f"category.in.({cat_filter}),subcategory.in.({cat_filter})")

    if room:
        query = query.ilike("room_type", f"%{room}%")

    if style:
        query = query.or_(f"style.ilike.%{style}%,style.is.null")

    if min_price is not None:
        query = query.gte("price", min_price)

    if max_price is not None:
        query = query.lte("price", max_price)

    if max_width:
        query = query.or_(f"width_cm.lte.{max_width},width_cm.is.null")

    if require_usable_image:
        query = query.eq("image_usable", True)
        query = query.not_.is_("r2_main_image_key", "null")

    if require_proportions:
        query = query.not_.is_("proportion_w_h", "null")

    query = query.eq("in_stock", True)

    if preferred_sources:
        query = query.in_("source_domain", preferred_sources)

    query = query.order("rating", desc=True, nulls_last=True)
    query = query.limit(limit)

    result = query.execute()
    return result.data


def rank_candidates(candidates: list, target_price: float, tier: str) -> dict:
    """Score and rank furniture candidates. Returns best match."""
    scored = []
    for c in candidates:
        score = 0

        # Price proximity to target
        if c.get("price") and target_price:
            price_ratio = c["price"] / target_price
            if 0.6 <= price_ratio <= 1.1:
                score += 30
            elif 0.4 <= price_ratio <= 1.3:
                score += 15
            if tier == "luxury" and price_ratio > 0.8:
                score += 10

        # Has R2 image (essential)
        if c.get("r2_main_image_key"):
            score += 25

        # Has AI-verified dimensions (essential for proportion accuracy)
        if c.get("dimensions_source") in ("website_verified", "ai_estimated"):
            score += 20
        elif c.get("width_cm"):
            score += 10

        # Has visual description (better Nano Banana prompt)
        if c.get("visual_description"):
            score += 15

        # Has proportion ratios (critical for rendering)
        if c.get("proportion_w_h"):
            score += 15

        # Luxury score matches tier
        if c.get("luxury_score"):
            if tier == "luxury" and c["luxury_score"] > 0.7:
                score += 15
            elif tier == "budget" and c["luxury_score"] < 0.3:
                score += 10
            elif tier in ("standard", "premium") and 0.3 <= c["luxury_score"] <= 0.7:
                score += 10

        # Rating
        if c.get("rating") and c["rating"] >= 4.0:
            score += 10

        scored.append((score, c))

    scored.sort(key=lambda x: -x[0])
    return scored[0][1] if scored else candidates[0]
```

### Multi-Room Budget Distribution

```python
ROOM_BUDGET_WEIGHT = {
    "living room":  0.30,
    "bedroom":      0.25,
    "kitchen":      0.20,
    "dining room":  0.10,
    "office":       0.08,
    "kids room":    0.05,
    "bathroom":     0.02,
}

def distribute_budget_across_rooms(rooms: list, total_budget: float) -> dict:
    """Split total budget across rooms proportionally."""
    weights = {}
    for room in rooms:
        rtype = room["type"]
        base = ROOM_BUDGET_WEIGHT.get(rtype, 0.05)
        area = room.get("estimated_area_sqm", 15)
        weights[room["id"]] = base * (area / 15)

    total_weight = sum(weights.values())
    return {
        rid: round((w / total_weight) * total_budget, 2)
        for rid, w in weights.items()
    }
```

---

## STAGE 4: Design Generator (Nano Banana)

**Status: Needs to be built**

### What it does
Takes the room layout + matched products → **automatically fetches each product's photo from R2** → sends everything to Nano Banana → gets a photorealistic render with proportionally correct real furniture.

### How product images are automatically included

This is NOT optional. Every render request automatically:
1. Gets the list of matched products from Stage 3 (which includes `r2_main_image_key` for each)
2. Downloads each product image from Cloudflare R2
3. Includes ALL product images in the Nano Banana prompt as visual references
4. Includes each product's AI-generated `visual_description` + verified dimensions
5. Includes proportion ratios so Nano Banana knows relative sizes

```python
# design_generator.py

from google import genai
from r2_client import get_r2_image_bytes, get_image_url, upload_image
from supabase_client import supabase
import base64
import json
import uuid

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_room_design(
    sketch_image: bytes,
    room_data: dict,          # from Stage 2
    matched_products: dict,   # from Stage 3
    style: str = "modern",
    design_id: str = None,
) -> dict:
    """
    Generate photorealistic room render.

    ALWAYS sends the actual product photos from R2 as visual references
    so Nano Banana knows exactly what each piece looks like.
    """

    if not design_id:
        design_id = str(uuid.uuid4())[:12]

    # Room description
    room = room_data
    room_desc = (
        f"{room['type'].title()}, {room['estimated_width_cm']}cm × "
        f"{room['estimated_depth_cm']}cm ({room['estimated_area_sqm']} m²)"
    )

    tier = matched_products["tier"]

    # === BUILD THE MULTIMODAL PROMPT ===
    parts = []

    # Part 1: The sketch
    parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(sketch_image).decode()}})
    parts.append({"text": f"Above is the floor plan sketch for a {room_desc}.\n\n"})

    # Part 2: Each product image from R2 + its description + dimensions
    parts.append({"text": "Below are the REAL furniture products to place in this room. "
                          "Each product photo is followed by its exact description and dimensions. "
                          "The furniture in the render MUST visually match these product photos "
                          "and respect their proportions.\n\n"})

    product_reference_data = matched_products.get("product_images_for_render", [])

    for item in product_reference_data:
        r2_key = item.get("r2_key")
        if not r2_key:
            continue

        # Fetch the actual product image from Cloudflare R2
        try:
            img_bytes = get_r2_image_bytes(r2_key)
            img_b64 = base64.b64encode(img_bytes).decode()

            # Add product image
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img_b64}})

            # Add product metadata — dimensions + visual description
            dims_text = ""
            if item.get("width_cm") and item.get("height_cm"):
                dims_text = (f"Dimensions: {item['width_cm']}W × {item.get('height_cm', '?')}H "
                            f"× {item.get('depth_cm', '?')}D cm")
                if item.get("proportion_w_h"):
                    dims_text += f" (width:height ratio = {item['proportion_w_h']}:1)"

            visual_desc = item.get("visual_description", "")

            parts.append({"text": (
                f"↑ {item['slot'].upper()}: "
                f"{visual_desc}\n"
                f"{dims_text}\n"
                f"Color: {item.get('color', 'as shown')} | "
                f"Material: {item.get('primary_material', 'as shown')}\n"
                f"Place against: {item.get('placement', {}).get('wall', 'best position')}\n\n"
            )})
        except Exception as e:
            print(f"Failed to load product image {r2_key}: {e}")
            continue

    # Part 3: Rendering instructions with proportion enforcement
    tier_style = {
        "luxury": "Luxurious high-end interior: marble, brass, velvet, natural stone, herringbone hardwood floors, designer fixtures, museum-quality lighting",
        "premium": "Premium quality interior: quality hardwood, designer fabrics, polished surfaces, statement lighting",
        "standard": "Well-designed modern interior: clean lines, quality materials, warm wood tones, comfortable atmosphere",
        "budget": "Clean functional interior: simple materials, bright and airy, practical layout",
    }

    parts.append({"text": f"""
RENDERING INSTRUCTIONS:

Generate a photorealistic interior design render of this {room['type']}.
Camera angle: perspective view from doorway, eye-level (~160cm height).

CRITICAL PROPORTION RULES:
- The room is {room['estimated_width_cm']}cm × {room['estimated_depth_cm']}cm
- Each product's dimensions are listed above — render them at CORRECT SIZE
  relative to the room and to each other
- A sofa that is 275cm wide should take up roughly {round(275/room['estimated_width_cm']*100)}% of the room width
- Standard door height is 200cm — use this as visual reference
- Furniture must not float, overlap, or clip through walls/other furniture
- Leave minimum 80cm walking paths between furniture pieces

STYLE: {style.title()} — {tier_style.get(tier, tier_style['standard'])}

RENDERING QUALITY:
- Photorealistic, architectural visualization quality (like a professional Vray render)
- Warm natural daylight coming through windows
- Subtle ambient occlusion shadows under furniture
- European apartment style (Bulgarian/Eastern European architecture)
- White or light-colored walls
- {'Premium hardwood floors, textured wallpaper accents, crown molding' if tier in ('luxury', 'premium') else 'Wood or laminate flooring, clean painted walls'}

The furniture in this render must look like the ACTUAL products shown in the reference images above.
Do NOT substitute generic furniture — match the specific designs, colors, and proportions shown.
"""})

    # === SEND TO NANO BANANA ===
    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-image-generation",
        contents=[{"role": "user", "parts": parts}],
        generation_config={"response_modalities": ["IMAGE", "TEXT"]},
    )

    # Extract generated image
    render_bytes = None
    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            render_bytes = part.inline_data.data
            break

    if not render_bytes:
        return {"error": "no_image_generated", "design_id": design_id}

    # Upload render to R2
    render_r2_key = f"renders/{design_id}/render_v1.jpg"
    render_url = upload_image(render_bytes, render_r2_key)

    # Upload sketch to R2
    sketch_r2_key = f"sketches/{design_id}/sketch.jpg"
    upload_image(sketch_image, sketch_r2_key)

    # Save design to Supabase
    supabase.table("designs").insert({
        "id": design_id,
        "sketch_r2_key": sketch_r2_key,
        "room_analysis": json.dumps(room_data),
        "tier": tier,
        "style": style,
        "budget_eur": matched_products["budget_total"],
        "matched_products": json.dumps(matched_products["products"], default=str),
        "budget_spent": matched_products["budget_spent"],
        "budget_remaining": matched_products["budget_remaining"],
        "render_r2_key": render_r2_key,
        "render_prompt": parts[-1]["text"],  # save for debugging
    }).execute()

    return {
        "design_id": design_id,
        "render_url": render_url,
        "sketch_url": get_image_url(sketch_r2_key),
        "products": matched_products["buy_links"],
        "budget_spent": matched_products["budget_spent"],
        "budget_remaining": matched_products["budget_remaining"],
    }


def swap_product_in_design(
    design_id: str,
    slot_to_swap: str,
    new_product: dict,
) -> dict:
    """Swap one product in an existing design → re-render with new product photo from R2."""

    # Load existing design
    design = supabase.table("designs").select("*").eq("id", design_id).single().execute().data

    # Load current render from R2
    current_render = get_r2_image_bytes(design["render_r2_key"])

    # Build swap prompt with new product's ACTUAL image from R2
    parts = [
        {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(current_render).decode()}},
        {"text": f"Above is the current room render.\n\n"},
    ]

    # Add the NEW product's reference image from R2
    if new_product.get("r2_main_image_key"):
        try:
            new_img = get_r2_image_bytes(new_product["r2_main_image_key"])
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(new_img).decode()}})
        except:
            pass

    # Swap instructions with dimension awareness
    parts.append({"text": f"""
Replace the {slot_to_swap} in this room render with the product shown above.

NEW PRODUCT DETAILS:
- {new_product.get('visual_description', new_product.get('name', 'new product'))}
- Dimensions: {new_product.get('width_cm', '?')}W × {new_product.get('height_cm', '?')}H × {new_product.get('depth_cm', '?')}D cm
- Color: {new_product.get('color', 'as shown')}
- Material: {new_product.get('primary_material', 'as shown')}
- Proportion ratio: {new_product.get('proportion_w_h', '?')}:1 (W:H)

RULES:
- Replace ONLY the {slot_to_swap} — keep everything else EXACTLY the same
- Match the new product's appearance from the reference photo above
- Maintain correct proportions relative to the room and other furniture
- Same lighting, angle, and atmosphere
"""})

    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-image-generation",
        contents=[{"role": "user", "parts": parts}],
        generation_config={"response_modalities": ["IMAGE", "TEXT"]},
    )

    render_bytes = None
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            render_bytes = part.inline_data.data
            break

    if not render_bytes:
        return {"error": "swap_render_failed"}

    # Count existing versions
    version = len([k for k in list_r2_keys(f"renders/{design_id}/") if k.endswith(".jpg")]) + 1
    render_r2_key = f"renders/{design_id}/render_v{version}.jpg"
    render_url = upload_image(render_bytes, render_r2_key)

    # Update design in Supabase
    supabase.table("designs").update({
        "render_r2_key": render_r2_key,
    }).eq("id", design_id).execute()

    return {
        "design_id": design_id,
        "render_url": render_url,
        "swapped_slot": slot_to_swap,
        "new_product": {
            "name": new_product["name"],
            "price": new_product["price"],
            "image_url": get_image_url(new_product["r2_main_image_key"]),
        },
    }
```

### Why this approach gives accurate proportions

The proportion accuracy chain:

```
1. Scraper gets product dimensions from website (width_cm, height_cm, depth_cm)
        ↓
2. Vision Enrichment VERIFIES dimensions against the product photo
   - If dimensions exist: confirms they're plausible
   - If dimensions missing: estimates from image using reference objects
   - Calculates proportion_w_h and proportion_w_d ratios
        ↓
3. Room Analyzer measures the room from the sketch
   - Room width/depth in cm
   - Each wall's usable length
        ↓
4. Matcher checks: product.width_cm ≤ wall.free_length_cm
   (only selects furniture that physically fits)
        ↓
5. Nano Banana prompt includes:
   - Room dimensions: "450cm × 380cm"
   - Product dimensions: "sofa is 275cm wide"
   - Proportion ratios: "sofa width:height = 3.1:1"
   - Percentage: "sofa takes up 61% of south wall"
   - Visual description: "low-profile 3-seat sofa with track arms..."
   - ACTUAL product photo: so Nano Banana can see the exact proportions

This means:
- The sofa won't be rendered as tall as the wardrobe
- The coffee table won't be wider than the sofa
- The bed won't clip through the wall
- The nightstands will be visually proportional to the bed
```

---

## STAGE 5: API & Frontend

**Status: Needs to be built**

### Backend API (FastAPI)

```python
# api.py

from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import JSONResponse

app = FastAPI(title="AI Interior Design API")


@app.post("/api/analyze")
async def analyze_sketch(sketch: UploadFile = File(...)):
    """Upload sketch → get room analysis."""
    image_data = await sketch.read()
    room_data = await analyze_room(image_data, sketch.content_type)
    return room_data


@app.post("/api/furnish")
async def furnish_room(
    sketch: UploadFile = File(...),
    room_id: str = Query(default="room_1"),
    budget: float = Query(..., description="Budget in EUR"),
    tier: str = Query(default="standard"),
    style: str = Query(default="modern"),
):
    """Upload sketch + budget → get rendered room with real products."""
    image_data = await sketch.read()

    # Stage 2: Analyze room
    rooms = await analyze_room(image_data, sketch.content_type)
    room = next((r for r in rooms["rooms"] if r["id"] == room_id), rooms["rooms"][0])

    # Stage 3: Match furniture from Supabase
    matched = match_furniture_for_room(room, budget, tier, style)

    # Stage 4: Generate render (auto-includes product photos from R2)
    result = generate_room_design(image_data, room, matched, style)

    return result


@app.post("/api/swap")
async def swap_product(
    design_id: str,
    slot: str = Query(...),
    product_id: str = Query(None),
    max_price: float = Query(None),
):
    """Swap one product → show alternatives or re-render."""
    if not product_id:
        # Show alternatives
        design = supabase.table("designs").select("*").eq("id", design_id).single().execute().data
        alternatives = query_supabase_for_matching(
            categories=[slot],
            max_price=max_price or design["budget_remaining"] + get_current_product_price(design, slot),
            require_usable_image=True,
            limit=5,
        )
        return {"alternatives": [
            {
                "id": a["id"],
                "name": a["name"],
                "price": a["price"],
                "image_url": get_image_url(a["r2_main_image_key"]),
                "visual_description": a.get("visual_description"),
            }
            for a in alternatives
        ]}

    # Re-render with selected product
    product = supabase.table("products").select("*").eq("id", product_id).single().execute().data
    result = swap_product_in_design(design_id, slot, product)
    return result


@app.get("/api/products/search")
async def search_products(
    q: str = None,
    category: str = None,
    room: str = None,
    style: str = None,
    min_price: float = None,
    max_price: float = None,
    source: str = None,
):
    """Search the furniture database."""
    query = supabase.table("products").select("id, name, price, currency, category, "
                                              "room_type, style, r2_main_image_key, "
                                              "width_cm, height_cm, depth_cm, rating, "
                                              "source_domain, product_url, in_stock")

    if q: query = query.or_(f"name.ilike.%{q}%,description.ilike.%{q}%")
    if category: query = query.eq("category", category)
    if room: query = query.ilike("room_type", f"%{room}%")
    if style: query = query.ilike("style", f"%{style}%")
    if min_price: query = query.gte("price", min_price)
    if max_price: query = query.lte("price", max_price)
    if source: query = query.ilike("source_domain", f"%{source}%")

    result = query.limit(20).execute()
    return result.data


@app.get("/api/stats")
async def stats():
    """Database statistics."""
    total = supabase.table("products").select("id", count="exact").execute()
    enriched = supabase.table("products").select("id", count="exact").eq("vision_enriched", True).execute()
    usable = supabase.table("products").select("id", count="exact").eq("image_usable", True).execute()

    return {
        "total_products": total.count,
        "vision_enriched": enriched.count,
        "usable_for_render": usable.count,
        "enrichment_pct": round((enriched.count / max(total.count, 1)) * 100, 1),
    }


@app.get("/api/tiers")
async def get_tiers():
    return BUDGET_TIERS
```

### Frontend Screens

**Screen 1: Upload**
- Drag & drop sketch / take photo with phone camera
- Camera integration for mobile (most users will photograph hand-drawn sketches)

**Screen 2: Configure**
- Room detected: "Хол / Living Room — ~17 m²"
- User can adjust detected dimensions if AI got them wrong
- Style picker: Modern | Scandinavian | Industrial | Classic | Minimalist
- Budget tier selector with previews:
  - Бюджетен (€500-1000) — clean, functional
  - Стандартен (€1000-2500) — well-designed, comfortable
  - Премиум (€2500-5000) — high-quality, designer
  - Луксозен (€5000+) — luxury, premium materials
- Custom budget slider / input field
- "Генерирай дизайн / Generate Design" button

**Screen 3: Result**
- Full-width photorealistic render (served from R2)
- Side panel: each product as a card
  - Product image (from R2)
  - Name (in Bulgarian)
  - Price in EUR
  - Source store logo
  - Dimensions
  - "Купи / Buy" button → links to product page
  - "Замени / Swap" button → shows alternatives
- Bottom bar: "Общо: €1,847 от €2,000 бюджет"
- "Ново поколение / Re-generate" for a variation
- "Изтегли / Download" for the render

**Screen 4: Swap**
- Click "Swap" on any product
- Modal shows 3-5 alternatives from DB (same category, fits space, within budget)
- Each alternative shows: image, name, price, visual description
- Select one → auto re-renders with new product photo → updates price total

---

## Implementation Order

### Phase 1: Foundation (Week 1-2)
1. ✅ Set up Firecrawl scraper (done — your .tar file)
2. Set up Supabase project — create tables from schema above
3. Set up Cloudflare R2 bucket — configure public access
4. Modify scraper to write to Supabase instead of SQLite
5. Modify scraper to upload images to R2 instead of local filesystem
6. Deploy scraper on VPS, run initial scrapes — 500-1000 products
7. Verify data in Supabase dashboard: prices, categories, images in R2

### Phase 2: Vision Enrichment (Week 3-4)
8. Get Gemini API key from Google AI Studio
9. Build `vision_enrichment.py`
10. Run enrichment on all scraped products
11. Verify: dimensions verified, visual descriptions generated, proportion ratios calculated
12. Check `image_usable` flags — how many products have render-quality images?
13. If <50% usable, scrape more sites or download better product photos
14. Add enrichment to scheduler — auto-runs after every scrape batch

### Phase 3: Room Analyzer (Week 5)
15. Build `room_analyzer.py`
16. Test with 20+ sketch photos (hand-drawn, digital, blurry, rotated)
17. Fine-tune prompt for accurate dimension extraction
18. Test that max wall dimensions correctly constrain furniture matching

### Phase 4: Furniture Matcher (Week 6-7)
19. Build `furniture_matcher.py` with budget allocation logic
20. Build Supabase query functions
21. Test budget scenarios:
    - €500 студентска спалня (student bedroom)
    - €2000 standard living room
    - €5000 premium open-plan living+dining
    - €15000 luxury апартамент (whole apartment)
22. Verify: products fit room, budget is respected, images are usable

### Phase 5: Design Generator (Week 8-9)
23. Build `design_generator.py` with auto product photo inclusion
24. Test renders: do products visually match their reference photos?
25. Test proportions: is the sofa the right size relative to the room?
26. Iterate on prompts for best visual quality
27. Build swap functionality
28. Test luxury vs budget renders — visual quality should match tier

### Phase 6: API & Frontend (Week 10-12)
29. Build FastAPI backend
30. Build React/Next.js frontend
31. User flow: upload → configure → generate → view → swap → buy
32. Mobile responsive
33. Deploy to Cloudflare Pages (frontend) + VPS (backend)

### Phase 7: Polish & Launch (Week 13-14)
34. Add more furniture sites to scraper
35. User accounts — save designs (Supabase Auth)
36. Share designs (public link to view)
37. Analytics — which products get placed most often
38. SEO: "AI интериорен дизайн България", "дизайн на стая онлайн"

---

## Tech Stack Summary

| Component | Technology | Cost |
|-----------|-----------|------|
| Furniture scraping | Firecrawl API | €16-83/month |
| Product database | **Supabase** (Postgres) | Free tier (500MB) → Pro €25/month |
| Product images | **Cloudflare R2** | Free (10GB) → ~€0.015/GB/month |
| Generated renders | **Cloudflare R2** | Same bucket |
| Vision enrichment | Gemini 2.5 Flash | Free tier (1500 req/day) |
| Room analysis | Gemini 2.5 Flash | Same API key |
| Design rendering | Gemini Image model (Nano Banana) | Free tier / pay per generation |
| Backend | FastAPI (Python) on VPS | VPS cost |
| Frontend | Next.js on Cloudflare Pages | Free |
| VPS | Ubuntu (Hetzner/DigitalOcean) | €5-20/month |
| Domain + SSL | Your domain | €10-15/year |

**Total estimated cost: €25-130/month** to run the full platform.

---

## Key Technical Risks

| Risk | Mitigation |
|------|-----------|
| Nano Banana renders products that don't match reference photos | Improve visual descriptions, use multiple angles, test prompt variations |
| Products rendered at wrong proportions | Vision enrichment calculates proportion ratios, prompt includes exact dimensions + percentages of room width |
| Not enough products in DB with verified dimensions | Vision enrichment estimates dimensions from photos, priority-enrich products without dimensions |
| Budget algorithm picks bad style combinations | Luxury score from vision enrichment helps — budget tier furniture looks budget, luxury looks luxury |
| Bulgarian sites block scraping | Firecrawl handles anti-bot; hosted version has proxy rotation |
| Sketch analysis gives wrong room sizes | Frontend lets user manually adjust detected dimensions before generating |
| Generated image looks AI-fake | Prompt specifies "architectural visualization quality", test extensively |
| R2 costs spike from too many images | 10GB free tier = ~20,000 product images. Only keep best image per product |
| Supabase free tier limit | 500MB fits ~50,000 products easily. Upgrade to Pro (€25/mo) if needed |
| Gemini rate limits | Free tier = 1500 req/day for Flash. Batch enrichment overnight. Upgrade if needed |
