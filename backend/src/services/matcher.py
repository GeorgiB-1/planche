"""
Furniture matcher service.

Takes room analysis data, budget, tier, and style, then queries the product
database to find the best furniture matches for each room slot. Implements a
scoring system to rank candidates and returns a fully populated MatchResult.
"""

from __future__ import annotations

from src.config import (
    BUDGET_TIERS,
    ROOM_BUDGET_ALLOCATION,
    ROOM_FURNITURE_REQUIREMENTS,
)
from src.storage.supabase_client import query_products
from src.storage.r2_client import get_image_url
from src.models.design import (
    BuyLink,
    ProductImageForRender,
    MatchedProduct,
    MatchResult,
)


# ---------------------------------------------------------------------------
# Scoring / ranking
# ---------------------------------------------------------------------------

def rank_candidates(
    candidates: list[dict],
    slot_budget: float,
    tier: str,
    style: str | None,
) -> list[dict]:
    """Score each candidate product on a 0-100 scale and return sorted list.

    Scoring breakdown (max 115, normalised later isn't needed -- we just sum):
        - Price proximity to slot budget   +30 max
        - Has R2 image                     +25
        - Verified dimensions              +20
        - Visual description present       +15
        - Luxury-score tier match          +15
        - Rating                           +10
    """

    scored: list[dict] = []

    for product in candidates:
        score = 0.0

        # -- Price proximity (max 30) -----------------------------------------
        price = product.get("price") or 0.0
        if slot_budget > 0 and price > 0:
            if price <= slot_budget:
                # Closer to the budget ceiling = better value utilisation
                ratio = price / slot_budget  # 0..1
                score += 30.0 * ratio
            else:
                # Over budget -- penalise proportionally; 2x budget => 0 pts
                overshoot = (price - slot_budget) / slot_budget
                score += max(0.0, 30.0 * (1.0 - overshoot))

        # -- Has R2 image (max 25) --------------------------------------------
        if product.get("r2_main_image_key"):
            score += 25.0

        # -- Verified dimensions (max 20) -------------------------------------
        has_proportions = product.get("proportion_w_h") is not None
        ai_verified = product.get("dimensions_source") == "ai_verified"
        if has_proportions or ai_verified:
            score += 20.0

        # -- Visual description (max 15) --------------------------------------
        visual_desc = product.get("visual_description") or ""
        if visual_desc.strip():
            score += 15.0

        # -- Luxury score tier match (max 15) ----------------------------------
        luxury_score = product.get("luxury_score")
        if luxury_score is not None:
            if tier == "luxury" and luxury_score > 0.5:
                score += 15.0
            elif tier == "premium" and 0.3 <= luxury_score <= 0.7:
                score += 10.0
            elif tier == "budget" and luxury_score < 0.3:
                score += 15.0
            elif tier == "standard" and luxury_score < 0.5:
                score += 10.0

        # -- Rating (max 10) --------------------------------------------------
        rating = product.get("rating")
        if rating is not None:
            # Assume rating is on a 0-5 scale
            score += min(10.0, (rating / 5.0) * 10.0)
        else:
            score += 5.0  # null rating gets 5 points

        product["_match_score"] = round(score, 2)
        scored.append(product)

    scored.sort(key=lambda p: p.get("_match_score", 0), reverse=True)
    return scored


# ---------------------------------------------------------------------------
# Dimension helpers
# ---------------------------------------------------------------------------

def get_max_dimension_for_slot(room: dict, slot_name: str) -> float | None:
    """Return the maximum width (cm) that furniture in *slot_name* may occupy.

    Strategy:
        1. If the room exposes ``usable_walls``, find the wall whose
           ``suitable_for`` list contains the slot name and return its
           ``free_length_cm``.
        2. Fallback: 60 % of the room's ``estimated_width_cm``.
        3. If neither is available, return ``None`` (no constraint).
    """

    usable_walls = room.get("usable_walls") or []

    # Try to find the most suitable wall for this slot
    for wall in usable_walls:
        suitable_for = wall.get("suitable_for") or []
        if slot_name in suitable_for:
            free_length = wall.get("free_length_cm")
            if free_length is not None:
                return float(free_length)

    # Fallback: 60% of estimated room width
    estimated_width = room.get("estimated_width_cm")
    if estimated_width is not None:
        return float(estimated_width) * 0.6

    return None


# ---------------------------------------------------------------------------
# Main matching entry-point
# ---------------------------------------------------------------------------

