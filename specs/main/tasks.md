# Tasks: Planche.bg — AI Interior Design MVP

**Input**: Design documents from `/specs/main/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.yaml, quickstart.md

**Tests**: Not included (spec does not request TDD — manual testing for MVP per plan.md)

**Organization**: Tasks grouped by user story. US1 (Furniture Database Crawler) and US2 (Sketch-to-Render Pipeline) are both P1. US1 must complete first because US2 depends on having products in the database.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/`
- Backend: Python 3.11+ / FastAPI
- Frontend: TypeScript / Next.js / React

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, directory structure, dependencies, environment configuration

- [x] T001 Create backend project structure: `backend/src/models/`, `backend/src/services/`, `backend/src/api/`, `backend/src/storage/`, `backend/requirements.txt`, `backend/.env.example`
- [x] T002 Create `backend/requirements.txt` with all dependencies: fastapi, uvicorn, python-multipart, google-genai, firecrawl-py, supabase, boto3, pydantic, python-dotenv, httpx, Pillow
- [x] T003 [P] Create frontend project with Next.js: `npx create-next-app@latest frontend --typescript --tailwind` with `frontend/src/components/`, `frontend/src/pages/`, `frontend/src/services/`, `frontend/src/i18n/`
- [x] T004 [P] Create `backend/.env.example` with all required environment variables (SUPABASE_URL, SUPABASE_SERVICE_KEY, CF_ACCOUNT_ID, R2_ACCESS_KEY, R2_SECRET_KEY, R2_BUCKET, R2_PUBLIC_URL, GEMINI_API_KEY, FIRECRAWL_API_KEY) per quickstart.md
- [x] T005 [P] Create `.gitignore` at repo root with entries for: `*.pyc`, `__pycache__/`, `.env`, `venv/`, `node_modules/`, `.next/`, `.env.local`

**Checkpoint**: Project skeleton ready — both backend and frontend initialized

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core storage clients and configuration that ALL user stories depend on

**WARNING**: No user story work can begin until this phase is complete

- [x] T006 Create Supabase schema SQL file at `backend/src/storage/schema.sql` with CREATE TABLE statements for products, price_history, scrape_jobs, designs and all CREATE INDEX statements from data-model.md
- [x] T007 Implement configuration module at `backend/src/config.py` — load env vars via python-dotenv, define BUDGET_TIERS dict (budget/standard/premium/luxury with Bulgarian+English labels, per_sqm_eur ranges, preferred_sources), BG_TO_EN_CATEGORY mapping dict (Дивани→sofa, Маси→table, Столове→chair, etc. per data-model.md), ROOM_BUDGET_ALLOCATION dict, ROOM_FURNITURE_REQUIREMENTS dict, TARGET_SITES list with URLs and priority
- [x] T008 Implement Supabase client at `backend/src/storage/supabase_client.py` — initialize supabase.create_client from env vars, implement save_product() with stable ID generation (SHA256(domain:sku:name)[:16]), upsert with price change detection and price_history insert, save_scrape_job(), update_scrape_job(), save_design(), get_product_by_id(), query helper methods
- [x] T009 [P] Implement R2 client at `backend/src/storage/r2_client.py` — initialize boto3 S3 client with R2 endpoint URL, implement upload_image() with ContentType header, get_image_url() returning public URL, get_r2_image_bytes() for downloading, delete_image(), upload_product_images() that downloads from source URLs, converts to WebP via Pillow, uploads to R2 with key pattern `products/{domain}/{product_id}/{NNN}.webp`, returns list of R2 keys
- [x] T010 [P] Create Pydantic models at `backend/src/models/product.py` — ProductBase (all product fields from data-model.md), ProductCreate (for scraper input), ProductDB (with id, timestamps), ProductSummary (for API list responses with subset of fields), VisionEnrichment (dimensions_verification, proportion_ratios, visual_description, material_analysis, color_analysis, style_classification, category_verification, image_quality)
- [x] T011 [P] Create Pydantic models at `backend/src/models/room.py` — RoomFeatures (windows, doors), UsableWall (wall, free_length_cm, suitable_for), FurnitureZone, Room (id, type, dimensions, features, usable_walls, zones), RoomAnalysis (rooms list, overall stats)
- [x] T012 [P] Create Pydantic models at `backend/src/models/design.py` — MatchedProduct (slot, product_id, placement), DesignCreate, DesignResult (design_id, render_url, sketch_url, products as BuyLink list, budget_spent, budget_remaining), BuyLink (name, price, currency, url, source, image_url), SwapAlternative, SwapResult, BudgetTier

