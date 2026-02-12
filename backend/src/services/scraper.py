"""
Furniture scraper service for Planche.bg

Discovers and scrapes product pages from Bulgarian furniture websites using
Firecrawl API, then extracts structured product data via Gemini Flash.
"""

import json
import re
import sys
import time
from uuid import uuid4

from firecrawl import Firecrawl
from google import genai

from src.config import (
    BG_TO_EN_CATEGORY,
    BGN_TO_EUR_RATE,
    FIRECRAWL_API_KEY,
    GEMINI_API_KEY,
    PRODUCT_EXTRACTION_PROMPT,
    TARGET_SITES,
)
from src.storage.r2_client import get_image_url, upload_product_images
from src.storage.supabase_client import save_product, save_scrape_job, update_scrape_job

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------

firecrawl_app = Firecrawl(api_key=FIRECRAWL_API_KEY)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ---------------------------------------------------------------------------
# Default Bulgarian search terms for product discovery
# ---------------------------------------------------------------------------

DEFAULT_SEARCH_TERMS: list[str] = [
    "мебели",
    "дивани",
    "маси",
    "столове",
    "легла",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_gemini_json(text: str) -> dict | None:
    """Parse JSON from Gemini response, stripping markdown fencing if present."""
    cleaned = text.strip()
    # Remove ```json ... ``` or ``` ... ``` wrappers
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        print(f"[scraper] Failed to parse Gemini JSON: {exc}")
        return None


def _convert_bgn_to_eur(product: dict) -> dict:
    """If the product currency is BGN, convert price fields to EUR."""
    currency = (product.get("currency") or "").upper()
    if currency == "BGN":
        if product.get("price") is not None:
            try:
                product["price"] = round(float(product["price"]) / BGN_TO_EUR_RATE, 2)
            except (TypeError, ValueError):
                pass
        if product.get("original_price") is not None:
            try:
                product["original_price"] = round(
                    float(product["original_price"]) / BGN_TO_EUR_RATE, 2
                )
            except (TypeError, ValueError):
                pass
        product["currency"] = "EUR"
    return product


def _normalize_for_db(product: dict) -> dict:
    """Map Gemini extraction fields to the DB schema columns."""
    # dimensions object → flat columns
    dims = product.pop("dimensions", None) or {}
    if isinstance(dims, dict):
        if dims.get("width_cm") is not None:
            product["width_cm"] = dims["width_cm"]
        if dims.get("height_cm") is not None:
            product["height_cm"] = dims["height_cm"]
        if dims.get("depth_cm") is not None:
            product["depth_cm"] = dims["depth_cm"]

    # colors list → available_colors (JSONB) + color (first item)
    colors = product.pop("colors", None)
    if colors and isinstance(colors, list):
        product["available_colors"] = colors
        product["color"] = colors[0] if colors else None

    # room_type: list → first item as text (DB column is TEXT)
    room_type = product.get("room_type")
    if isinstance(room_type, list):
        product["suitable_rooms"] = room_type
        product["room_type"] = room_type[0] if room_type else None

    # subcategory → ai_subcategory too
    if product.get("subcategory"):
        product["ai_subcategory"] = product["subcategory"]

    # source_url → product_url
    if "source_url" in product and "product_url" not in product:
        product["product_url"] = product.pop("source_url")

    # domain → source_domain
    if "domain" in product:
        product["source_domain"] = product.pop("domain")

    # description_bg → description (DB column is for original language)
    # English description → visual_description (used for rendering prompts)
    desc_bg = product.pop("description_bg", None)
    desc_en = product.get("description")
    if desc_bg:
        product["description"] = desc_bg
    if desc_en and desc_en != desc_bg:
        product["visual_description"] = desc_en

    # Only keep keys that exist in the DB schema
    ALLOWED_COLUMNS = {
        "id", "name", "brand", "sku", "model", "price", "original_price",
        "currency", "on_sale", "category", "subcategory", "room_type",
        "style", "width_cm", "height_cm", "depth_cm", "weight_kg",
        "seat_height_cm", "diameter_cm", "dimensions_source",
        "dimensions_confidence", "proportion_w_h", "proportion_w_d",
        "visual_description", "color", "color_hex", "color_tone",
        "available_colors", "materials", "primary_material", "finish",
        "upholstery", "luxury_score", "ai_category", "ai_subcategory",
        "suitable_rooms", "image_type", "image_usable", "image_urls",
        "main_image_url", "r2_image_keys", "r2_main_image_key",
        "r2_image_count", "description", "features", "assembly_required",
        "warranty", "max_load_kg", "seating_capacity", "number_of_drawers",
        "adjustable", "foldable", "outdoor_suitable", "in_stock",
        "delivery_info", "delivery_days", "free_delivery", "rating",
        "review_count", "vision_data", "vision_enriched",
        "vision_enriched_at", "product_url", "source_domain",
    }
    product = {k: v for k, v in product.items() if k in ALLOWED_COLUMNS}

    return product


def _map_category(product: dict) -> dict:
    """Map Bulgarian category name to English using BG_TO_EN_CATEGORY."""
    category = product.get("category") or ""
    # Try exact match first
    if category in BG_TO_EN_CATEGORY:
        product["category"] = BG_TO_EN_CATEGORY[category]
    else:
        # Try case-insensitive / partial match
        category_lower = category.lower().strip()
        for bg_name, en_name in BG_TO_EN_CATEGORY.items():
            if bg_name.lower() == category_lower:
                product["category"] = en_name
                break
    return product


def _is_product_url(url: str) -> bool:
    """Heuristic check: does the URL look like a product page?"""
    product_segments = [
        "/product/",
        "/products/",
        "/produkti/",
        "/produkt/",
        "/p/",
        "/item/",
        "/стока/",
        "-p-",
        "/tovar/",
        "/detail/",
        "/details/",
        "/offer/",
    ]
    url_lower = url.lower()
    # Positive signals – URL contains a product-like path segment
    if any(seg in url_lower for seg in product_segments):
        return True
    # URLs with numeric IDs in the path are often product pages
    if re.search(r"/\d{3,}", url_lower):
        return True
    # Slug-like trailing segments (e.g. /divan-roma-siv-123) are common for products
    if re.search(r"/[a-z0-9]+-[a-z0-9]+-[a-z0-9]+", url_lower):
        return True
    return False


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def scrape_single_product(url: str, site_config: dict) -> dict | None:
    """
    Scrape a single product page and extract structured data.

    1. Use Firecrawl /scrape to get Markdown from the page.
    2. Send the Markdown to Gemini Flash for structured extraction.
    3. Post-process: map categories, convert currencies.

    Returns a product dict or None on failure.
    """
    try:
        # ----- Firecrawl scrape (v4 SDK) -----
        result = firecrawl_app.scrape(
            url=url,
            formats=["markdown"],
        )

        # v4 returns a dict with 'markdown' key directly
        markdown = ""
        if isinstance(result, dict):
            markdown = result.get("markdown") or ""
        elif hasattr(result, "markdown"):
            markdown = result.markdown or ""
        if not markdown:
            print(f"[scraper] No markdown returned for {url}")
            return None

        # ----- Gemini extraction -----
        prompt = PRODUCT_EXTRACTION_PROMPT.format(markdown=markdown)
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        raw_text = response.text or ""
        product = _parse_gemini_json(raw_text)
        if not product:
            print(f"[scraper] Could not extract product data from {url}")
            return None

        # ----- Post-processing -----
        product["source_url"] = url
        product["domain"] = site_config.get("domain", "")
        product = _map_category(product)
        product = _convert_bgn_to_eur(product)
        product = _normalize_for_db(product)

        return product

    except Exception as exc:
        print(f"[scraper] Error scraping {url}: {exc}")
        return None


def _discover_via_category_scrape(site_config: dict) -> set[str]:
    """
    Fallback discovery: scrape each category page and extract product links
    from the rendered HTML. Useful for JS-heavy sites where /map returns
    very few URLs.
    """
    base_url = site_config.get("url", "")
    domain = site_config.get("domain", "")
    found_urls: set[str] = set()

    # First, scrape the main catalog page to discover category links
    try:
        result = firecrawl_app.scrape(url=base_url, formats=["links"])
        links = []
        if isinstance(result, dict):
            links = result.get("links") or []
        elif hasattr(result, "links"):
            links = result.links or []

        # Identify category pages (paths under /catalog/ that aren't product pages)
        category_urls = []
        for link in links:
            link_str = link if isinstance(link, str) else getattr(link, "url", "")
            if domain in link_str and "/catalog/" in link_str and not _is_product_url(link_str):
                category_urls.append(link_str)
            # Also collect any product URLs found on the main page
            if domain in link_str and _is_product_url(link_str):
                found_urls.add(link_str)

        # Deduplicate category URLs
        category_urls = list(set(category_urls))
        print(f"[scraper] Found {len(category_urls)} category pages to crawl on {domain}")

        # Scrape each category page for product links
        for cat_url in category_urls:
            try:
                cat_result = firecrawl_app.scrape(url=cat_url, formats=["links"])
                cat_links = []
                if isinstance(cat_result, dict):
                    cat_links = cat_result.get("links") or []
                elif hasattr(cat_result, "links"):
                    cat_links = cat_result.links or []

                for link in cat_links:
                    link_str = link if isinstance(link, str) else getattr(link, "url", "")
                    if domain in link_str and _is_product_url(link_str):
                        found_urls.add(link_str)

                print(f"[scraper] Category {cat_url}: found {len(found_urls)} product URLs so far")
                time.sleep(1)  # Rate limiting between category scrapes
            except Exception as exc:
                print(f"[scraper] Error scraping category {cat_url}: {exc}")

    except Exception as exc:
        print(f"[scraper] Error in category discovery for {domain}: {exc}")

    return found_urls


def discover_product_urls(
    site_config: dict,
    search_terms: list[str] | None = None,
) -> list[str]:
    """
    Discover product URLs from a furniture site.

    Strategy:
    1. Try Firecrawl /map with search terms.
    2. If /map yields too few results, fall back to scraping category pages
       and extracting product links from rendered HTML.
    """
    terms = search_terms or DEFAULT_SEARCH_TERMS
    base_url = site_config.get("url", "")
    all_urls: set[str] = set()

    # --- Strategy 1: Firecrawl /map ---
    for term in terms:
        try:
            map_result = firecrawl_app.map(
                url=base_url,
                search=term,
            )
            # v4 may return LinkResult objects, dicts, or strings
            raw_urls = []
            if isinstance(map_result, dict):
                raw_urls = map_result.get("links") or map_result.get("urls") or []
            elif isinstance(map_result, list):
                raw_urls = map_result
            elif hasattr(map_result, "links"):
                raw_urls = map_result.links or []

            # Extract URL strings from LinkResult objects or dicts
            for item in raw_urls:
                if isinstance(item, str):
                    all_urls.add(item)
                elif hasattr(item, "url"):
                    all_urls.add(item.url)
                elif isinstance(item, dict) and "url" in item:
                    all_urls.add(item["url"])
        except Exception as exc:
            print(f"[scraper] Map error for term on {base_url}: {exc}")

    # Filter to product-like URLs only
    product_urls = [u for u in all_urls if _is_product_url(u)]

    # --- Strategy 2: Fallback to category page scraping ---
    if len(product_urls) < 5:
        print(
            f"[scraper] /map found only {len(product_urls)} product URLs on "
            f"{site_config.get('domain', base_url)}, falling back to category scraping..."
        )
        fallback_urls = _discover_via_category_scrape(site_config)
        product_urls = list(set(product_urls) | fallback_urls)

    print(
        f"[scraper] Discovered {len(product_urls)} product URLs "
        f"(from {len(all_urls)} map + fallback) on {site_config.get('domain', base_url)}"
    )
    return product_urls


def scrape_site(site_config: dict, max_products: int = 100) -> dict:
    """
    Full scrape pipeline for a single site:

    1. Discover product URLs.
    2. Scrape each URL (up to *max_products*).
    3. Upload images to R2 and persist products to Supabase.
    4. Return stats dict.
    """
    domain = site_config.get("domain", "unknown")
    start_time = time.time()
    stats = {
        "products_found": 0,
        "pages_scraped": 0,
        "errors": 0,
        "duration_seconds": 0.0,
    }

    # Step 1 – discover
    urls = discover_product_urls(site_config)
    urls = urls[:max_products]
    total = len(urls)
    print(f"[scraper] Will scrape up to {total} products from {domain}")

    # Step 2 – scrape each URL
    for i, url in enumerate(urls, start=1):
        print(f"[scraper] Scraping {domain}: {i}/{total} - {url}")
        product = scrape_single_product(url, site_config)
        stats["pages_scraped"] += 1

        if product is None:
            stats["errors"] += 1
            time.sleep(1.5)
            continue

        # Step 3 – upload images & persist
        try:
            image_urls = product.get("image_urls") or []
            product_id = None

            # Save product first to obtain an ID for image storage
            product_id = save_product(product, domain)

            # Store the source page URL
            product["product_url"] = url

            if product_id and image_urls:
                r2_keys = upload_product_images(
                    product_id=product_id,
                    domain=domain,
                    image_urls=image_urls,
                )
                if r2_keys:
                    product["r2_image_keys"] = r2_keys
                    product["r2_main_image_key"] = r2_keys[0]
                    product["r2_image_count"] = len(r2_keys)
                    # Store public URLs so Gemini can access images
                    product["main_image_url"] = get_image_url(r2_keys[0])
                    # Re-save with image keys and URLs
                    save_product(product, domain)

            stats["products_found"] += 1

        except Exception as exc:
            print(f"[scraper] Error saving product from {url}: {exc}")
            stats["errors"] += 1

        # Rate limiting
        time.sleep(1.5)

    stats["duration_seconds"] = round(time.time() - start_time, 2)
    print(
        f"[scraper] Finished {domain}: "
        f"{stats['products_found']} products, "
        f"{stats['pages_scraped']} pages, "
        f"{stats['errors']} errors, "
        f"{stats['duration_seconds']}s"
    )
    return stats


def scrape_all_sites(max_per_site: int = 100) -> dict:
    """
    Scrape every site in TARGET_SITES, ordered by priority (HIGH first).

    Creates and updates scrape-job records in Supabase for tracking.
    Returns aggregate stats across all sites.
    """
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    sorted_sites = sorted(
        TARGET_SITES,
        key=lambda s: priority_order.get((s.get("priority") or "LOW").upper(), 2),
    )

    aggregate: dict = {
        "total_products_found": 0,
        "total_pages_scraped": 0,
        "total_errors": 0,
        "total_duration_seconds": 0.0,
        "sites": {},
    }

    for site_config in sorted_sites:
        domain = site_config.get("domain", "unknown")
        job_id = str(uuid4())

        # Record job start
        try:
            save_scrape_job(job_id, site_config.get("url", ""))
        except Exception as exc:
            print(f"[scraper] Could not create scrape job for {domain}: {exc}")

        # Run the scrape
        site_stats = scrape_site(site_config, max_products=max_per_site)

        # Update job record
        try:
            error_count = site_stats["errors"]
            status = "completed" if error_count == 0 else "completed_with_errors"
            update_scrape_job(
                job_id=job_id,
                status=status,
                products_found=site_stats["products_found"],
                pages_scraped=site_stats["pages_scraped"],
                errors=f"{error_count} errors" if error_count > 0 else None,
                duration_seconds=site_stats["duration_seconds"],
            )
        except Exception as exc:
            print(f"[scraper] Could not update scrape job for {domain}: {exc}")

        # Aggregate
        aggregate["total_products_found"] += site_stats["products_found"]
        aggregate["total_pages_scraped"] += site_stats["pages_scraped"]
        aggregate["total_errors"] += site_stats["errors"]
        aggregate["total_duration_seconds"] += site_stats["duration_seconds"]
        aggregate["sites"][domain] = site_stats

    print(
        f"\n[scraper] === All sites done === "
        f"Products: {aggregate['total_products_found']}, "
        f"Pages: {aggregate['total_pages_scraped']}, "
        f"Errors: {aggregate['total_errors']}, "
        f"Duration: {aggregate['total_duration_seconds']}s"
    )
    return aggregate


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        print("Usage:")
        print('  python -m src.services.scraper "URL"           — scrape a single product URL')
        print("  python -m src.services.scraper --all           — scrape all TARGET_SITES")
        print("  python -m src.services.scraper --site DOMAIN   — scrape a specific site")
        sys.exit(0)

    if args[0] == "--all":
        result = scrape_all_sites()
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args[0] == "--site":
        if len(args) < 2:
            print("Error: --site requires a domain argument (e.g. videnov.bg)")
            sys.exit(1)
        target_domain = args[1]
        matched_site = None
        for site in TARGET_SITES:
            if site.get("domain") == target_domain:
                matched_site = site
                break
        if matched_site is None:
            print(f"Error: domain '{target_domain}' not found in TARGET_SITES")
            print("Available domains:", [s.get("domain") for s in TARGET_SITES])
            sys.exit(1)
        result = scrape_site(matched_site)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    else:
        # Treat first positional argument as a product URL
        product_url = args[0]
        # Try to find a matching site config by domain
        matched_config: dict = {}
        for site in TARGET_SITES:
            if site.get("domain") and site["domain"] in product_url:
                matched_config = site
                break
        if not matched_config:
            # Use minimal defaults
            matched_config = {"domain": "", "wait_for": None, "only_main_content": True}

        product = scrape_single_product(product_url, matched_config)
        if product:
            print(json.dumps(product, indent=2, ensure_ascii=False))
        else:
            print(f"Failed to extract product data from {product_url}")
            sys.exit(1)
