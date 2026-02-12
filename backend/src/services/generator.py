"""
Room design generator service.

Takes a sketch image, room analysis data, matched products, and style
preferences, then generates a photorealistic room render using Gemini's
image-generation capability.  Builds a multimodal prompt containing the
sketch, product reference photos, and detailed rendering instructions.
"""

from __future__ import annotations

import base64
import uuid
from typing import Any

from google import genai
from google.genai import types as genai_types

from src.config import GEMINI_API_KEY, R2_PUBLIC_URL
from src.models.design import BuyLink, DesignResult, ProductImageForRender
from src.storage.r2_client import (
    get_image_url,
    get_r2_image_bytes,
    resize_for_prompt,
    upload_image,
)
from src.storage.supabase_client import get_design, save_design, update_design

# ---------------------------------------------------------------------------
# Gemini client
# ---------------------------------------------------------------------------
_gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# Image-generation model (see research.md — model ID may be updated later)
_IMAGE_MODEL = "gemini-3-pro-image-preview"

# Maximum number of product images included in the prompt to stay within
# token / context limits.
_MAX_PRODUCT_IMAGES = 8

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mime_to_ext(mime_type: str) -> str:
    """Return a file extension (with leading dot) for a given MIME type."""
    if mime_type == "image/jpeg":
        return ".jpg"
    if mime_type == "image/png":
        return ".png"
    return ".webp"