**Checkpoint**: Foundation ready — storage clients work, models defined, config loaded. User story implementation can begin.

---

## Phase 3: User Story 1 — Furniture Database Crawler (Priority: P1) MVP

**Goal**: Automated system that crawls Bulgarian furniture websites, extracts product data, stores in Supabase with images in R2, and enriches with AI vision analysis. Database populated with 500+ products.

**Independent Test**: Run scraper against videnov.bg → verify products in Supabase with images in R2 → run vision enrichment → verify visual_description, proportions, image_usable flags populated.

### Implementation for User Story 1

- [x] T013 [US1] Implement scraper service at `backend/src/services/scraper.py` — use Firecrawl /map endpoint to discover product URLs for a given site, then /scrape each product page individually. Extract Markdown content from Firecrawl response. Send Markdown to Gemini Flash with extraction prompt (from AI_Interior_Design_Full_Implementation_Plan.md config.py) to get structured JSON with 40+ fields. Map Bulgarian categories to English using BG_TO_EN_CATEGORY from config.py. Convert BGN prices to EUR (divide by 1.9558). Call r2_client.upload_product_images() to download+convert+upload images. Call supabase_client.save_product() to upsert. Track scrape job via save_scrape_job(). Implement per-domain rate limiting (2-3 concurrent, 1-2s delay). Support CLI: `python -m src.services.scraper "URL"` for single URL, `--all` for all TARGET_SITES.
- [x] T014 [US1] Implement site-specific scraping configs in `backend/src/config.py` — add TARGET_SITES list with per-site configuration: videnov.bg (wait_for=2000, priority=HIGH), aiko-bg.com (wait_for=1000, priority=HIGH), ikea.bg (wait_for=3000, priority=HIGH, use_proxy=True), jysk.bg (wait_for=3000, priority=MEDIUM), emag.bg (wait_for=5000, priority=LOW). Include Firecrawl options per site (--only-main-content, --wait-for values). Include the Gemini extraction prompt as PRODUCT_EXTRACTION_PROMPT constant.
- [x] T015 [US1] Implement vision enrichment service at `backend/src/services/vision.py` — initialize google-genai client. For each unenriched product (vision_enriched=False, has main_image_url): fetch image bytes from R2 via r2_client.get_r2_image_bytes(), resize to 512px max side via Pillow, send to Gemini Flash with PRODUCT_VISION_PROMPT (from the implementation plan — verify/estimate dimensions, calculate proportion ratios, generate visual description, analyze materials/colors, classify style with luxury_score, verify category, assess image quality). Parse JSON response into VisionEnrichment model. Update product in Supabase with enriched fields (visual_description, proportion_w_h, proportion_w_d, dimensions_source, color_hex, color_tone, luxury_score, ai_category, suitable_rooms, image_type, image_usable, vision_data, vision_enriched=True). Support CLI: `python -m src.services.vision --all` or `--product-id X`. Rate limit: 1 request/second (Gemini free tier). Implement enrich_all_unenriched() that queries for unenriched products and processes them in batch.
- [x] T016 [US1] Implement scheduler at `backend/src/services/scheduler.py` — daily re-scrape of all TARGET_SITES (configurable via SCRAPE_INTERVAL_HOURS env var, default 24). After each scrape batch, run enrich_all_unenriched(). Use asyncio.sleep for scheduling (no external dependencies). Log scrape stats (products found, enriched, errors). Support CLI: `python -m src.services.scheduler` for daemon mode.
- [x] T017 [US1] Implement product search API routes at `backend/src/api/routes_product.py` — GET /api/products/search (params: q, category, room, style, min_price, max_price, source, limit per api.yaml), GET /api/stats (total_products, vision_enriched, usable_for_render, enrichment_pct), GET /api/tiers (return BUDGET_TIERS from config). Wire to supabase_client queries with proper filtering. Return ProductSummary models with R2 image URLs.
- [x] T018 [US1] Create FastAPI app entry point at `backend/src/api/main.py` — create FastAPI app with title "Planche.bg API", add CORS middleware (allow all origins for MVP), include routes_product and routes_design routers, add root endpoint returning API info. Load .env via python-dotenv on startup.

