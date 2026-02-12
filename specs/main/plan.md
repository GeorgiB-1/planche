# Implementation Plan: Planche.bg — AI Interior Design MVP

**Branch**: `main` | **Date**: 2026-02-12 | **Spec**: [specs/main/spec.md](spec.md)
**Input**: Feature specification from `/specs/main/spec.md`

## Summary

Build an MVP platform where users upload hand-drawn room sketches and receive photorealistic renders filled with real, purchasable furniture from Bulgarian/European stores. Two parallel tracks: (1) an automated web crawler (Firecrawl) that populates a Supabase product database with AI-enriched product data and images in Cloudflare R2, and (2) a sketch-to-render pipeline using Gemini Vision for room analysis and Gemini Image Generation for photorealistic rendering with actual product reference photos.

## Technical Context

**Language/Version**: Python 3.11+ (backend/scraper), TypeScript/React (frontend via Next.js)
**Primary Dependencies**: FastAPI, google-genai (Gemini), firecrawl-py, supabase-py, boto3 (R2), Next.js, React
**Storage**: Supabase (Postgres) for structured data + Cloudflare R2 for images (product photos, sketches, renders)
**Testing**: pytest (backend), manual testing (MVP — automated tests deferred to post-MVP)
**Target Platform**: Web (responsive — mobile-first for sketch photo capture)
**Project Type**: Web application (Python backend + Next.js frontend)
**Performance Goals**: End-to-end sketch-to-render < 60 seconds, scraper throughput 100+ products/hour
**Constraints**: Free/low-cost tiers for all services (Supabase free, R2 free 10GB, Gemini free 1500 req/day), total infra < €30/month for MVP
**Scale/Scope**: 500-5000 products in DB, < 100 concurrent users, 5 target furniture sites

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution is not yet defined (blank template). No gate violations to check. Proceeding with sensible defaults:
- Keep architecture simple — minimal services
- No premature abstractions
- Start with monolithic backend, split later if needed
- Test at system boundaries (API endpoints, scraper output)

## Project Structure

### Documentation (this feature)

```text
specs/main/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research output
├── data-model.md        # Phase 1 data model
├── quickstart.md        # Phase 1 quickstart guide
├── contracts/           # Phase 1 API contracts
│   └── api.yaml         # OpenAPI spec for backend API
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/              # Pydantic models (product, design, room)
│   │   ├── product.py
│   │   ├── design.py
│   │   └── room.py
│   ├── services/            # Business logic
│   │   ├── scraper.py       # Firecrawl-based product scraper
│   │   ├── vision.py        # Gemini Vision enrichment pipeline
│   │   ├── room_analyzer.py # Sketch → room layout JSON
│   │   ├── matcher.py       # Room + budget → product selection
│   │   ├── generator.py     # Nano Banana render generation
│   │   └── scheduler.py     # Cron-style scrape scheduling
│   ├── api/                 # FastAPI routes
│   │   ├── main.py          # App entry + CORS
│   │   ├── routes_design.py # /api/analyze, /api/furnish, /api/swap
│   │   └── routes_product.py # /api/products/search, /api/stats
│   ├── storage/             # Data access
│   │   ├── supabase.py      # Supabase client + product CRUD
│   │   └── r2.py            # Cloudflare R2 client (boto3)
│   └── config.py            # Environment variables, constants, BG category mappings
├── requirements.txt
└── Dockerfile

frontend/
├── src/
│   ├── components/
│   │   ├── SketchUpload.tsx      # Drag-drop + camera capture
│   │   ├── ConfigPanel.tsx       # Room type, style, budget, tier
│   │   ├── RenderView.tsx        # Full-width render display
│   │   ├── ProductCard.tsx       # Individual product with buy/swap
│   │   ├── ProductList.tsx       # Side panel of matched products
│   │   ├── SwapModal.tsx         # Alternative product picker
│   │   └── BudgetBar.tsx         # Budget spent/remaining bar
│   ├── pages/
│   │   ├── index.tsx             # Landing / upload page
│   │   ├── design/[id].tsx       # Design result page
│   │   └── browse.tsx            # Product search/browse
│   ├── services/
│   │   └── api.ts                # Backend API client
│   ├── i18n/
│   │   └── bg.ts                 # Bulgarian translations
│   └── styles/
│       └── globals.css
├── package.json
├── next.config.js
└── tsconfig.json
```

