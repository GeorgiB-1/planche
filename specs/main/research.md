# Research: Planche.bg — AI Interior Design MVP

**Date**: 2026-02-12
**Status**: Complete
**Purpose**: Resolve all technical unknowns before implementation planning

---

## 1. Image Generation Model (Nano Banana / Gemini)

### Decision: Gemini 2.0 Flash (Image Generation) via Google GenAI API

**Rationale**:
- Gemini's image generation model (internally "Nano Banana") supports multimodal input: text + multiple reference images in a single prompt
- This is critical — the render prompt includes the user's sketch + ALL matched product photos from R2
- The model can generate photorealistic interior renders when given detailed prompts with dimension constraints
- Free tier provides sufficient volume for MVP (1500 requests/day for Flash)

**Model ID**: `gemini-2.5-flash-preview-image-generation` (as of mid-2025)
- **WARNING**: This preview model ID is likely outdated by Feb 2026. Google rotates preview models every 2-4 months.
- At implementation time, verify the current model by checking Google AI Studio or querying:
  `curl "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY"`
- Image generation may now be a native capability of `gemini-2.5-flash` (no suffix) or a newer `gemini-3.x-flash`
- The API uses `response_modalities: ["IMAGE", "TEXT"]` in `generation_config`

**Multi-image input**: Confirmed — Gemini supports arbitrary mix of image + text parts in a single prompt. Can comfortably send 5-10 reference images + sketch + text. **Resize product images to ~512px** on longest side before encoding to save tokens.

**Output**: Typically 1024x1024 resolution. No control over output resolution. No negative_prompt, no seed for reproducibility.

**Pricing** (mid-2025, verify current rates at ai.google.dev/pricing):
- Free tier: 1500 req/day, 2 RPM for image generation
- Paid: ~$0.02-$0.10 per render estimated (input tokens negligible, image output is the main cost)

**Alternatives Considered**:
- Stable Diffusion / SDXL: Better control via ControlNet, but requires self-hosting GPU infrastructure. Rejected for MVP due to cost/complexity.
- DALL-E 3: Good quality but no multi-image reference input. Cannot show it actual product photos.
- Midjourney: No API available for automated integration.

**Key Concerns & Mitigations**:
1. **Product fidelity is imperfect**: Model captures general character (color, shape, style) but won't reproduce exact product designs pixel-perfectly. Mitigation: detailed `visual_description` + actual photo reference. Set user expectations — this is an "inspiration tool", not a professional 3D render.
2. **Proportions can be inconsistent**: Despite dimension instructions, furniture may be slightly wrong-sized. Mitigation: proportion ratios + percentage-of-room-width in prompt.
3. **Re-render consistency is poor**: Product swap re-renders may change camera angle, lighting, wall colors. Mitigation: include the previous render as reference in the swap prompt. Accept some variation.
4. **Resolution limited to ~1024px**: Good for screen, not for print. Acceptable for MVP.

---

## 2. Room Analysis (Sketch Understanding)

### Decision: Gemini 2.5 Flash Vision (text-only output)

**Rationale**:
- Gemini Flash excels at vision-to-structured-JSON tasks
- Fast and cheap — room analysis doesn't need image generation, just understanding
- Good at reading hand-drawn sketches, detecting room boundaries, estimating dimensions
- Handles Bulgarian labels (хол, спалня, кухня, баня) naturally

**Alternatives Considered**:
- GPT-4 Vision: Comparable quality but higher cost, no advantage for this task
- Custom CV model: Would need training data of floor plan sketches. Overkill for MVP.

**Risk**: Dimension estimation accuracy from rough sketches. Mitigation: frontend allows user to manually adjust detected dimensions before generating.

---

## 3. Web Scraping (Furniture Data)

### Decision: Firecrawl API for structured extraction

**Rationale**:
- Firecrawl handles JavaScript-rendered pages (many BG furniture sites use heavy JS)
- Built-in proxy rotation handles anti-bot measures
- LLM-based extraction can parse Bulgarian product pages without custom selectors
- The existing scraper codebase (from .tar) already uses Firecrawl

**Pricing**: Hobby plan ~$16/mo (3,000 credits), Standard ~$83/mo (100K credits), Scale $333+/mo (500K credits)
- Each `/scrape` call = 1 credit. Hobby (3K) is enough for initial MVP crawling of 500+ products.
- `/map` for URL discovery is cheap (1 credit per call, returns many URLs).
- Budget: ~35K credits for initial full scrape, ~3K/week for updates.

**Recommended Scraping Strategy** (hybrid approach):
1. **`/map`** to discover product URLs: `firecrawl map https://videnov.bg --search "мебели"`
2. **`/scrape`** each product page individually (1 credit each, most reliable)
3. **Gemini Flash** for structured extraction from scraped Markdown (free tier, 1500 req/day)
- This gives full control over the 40+ field extraction prompt, handles Bulgarian text better than Firecrawl's built-in LLM extraction, and is cheaper.
- Do NOT use `/extract` for detailed product data — it struggles with 40+ field schemas and varied Bulgarian page layouts.