**Checkpoint**: Scraper can populate 500+ products from videnov.bg + aiko-bg.com. Vision enrichment adds dimensions/descriptions. /api/stats shows database health. /api/products/search returns filtered results.

---

## Phase 4: User Story 2 — Sketch-to-Render Pipeline (Priority: P1)

**Goal**: User uploads sketch photo → room analysis → furniture matching → photorealistic render with real products from DB → product cards with buy links.

**Independent Test**: Upload a sketch image to POST /api/furnish with budget=2000, tier=standard, style=modern → receive render_url + products list with buy links. Verify render shows furniture, product cards have valid links.

**Depends on**: US1 (needs populated product database with vision-enriched products)

### Implementation for User Story 2

- [x] T019 [US2] Implement room analyzer at `backend/src/services/room_analyzer.py` — initialize google-genai client. Take sketch image bytes + optional mime_type. Send to Gemini Flash with ROOM_ANALYSIS_PROMPT (from implementation plan: extract room type, dimensions in cm, windows, doors, usable walls with max furniture width, furniture zones). Parse response into RoomAnalysis model. Handle Bulgarian labels (хол→living room, спалня→bedroom, кухня→kitchen, баня→bathroom). Return structured JSON matching RoomAnalysis schema. Include error handling for unreadable/blurry sketches.
- [x] T020 [US2] Implement furniture matcher at `backend/src/services/matcher.py` — implement match_furniture_for_room(room, budget_eur, tier, style) per implementation plan. Step 1: fill required furniture slots from ROOM_FURNITURE_REQUIREMENTS (sofa+coffee_table for living room, bed+wardrobe for bedroom, etc.). Step 2: fill optional slots with remaining budget. For each slot: query supabase for matching products (category IN categories, in_stock=True, image_usable=True, price <= slot_budget, width_cm <= max_dimension from room). Implement rank_candidates() scoring: price proximity (+30), R2 image (+25), verified dimensions (+20), visual description (+15), proportion ratios (+15), luxury_score tier match (+15), rating (+10). Implement get_max_dimension_for_slot() using room usable_walls or fallback proportional limits. Implement budget allocation from ROOM_BUDGET_ALLOCATION. Return MatchResult with products list, product_images_for_render (with R2 keys, visual_description, dimensions, proportions), buy_links, budget breakdown.
- [x] T021 [US2] Implement design generator at `backend/src/services/generator.py` — implement generate_room_design(sketch_image, room_data, matched_products, style). Build multimodal prompt: Part 1 = sketch image as inline_data. Part 2 = "Below are the REAL furniture products..." intro text. Part 3 = for each matched product: fetch image from R2 via r2_client.get_r2_image_bytes(), resize to 512px via Pillow, add as inline_data + text with slot name, visual_description, dimensions, proportion ratios, color, material, wall placement. Part 4 = rendering instructions (room dimensions, proportion rules, style/tier description, quality requirements per implementation plan). Send to Gemini image generation model (verify current model ID — see research.md warning). Extract generated image from response.candidates[0].content.parts. Upload render to R2 at renders/{design_id}/render_v1.jpg. Upload sketch to R2 at sketches/{design_id}/sketch.{ext}. Save design to Supabase via supabase_client.save_design(). Return DesignResult with render_url, products, budget summary.
- [x] T022 [US2] Implement design API routes at `backend/src/api/routes_design.py` — POST /api/analyze (upload sketch → return RoomAnalysis JSON). POST /api/furnish (upload sketch + budget + tier + style → call room_analyzer.analyze_room() → matcher.match_furniture_for_room() → generator.generate_room_design() → return DesignResult with render_url + products + budget). Both endpoints accept multipart/form-data per api.yaml contract. Include error handling: 400 for invalid image, 422 for no matching products, 500 for Gemini API errors. Add request size limit for sketch uploads (10MB max).
- [x] T023 [US2] Create Bulgarian translations file at `frontend/src/i18n/bg.ts` — export object with all UI strings from research.md Bulgarian terms table: uploadSketch="Качи скица", budget="Бюджет", style="Стил", generateDesign="Генерирай дизайн", buy="Купи", swap="Замени", room types (хол, спалня, кухня, баня, офис, детска стая, трапезария), tier labels (бюджетен, стандартен, премиум, луксозен), total="Общо", remaining="Остатък", inStock="Наличен", outOfStock="Изчерпан", delivery="Доставка", dimensions="Размери", materials="Материали", style labels (модерен, скандинавски, индустриален, класически, минималистичен)
- [x] T024 [US2] Create API client at `frontend/src/services/api.ts` — export functions: analyzeSketch(file: File) → POST /api/analyze as FormData, furnishRoom(file: File, budget: number, tier: string, style: string, roomId?: string) → POST /api/furnish as FormData, searchProducts(params) → GET /api/products/search, getStats() → GET /api/stats, getTiers() → GET /api/tiers, getAlternatives(designId, slot) → POST /api/swap without product_id, swapProduct(designId, slot, productId) → POST /api/swap with product_id. Base URL from NEXT_PUBLIC_API_URL env var. All functions typed with response interfaces matching api.yaml schemas.
- [x] T025 [P] [US2] Create SketchUpload component at `frontend/src/components/SketchUpload.tsx` — drag-and-drop zone + file input button + mobile camera capture (accept="image/*" capture="environment"). Show image preview after selection. Validate file type (JPEG, PNG, WebP) and size (<10MB). Display "Качи скица" label. Emit onFileSelected(file: File) callback.
- [x] T026 [P] [US2] Create ConfigPanel component at `frontend/src/components/ConfigPanel.tsx` — room type dropdown (auto-detected, with manual override) using Bulgarian labels from bg.ts. Style picker with options: модерен, скандинавски, индустриален, класически, минималистичен. Budget tier selector with 4 cards showing Bulgarian labels + EUR range + description. Custom budget input (€100-€50,000 slider + number field). "Генерирай дизайн" submit button. Emit onSubmit({budget, tier, style, roomId}).
- [x] T027 [P] [US2] Create ProductCard component at `frontend/src/components/ProductCard.tsx` — product image from R2 (using NEXT_PUBLIC_R2_URL + r2_main_image_key). Name (Bulgarian). Price in EUR with € symbol. Source store name/logo. Dimensions (Ш×В×Д cm). "Купи" button as external link to product_url. "Замени" button emitting onSwap(slot). Compact card layout for sidebar.
- [x] T028 [P] [US2] Create BudgetBar component at `frontend/src/components/BudgetBar.tsx` — horizontal progress bar showing budget_spent / budget_total. "Общо: €X от €Y бюджет" text. Color: green when under budget, yellow 80-100%, red over budget. Show budget_remaining.
- [x] T029 [US2] Create RenderView component at `frontend/src/components/RenderView.tsx` — full-width photorealistic render image from render_url. Loading state with spinner while generating (~30-60s). Error state if generation fails. Download button ("Изтегли"). Zoom/lightbox on click.
- [x] T030 [US2] Create ProductList component at `frontend/src/components/ProductList.tsx` — sidebar panel listing all matched products as ProductCard components. Scrollable if many products. Header: "Мебели в дизайна" (Furniture in design). Total product count.
- [x] T031 [US2] Create upload/landing page at `frontend/src/pages/index.tsx` — hero section with app name "Planche.bg" and tagline "AI Интериорен Дизайн" (AI Interior Design). SketchUpload component. After file selected: show ConfigPanel. On submit: call api.furnishRoom() → navigate to /design/[id] with response data. Loading overlay during generation. Error handling with Bulgarian error messages.
- [x] T032 [US2] Create design result page at `frontend/src/pages/design/[id].tsx` — two-column layout: left = RenderView (main render), right = ProductList (matched products sidebar). Below render: BudgetBar. Mobile: stack vertically (render on top, products below). Load design data from page props or API call. "Ново поколение" (Re-generate) button to call furnish again with same params.
- [x] T033 [US2] Create global styles at `frontend/src/styles/globals.css` — responsive layout (mobile-first). Bulgarian-friendly typography (support Cyrillic). Color palette matching interior design aesthetics (warm neutrals). Card styles for ProductCard. Loading spinner animation.

