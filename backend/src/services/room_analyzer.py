"""Room analysis service using Gemini Flash vision model.

Accepts a sketch or floor plan image, sends it to Gemini Flash for
vision analysis, and returns structured room data (dimensions, walls,
furniture zones, etc.) as a validated RoomAnalysis model.
"""

import base64
import json
import logging
import re

from google import genai

from src.config import GEMINI_API_KEY, ROOM_ANALYSIS_PROMPT, SCENE_DESCRIPTION_PROMPT
from src.models.room import (
    CameraInfo,
    CompositionInfo,
    DoorFeature,
    FurnitureZone,
    Room,
    RoomAnalysis,
    RoomAnalysisOverall,
    RoomFeatures,
    SceneDescription,
    SpatialObject,
    SpatialRelationship,
    UsableWall,
    VisibleSurfaces,
    WallSurfaceDetail,
    WindowFeature,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Bulgarian room name -> normalised English type mapping
# ---------------------------------------------------------------------------
BG_ROOM_TYPE_MAP: dict[str, str] = {
    "хол": "living_room",
    "спалня": "bedroom",
    "кухня": "kitchen",
    "баня": "bathroom",
    "коридор": "hallway",
    "балкон": "balcony",
    "детска стая": "kids_room",
    "кабинет": "office",
    "трапезария": "dining_room",
}

# ---------------------------------------------------------------------------
# Gemini client initialisation
# ---------------------------------------------------------------------------
_client = genai.Client(api_key=GEMINI_API_KEY)

GEMINI_MODEL = "gemini-2.5-flash"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_gemini_json(raw_text: str) -> dict:
    """Strip optional markdown code fencing and parse the JSON payload."""
    text = raw_text.strip()
    # Remove ```json ... ``` or ``` ... ``` wrappers
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return json.loads(text)


def _normalise_room_type(name: str) -> str:
    """Map a Bulgarian (or English) room name to a canonical English type."""
    lowered = name.strip().lower()
    if lowered in BG_ROOM_TYPE_MAP:
        return BG_ROOM_TYPE_MAP[lowered]
    # Also try matching against values in case the response already uses English
    if lowered.replace(" ", "_") in BG_ROOM_TYPE_MAP.values():
        return lowered.replace(" ", "_")
    # Fallback: slugify the original name
    return re.sub(r"\s+", "_", lowered)


def _metres_to_cm(value: float | int | None) -> float:
    """Convert a value in metres to centimetres, defaulting to 0."""
    if value is None:
        return 0.0
    return float(value) * 100.0


def _safe_float(value, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _build_default_analysis() -> RoomAnalysis:
    """Return a sensible default when the image cannot be analysed."""
    return RoomAnalysis(
        rooms=[
            Room(
                id="room_1",
                type="living_room",
                estimated_width_cm=500.0,
                estimated_depth_cm=400.0,
                estimated_area_sqm=20.0,
                features=RoomFeatures(),
                usable_walls=[],
                furniture_zones=[],
            )
        ],
        overall=RoomAnalysisOverall(
            total_rooms=1,
            total_area_sqm=20.0,
            style_hints=[],
            detected_labels=["generic_room"],
        ),
    )


# ---------------------------------------------------------------------------
# Mapping helpers (Gemini response dict -> Pydantic models)
# ---------------------------------------------------------------------------

def _map_windows(raw_windows: list[dict]) -> list[WindowFeature]:
    windows: list[WindowFeature] = []
    for w in raw_windows:
        windows.append(
            WindowFeature(
                wall=w.get("wall", "unknown"),
                width_cm=_metres_to_cm(w.get("width_m")) if w.get("width_m") is not None else w.get("width_cm"),
                position=w.get("position"),
            )
        )
    return windows


def _map_doors(raw_doors: list[dict]) -> list[DoorFeature]:
    doors: list[DoorFeature] = []
    for d in raw_doors:
        doors.append(
            DoorFeature(
                wall=d.get("wall", "unknown"),
                width_cm=_metres_to_cm(d.get("width_m")) if d.get("width_m") is not None else d.get("width_cm"),
                type=d.get("type"),
                connects_to=d.get("connects_to"),
            )
        )
    return doors


def _map_usable_walls(raw_walls: list[dict]) -> list[UsableWall]:
    walls: list[UsableWall] = []
    for uw in raw_walls:
        free_length = uw.get("free_length_m")
        if free_length is not None:
            free_length_cm = _metres_to_cm(free_length)
        else:
            free_length_cm = _safe_float(uw.get("free_length_cm"), 0.0)
        walls.append(
            UsableWall(
                wall=uw.get("wall", "unknown"),
                free_length_cm=free_length_cm,
                suitable_for=uw.get("suitable_for", []),
            )
        )
    return walls


def _map_furniture_zones(raw_zones: list[dict]) -> list[FurnitureZone]:
    zones: list[FurnitureZone] = []
    for fz in raw_zones:
        area_cm = fz.get("area_cm")
        # If the response provides area in metres, convert
        if area_cm is None and fz.get("area_m") is not None:
            raw_area = fz["area_m"]
            if isinstance(raw_area, list):
                area_cm = [_metres_to_cm(v) for v in raw_area]
            else:
                area_cm = None
        zones.append(
            FurnitureZone(
                zone=fz.get("zone", "unknown"),
                position=fz.get("position", "unknown"),
                area_cm=area_cm,
            )
        )
    return zones


def _map_room(raw_room: dict, index: int) -> Room:
    """Convert a single room dict from the Gemini response to a Room model."""
    name = raw_room.get("name", raw_room.get("name_bg", "room"))
    room_type = _normalise_room_type(name)

    # Dimensions -- Gemini returns metres; convert to cm
    width_m = _safe_float(raw_room.get("dimensions", {}).get("width_m"))
    depth_m = _safe_float(raw_room.get("dimensions", {}).get("length_m",
                          raw_room.get("dimensions", {}).get("depth_m")))
    area_sqm = _safe_float(raw_room.get("dimensions", {}).get("area_sqm"))

    if area_sqm == 0.0 and width_m > 0 and depth_m > 0:
        area_sqm = round(width_m * depth_m, 2)

    # Features
    windows = _map_windows(raw_room.get("windows", []))
    doors = _map_doors(raw_room.get("doors", []))
    features = RoomFeatures(
        windows=windows,
        doors=doors,
        balcony_access=raw_room.get("balcony_access", False),
        fireplace=raw_room.get("fireplace", False),
    )

    # Usable walls & furniture zones
    usable_walls = _map_usable_walls(raw_room.get("usable_walls", []))
    furniture_zones = _map_furniture_zones(raw_room.get("furniture_zones", []))

    return Room(
        id=f"room_{index + 1}",
        type=room_type,
        estimated_width_cm=_metres_to_cm(width_m),
        estimated_depth_cm=_metres_to_cm(depth_m),
        estimated_area_sqm=area_sqm,
        features=features,
        usable_walls=usable_walls,
        furniture_zones=furniture_zones,
    )


def _map_overall(raw_overall: dict, rooms: list[Room]) -> RoomAnalysisOverall:
    total_rooms = raw_overall.get("total_rooms", len(rooms))
    total_area = _safe_float(raw_overall.get("total_area_sqm"))
    if total_area == 0.0 and rooms:
        total_area = round(sum(r.estimated_area_sqm for r in rooms), 2)

    return RoomAnalysisOverall(
        total_rooms=total_rooms,
        total_area_sqm=total_area,
        style_hints=raw_overall.get("style_hints", []),
        detected_labels=raw_overall.get("detected_labels", []),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def analyze_room(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
) -> RoomAnalysis:
    """Analyse a floor plan / sketch image and return structured room data.

    Parameters
    ----------
    image_bytes:
        Raw bytes of the uploaded image.
    mime_type:
        MIME type of the image (e.g. ``"image/jpeg"``, ``"image/png"``).

    Returns
    -------
    RoomAnalysis
        Validated model containing rooms and overall layout information.
    """
    try:
        # Encode image as base64 for inline_data
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        response = await _client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_image,
                            }
                        },
                        {
                            "text": ROOM_ANALYSIS_PROMPT,
                        },
                    ],
                }
            ],
        )

        raw_text = response.text
        if not raw_text:
            logger.warning("Gemini returned an empty response; using defaults.")
            return _build_default_analysis()

        parsed = _parse_gemini_json(raw_text)

        # Map rooms
        raw_rooms = parsed.get("rooms", [])
        if not raw_rooms:
            logger.warning("No rooms detected in Gemini response; using defaults.")
            return _build_default_analysis()

        rooms: list[Room] = [
            _map_room(raw_room, idx) for idx, raw_room in enumerate(raw_rooms)
        ]

        # Map overall layout
        raw_overall = parsed.get("overall_layout", parsed.get("overall", {}))
        overall = _map_overall(raw_overall, rooms)

        return RoomAnalysis(rooms=rooms, overall=overall)

    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Gemini JSON response: %s", exc)
        return _build_default_analysis()
    except Exception as exc:
        logger.error("Room analysis failed: %s", exc, exc_info=True)
        return _build_default_analysis()