**Structure Decision**: Web application with separate `backend/` (Python/FastAPI) and `frontend/` (Next.js/React) directories. The backend handles all AI processing, scraping, and data management. The frontend is a thin client that uploads images and displays results.

## MVP Phases

### Phase 1: Data Foundation (Week 1-2)

**Goal**: Populated product database with 500+ real products from Bulgarian stores.

| Step | What | Output |
|------|------|--------|
| 1.1 | Create Supabase project, run schema SQL (products, price_history, scrape_jobs, designs) | Tables + indexes ready |
| 1.2 | Create Cloudflare R2 bucket (`furniture-platform`), configure public access | R2 bucket with public URL |
| 1.3 | Build `storage/supabase.py` — product CRUD, upsert with price tracking | Working Supabase client |
| 1.4 | Build `storage/r2.py` — image upload/download/URL generation | Working R2 client |
| 1.5 | Build `config.py` — env vars, BG→EN category mapping, budget tiers, site targets | Configuration module |
| 1.6 | Migrate existing scraper to use Supabase + R2 instead of SQLite + local files | `services/scraper.py` |
| 1.7 | Run initial scrapes: videnov.bg, ikea.bg, aiko-bg.com | 500+ products in Supabase, images in R2 |
| 1.8 | Build `services/scheduler.py` — daily re-scrape with price change detection | Automated scraping |

### Phase 2: AI Intelligence Layer (Week 3-5)

**Goal**: Every product has AI-verified data. Sketches can be analyzed. Products can be matched to rooms.

| Step | What | Output |
|------|------|--------|
| 2.1 | Build `services/vision.py` — Gemini Flash vision enrichment pipeline | Vision enrichment module |
| 2.2 | Run enrichment on all 500+ products, verify quality | Products with visual_description, proportions, image_usable flags |
| 2.3 | Build `services/room_analyzer.py` — sketch → structured room JSON | Room analysis module |
| 2.4 | Test room analyzer with 10+ sketch photos (hand-drawn, digital, various quality) | Validated room analysis |
| 2.5 | Build `services/matcher.py` — room + budget + style → real product selection | Furniture matching module |
| 2.6 | Build `models/` — Pydantic models for Product, Design, Room, MatchResult | Type-safe data models |
| 2.7 | Test matching: €500 спалня, €2000 хол, €5000 премиум, €15000 луксозен | Validated budget allocation |

### Phase 3: Render & API (Week 6-8)

**Goal**: Working end-to-end flow from sketch upload to photorealistic render with product cards.

| Step | What | Output |
|------|------|--------|
| 3.1 | Build `services/generator.py` — Nano Banana render with auto product photo inclusion | Design generation module |
| 3.2 | Test renders: verify products visually match reference photos, proportions correct | Validated renders |
| 3.3 | Build FastAPI app (`api/main.py`, routes) — /analyze, /furnish, /swap, /products/search, /stats | Working API |
| 3.4 | Build Next.js frontend — upload, configure, view result, product cards, buy links | Working frontend |
| 3.5 | Wire frontend ↔ backend, test full flow | End-to-end MVP |
| 3.6 | Deploy: backend on Hetzner VPS, frontend on Cloudflare Pages | Live MVP |

### Post-MVP (Future phases — NOT part of this plan)

- User accounts (Supabase Auth) — save/share designs
- Product swap + re-render (US3)
- Product search/browse page (US4)
- More furniture sites (Wayfair UK, IKEA UK)
- SEO optimization for Bulgarian search terms
- Analytics dashboard
- Mobile app (React Native)

## Complexity Tracking

No constitution violations to justify — architecture is deliberately simple:
- 1 backend service (FastAPI monolith)
- 1 frontend app (Next.js)
- 2 managed services (Supabase, R2) — no self-hosted databases
- No message queues, no microservices, no container orchestration
- Direct function calls between modules (no service mesh)