**Checkpoint**: Full end-to-end flow works: upload sketch → configure budget/style → wait for generation → view render + product cards → click "Купи" opens store page. Verify on mobile (sketch photo capture).

---

## Phase 5: User Story 3 — Product Swap & Re-render (Priority: P2)

**Goal**: User can swap any furniture piece in a generated design for an alternative and see the room re-rendered.

**Independent Test**: Given a completed design, click "Замени" on a product → see alternatives → select one → verify re-rendered image updates and budget recalculates.

**Depends on**: US2 (needs completed designs to swap products in)

### Implementation for User Story 3

- [x] T034 [US3] Add swap_product_in_design() to `backend/src/services/generator.py` — load existing design from Supabase. Fetch current render from R2. Build swap prompt: Part 1 = current render as reference image. Part 2 = new product's image from R2. Part 3 = swap instructions (replace ONLY the specified slot, keep everything else identical, match new product's appearance/dimensions/proportions from reference photo). Send to Gemini image generation. Upload new render to R2 as render_v{N}.jpg. Update design in Supabase with new render_r2_key. Return SwapResult.
- [x] T035 [US3] Add swap route logic to `backend/src/api/routes_design.py` — POST /api/swap endpoint: if product_id is None, query Supabase for alternatives (same category, fits space, within remaining budget + current product price, image_usable=True, limit 5) and return SwapAlternatives. If product_id provided, call generator.swap_product_in_design() and return SwapResult with new render_url and updated budget.
- [x] T036 [US3] Create SwapModal component at `frontend/src/components/SwapModal.tsx` — overlay modal showing 3-5 alternative products for the selected slot. Each alternative: product image, name (BG), price (EUR), visual_description excerpt. "Избери" (Select) button per alternative. "Затвори" (Close) button. On select: call api.swapProduct() → close modal → update render + budget on design page.
- [x] T037 [US3] Wire swap flow in `frontend/src/pages/design/[id].tsx` — when ProductCard emits onSwap(slot): call api.getAlternatives(designId, slot) → open SwapModal with alternatives. On SwapModal select: show loading state → call api.swapProduct() → update render_url in RenderView → update product in ProductList → update BudgetBar with new totals.