# ---------------------------------------------------------------------------
# Scene Description helpers
# ---------------------------------------------------------------------------

def _build_default_scene_description() -> SceneDescription:
    """Return a sensible default scene description (standing, two-point, room entrance)."""
    return SceneDescription()


def _map_camera(raw: dict) -> CameraInfo:
    return CameraInfo(
        perspective_type=raw.get("perspective_type", "two-point"),
        eye_level=raw.get("eye_level", "standing"),
        eye_height_estimate=raw.get("eye_height_estimate", "~160 cm"),
        camera_position=raw.get("camera_position", "room entrance, center"),
        camera_direction=raw.get("camera_direction", "looking into the room"),
        horizontal_angle_deg=_safe_float(raw.get("horizontal_angle_deg"), 0.0),
        vertical_tilt_deg=_safe_float(raw.get("vertical_tilt_deg"), 0.0),
        fov_estimate=raw.get("fov_estimate", "normal (~60°)"),
        distance_to_subject=raw.get("distance_to_subject", "medium"),
    )


def _map_visible_surfaces(raw: dict) -> VisibleSurfaces:
    walls = []
    for w in raw.get("walls", []):
        walls.append(
            WallSurfaceDetail(
                wall_id=w.get("wall_id", "unknown"),
                coverage_pct=_safe_float(w.get("coverage_pct"), 0.0),
                features=w.get("features", []),
            )
        )
    return VisibleSurfaces(
        floor_visible=raw.get("floor_visible", True),
        floor_coverage_pct=_safe_float(raw.get("floor_coverage_pct"), 50.0),
        ceiling_visible=raw.get("ceiling_visible", False),
        ceiling_coverage_pct=_safe_float(raw.get("ceiling_coverage_pct"), 0.0),
        walls=walls,
    )


