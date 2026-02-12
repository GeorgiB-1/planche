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


def _build_product_text(
    product: ProductImageForRender,
    index: int,
    zone_hint: str | None = None,
) -> str:
    """Build the descriptive text block for a single product."""
    slot_label = product.slot.replace("_", " ").title()
    lines: list[str] = [f"PRODUCT {index + 1} — {slot_label}"]

    if product.visual_description:
        lines.append(f"  Visual appearance: {product.visual_description}")

    dims: list[str] = []
    if product.width_cm is not None:
        dims.append(f"W {product.width_cm} cm")
    if product.height_cm is not None:
        dims.append(f"H {product.height_cm} cm")
    if product.depth_cm is not None:
        dims.append(f"D {product.depth_cm} cm")
    if dims:
        lines.append(f"  Real-world dimensions: {', '.join(dims)}")

    if product.color:
        lines.append(f"  Color: {product.color}")
    if product.primary_material:
        lines.append(f"  Material: {product.primary_material}")

    placement = f"  Placement: use this EXACT product for the '{slot_label}' slot in the room."
    if zone_hint:
        placement += f" Position it {zone_hint}."
    lines.append(placement)

    return "\n".join(lines)


def _build_room_context(room_data: dict[str, Any]) -> str:
    """Build a textual description of the room from the analysis data."""
    room_type = room_data.get("type", "room").replace("_", " ")
    width_cm = room_data.get("estimated_width_cm", 0)
    depth_cm = room_data.get("estimated_depth_cm", 0)
    area_sqm = room_data.get("estimated_area_sqm", 0)

    lines: list[str] = [f"Room type: {room_type}"]

    if width_cm and depth_cm:
        lines.append(
            f"Dimensions: {width_cm / 100:.1f} m wide x {depth_cm / 100:.1f} m deep"
            f" ({area_sqm:.1f} sqm)"
        )

    # Windows
    features = room_data.get("features", {})
    windows = features.get("windows", [])
    if windows:
        win_descs = []
        for w in windows:
            desc = f"{w.get('wall', '?')} wall"
            if w.get("width_cm"):
                desc += f" ({w['width_cm']:.0f} cm wide)"
            win_descs.append(desc)
        lines.append(f"Windows: {', '.join(win_descs)}")

    # Doors
    doors = features.get("doors", [])
    if doors:
        door_descs = []
        for d in doors:
            desc = f"{d.get('wall', '?')} wall"
            if d.get("type"):
                desc += f" ({d['type']})"
            door_descs.append(desc)
        lines.append(f"Doors: {', '.join(door_descs)}")

    if features.get("balcony_access"):
        lines.append("Has balcony access")
    if features.get("fireplace"):
        lines.append("Has fireplace")

    # Furniture zones
    zones = room_data.get("furniture_zones", [])
    if zones:
        zone_descs = []
        for z in zones:
            zone_descs.append(f"{z.get('zone', '?')} ({z.get('position', '?')})")
        lines.append(f"Furniture zones: {', '.join(zone_descs)}")

    return "\n".join(lines)


