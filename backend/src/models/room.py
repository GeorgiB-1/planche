"""Pydantic v2 models for room analysis."""

from pydantic import BaseModel


class WindowFeature(BaseModel):
    """A window detected in a room."""

    wall: str
    width_cm: float | None = None
    position: str | None = None


class DoorFeature(BaseModel):
    """A door detected in a room."""

    wall: str
    width_cm: float | None = None
    type: str | None = None
    connects_to: str | None = None


class RoomFeatures(BaseModel):
    """Architectural features detected in a room."""

    windows: list[WindowFeature] = []
    doors: list[DoorFeature] = []
    balcony_access: bool = False
    fireplace: bool = False


class UsableWall(BaseModel):
    """A wall segment available for furniture placement."""

    wall: str
    free_length_cm: float
    suitable_for: list[str] = []


class FurnitureZone(BaseModel):
    """A designated zone for furniture within a room."""

    zone: str
    position: str
    area_cm: list[float] | None = None


class Room(BaseModel):
    """A single room parsed from floor-plan or photo analysis."""

    id: str
    type: str
    estimated_width_cm: float
    estimated_depth_cm: float
    estimated_area_sqm: float
    features: RoomFeatures = RoomFeatures()
    usable_walls: list[UsableWall] = []
    furniture_zones: list[FurnitureZone] = []


class RoomAnalysisOverall(BaseModel):
    """Aggregate metrics across all detected rooms."""

    total_rooms: int = 1
    total_area_sqm: float = 0
    style_hints: list[str] = []
    detected_labels: list[str] = []


class RoomAnalysis(BaseModel):
    """Complete room analysis result."""

    rooms: list[Room] = []
    overall: RoomAnalysisOverall = RoomAnalysisOverall()


# ---------------------------------------------------------------------------
# Scene Description models (camera / viewpoint / composition analysis)
# ---------------------------------------------------------------------------


class CameraInfo(BaseModel):
    """Camera and viewpoint data extracted from a sketch."""

    perspective_type: str = "two-point"
    eye_level: str = "standing"
    eye_height_estimate: str = "~160 cm"
    camera_position: str = "room entrance, center"
    camera_direction: str = "looking into the room"
    horizontal_angle_deg: float = 0.0
    vertical_tilt_deg: float = 0.0
    fov_estimate: str = "normal (~60°)"
    distance_to_subject: str = "medium"


class WallSurfaceDetail(BaseModel):
    """Detail about a single visible wall."""

    wall_id: str = "unknown"
    coverage_pct: float = 0.0
    features: list[str] = []


class VisibleSurfaces(BaseModel):
    """Which architectural surfaces are visible in the sketch."""

    floor_visible: bool = True
    floor_coverage_pct: float = 50.0
    ceiling_visible: bool = False
    ceiling_coverage_pct: float = 0.0
    walls: list[WallSurfaceDetail] = []


class SpatialObject(BaseModel):
    """An object/element detected in the sketch with spatial info."""

    name: str
    depth_zone: str = "midground"
    horizontal_position: str = "center"
    vertical_position: str = "middle"
    size_in_frame: str = "medium"
    occluded_by: str | None = None


class SpatialRelationship(BaseModel):
    """Spatial relationship between two objects in the scene."""

    object_a: str
    object_b: str
    relationship: str  # e.g. "in_front_of", "behind", "to_left_of", etc.


class CompositionInfo(BaseModel):
    """Visual composition data extracted from the sketch."""

    dominant_lines: list[str] = []
    focal_point: str = "center of room"
    visual_weight: str = "balanced"
    depth_cues: list[str] = []
    balance: str = "symmetric"


class SceneDescription(BaseModel):
    """Top-level container for full scene / camera analysis of a sketch."""

    camera: CameraInfo = CameraInfo()
    visible_surfaces: VisibleSurfaces = VisibleSurfaces()
    objects: list[SpatialObject] = []
    spatial_relationships: list[SpatialRelationship] = []
    composition: CompositionInfo = CompositionInfo()
    natural_language_summary: str = (
        "A standard interior view from a standing position at the room entrance, "
        "looking into the room with a two-point perspective."
    )
    generation_directive: str = (
        "Render from a standing eye-level viewpoint at the room entrance, "
        "using two-point perspective with the camera looking straight into the room."
    )
