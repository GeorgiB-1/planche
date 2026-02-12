-- Planche.bg Database Schema
-- Run this in Supabase SQL Editor to initialize the database

-- products table — one row per scraped furniture product
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Identity
    name TEXT NOT NULL,
    brand TEXT,
    sku TEXT,
    model TEXT,

    -- Pricing (EUR)
    price DECIMAL(10,2),
    original_price DECIMAL(10,2),
    currency TEXT DEFAULT 'EUR',
    on_sale BOOLEAN DEFAULT FALSE,

    -- Classification
    category TEXT,
    subcategory TEXT,
    room_type TEXT,
    style TEXT,

    -- Dimensions (cm/kg)
    width_cm DECIMAL(8,2),
    height_cm DECIMAL(8,2),
    depth_cm DECIMAL(8,2),
    weight_kg DECIMAL(8,2),
    seat_height_cm DECIMAL(8,2),
    diameter_cm DECIMAL(8,2),

    -- AI Vision Enrichment
    dimensions_source TEXT,
    dimensions_confidence TEXT,
    proportion_w_h DECIMAL(6,3),
    proportion_w_d DECIMAL(6,3),
    visual_description TEXT,
    color_hex TEXT,
    color_tone TEXT,
    luxury_score DECIMAL(3,2),
    ai_category TEXT,
    ai_subcategory TEXT,
    suitable_rooms JSONB,
    image_type TEXT,
    image_usable BOOLEAN DEFAULT FALSE,
    vision_data JSONB,
    vision_enriched BOOLEAN DEFAULT FALSE,
    vision_enriched_at TIMESTAMPTZ,

    -- Materials & Appearance
    materials JSONB,
    primary_material TEXT,
    color TEXT,
    available_colors JSONB,
    finish TEXT,
    upholstery TEXT,

    -- Images — Cloudflare R2
    image_urls JSONB,
    main_image_url TEXT,
    r2_image_keys JSONB,
    r2_main_image_key TEXT,
    r2_image_count INTEGER DEFAULT 0,

    -- Details
    description TEXT,
    features JSONB,
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
    in_stock BOOLEAN DEFAULT TRUE,
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
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_room ON products(room_type);
CREATE INDEX IF NOT EXISTS idx_products_style ON products(style);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
CREATE INDEX IF NOT EXISTS idx_products_source ON products(source_domain);
CREATE INDEX IF NOT EXISTS idx_products_stock ON products(in_stock);
CREATE INDEX IF NOT EXISTS idx_products_enriched ON products(vision_enriched);
CREATE INDEX IF NOT EXISTS idx_products_usable ON products(image_usable);
CREATE INDEX IF NOT EXISTS idx_products_luxury ON products(luxury_score);
CREATE INDEX IF NOT EXISTS idx_products_dims ON products(width_cm, depth_cm);

-- Primary matching query — partial composite index
CREATE INDEX IF NOT EXISTS idx_products_match
    ON products(category, style, room_type, price)
    WHERE in_stock = TRUE;


-- price_history — tracks price changes over time
CREATE TABLE IF NOT EXISTS price_history (
    id BIGSERIAL PRIMARY KEY,
    product_id TEXT REFERENCES products(id),
    old_price DECIMAL(10,2),
    new_price DECIMAL(10,2),
    currency TEXT DEFAULT 'EUR',
    changed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_price_history_product
    ON price_history(product_id, changed_at DESC);


-- scrape_jobs — tracks each scrape run
CREATE TABLE IF NOT EXISTS scrape_jobs (
    id TEXT PRIMARY KEY,
    url TEXT,
    status TEXT DEFAULT 'running',
    products_found INTEGER DEFAULT 0,
    pages_scraped INTEGER DEFAULT 0,
    errors TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    duration_seconds DECIMAL(10,2)
);


-- designs — stores generated room designs
CREATE TABLE IF NOT EXISTS designs (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Input
    sketch_r2_key TEXT,
    room_analysis JSONB,
    tier TEXT,
    style TEXT,
    budget_eur DECIMAL(10,2),

    -- Matched products
    matched_products JSONB,
    budget_spent DECIMAL(10,2),
    budget_remaining DECIMAL(10,2),

    -- Output
    render_r2_key TEXT,
    render_prompt TEXT,

    -- User
    user_id TEXT,
    is_public BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_designs_user
    ON designs(user_id, created_at DESC);