**Checkpoint**: Swap flow works end-to-end. User can swap any product, see alternatives, select one, and the render updates.

---

## Phase 6: User Story 4 — Product Search & Browse (Priority: P3)

**Goal**: Standalone product search/browse page with filters for category, room, style, price, source.

**Independent Test**: Navigate to /browse → filter by category=sofa, style=modern, max_price=800 → see matching products with images and buy links.

### Implementation for User Story 4

- [x] T038 [P] [US4] Create browse page at `frontend/src/pages/browse.tsx` — search input for text query (supports Bulgarian). Filter sidebar: category dropdown (sofa, table, chair, bed, etc. with Bulgarian labels), room type dropdown, style dropdown, price range slider (min/max EUR), source store checkboxes. Product grid showing ProductCard components. Pagination or infinite scroll (limit=20 per page). Empty state: "Няма намерени продукти" (No products found). Call api.searchProducts() on filter change. Show total count header.

**Checkpoint**: Users can independently browse and search the furniture database.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements across all user stories before deployment

- [x] T039 Add error handling middleware to `backend/src/api/main.py` — catch Gemini API errors, Supabase connection errors, R2 upload failures. Return structured JSON error responses with user-friendly Bulgarian messages. Log errors with context (product_id, design_id, etc.).
- [x] T040 [P] Add request validation to all API routes — validate file uploads (size <10MB, type in JPEG/PNG/WebP), validate budget range (100-50000), validate tier enum, validate style enum. Return 400 with clear error messages.
- [x] T041 [P] Create Dockerfile at `backend/Dockerfile` — Python 3.11 slim base, copy requirements.txt and install, copy src/, expose port 8000, CMD uvicorn src.api.main:app --host 0.0.0.0 --port 8000.
- [ ] T042 Run quickstart.md validation — follow the quickstart.md steps end-to-end on a clean environment. Verify: backend starts, scraper runs, vision enrichment works, API responds, frontend loads, full flow completes. Fix any issues found.
- [ ] T043 Deploy backend to Hetzner VPS — set up systemd service for FastAPI, configure .env with production credentials, set up scraper scheduler as systemd timer or cron job.
- [ ] T044 [P] Deploy frontend to Cloudflare Pages — connect repo, set build command (`cd frontend && npm run build`), set environment variables (NEXT_PUBLIC_API_URL, NEXT_PUBLIC_R2_URL), verify deployment.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — builds the data foundation
- **US2 (Phase 4)**: Depends on Phase 2 + US1 having populated data (at least partial)
- **US3 (Phase 5)**: Depends on US2 (needs completed designs)
- **US4 (Phase 6)**: Depends on Phase 2 + US1 having data (independent of US2/US3)
- **Polish (Phase 7)**: Depends on US1 + US2 minimum