def _build_scene_context(scene_data: dict[str, Any] | None) -> str:
    """Format scene description data into structured text for the prompt."""
    if not scene_data:
        return ""

    lines: list[str] = []

    # Camera info
    cam = scene_data.get("camera", {})
    if cam:
        lines.append("CAMERA:")
        lines.append(f"  Perspective: {cam.get('perspective_type', 'two-point')}")
        lines.append(f"  Eye level: {cam.get('eye_level', 'standing')} ({cam.get('eye_height_estimate', '~160 cm')})")
        lines.append(f"  Position: {cam.get('camera_position', 'room entrance')}")
        lines.append(f"  Direction: {cam.get('camera_direction', 'looking into room')}")
        h_angle = cam.get("horizontal_angle_deg", 0)
        v_tilt = cam.get("vertical_tilt_deg", 0)
        lines.append(f"  Horizontal angle: {h_angle}° | Vertical tilt: {v_tilt}°")
        lines.append(f"  FOV: {cam.get('fov_estimate', 'normal (~60°)')}")
        lines.append(f"  Distance: {cam.get('distance_to_subject', 'medium')}")

    # Visible surfaces
    surfaces = scene_data.get("visible_surfaces", {})
    if surfaces:
        lines.append("VISIBLE SURFACES:")
        if surfaces.get("floor_visible"):
            lines.append(f"  Floor: {surfaces.get('floor_coverage_pct', 0):.0f}% visible")
        if surfaces.get("ceiling_visible"):
            lines.append(f"  Ceiling: {surfaces.get('ceiling_coverage_pct', 0):.0f}% visible")
        for wall in surfaces.get("walls", []):
            feats = ", ".join(wall.get("features", []))
            feat_str = f" [{feats}]" if feats else ""
            lines.append(f"  {wall.get('wall_id', 'wall')}: {wall.get('coverage_pct', 0):.0f}%{feat_str}")

    # Objects
    objects = scene_data.get("objects", [])
    if objects:
        obj_parts = []
        for obj in objects:
            obj_parts.append(
                f"{obj.get('name', '?')} [{obj.get('depth_zone', '?')}, "
                f"{obj.get('horizontal_position', '?')}]"
            )
        lines.append(f"OBJECTS IN SCENE: {'; '.join(obj_parts)}")

    # Spatial relationships (cap at 10)
    rels = scene_data.get("spatial_relationships", [])[:10]
    if rels:
        rel_parts = []
        for r in rels:
            rel_parts.append(
                f"{r.get('object_a', '?')} {r.get('relationship', '?')} {r.get('object_b', '?')}"
            )
        lines.append(f"KEY SPATIAL RELATIONSHIPS: {'; '.join(rel_parts)}")

    # Generation directive — most critical
    directive = scene_data.get("generation_directive", "")
    if directive:
        lines.append("")
        lines.append(f"*** CAMERA DIRECTIVE: {directive} ***")

    return "\n".join(lines)


