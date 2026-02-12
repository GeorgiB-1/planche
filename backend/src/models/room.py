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