def _build_product_text(product: ProductImageForRender, index: int) -> str:
    """Build the descriptive text block for a single product."""
    lines: list[str] = [f"Product {index + 1} — Slot: {product.slot}"]

    if product.visual_description:
        lines.append(f"  Description: {product.visual_description}")

    dims: list[str] = []
    if product.width_cm is not None:
        dims.append(f"W {product.width_cm} cm")
    if product.height_cm is not None:
        dims.append(f"H {product.height_cm} cm")
    if product.depth_cm is not None:
        dims.append(f"D {product.depth_cm} cm")
    if dims:
        lines.append(f"  Dimensions: {', '.join(dims)}")

    if product.color:
        lines.append(f"  Color: {product.color}")
    if product.primary_material:
        lines.append(f"  Material: {product.primary_material}")

    lines.append(f"  Place this product in the room in the '{product.slot}' position.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def generate_room_design(
    sketch_bytes: bytes,
    sketch_mime: str,
    room_data: dict[str, Any],
    product_images: list[dict[str, Any]],
    buy_links: list[dict[str, Any]],
    style: str | None,
    tier: str,
    budget_spent: float,
    budget_remaining: float,
) -> DesignResult:
    """Generate a photorealistic room render and persist the result.

    Parameters
    ----------
    sketch_bytes:
        Raw bytes of the uploaded sketch image.
    sketch_mime:
        MIME type of the sketch (e.g. ``image/jpeg``).
    room_data:
        Room analysis dictionary (dimensions, features, etc.).
    product_images:
        List of product-image dicts matching ``ProductImageForRender`` fields.
    buy_links:
        List of buy-link dicts matching ``BuyLink`` fields.
    style:
        Optional style keyword (e.g. "scandinavian", "industrial").
    tier:
        Product quality tier (e.g. "budget", "mid", "premium").
    budget_spent:
        Total money spent on matched products.
    budget_remaining:
        Remaining budget after purchases.

    Returns
    -------
    DesignResult
        Contains design_id, render URL, sketch URL, products, and budget info.
    """

    # ------------------------------------------------------------------
    # 1.  Unique design ID
    # ------------------------------------------------------------------
    design_id: str = uuid.uuid4().hex[:12]
    print(f"[generator] Starting design {design_id}")

    # ------------------------------------------------------------------
    # 2.  Upload the sketch to R2
    # ------------------------------------------------------------------
    sketch_ext = _mime_to_ext(sketch_mime)
    sketch_r2_key = f"sketches/{design_id}/sketch{sketch_ext}"
    sketch_content_type = sketch_mime if sketch_mime.startswith("image/") else "image/webp"
    sketch_url = upload_image(sketch_bytes, sketch_r2_key, content_type=sketch_content_type)
    print(f"[generator] Sketch uploaded to R2: {sketch_r2_key}")

    # ------------------------------------------------------------------
    # 3.  Parse product images into Pydantic models
    # ------------------------------------------------------------------
    products: list[ProductImageForRender] = []
    for raw in product_images[:_MAX_PRODUCT_IMAGES]:
        try:
            products.append(ProductImageForRender(**raw))
        except Exception as exc:
            print(f"[generator] Skipping invalid product entry: {exc}")

    print(f"[generator] Building prompt with {len(products)} product images...")

    # ------------------------------------------------------------------
    # 4.  Build multimodal prompt parts
    # ------------------------------------------------------------------
    parts: list[genai_types.Part] = []

    # Part 1 — sketch image (inline base64)
    sketch_b64 = base64.b64encode(sketch_bytes).decode("utf-8")
    parts.append(
        genai_types.Part(
            inline_data=genai_types.Blob(
                mime_type=sketch_mime,
                data=sketch_b64,
            )
        )
    )

    # Part 2 — text intro
    parts.append(
        genai_types.Part(
            text=(
                "You are an expert interior designer. Below is a rough floor "
                "plan sketch of a room. Generate a PHOTOREALISTIC render of "
                "this room furnished with the REAL products shown below."
            )
        )
    )

    # Parts 3+ — product images + descriptions
    for idx, product in enumerate(products):
        # Fetch and resize product reference image from R2
        try:
            raw_img = get_r2_image_bytes(product.r2_key)
            resized_img = resize_for_prompt(raw_img, max_size=512)
            img_b64 = base64.b64encode(resized_img).decode("utf-8")

            # Inline product image
            parts.append(
                genai_types.Part(
                    inline_data=genai_types.Blob(
                        mime_type="image/webp",
                        data=img_b64,
                    )
                )
            )
        except Exception as exc:
            print(
                f"[generator] Could not fetch image for product "
                f"'{product.slot}' (r2_key={product.r2_key}): {exc}. "
                f"Skipping image, keeping text description."
            )

        # Descriptive text for this product
        parts.append(
            genai_types.Part(text=_build_product_text(product, idx))
        )

    # Final part — rendering instructions
    room_dims = room_data.get("dimensions", {})
    room_width = room_dims.get("width_m", "unknown")
    room_length = room_dims.get("length_m", "unknown")
    room_height = room_dims.get("height_m", "unknown")

    rendering_instructions = (
        f"Room dimensions: {room_width} m (W) x {room_length} m (L) x {room_height} m (H)\n"
        f"Style: {style or 'not specified'}, Tier: {tier}\n"
        "\n"
        "Create a photorealistic interior render showing all the furniture "
        "products naturally placed in the room.\n"
        "Match the products' actual appearance, colors, and proportions as "
        "closely as possible.\n"
        "Use warm, natural lighting. Show the room from a wide-angle perspective.\n"
        "Do NOT add any text, labels, or watermarks to the image."
    )
    parts.append(genai_types.Part(text=rendering_instructions))

    # ------------------------------------------------------------------
    # 5.  Call Gemini image generation
    # ------------------------------------------------------------------
    print(f"[generator] Generating render for design {design_id}...")

    config = genai_types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
    )

    response = _gemini_client.models.generate_content(
        model=_IMAGE_MODEL,
        contents=genai_types.Content(parts=parts),
        config=config,
    )

    # ------------------------------------------------------------------
    # 6.  Extract generated image from the response
    # ------------------------------------------------------------------
    render_bytes: bytes | None = None
    render_mime: str = "image/webp"

    if response.candidates:
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                render_mime = part.inline_data.mime_type or "image/webp"
                render_bytes = base64.b64decode(part.inline_data.data)
                break

    if render_bytes is None:
        raise RuntimeError(
            f"[generator] Gemini returned no image for design {design_id}. "
            "The response did not contain any inline_data parts with image content."
        )

    # ------------------------------------------------------------------
    # 7.  Upload render to R2
    # ------------------------------------------------------------------
    render_r2_key = f"renders/{design_id}/render_v1.webp"
    render_url = upload_image(render_bytes, render_r2_key, content_type="image/webp")
    print(f"[generator] Render uploaded to R2: {render_r2_key}")

    # ------------------------------------------------------------------
    # 8.  Persist design record in Supabase
    # ------------------------------------------------------------------
    design_record: dict[str, Any] = {
        "id": design_id,
        "sketch_r2_key": sketch_r2_key,
        "room_analysis": room_data,
        "tier": tier,
        "style": style,
        "budget_eur": budget_spent + budget_remaining,
        "matched_products": product_images,
        "budget_spent": budget_spent,
        "budget_remaining": budget_remaining,
        "render_r2_key": render_r2_key,
    }
    save_design(design_record)
    print(f"[generator] Design {design_id} saved to Supabase")

    # ------------------------------------------------------------------
    # 9.  Build and return DesignResult
    # ------------------------------------------------------------------
    parsed_buy_links: list[BuyLink] = []
    for bl in buy_links:
        try:
            parsed_buy_links.append(BuyLink(**bl))
        except Exception as exc:
            print(f"[generator] Skipping invalid buy link: {exc}")

    return DesignResult(
        design_id=design_id,
        render_url=render_url,
        sketch_url=sketch_url,
        products=parsed_buy_links,
        budget_spent=budget_spent,
        budget_remaining=budget_remaining,
    )


# ---------------------------------------------------------------------------
# Product Swap
# ---------------------------------------------------------------------------