def _find_zone_hint(slot: str, room_data: dict[str, Any]) -> str | None:
    """Try to find a placement hint for a product slot from furniture zones."""
    zones = room_data.get("furniture_zones", [])
    slot_lower = slot.lower().replace("_", " ")
    for z in zones:
        zone_name = (z.get("zone") or "").lower().replace("_", " ")
        if slot_lower in zone_name or zone_name in slot_lower:
            return z.get("position")
    # Check usable walls
    walls = room_data.get("usable_walls", [])
    for w in walls:
        suitable = [s.lower() for s in (w.get("suitable_for") or [])]
        if slot_lower in suitable or any(slot_lower in s for s in suitable):
            return f"against the {w.get('wall', '')} wall"
    return None


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
    scene_description: dict[str, Any] | None = None,
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

    # Part 2 — room context + sketch instructions
    room_type_label = room_data.get("type", "room").replace("_", " ")
    room_context = _build_room_context(room_data)
    product_count = len(products)

    scene_context = _build_scene_context(scene_description)

    scene_section = ""
    if scene_context:
        scene_section = f"SCENE & CAMERA ANALYSIS:\n{scene_context}\n\n"

    intro_text = (
        f"You are an expert interior designer and photorealistic renderer.\n\n"
        f"ABOVE IMAGE: A hand-drawn interior design sketch of a "
        f"{room_type_label}.\n\n"
        f"ROOM ANALYSIS:\n{room_context}\n\n"
        f"{scene_section}"
        f"YOUR TASK: Generate a PHOTOREALISTIC render that FAITHFULLY "
        f"reproduces the EXACT layout, furniture placement, camera angle, "
        f"and proportions shown in the sketch.\n\n"
        f"ITEM COUNT RULE: The sketch contains a SPECIFIC set of items. "
        f"Count every piece of furniture, light fixture, plant, and decorative "
        f"object in the sketch. The render MUST contain EXACTLY the same "
        f"number and type of items — no more, no less. Do NOT add extra "
        f"furniture, plants, poufs, shelves, vases, or decorative objects "
        f"that are not visible in the sketch.\n\n"
        f"CRITICAL: You MUST use the {product_count} REAL product(s) shown "
        f"below as REPLACEMENTS for the corresponding items in the sketch. "
        f"Match each product's appearance, color, material, and proportions "
        f"as closely as possible. If a catalogue product does not have a "
        f"corresponding item in the sketch, DO NOT place it — skip it. "
        f"Items in the sketch that have no matching catalogue product should "
        f"be rendered as generic furniture matching the sketch's style.\n\n"
        f"The following are the REAL products to incorporate:"
    )
    parts.append(genai_types.Part(text=intro_text))

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

        # Descriptive text for this product with zone placement hints
        zone_hint = _find_zone_hint(product.slot, room_data)
        parts.append(
            genai_types.Part(
                text=_build_product_text(product, idx, zone_hint=zone_hint)
            )
        )

    # Final part — rendering instructions
    style_label = style.replace("_", " ").title() if style else "not specified"

    # Build camera directive from scene description if available
    camera_directive = ""
    if scene_description:
        directive = scene_description.get("generation_directive", "")
        if directive:
            camera_directive = directive

    camera_instruction = (
        f"1. CAMERA & PERSPECTIVE FIDELITY (MOST IMPORTANT): "
    )
    if camera_directive:
        camera_instruction += (
            f"{camera_directive} "
            f"This is the MOST CRITICAL instruction — the rendered viewpoint "
            f"MUST match the sketch's camera angle exactly."
        )
    else:
        camera_instruction += (
            f"Reproduce the sketch's exact camera angle and perspective. "
            f"The rendered viewpoint MUST match the sketch."
        )

    rendering_instructions = (
        f"\n--- RENDERING INSTRUCTIONS ---\n\n"
        f"Style: {style_label} | Quality tier: {tier}\n\n"
        f"{camera_instruction}\n\n"
        f"2. LAYOUT FIDELITY: Reproduce the sketch's exact room layout — "
        f"same wall positions, same proportions. The sketch is your primary "
        f"spatial reference.\n\n"
        f"3. PRODUCT FIDELITY: Each product image above shows a REAL "
        f"furniture item. Render each one faithfully — same shape, color, "
        f"material, and texture. Do NOT substitute with generic furniture. "
        f"Scale each product correctly using its real-world dimensions.\n\n"
        f"4. PLACEMENT: Position the products in their designated slots as "
        f"shown in the sketch layout. Respect the room's usable walls and "
        f"furniture zones.\n\n"
        f"5. ENVIRONMENT: Use warm, natural lighting. Render realistic "
        f"flooring, wall finishes, and ceiling that match the {style_label} "
        f"style. Do NOT add decorative staging — no extra plants, vases, "
        f"poufs, candles, books, trays, or accessories unless they are "
        f"clearly visible in the original sketch.\n\n"
        f"6. QUALITY: Photorealistic quality — real materials, natural "
        f"shadows, accurate reflections.\n\n"
        f"7. STRICT ITEM FIDELITY: The render must contain ONLY the items "
        f"visible in the sketch. Do NOT invent, add, or hallucinate extra "
        f"furniture, decor, plants, or objects. If the sketch shows 1 plant, "
        f"render exactly 1 plant. If the sketch shows 3 pendant lights, "
        f"render exactly 3 pendant lights. Count items carefully.\n\n"
        f"8. RESTRICTIONS: Do NOT add any text, labels, dimensions, "
        f"watermarks, or annotations. Do NOT change the room type or "
        f"fundamental layout from the sketch."
    )
    parts.append(genai_types.Part(text=rendering_instructions))

    # ------------------------------------------------------------------
    # 5.  Call Gemini image generation
    # ------------------------------------------------------------------
    print(f"[generator] Generating render for design {design_id}...")

    config = genai_types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
        image_config=genai_types.ImageConfig(
            aspect_ratio="16:9",
            image_size="2K",
        ),
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
                raw_data = part.inline_data.data
                # google-genai SDK returns raw bytes; fall back to b64 decode
                # only if the response is a string (older SDK versions).
                if isinstance(raw_data, bytes):
                    render_bytes = raw_data
                else:
                    render_bytes = base64.b64decode(raw_data)
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
        "scene_description": scene_description,
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
# Iterative Refinement
# ---------------------------------------------------------------------------