def _map_objects(raw_list: list[dict]) -> list[SpatialObject]:
    objects = []
    for obj in raw_list:
        objects.append(
            SpatialObject(
                name=obj.get("name", "unknown"),
                depth_zone=obj.get("depth_zone", "midground"),
                horizontal_position=obj.get("horizontal_position", "center"),
                vertical_position=obj.get("vertical_position", "middle"),
                size_in_frame=obj.get("size_in_frame", "medium"),
                occluded_by=obj.get("occluded_by"),
            )
        )
    return objects


def _map_spatial_relationships(raw_list: list[dict]) -> list[SpatialRelationship]:
    relationships = []
    for rel in raw_list:
        if "object_a" in rel and "object_b" in rel and "relationship" in rel:
            relationships.append(
                SpatialRelationship(
                    object_a=rel["object_a"],
                    object_b=rel["object_b"],
                    relationship=rel["relationship"],
                )
            )
    return relationships


def _map_composition(raw: dict) -> CompositionInfo:
    return CompositionInfo(
        dominant_lines=raw.get("dominant_lines", []),
        focal_point=raw.get("focal_point", "center of room"),
        visual_weight=raw.get("visual_weight", "balanced"),
        depth_cues=raw.get("depth_cues", []),
        balance=raw.get("balance", "symmetric"),
    )


# ---------------------------------------------------------------------------
# Public API — Scene Description
# ---------------------------------------------------------------------------

async def describe_scene(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
) -> SceneDescription:
    """Analyse a sketch image for camera viewpoint and spatial composition.

    Parameters
    ----------
    image_bytes:
        Raw bytes of the uploaded image.
    mime_type:
        MIME type of the image.

    Returns
    -------
    SceneDescription
        Validated model containing camera, surfaces, objects, composition data.
    """
    try:
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        response = await _client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_image,
                            }
                        },
                        {
                            "text": SCENE_DESCRIPTION_PROMPT,
                        },
                    ],
                }
            ],
        )

        raw_text = response.text
        if not raw_text:
            logger.warning("Gemini returned empty scene description; using defaults.")
            return _build_default_scene_description()

        parsed = _parse_gemini_json(raw_text)

        camera = _map_camera(parsed.get("camera", {}))
        visible_surfaces = _map_visible_surfaces(parsed.get("visible_surfaces", {}))
        objects = _map_objects(parsed.get("objects", []))
        spatial_relationships = _map_spatial_relationships(
            parsed.get("spatial_relationships", [])
        )
        composition = _map_composition(parsed.get("composition", {}))

        return SceneDescription(
            camera=camera,
            visible_surfaces=visible_surfaces,
            objects=objects,
            spatial_relationships=spatial_relationships,
            composition=composition,
            natural_language_summary=parsed.get(
                "natural_language_summary",
                SceneDescription().natural_language_summary,
            ),
            generation_directive=parsed.get(
                "generation_directive",
                SceneDescription().generation_directive,
            ),
        )

    except json.JSONDecodeError as exc:
        logger.error("Failed to parse scene description JSON: %s", exc)
        return _build_default_scene_description()
    except Exception as exc:
        logger.error("Scene description failed: %s", exc, exc_info=True)
        return _build_default_scene_description()