def match_furniture_for_room(
    room: dict,
    budget_eur: float,
    tier: str,
    style: str | None = None,
) -> MatchResult:
    """Match furniture for every slot in a room and return a ``MatchResult``.

    Parameters
    ----------
    room:
        Room dict (must contain at least ``type``; optionally
        ``estimated_width_cm``, ``estimated_depth_cm``, ``usable_walls``).
    budget_eur:
        Total budget in EUR allocated to this room.
    tier:
        One of the keys in ``BUDGET_TIERS``.
    style:
        Optional style hint (e.g. "scandinavian", "industrial").
    """

    room_type: str = room.get("type", "living_room")

    # -- Furniture requirements ------------------------------------------------
    requirements = ROOM_FURNITURE_REQUIREMENTS.get(
        room_type,
        ROOM_FURNITURE_REQUIREMENTS.get("living_room", {}),
    )
    required_slots: list[dict] = requirements.get("required", [])
    optional_slots: list[dict] = requirements.get("optional", [])

    # -- Budget allocation percentages ----------------------------------------
    allocation = ROOM_BUDGET_ALLOCATION.get(room_type)
    if allocation is None:
        # Equal allocation across all slots
        all_slots = required_slots + optional_slots
        if all_slots:
            equal_pct = 1.0 / len(all_slots)
            allocation = {}
            for slot_def in all_slots:
                cat = slot_def.get("slot", "unknown")
                allocation[cat] = (equal_pct * 0.8, equal_pct * 1.2)

    # -- Tier config -----------------------------------------------------------
    tier_config = BUDGET_TIERS.get(tier, BUDGET_TIERS.get("standard", {}))
    preferred_sources: list[str] = tier_config.get("preferred_sources", [])
    max_single_item_pct: float = tier_config.get("max_single_item_pct", 0.5)

    # -- Collect matches -------------------------------------------------------
    matched_products: list[MatchedProduct] = []
    product_images: list[ProductImageForRender] = []
    buy_links: list[BuyLink] = []
    budget_remaining = budget_eur

    def _process_slots(slot_list: list[dict], is_required: bool) -> None:
        nonlocal budget_remaining

        for slot_def in slot_list:
            slot_name: str = slot_def.get("slot", "unknown")
            categories: list[str] = slot_def.get("categories", [])
            quantity: int = slot_def.get("quantity", 1)

            # Skip optional slots when budget is exhausted
            if not is_required and budget_remaining <= 0:
                continue

            # --- Compute slot budget ------------------------------------------
            slot_alloc = (allocation or {}).get(slot_name)
            if slot_alloc is not None:
                min_pct, max_pct = slot_alloc
                midpoint_pct = (min_pct + max_pct) / 2.0
                slot_budget = budget_eur * midpoint_pct
            else:
                # Fallback: divide remaining evenly among un-allocated slots
                slot_budget = budget_remaining * 0.3

            # Cap by max single-item percentage
            max_item_price = budget_eur * max_single_item_pct
            per_unit_budget = min(slot_budget / max(quantity, 1), max_item_price)

            # --- Max dimension ------------------------------------------------
            max_width = get_max_dimension_for_slot(room, slot_name)

            # --- Query products -----------------------------------------------
            candidates = query_products(
                categories=categories,
                room=room_type,
                style=style,
                min_price=None,
                max_price=per_unit_budget,
                max_width=max_width,
                preferred_sources=preferred_sources,
                require_usable_image=True,
                require_proportions=False,
                limit=10,
            )

            print(
                f"[matcher] Matching {slot_name}: "
                f"found {len(candidates)} candidates"
            )

            if not candidates:
                continue

            # --- Rank and pick ------------------------------------------------
            ranked = rank_candidates(candidates, per_unit_budget, tier, style)
            best = ranked[0]
            unit_price = best.get("price") or 0.0
            total_price = unit_price * quantity

            # Skip if total price would exceed remaining budget (optional only)
            if not is_required and total_price > budget_remaining:
                continue

            budget_remaining -= total_price

            # --- Build MatchedProduct -----------------------------------------
            matched_products.append(
                MatchedProduct(
                    slot=slot_name,
                    product=best,
                    quantity=quantity,
                    placement=None,
                )
            )

            # --- Build ProductImageForRender ----------------------------------
            r2_key = best.get("r2_main_image_key")
            if r2_key:
                r2_url = get_image_url(r2_key)
                product_images.append(
                    ProductImageForRender(
                        slot=slot_name,
                        r2_key=r2_key,
                        r2_url=r2_url,
                        visual_description=best.get("visual_description", ""),
                        width_cm=best.get("width_cm"),
                        height_cm=best.get("height_cm"),
                        depth_cm=best.get("depth_cm"),
                        proportion_w_h=best.get("proportion_w_h"),
                        proportion_w_d=best.get("proportion_w_d"),
                        color=best.get("color"),
                        primary_material=best.get("primary_material"),
                    )
                )

            # --- Build BuyLink ------------------------------------------------
            image_url = ""
            if r2_key:
                image_url = get_image_url(r2_key)

            buy_links.append(
                BuyLink(
                    name=best.get("name", slot_name),
                    price=unit_price,
                    currency=best.get("currency", "EUR"),
                    url=best.get("product_url", ""),
                    source=best.get("source_domain", ""),
                    image_url=image_url,
                )
            )

    # Step 1: required slots
    _process_slots(required_slots, is_required=True)

    # Step 2: optional slots (only with remaining budget)
    _process_slots(optional_slots, is_required=False)

    # -- Assemble result -------------------------------------------------------
    budget_spent = budget_eur - budget_remaining
    utilization = (budget_spent / budget_eur * 100.0) if budget_eur > 0 else 0.0

    return MatchResult(
        room=room,
        tier=tier,
        style=style,
        budget_total=round(budget_eur, 2),
        budget_spent=round(budget_spent, 2),
        budget_remaining=round(budget_remaining, 2),
        budget_utilization_pct=round(utilization, 2),
        products=matched_products,
        product_count=len(matched_products),
        product_images_for_render=product_images,
        buy_links=buy_links,
    )