**Bulgarian Site Considerations**:
- Product names: Keep in Bulgarian (Cyrillic). Example: "Диван ъглов Марио". Firecrawl preserves UTF-8 Cyrillic natively.
- Validate special chars after scraping: `ъ`, `щ`, `ю`, `я`, `ь`, `ж`, `ч`, `ш`, `ц`
- Categories: Translate to English for DB queries. BG → EN mapping needed:
  - мебели → furniture
  - дивани → sofas
  - маси → tables
  - столове → chairs
  - легла → beds
  - гардероби → wardrobes
  - шкафове → cabinets
  - матраци → mattresses
  - осветление → lighting
  - килими → rugs/carpets
  - баня → bathroom
  - кухня → kitchen
- Prices: Bulgarian sites show BGN (лв.). Convert to EUR at fixed rate: **1 EUR = 1.9558 BGN** (fixed peg, not floating).
- Dimensions: Usually in cm, same as our DB schema. Some sites use "Ш x В x Д" (Ширина x Височина x Дълбочина = Width x Height x Depth).

**Target Sites — Anti-Bot Analysis**:

| Site | Priority | Protection | Strategy |
|------|----------|------------|----------|
| **videnov.bg** | HIGH | Low-Med | Standard scrape. Server-rendered. Lazy-loads images — use `--wait-for 2000`. Start here. |
| **ikea.bg** | HIGH | Med-High | React SPA + Akamai bot detection. Use proxy rotation. Consider scraping their semi-public JSON API endpoints instead of HTML. |
| **aiko-bg.com** | HIGH | Low | Traditional e-commerce (Magento-like). Easiest target. Scrape first alongside videnov. |
| **jysk.bg** | MEDIUM | Medium | Modern JS frontend. Use `--wait-for 3000`. Dimensions often in description text, not structured. |
| **emag.bg** | LOW (deprioritize) | **HIGH** | Cloudflare enterprise protection, CAPTCHAs, fingerprinting. 10-20% failure rate expected. Marketplace = variable data quality. Scrape last, treat as nice-to-have. |

**Rate Limiting Strategy**:
- Max 2-3 concurrent requests per domain (even if Firecrawl supports 100 total)
- 1-2 second delay between requests to same domain
- Scrape during off-peak hours: 02:00-06:00 EET
- Use `--only-main-content` to reduce load time and avoid triggering protections

**Alternatives Considered**:
- Scrapy/Beautiful Soup: Manual selector writing per site. Fragile, high maintenance. Rejected.
- Playwright scraping: Good for JS sites but no built-in extraction intelligence. More code to maintain.

---

## 4. Database & Storage

### Decision: Supabase (Postgres) + Cloudflare R2

**Rationale**:
- **Supabase**: Managed Postgres with REST API, auth, real-time subscriptions. Free tier: 500MB storage, 50K monthly active users, 500MB bandwidth. Sufficient for MVP (50K products < 200MB).
- **Cloudflare R2**: S3-compatible object storage. Free tier: 10GB storage, 10M Class B requests/month, 1M Class A requests/month. Zero egress fees (critical — images served frequently to frontend + AI models).

**Schema Approach** (Hybrid — core columns + JSONB):
- **Tier 1 — Queryable columns**: Fields you filter/sort/index on as proper typed columns (id, name, price, category, dimensions, in_stock, style, room_type, image_usable, source_domain)
- **Tier 2 — JSONB columns**: Grouped semi-structured data (vision_data, materials, colors, suitable_rooms, available_colors, features). Only read, rarely queried directly.
- **Tier 3 — Related tables**: price_history, scrape_jobs (separate entities)
- This avoids a painful 60+ column ALTER TABLE situation while keeping fast queries on core fields.

**Python Client Notes**:
- Use `supabase` 2.x package (renamed from `supabase-py`) for CRUD operations
- For **bulk scraper inserts**, consider direct `asyncpg` or `psycopg2` connection to the Supabase Postgres URL for better performance (PostgREST HTTP adds overhead for batch ops)
- Use `.upsert()` with arrays rather than individual inserts for batch operations

**Supabase Free Tier Gotchas**:
- 500 MB database — fits ~5,000-10,000 enriched products (estimate ~50KB/product with JSONB). Monitor closely.
- **Projects pause after 1 week of inactivity** — problematic for a crawler that runs periodically. Need regular pings or upgrade to Pro ($25/mo).
- No daily backups on free tier — risk for scraped data. Consider pg_dump as backup strategy.
- 5 GB/month bandwidth — should be fine since images are on R2, not Supabase.
- Realtime: **Skip for MVP**. Simple HTTP polling for design generation progress is sufficient.

**Indexing Strategy**:
- **Primary matching index** (partial): `(category, style, room_type, price) WHERE in_stock = TRUE` — equality filters first, range last
- **Dimension indexes** (partial): `(width_cm) WHERE in_stock = TRUE`, same for height/depth
- Individual indexes: source_domain, vision_enriched, image_usable, luxury_score
- Start with 4-5 indexes max — each slows INSERT/UPDATE (scraper does many of these). Add more based on `EXPLAIN ANALYZE`.
- Consider `pg_trgm` on `name` for fuzzy Bulgarian text search (post-MVP)