### User Story Dependencies

```
Phase 1: Setup
    ↓
Phase 2: Foundational
    ↓
Phase 3: US1 (Crawler) ←── Must have products before US2 can test
    ↓                ↘
Phase 4: US2 (Render)    Phase 6: US4 (Browse) — can run in parallel with US2
    ↓
Phase 5: US3 (Swap)
    ↓
Phase 7: Polish + Deploy
```

### Within Each User Story

- Models/config before services
- Services before API routes
- API routes before frontend components
- Core components before page integration
- Backend complete before dependent frontend work

### Parallel Opportunities

**Phase 1** (all [P] tasks):
- T003 (frontend init), T004 (.env.example), T005 (.gitignore) can run in parallel

**Phase 2** (after T006-T008):
- T009 (R2 client), T010 (Product model), T011 (Room model), T012 (Design model) can all run in parallel

**Phase 4 — US2** (after backend services T019-T022):
- T025 (SketchUpload), T026 (ConfigPanel), T027 (ProductCard), T028 (BudgetBar) can all run in parallel
- T023 (translations) and T024 (API client) can run in parallel with backend work

**Phase 7**:
- T040 (validation), T041 (Dockerfile), T044 (frontend deploy) can run in parallel

---

## Parallel Example: User Story 2

```bash
# After backend services (T019-T022) are complete, launch frontend components in parallel:
Task: "Create SketchUpload component at frontend/src/components/SketchUpload.tsx"
Task: "Create ConfigPanel component at frontend/src/components/ConfigPanel.tsx"
Task: "Create ProductCard component at frontend/src/components/ProductCard.tsx"
Task: "Create BudgetBar component at frontend/src/components/BudgetBar.tsx"

# Then sequentially:
Task: "Create RenderView component" (depends on render_url pattern)
Task: "Create ProductList component" (depends on ProductCard)
Task: "Create landing page" (depends on SketchUpload + ConfigPanel)
Task: "Create design result page" (depends on RenderView + ProductList + BudgetBar)
```

---

## Implementation Strategy

### MVP First (US1 + US2 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T012)
3. Complete Phase 3: US1 — Crawler (T013-T018)
4. **VALIDATE**: Run scraper, verify 500+ products in Supabase, vision enrichment working
5. Complete Phase 4: US2 — Render pipeline (T019-T033)
6. **VALIDATE**: Upload sketch → get render + product cards with buy links
7. **DEPLOY**: Backend on VPS, frontend on Cloudflare Pages
8. **MVP LIVE** — 44 tasks total, core experience working

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 (Crawler) → Standalone product database, API searchable → First demo
3. US2 (Render) → Full sketch-to-render flow → **MVP Launch**
4. US3 (Swap) → Enhanced user experience → Update
5. US4 (Browse) → Product discovery → Update
6. Polish + Deploy → Production ready

### Suggested MVP Scope

**Minimum**: Phase 1 + Phase 2 + Phase 3 (US1) + Phase 4 (US2) = **T001-T033** (33 tasks)
This delivers the complete core experience: upload sketch → get furnished room render with real, buyable products.

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| Phase 1: Setup | T001-T005 (5) | Project structure, dependencies |
| Phase 2: Foundational | T006-T012 (7) | Storage clients, models, config |
| Phase 3: US1 Crawler | T013-T018 (6) | Scraper, vision enrichment, product API |
| Phase 4: US2 Render | T019-T033 (15) | Room analyzer, matcher, generator, full frontend |
| Phase 5: US3 Swap | T034-T037 (4) | Swap alternatives + re-render |
| Phase 6: US4 Browse | T038 (1) | Product search page |
| Phase 7: Polish | T039-T044 (6) | Error handling, deployment |
| **Total** | **44 tasks** | |

## Notes

- [P] tasks = different files, no dependencies — can run in parallel
- [Story] label maps task to specific user story for traceability
- No test tasks included (manual testing for MVP per plan.md)
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- BGN→EUR conversion rate: 1.9558 (fixed peg)
- Gemini model ID must be verified at implementation time (see research.md)