def _is_camera_change(instruction: str) -> bool:
    """Detect whether the user instruction involves a camera/angle change."""
    lower = instruction.lower()
    camera_keywords = [
        "angle", "camera", "perspective", "rotate", "turn", "degree",
        "градус", "ъгъл", "завърт", "перспектив", "камер",
        "left", "right", "up", "down", "наляво", "надясно",
        "bird", "eye", "overhead", "отгоре", "отдолу",
        "closer", "further", "zoom", "по-близо", "по-далеч",
        "wide", "narrow", "панорам",
    ]
    return any(kw in lower for kw in camera_keywords)


async def refine_design_render(
    design_id: str,
    instruction: str,
    reference_image_bytes: bytes | None = None,
    reference_image_mime: str | None = None,
) -> dict:
    """Refine an existing design render based on user instruction.

    Sends the original sketch + current render + scene context + user text
    to Gemini for a targeted edit. For camera/angle changes, includes full
    spatial context so the model can re-render from a new viewpoint.

    Returns a dict compatible with RefineResult.
    """

    # 1. Load existing design
    design = get_design(design_id)
    if design is None:
        raise ValueError(f"Design '{design_id}' not found.")

    # 2. Fetch current render from R2 (higher quality for refinement)
    current_render_key = design["render_r2_key"]
    current_render_bytes = get_r2_image_bytes(current_render_key)
    current_render_resized = resize_for_prompt(current_render_bytes, max_size=1024)
    current_render_url = get_image_url(current_render_key)
    print(f"[refine] Fetched current render: {current_render_key}")

    # 3. Determine current version
    try:
        version_str = current_render_key.rsplit("_v", 1)[-1].replace(".webp", "")
        current_version = int(version_str)
    except (ValueError, IndexError):
        current_version = 1

    # 4. Detect if this is a camera/angle change
    is_camera = _is_camera_change(instruction) if instruction else False

    # 5. Load original sketch from R2 if available
    sketch_r2_key = design.get("sketch_r2_key")
    sketch_bytes: bytes | None = None
    if sketch_r2_key:
        try:
            raw_sketch = get_r2_image_bytes(sketch_r2_key)
            sketch_bytes = resize_for_prompt(raw_sketch, max_size=1024)
            print(f"[refine] Loaded original sketch: {sketch_r2_key}")
        except Exception as exc:
            print(f"[refine] Could not load sketch: {exc}")

    # 6. Load scene description and room analysis from design record
    scene_data = design.get("scene_description")
    room_data = design.get("room_analysis")

    # 7. Build multimodal prompt
    parts: list[genai_types.Part] = []

    # Part A — original sketch (spatial ground truth)
    if sketch_bytes is not None:
        parts.append(
            genai_types.Part(
                inline_data=genai_types.Blob(
                    mime_type="image/webp",
                    data=base64.b64encode(sketch_bytes).decode("utf-8"),
                )
            )
        )
        parts.append(
            genai_types.Part(
                text="ABOVE: The original sketch this design was based on."
            )
        )

    # Part B — current render image
    render_b64 = base64.b64encode(current_render_resized).decode("utf-8")
    parts.append(
        genai_types.Part(
            inline_data=genai_types.Blob(
                mime_type="image/webp",
                data=render_b64,
            )
        )
    )
    parts.append(
        genai_types.Part(
            text="ABOVE: The current room render (latest version) to be refined."
        )
    )

    # Part C — spatial context (scene description + room analysis)
    context_lines: list[str] = []
    if scene_data:
        scene_ctx = _build_scene_context(scene_data)
        if scene_ctx:
            context_lines.append(f"SCENE & CAMERA CONTEXT:\n{scene_ctx}")
    if room_data:
        # Include basic room info
        rooms = room_data.get("rooms", [])
        if rooms:
            r = rooms[0] if isinstance(rooms, list) else rooms
            if isinstance(r, dict):
                room_ctx = _build_room_context(r)
                context_lines.append(f"ROOM CONTEXT:\n{room_ctx}")

    if context_lines:
        parts.append(
            genai_types.Part(text="\n\n".join(context_lines))
        )

    # Part D — system preamble (different for camera vs non-camera edits)
    if is_camera:
        preamble = (
            "You are RE-RENDERING this room from a DIFFERENT CAMERA ANGLE as "
            "requested. Use the original sketch and scene context above to "
            "understand the full 3D layout of the room — where every piece of "
            "furniture is, what the walls look like, and the room's dimensions. "
            "Then generate a NEW photorealistic render from the requested "
            "viewpoint. Keep ALL furniture, colors, materials, lighting, and "
            "style IDENTICAL — only the camera position and angle should change. "
            "Do NOT mirror/flip the image. Actually re-render the 3D scene "
            "from the new viewpoint so objects have correct perspective, "
            "parallax, and occlusion."
        )
    else:
        preamble = (
            "You are performing a TARGETED EDIT on the room render above. "
            "Change ONLY what is requested. Keep everything else IDENTICAL — "
            "same camera angle, same perspective, same lighting, same "
            "furniture (unless specifically asked to change), same walls, "
            "same floor. The result should look like the same photograph "
            "with only the requested modification applied."
        )
    parts.append(genai_types.Part(text=preamble))

    # Part E — reference image (optional)
    if reference_image_bytes is not None:
        ref_resized = resize_for_prompt(reference_image_bytes, max_size=1024)
        ref_b64 = base64.b64encode(ref_resized).decode("utf-8")
        ref_mime = reference_image_mime or "image/webp"
        parts.append(
            genai_types.Part(
                inline_data=genai_types.Blob(
                    mime_type=ref_mime,
                    data=ref_b64,
                )
            )
        )
        parts.append(
            genai_types.Part(
                text="ABOVE: Reference image. Match its appearance for the relevant item."
            )
        )

    # Part F — user instruction
    if instruction.strip():
        parts.append(
            genai_types.Part(text=f"EDIT INSTRUCTION: {instruction}")
        )
    elif reference_image_bytes is not None:
        parts.append(
            genai_types.Part(
                text="EDIT INSTRUCTION: Replace the most similar item with the reference image."
            )
        )

    # Part G — constraints
    if is_camera:
        constraints = (
            "Generate ONE photorealistic image from the new camera angle. "
            "Do NOT add text, labels, or watermarks. Do NOT add or remove "
            "any furniture. Do NOT mirror/flip — re-render with correct "
            "3D perspective from the new viewpoint."
        )
    else:
        constraints = (
            "Generate ONE photorealistic image. Do NOT add text, labels, "
            "or watermarks. Do NOT change camera angle or perspective. "
            "Do NOT add or remove furniture unless specifically requested."
        )
    parts.append(genai_types.Part(text=constraints))

    # 8. Call Gemini
    print(f"[refine] Generating refined render for design {design_id} (camera_change={is_camera})...")

    config = genai_types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
        image_config=genai_types.ImageConfig(
            aspect_ratio="16:9",
            image_size="2K",
        ),
    )

    response = _gemini_client.models.generate_content(
        model=_IMAGE_MODEL,
        contents=genai_types.Content(parts=parts),
        config=config,
    )

    # 9. Extract generated image
    render_bytes: bytes | None = None
    if response.candidates:
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                raw_data = part.inline_data.data
                if isinstance(raw_data, bytes):
                    render_bytes = raw_data
                else:
                    render_bytes = base64.b64decode(raw_data)
                break

    if render_bytes is None:
        raise RuntimeError(
            "Gemini не генерира изображение. Моля, опитайте с различна инструкция."
        )

    # 10. Upload new render to R2
    new_version = current_version + 1
    new_render_key = f"renders/{design_id}/render_v{new_version}.webp"
    new_render_url = upload_image(render_bytes, new_render_key, content_type="image/webp")
    print(f"[refine] New render uploaded to R2: {new_render_key}")

    # 11. Update design in Supabase
    update_design(design_id, {"render_r2_key": new_render_key})
    print(f"[refine] Design {design_id} updated with version {new_version}")

    # 12. Return RefineResult-compatible dict
    return {
        "design_id": design_id,
        "render_url": new_render_url,
        "version": new_version,
        "refinement_description": instruction or None,
        "previous_render_url": current_render_url,
    }


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
        image_config=genai_types.ImageConfig(
            aspect_ratio="16:9",
            image_size="2K",
        ),
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
                raw_data = part.inline_data.data
                if isinstance(raw_data, bytes):
                    render_bytes = raw_data
                else:
                    render_bytes = base64.b64decode(raw_data)
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
