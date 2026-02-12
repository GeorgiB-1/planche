# Feature Specification: Planche.bg — AI Interior Design MVP

**Feature Branch**: `main`
**Created**: 2026-02-12
**Status**: Draft
**Input**: AI Interior Design Full Implementation Plan + user request for MVP focus

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Furniture Database Crawler (Priority: P1)

As a platform operator, I need an automated system that crawls Bulgarian and European furniture websites, extracts structured product data (name, price, dimensions, images, materials, colors), stores it in Supabase with images in Cloudflare R2, and enriches each product with AI-verified dimensions and visual descriptions — so the platform has real, purchasable products to recommend.

**Why this priority**: Without a populated product database, no design generation is possible. This is the foundational data layer everything depends on.

**Independent Test**: Can be fully tested by running the crawler against videnov.bg, verifying products appear in Supabase with images in R2, and confirming vision enrichment adds dimensions/descriptions. Delivers value as a standalone product database.

**Acceptance Scenarios**:

1. **Given** a configured target URL (e.g., `videnov.bg/mebeli/divani`), **When** the scraper runs, **Then** products are extracted with name (Bulgarian OK), price (EUR), dimensions (cm), image URLs, and stored in Supabase with a stable product ID.
2. **Given** scraped products with images in R2, **When** vision enrichment runs, **Then** each product gets: verified/estimated dimensions, proportion ratios, visual description (English, optimized for image generation), style classification, material analysis, and `image_usable` flag.
3. **Given** a product that was previously scraped, **When** re-scraped with a different price, **Then** the price change is recorded in `price_history` and the product is updated.
4. **Given** product names in Bulgarian (e.g., "Диван ъглов Марио"), **When** stored, **Then** the original Bulgarian name is preserved, but category/style/room_type fields are in English for querying.

---

### User Story 2 - Sketch-to-Render Pipeline (Priority: P1)

As a user, I want to upload a photo of my hand-drawn room sketch, select a budget and style, and receive a photorealistic render of that room filled with real, purchasable furniture from Bulgarian stores — so I can visualize my space and buy the exact furniture shown.

**Why this priority**: This is the core value proposition. Combined with US1, it delivers the complete MVP experience.

**Independent Test**: Can be tested by uploading a sketch, receiving a render with real products from the database, and verifying product cards with "buy" links.

**Acceptance Scenarios**:

1. **Given** an uploaded sketch image, **When** the room analyzer runs, **Then** it returns structured JSON with: room type, estimated dimensions (cm), windows, doors, usable wall lengths, and furniture zones. Bulgarian labels (хол, спалня) are detected and translated.
2. **Given** room analysis + budget (EUR) + tier (бюджетен/стандартен/премиум/луксозен) + style, **When** the furniture matcher runs, **Then** it returns a list of real products from Supabase that: fit the room dimensions, match the style, stay within budget, are in stock, and have usable images with proportion data.
3. **Given** matched products with R2 image references, **When** the design generator runs, **Then** it produces a photorealistic render where furniture visually matches the product reference photos and is proportionally correct relative to the room.
4. **Given** a generated design, **When** the user views the result, **Then** they see the render + product cards showing: product image, name (Bulgarian), price (EUR), source store, dimensions, "Купи" (Buy) link, and "Замени" (Swap) option.

---

### User Story 3 - Product Swap & Re-render (Priority: P2)

As a user viewing a generated design, I want to swap any individual furniture piece for an alternative from the database and see the room re-rendered with the new product — so I can customize the design to my taste.

**Why this priority**: Enhances user engagement and satisfaction, but the core MVP works without it.

**Independent Test**: Can be tested by selecting "Swap" on a product in a completed design, choosing an alternative, and verifying the re-rendered image shows the new product.

**Acceptance Scenarios**:

1. **Given** a completed design with matched products, **When** the user clicks "Замени" (Swap) on a product, **Then** they see 3-5 alternative products from the same category that fit the space and budget.
2. **Given** a selected alternative product, **When** re-render is triggered, **Then** only the swapped product changes in the render — everything else stays identical.
3. **Given** a swap, **When** the new product has a different price, **Then** the budget summary updates to reflect the new total.

---

### User Story 4 - Product Search & Browse (Priority: P3)

As a user, I want to search and browse the furniture database independently — filtering by category, room type, style, price range, and source store.

**Why this priority**: Nice-to-have for discovery. The main flow auto-selects products.

**Independent Test**: Can be tested by querying the `/api/products/search` endpoint with various filters.

**Acceptance Scenarios**:

1. **Given** the search endpoint, **When** querying with `category=sofa&style=modern&max_price=800`, **Then** matching in-stock products are returned with images, prices, and links.

---

### Edge Cases

- What happens when a sketch is too blurry or rotated for the room analyzer to interpret?
- How does the system handle rooms where no products in the DB fit the dimensions + budget?
- What happens when a product goes out of stock between matching and the user clicking "Buy"?
- How does the system handle price currency conversion (BGN → EUR)?
- What happens when vision enrichment fails for a product image (blurry, lifestyle shot)?
- How does the system handle multi-room sketches where the user only has budget for one room?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST scrape furniture product data from configured Bulgarian/European websites using Firecrawl
- **FR-002**: System MUST store product data in Supabase (Postgres) with images in Cloudflare R2
- **FR-003**: System MUST enrich each product with AI vision analysis (Gemini 2.5 Flash): verified dimensions, proportion ratios, visual description, style classification, material analysis, image quality assessment
- **FR-004**: System MUST preserve Bulgarian product names but use English for category/style/room_type fields
- **FR-005**: System MUST analyze uploaded sketch images using Gemini 2.5 Flash Vision to extract room layout, dimensions, and features
- **FR-006**: System MUST match real products from the database that fit the room, style, and budget constraints
- **FR-007**: System MUST generate photorealistic room renders using Gemini Image Generation (Nano Banana) with actual product reference photos from R2
- **FR-008**: System MUST present results with product cards showing name, price, image, source, and "Buy" link
- **FR-009**: System MUST support 4 budget tiers: бюджетен (budget), стандартен (standard), премиум (premium), луксозен (luxury)
- **FR-010**: System MUST track price changes over time in `price_history` table
- **FR-011**: System MUST distribute budget across furniture pieces using room-type-specific allocation percentages

### Key Entities

- **Product**: A furniture item scraped from a store — name, price, dimensions, images, materials, style, room type, vision enrichment data, R2 image keys, source URL
- **Design**: A generated room design — input sketch, room analysis, matched products, generated render, budget breakdown
- **ScrapeJob**: A record of each scraping run — URL, status, products found, errors
- **PriceHistory**: Price change events — product reference, old/new price, timestamp

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Database contains 500+ products from at least 3 Bulgarian furniture stores within first week of crawler operation
- **SC-002**: 80%+ of scraped products pass vision enrichment with `image_usable = true`
- **SC-003**: Room analyzer correctly identifies room type and estimates dimensions within 20% accuracy for 80%+ of clear sketches
- **SC-004**: Furniture matcher returns valid product sets (fits space, within budget) for 90%+ of requests
- **SC-005**: End-to-end sketch-to-render flow completes in under 60 seconds
- **SC-006**: Generated renders show furniture that visually resembles the reference product photos
- **SC-007**: All product "Buy" links resolve to valid product pages on source stores
