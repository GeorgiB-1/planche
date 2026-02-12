"""
AI Vision Enrichment Service for Planche.bg

Downloads product images from R2 (or URL fallback), sends them to
Gemini Flash for visual analysis, and updates product records in Supabase
with enriched data: dimensions verification, proportions, visual
descriptions, material analysis, colour analysis, style classification,
category verification, and image-quality metadata.
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from google import genai

from src.config import GEMINI_API_KEY, PRODUCT_VISION_PROMPT
from src.storage.r2_client import get_r2_image_bytes, resize_for_prompt
from src.storage.supabase_client import (
    get_product_by_id,
    get_unenriched_products,
    update_product,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini client
# ---------------------------------------------------------------------------

_gemini_client = genai.Client(api_key=GEMINI_API_KEY)

GEMINI_MODEL = "gemini-2.5-flash"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Mapping: category keyword -> list of suitable rooms
_CATEGORY_ROOM_MAP: dict[str, list[str]] = {
    "sofa": ["living_room", "lounge"],
    "couch": ["living_room", "lounge"],
    "armchair": ["living_room", "lounge", "bedroom"],
    "chair": ["dining_room", "office", "living_room"],
    "dining_chair": ["dining_room", "kitchen"],
    "office_chair": ["office"],
    "bed": ["bedroom"],
    "mattress": ["bedroom"],
    "nightstand": ["bedroom"],
    "bedside": ["bedroom"],
    "wardrobe": ["bedroom", "hallway"],
    "closet": ["bedroom", "hallway"],
    "dresser": ["bedroom"],
    "chest": ["bedroom", "living_room"],
    "desk": ["office", "bedroom"],
    "bookshelf": ["office", "living_room", "bedroom"],
    "bookcase": ["office", "living_room", "bedroom"],
    "shelf": ["living_room", "office", "bedroom", "kitchen"],
    "table": ["dining_room", "living_room", "kitchen"],
    "dining_table": ["dining_room", "kitchen"],
    "coffee_table": ["living_room", "lounge"],
    "side_table": ["living_room", "bedroom"],
    "console": ["hallway", "living_room"],
    "tv_stand": ["living_room"],
    "media": ["living_room"],
    "cabinet": ["living_room", "dining_room", "kitchen"],
    "sideboard": ["dining_room", "living_room"],
    "buffet": ["dining_room"],
    "mirror": ["bedroom", "hallway", "bathroom"],
    "lamp": ["living_room", "bedroom", "office"],
    "lighting": ["living_room", "bedroom", "office", "dining_room"],
    "rug": ["living_room", "bedroom", "dining_room"],
    "carpet": ["living_room", "bedroom"],
    "curtain": ["living_room", "bedroom", "dining_room"],
    "kitchen": ["kitchen"],
    "bathroom": ["bathroom"],
    "outdoor": ["outdoor", "balcony", "garden"],
    "garden": ["outdoor", "garden"],
    "kids": ["kids_room"],
    "child": ["kids_room"],
    "baby": ["kids_room", "nursery"],
}

# Style keywords that indicate luxury / premium
_LUXURY_KEYWORDS = {
    "luxury",
    "art_deco",
    "art deco",
    "designer",
    "bespoke",
    "premium",
    "haute",
    "couture",
    "opulent",
    "glamour",
    "glamorous",
    "high-end",
    "high_end",
    "exclusive",
}


def _detect_mime_type(image_bytes: bytes) -> str:
    """Detect MIME type from the magic bytes of an image."""
    if image_bytes[:2] == b"\xff\xd8":
        return "image/jpeg"
    if image_bytes[:4] == b"\x89PNG":
        return "image/png"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    if image_bytes[:4] == b"GIF8":
        return "image/gif"
    if image_bytes[:4] == b"II\x2a\x00" or image_bytes[:4] == b"MM\x00\x2a":
        return "image/tiff"
    # Fallback – JPEG is the safest default for furniture photos
    return "image/jpeg"


def _strip_code_fencing(text: str) -> str:
    """Remove markdown code fencing (```json ... ```) from Gemini responses."""
    text = text.strip()
    if text.startswith("```"):
        # Remove opening fence (optionally with language tag)
        first_newline = text.index("\n") if "\n" in text else len(text)
        text = text[first_newline + 1 :]
    if text.endswith("```"):
        text = text[: -3]
    return text.strip()


def _compute_luxury_score(style_classification: Any) -> float:
    """
    Derive a 0-1 luxury score from the style_classification section.

    Accepts either a list of {style, confidence} dicts or a dict keyed by
    style name with confidence values.
    """
    if not style_classification:
        return 0.0

    scores: list[float] = []

    if isinstance(style_classification, list):
        for entry in style_classification:
            style_name = str(entry.get("style", "")).lower()
            confidence = float(entry.get("confidence", 0))
            if any(kw in style_name for kw in _LUXURY_KEYWORDS):
                scores.append(confidence)
    elif isinstance(style_classification, dict):
        for style_name, value in style_classification.items():
            name_lower = style_name.lower()
            if any(kw in name_lower for kw in _LUXURY_KEYWORDS):
                conf = float(value) if isinstance(value, (int, float)) else float(
                    value.get("confidence", 0) if isinstance(value, dict) else 0
                )
                scores.append(conf)

    if not scores:
        return 0.0

    # Average of matching luxury-style confidences, clamped to [0, 1]
    return round(min(max(sum(scores) / len(scores), 0.0), 1.0), 3)


def _derive_suitable_rooms(
    category: str | None,
    subcategory: str | None,
    style_classification: Any,
) -> list[str]:
    """Map product category / subcategory to a list of suitable room types."""
    rooms: set[str] = set()
    tokens: list[str] = []

    if category:
        tokens.append(category.lower().replace(" ", "_"))
    if subcategory:
        tokens.append(subcategory.lower().replace(" ", "_"))

    for token in tokens:
        for keyword, room_list in _CATEGORY_ROOM_MAP.items():
            if keyword in token:
                rooms.update(room_list)

    # Fallback: if nothing matched, provide a sensible default
    if not rooms:
        rooms.add("living_room")

    return sorted(rooms)


def _download_image_from_url(url: str) -> bytes:
    """Download image bytes from an HTTP(S) URL."""
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.content


# ---------------------------------------------------------------------------
# Core enrichment
# ---------------------------------------------------------------------------


def enrich_product(product: dict) -> dict | None:
    """
    Enrich a single product with AI vision analysis.

    Returns the dict of updates applied on success, or None on failure.
    """
    product_id: str = product.get("id", "unknown")
    product_name: str = product.get("name", product_id)

    try:
        # ----- 1. Obtain image bytes -----------------------------------
        image_bytes: bytes | None = None
        r2_key: str | None = product.get("r2_main_image_key")
        main_image_url: str | None = product.get("main_image_url")

        if r2_key:
            try:
                image_bytes = get_r2_image_bytes(r2_key)
            except Exception as exc:
                logger.warning(
                    "[vision] R2 download failed for %s, falling back to URL: %s",
                    product_name,
                    exc,
                )

        if image_bytes is None and main_image_url:
            try:
                image_bytes = _download_image_from_url(main_image_url)
            except Exception as exc:
                logger.error(
                    "[vision] URL download also failed for %s: %s",
                    product_name,
                    exc,
                )
                return None

        if image_bytes is None:
            logger.warning(
                "[vision] No image available for %s — skipping.", product_name
            )
            return None

        # ----- 2. Resize for prompt -----------------------------------
        image_bytes = resize_for_prompt(image_bytes, max_size=512)

        # ----- 3. Call Gemini Flash ------------------------------------
        mime_type = _detect_mime_type(image_bytes)

        response = _gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                {
                    "parts": [
                        {"text": PRODUCT_VISION_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64.b64encode(image_bytes).decode("utf-8"),
                            },
                        },
                    ],
                }
            ],
        )

        raw_text = response.text
        if not raw_text:
            logger.error(
                "[vision] Empty Gemini response for %s", product_name
            )
            return None

        # ----- 4. Parse JSON response ---------------------------------
        cleaned = _strip_code_fencing(raw_text)
        try:
            vision_data: dict = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error(
                "[vision] JSON parse error for %s: %s\nRaw text: %s",
                product_name,
                exc,
                raw_text[:500],
            )
            return None

        # ----- 5. Extract & flatten fields ----------------------------
        dimensions_estimate = vision_data.get("dimensions_estimate", {}) or {}
        proportion_ratios = vision_data.get("proportion_ratios", {}) or {}
        color_analysis = vision_data.get("color_analysis", {}) or {}
        style_classification = vision_data.get("style_classification")
        category_verification = vision_data.get("category_verification", {}) or {}
        image_quality = vision_data.get("image_quality", {}) or {}

        primary_color = color_analysis.get("primary_color", {}) or {}
        dim_confidence = str(dimensions_estimate.get("confidence", "")).lower()

        updates: dict[str, Any] = {
            "visual_description": vision_data.get("visual_description", ""),
            "dimensions_source": (
                "ai_verified" if dim_confidence in ("high", "medium") else "ai_estimated"
            ),
            "dimensions_confidence": dim_confidence or None,
            "proportion_w_h": proportion_ratios.get("width_to_height"),
            "proportion_w_d": proportion_ratios.get("width_to_depth"),
            "color_hex": primary_color.get("hex_estimate"),
            "color_tone": color_analysis.get("overall_tone"),
            "luxury_score": _compute_luxury_score(style_classification),
            "ai_category": category_verification.get("suggested_category"),
            "ai_subcategory": category_verification.get("suggested_subcategory"),
            "suitable_rooms": _derive_suitable_rooms(
                category_verification.get("suggested_category"),
                category_verification.get("suggested_subcategory"),
                style_classification,
            ),
            "image_type": image_quality.get("background"),
            "image_usable": image_quality.get("suitable_for_rendering"),
            "vision_data": vision_data,
            "vision_enriched": True,
            "vision_enriched_at": "now()",
        }

        # ----- 6. Backfill missing dimensions -------------------------
        if dim_confidence in ("high", "medium"):
            estimated = dimensions_estimate.get("estimated", {}) or {}
            # Also support flat keys like width_cm directly in dimensions_estimate
            est_w = estimated.get("width_cm") or dimensions_estimate.get("width_cm")
            est_h = estimated.get("height_cm") or dimensions_estimate.get("height_cm")
            est_d = estimated.get("depth_cm") or dimensions_estimate.get("depth_cm")

            if est_w and not product.get("width_cm"):
                updates["width_cm"] = float(est_w)
            if est_h and not product.get("height_cm"):
                updates["height_cm"] = float(est_h)
            if est_d and not product.get("depth_cm"):
                updates["depth_cm"] = float(est_d)

        # ----- 7. Persist to Supabase ---------------------------------
        update_product(product_id, updates)
        logger.info("[vision] Enriched %s successfully.", product_name)
        return updates

    except Exception as exc:
        logger.error(
            "[vision] Unexpected error enriching %s: %s", product_name, exc,
            exc_info=True,
        )
        return None


# ---------------------------------------------------------------------------
# Batch enrichment
# ---------------------------------------------------------------------------


def enrich_all_unenriched(limit: int = 100) -> dict:
    """
    Enrich all unenriched products up to *limit*.

    Returns stats: {total, enriched, failed, skipped}.
    """
    products = get_unenriched_products(limit=limit)
    total = len(products)
    enriched = 0
    failed = 0
    skipped = 0

    print(f"[vision] Found {total} unenriched product(s) to process.")

    for i, product in enumerate(products, start=1):
        product_name = product.get("name", product.get("id", "?"))
        print(f"[vision] Enriching {i}/{total}: {product_name}")

        # Skip products without any image source
        if not product.get("r2_main_image_key") and not product.get("main_image_url"):
            print(f"[vision] Skipped (no image): {product_name}")
            skipped += 1
            continue

        result = enrich_product(product)

        if result is not None:
            enriched += 1
        else:
            failed += 1

        # Rate-limit: 1 second between Gemini calls (free-tier limit)
        if i < total:
            time.sleep(1.0)

    stats = {
        "total": total,
        "enriched": enriched,
        "failed": failed,
        "skipped": skipped,
    }

    print(f"\n[vision] Batch complete: {json.dumps(stats, indent=2)}")
    return stats


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="AI Vision Enrichment Service for Planche.bg products",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Enrich all unenriched products",
    )
    parser.add_argument(
        "--product-id",
        type=str,
        default=None,
        help="Enrich a single product by ID",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of products to enrich in batch mode (default: 100)",
    )

    args = parser.parse_args()

    if args.product_id:
        product = get_product_by_id(args.product_id)
        if product is None:
            print(f"[vision] Product not found: {args.product_id}")
            raise SystemExit(1)

        print(f"[vision] Enriching single product: {product.get('name', args.product_id)}")
        result = enrich_product(product)
        if result:
            print(f"[vision] Success. Updated fields: {list(result.keys())}")
        else:
            print("[vision] Enrichment failed.")
            raise SystemExit(1)

    elif args.all:
        stats = enrich_all_unenriched(limit=args.limit)
        if stats["failed"] > 0:
            raise SystemExit(1)

    else:
        parser.print_help()
        raise SystemExit(0)