**R2 Best Practices**:
- **Public bucket with custom domain** (e.g., `images.planche.bg`) — zero-cost CDN image serving, no pre-signed URLs needed
- **Convert images to WebP** before upload (Pillow) — ~60% smaller than JPEG, saves R2 storage
- Set `ContentType` header on every upload so browsers render correctly
- Use `concurrent.futures.ThreadPoolExecutor` for parallel image uploads (boto3 is not async-native)
- R2 may return 503s under load — implement exponential backoff retries
- Free tier: 10 GB storage = ~10,000 products at 5 WebP images each (~200KB each)

**R2 Structure**:
- `products/{domain}/{product_id}/{NNN}.webp` — product images (WebP optimized)
- `sketches/{design_id}/sketch.{ext}` — user uploads
- `renders/{design_id}/render_vN.{ext}` — generated renders

**Alternatives Considered**:
- SQLite + local filesystem: Works for prototype but doesn't scale. No API, no real-time, single-node.
- Firebase/Firestore: Document DB not ideal for relational product queries with complex filters.
- AWS S3: Egress fees (~$0.09/GB) would be significant with frequent image serving. R2 has zero egress fees.

---

## 5. Backend Framework

### Decision: FastAPI (Python 3.11+)

**Rationale**:
- Python ecosystem has the best AI/ML library support (google-genai, supabase-py, boto3)
- FastAPI provides async support, auto-docs (Swagger), type validation with Pydantic
- The existing scraper code is already in Python
- Fast enough for MVP load (< 100 concurrent users)

**Alternatives Considered**:
- Node.js/Express: Would require rewriting scraper. JS AI libraries less mature.
- Go: Fast but worse AI library ecosystem.

---

## 6. Frontend Framework

### Decision: Next.js (React) deployed on Cloudflare Pages

**Rationale**:
- SSR for SEO (important for Bulgarian search: "AI интериорен дизайн")
- React component ecosystem for upload, gallery, product cards
- Cloudflare Pages: free hosting, global CDN, close to R2 (same network)
- Supports mobile-responsive design (many users will photograph sketches on phone)

**Alternatives Considered**:
- SvelteKit: Lighter but smaller ecosystem.
- Plain React SPA: No SSR, worse SEO.

---

## 7. Bulgarian Language & i18n Strategy

### Decision: Bulgarian-first UI with English internal data

**Rationale**:
- Target market is Bulgaria — UI text must be in Bulgarian
- Product names stay in original language (Bulgarian) as scraped
- Internal classification fields (category, style, room_type) in English for consistent querying
- AI prompts to Gemini use English (better model performance)
- Category mapping table: BG display name ↔ EN query value

**Key Bulgarian UI Terms**:
| English | Bulgarian | Context |
|---------|-----------|---------|
| Upload Sketch | Качи скица | Upload button |
| Budget | Бюджет | Budget input |
| Style | Стил | Style selector |
| Generate Design | Генерирай дизайн | Main CTA |
| Buy | Купи | Product card |
| Swap | Замени | Product swap |
| Living Room | Хол / Дневна | Room type |
| Bedroom | Спалня | Room type |
| Kitchen | Кухня | Room type |
| Bathroom | Баня | Room type |
| Office | Офис / Кабинет | Room type |
| Kids Room | Детска стая | Room type |
| Dining Room | Трапезария | Room type |
| Budget tier | Бюджетен | Tier |
| Standard tier | Стандартен | Tier |
| Premium tier | Премиум | Tier |
| Luxury tier | Луксозен | Tier |
| Total | Общо | Budget summary |
| Remaining | Остатък | Budget summary |
| In Stock | Наличен | Product status |
| Out of Stock | Изчерпан | Product status |
| Delivery | Доставка | Product info |
| Dimensions | Размери | Product info |
| Materials | Материали | Product info |

---

## 8. Deployment & Infrastructure

### Decision: VPS (Hetzner) + Cloudflare Pages

**Rationale**:
- **Backend**: Hetzner VPS (€5-10/mo) for FastAPI + scraper + scheduler. Hetzner has EU data centers (GDPR compliance). Good value.
- **Frontend**: Cloudflare Pages (free). Same network as R2 for fast image serving.
- **Domain**: planche.bg (or similar Bulgarian domain)

**Alternatives Considered**:
- AWS/GCP: Overkill for MVP, more expensive, more complex.
- Railway/Render: Good but less control, potentially more expensive at scale.
- Vercel: Great for Next.js but R2 integration less natural than Cloudflare Pages.

---

## 9. MVP Phasing Decision

### Decision: Two-track MVP with 3 phases

**Rationale**: The two core features (database + render) can be built in parallel tracks but the render track depends on having data. So:

**Phase 1 (Foundation)**: Supabase schema + R2 bucket + scraper migration → populate 500+ products
**Phase 2 (Intelligence)**: Vision enrichment + room analyzer + furniture matcher
**Phase 3 (Generation)**: Design generator + API + minimal frontend

This lets the database accumulate products while the AI pipeline is being built.