def swap_product_in_design(
    design_id: str,
    slot: str,
    new_product: dict,
) -> dict:
    """
    Swap one product in an existing design and re-render.

    Steps:
        1. Load existing design from Supabase.
        2. Fetch current render from R2 as reference.
        3. Fetch new product image from R2.
        4. Build swap prompt with current render + new product image.
        5. Generate new render via Gemini.
        6. Upload new render to R2 as render_v{N}.
        7. Update design in Supabase.
        8. Return SwapResult-compatible dict.
    """

    # ------------------------------------------------------------------
    # 1.  Load existing design from Supabase
    # ------------------------------------------------------------------
    design = get_design(design_id)
    if design is None:
        raise ValueError(f"Design '{design_id}' not found in Supabase.")

    print(f"[swap] Loaded design {design_id}")

    # ------------------------------------------------------------------
    # 2.  Fetch current render from R2 as reference
    # ------------------------------------------------------------------
    current_render_key = design["render_r2_key"]
    current_render_bytes = get_r2_image_bytes(current_render_key)
    current_render_resized = resize_for_prompt(current_render_bytes, max_size=512)
    print(f"[swap] Fetched current render: {current_render_key}")

    # ------------------------------------------------------------------
    # 3.  Fetch new product image from R2
    # ------------------------------------------------------------------
    new_product_r2_key = new_product.get("r2_main_image_key")
    if not new_product_r2_key:
        raise ValueError("new_product must include 'r2_main_image_key'.")

    new_product_bytes = get_r2_image_bytes(new_product_r2_key)
    new_product_resized = resize_for_prompt(new_product_bytes, max_size=512)
    print(f"[swap] Fetched new product image: {new_product_r2_key}")

    # ------------------------------------------------------------------
    # 4.  Build multimodal swap prompt
    # ------------------------------------------------------------------
    parts: list[genai_types.Part] = []

    # Part 1 — current render image (inline base64)
    render_b64 = base64.b64encode(current_render_resized).decode("utf-8")
    parts.append(
        genai_types.Part(
            inline_data=genai_types.Blob(
                mime_type="image/webp",
                data=render_b64,
            )
        )
    )

    # Part 2 — text explaining the swap intent
    parts.append(
        genai_types.Part(
            text=(
                f"This is the current room render. I want to SWAP the "
                f"{slot} furniture piece."
            )
        )
    )

    # Part 3 — new product image (inline base64)
    product_b64 = base64.b64encode(new_product_resized).decode("utf-8")
    parts.append(
        genai_types.Part(
            inline_data=genai_types.Blob(
                mime_type="image/webp",
                data=product_b64,
            )
        )
    )

    # Part 4 — new product description
    desc_lines: list[str] = ["New product details:"]
    if new_product.get("visual_description"):
        desc_lines.append(f"  Description: {new_product['visual_description']}")
    if new_product.get("dimensions"):
        desc_lines.append(f"  Dimensions: {new_product['dimensions']}")
    if new_product.get("color"):
        desc_lines.append(f"  Color: {new_product['color']}")
    if new_product.get("material"):
        desc_lines.append(f"  Material: {new_product['material']}")
    parts.append(genai_types.Part(text="\n".join(desc_lines)))

    # Part 5 — swap instructions
    parts.append(
        genai_types.Part(
            text=(
                f"Replace ONLY the {slot} in the room. Keep everything else "
                f"identical - same camera angle, same lighting, same walls, "
                f"same other furniture. Only change the {slot} to match the "
                f"new product shown above."
            )
        )
    )

    # ------------------------------------------------------------------
    # 5.  Call Gemini image generation
    # ------------------------------------------------------------------
    print(f"[swap] Generating swap render for design {design_id}, slot '{slot}'...")

    config = genai_types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
    )

    response = _gemini_client.models.generate_content(
        model=_IMAGE_MODEL,
        contents=genai_types.Content(parts=parts),
        config=config,
    )

    # ------------------------------------------------------------------
    # 6.  Extract generated image from the response
    # ------------------------------------------------------------------
    render_bytes: bytes | None = None

    if response.candidates:
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                render_bytes = base64.b64decode(part.inline_data.data)
                break

    if render_bytes is None:
        raise RuntimeError(
            f"[swap] Gemini returned no image for swap on design {design_id}. "
            "The response did not contain any inline_data parts with image content."
        )

    # ------------------------------------------------------------------
    # 7.  Determine render version and upload to R2
    # ------------------------------------------------------------------
    # Simple versioning: parse current key to find version, increment by 1
    current_key = design["render_r2_key"]
    try:
        # Expected format: renders/{design_id}/render_v{N}.webp
        version_str = current_key.rsplit("_v", 1)[-1].replace(".webp", "")
        current_version = int(version_str)
    except (ValueError, IndexError):
        current_version = 1

    new_version = current_version + 1
    new_render_key = f"renders/{design_id}/render_v{new_version}.webp"
    new_render_url = upload_image(render_bytes, new_render_key, content_type="image/webp")
    print(f"[swap] New render uploaded to R2: {new_render_key}")

    # ------------------------------------------------------------------
    # 8.  Update design in Supabase with new render key
    # ------------------------------------------------------------------
    update_design(design_id, {"render_r2_key": new_render_key})
    print(f"[swap] Design {design_id} updated in Supabase with new render key")

    # ------------------------------------------------------------------
    # 9.  Return SwapResult-compatible dict
    # ------------------------------------------------------------------
    return {
        "design_id": design_id,
        "render_url": new_render_url,
        "swapped_slot": slot,
        "new_product": new_product,
    }
