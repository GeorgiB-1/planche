"""Design API routes for the sketch-to-render pipeline.

Handles sketch upload, room analysis, furniture matching, and design generation.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, field_validator

from src.config import ROOM_FURNITURE_REQUIREMENTS
from src.models.design import DesignResult, MatchResult
from src.models.room import RoomAnalysis, SceneDescription
from src.services.generator import generate_room_design, refine_design_render, swap_product_in_design
from src.services.matcher import match_furniture_for_room
from src.services.room_analyzer import analyze_room, describe_scene
from src.storage.r2_client import get_image_url
from src.storage.supabase_client import get_design, get_product_by_id, query_products

router = APIRouter(prefix="/api", tags=["design"])

ALLOWED_IMAGE_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp"]
MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB
VALID_TIERS: set[str] = {"budget", "standard", "premium", "luxury"}
VALID_STYLES: set[str] = {
    "modern",
    "scandinavian",
    "industrial",
    "classic",
    "minimalist",
    "mid-century",
    "art_deco",
    "rustic",
    "contemporary",
    "traditional",
}


# ---------------------------------------------------------------------------
# Request model for the /swap stub
# ---------------------------------------------------------------------------

class SwapRequest(BaseModel):
    design_id: str
    slot: str
    product_id: str | None = None

    @field_validator("design_id", "slot")
    @classmethod
    def must_be_non_empty(cls, v: str, info) -> str:  # noqa: N805
        if not v or not v.strip():
            raise ValueError(f"'{info.field_name}' must be a non-empty string.")
        return v


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _read_and_validate_image(sketch: UploadFile) -> tuple[bytes, str]:
    """Read an uploaded sketch file, validate type and size.

    Returns:
        A tuple of (image_bytes, mime_type).

    Raises:
        HTTPException 400 if the file is not an allowed image type or exceeds
        the maximum size.
    """
    mime_type = sketch.content_type or ""
    if mime_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Невалиден формат на изображение. Използвайте JPEG, PNG или WebP.",
        )

    image_bytes = await sketch.read()

    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Файлът е прекалено голям. Максимален размер: 10MB.",
        )

    return image_bytes, mime_type


def _get_categories_for_slot(slot: str) -> list[str]:
    """Look up which product categories match a given furniture slot name."""
    for room_type, requirements in ROOM_FURNITURE_REQUIREMENTS.items():
        for req in requirements.get("required", []) + requirements.get("optional", []):
            if req["slot"] == slot:
                return req["categories"]
    # Fallback: use slot name as category
    return [slot.replace("_", " ")]


# ---------------------------------------------------------------------------
# POST /api/analyze
# ---------------------------------------------------------------------------

@router.post("/analyze")
async def analyze_sketch(sketch: UploadFile = File(...)) -> dict:
    """Upload a sketch and receive structured room analysis + scene description."""
    image_bytes, mime_type = await _read_and_validate_image(sketch)

    analysis, scene_desc = await asyncio.gather(
        analyze_room(image_bytes, mime_type),
        describe_scene(image_bytes, mime_type),
    )

    return {
        "room_analysis": analysis.model_dump(),
        "scene_description": scene_desc.model_dump(),
    }


# ---------------------------------------------------------------------------
# POST /api/furnish
# ---------------------------------------------------------------------------

@router.post("/furnish", response_model=DesignResult)
async def furnish_room(
    sketch: UploadFile = File(...),
    budget: float = Form(...),
    tier: str = Form(...),
    style: str | None = Form(None),
    room_id: str | None = Form(None),
) -> DesignResult:
    """Full pipeline: analyse sketch, match furniture, generate render."""

    # -- Validate image --
    image_bytes, mime_type = await _read_and_validate_image(sketch)

    # -- Validate budget --
    if budget < 100 or budget > 50_000:
        raise HTTPException(
            status_code=400,
            detail="Бюджетът трябва да е между €100 и €50,000.",
        )

    # -- Validate tier --
    if tier not in VALID_TIERS:
        raise HTTPException(
            status_code=400,
            detail="Невалиден бюджетен клас.",
        )

    # -- Validate style (if provided) --
    if style is not None and style not in VALID_STYLES:
        raise HTTPException(
            status_code=400,
            detail="Невалиден стил.",
        )

    # -- Step 1: Room analysis + Scene description (parallel) --
    analysis, scene_desc = await asyncio.gather(
        analyze_room(image_bytes, mime_type),
        describe_scene(image_bytes, mime_type),
    )

    # -- Step 2: Select room --
    if not analysis.rooms:
        raise HTTPException(
            status_code=422,
            detail="Room analysis did not detect any rooms in the sketch.",
        )

    if room_id is not None:
        selected_room = next(
            (r for r in analysis.rooms if r.id == room_id), None
        )
        if selected_room is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Room '{room_id}' not found in analysis. "
                    f"Available rooms: {[r.id for r in analysis.rooms]}"
                ),
            )
    else:
        selected_room = analysis.rooms[0]

    # -- Step 3: Match furniture --
    match_result: MatchResult = match_furniture_for_room(
        room=selected_room.model_dump(),
        budget_eur=budget,
        tier=tier,
        style=style,
    )

    if not match_result.products:
        raise HTTPException(
            status_code=422,
            detail="No products matched the given room, budget, and tier.",
        )

    # -- Step 4: Generate design --
    try:
        design_result: DesignResult = await generate_room_design(
            sketch_bytes=image_bytes,
            sketch_mime=mime_type,
            room_data=selected_room.model_dump(),
            product_images=[p.model_dump() for p in match_result.product_images_for_render],
            buy_links=[bl.model_dump() for bl in match_result.buy_links],
            style=style,
            tier=tier,
            budget_spent=match_result.budget_spent,
            budget_remaining=match_result.budget_remaining,
            scene_description=scene_desc.model_dump(),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Design generation failed: {exc}",
        ) from exc

    return design_result


# ---------------------------------------------------------------------------
# POST /api/refine
# ---------------------------------------------------------------------------

@router.post("/refine")
async def refine_design(
    design_id: str = Form(...),
    instruction: str = Form(""),
    reference_image: UploadFile | None = File(None),
) -> dict:
    """Refine an existing design render with a natural language instruction
    and/or a reference image."""

    # Validate: at least one of instruction or reference_image must be provided
    has_instruction = bool(instruction and instruction.strip())
    has_image = reference_image is not None and reference_image.filename

    if not has_instruction and not has_image:
        raise HTTPException(
            status_code=400,
            detail="Моля, въведете инструкция или прикачете референтно изображение.",
        )

    # Read reference image bytes if provided
    ref_bytes: bytes | None = None
    ref_mime: str | None = None
    if has_image:
        ref_mime = reference_image.content_type or ""
        if ref_mime not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail="Невалиден формат на референтно изображение. Използвайте JPEG, PNG или WebP.",
            )
        ref_bytes = await reference_image.read()
        if len(ref_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail="Референтното изображение е прекалено голямо. Максимален размер: 10MB.",
            )

    try:
        result = await refine_design_render(
            design_id=design_id,
            instruction=instruction,
            reference_image_bytes=ref_bytes,
            reference_image_mime=ref_mime,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Грешка при промяна на дизайна: {exc}",
        ) from exc

    return result


# ---------------------------------------------------------------------------
# POST /api/swap
# ---------------------------------------------------------------------------

@router.post("/swap")
async def swap_product(body: SwapRequest) -> dict:
    """Swap a product in an existing design or return alternatives.

    If ``product_id`` is *None*, returns up to 5 alternative products for
    the given slot (same category, in stock, usable image).

    If ``product_id`` is provided, performs the actual swap: replaces the
    product in the design and triggers a re-render.
    """

    # -- Case 1: No product_id  ->  return alternatives -------------------
    if body.product_id is None:
        # Verify the design exists
        design = get_design(body.design_id)
        if design is None:
            raise HTTPException(
                status_code=404,
                detail=f"Design '{body.design_id}' not found.",
            )

        # Determine categories from the slot name
        categories = _get_categories_for_slot(body.slot)

        # Query Supabase for alternative products
        rows = query_products(
            categories=categories,
            require_usable_image=True,
            limit=5,
        )

        alternatives = [
            {
                "id": row["id"],
                "name": row.get("name", ""),
                "price": row.get("price"),
                "image_url": (
                    get_image_url(row["r2_main_image_key"])
                    if row.get("r2_main_image_key")
                    else row.get("main_image_url")
                ),
                "visual_description": row.get("visual_description", ""),
            }
            for row in rows
        ]

        return {"alternatives": alternatives}

    # -- Case 2: product_id provided  ->  perform the swap ----------------
    product = get_product_by_id(body.product_id)
    if product is None:
        raise HTTPException(
            status_code=404,
            detail=f"Product '{body.product_id}' not found.",
        )

    try:
        result = swap_product_in_design(body.design_id, body.slot, product)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Swap failed: {exc}",
        ) from exc

    return result
