import uuid
from datetime import UTC, datetime
from enum import Enum

from qtpy.QtCore import QPointF
from qtpy.QtWidgets import QGraphicsItem


class AnnotationType(str, Enum):
    LINE = "line"
    RECT = "rect"
    CIRCLE = "circle"
    OVAL = "oval"
    TRIANGLE = "triangle"
    FREEHAND = "freehand"
    TEXT = "text"
    DIMENSION_LINEAR = "dimension_linear"
    DIMENSION_ALIGNED = "dimension_aligned"
    DIMENSION_RADIAL = "dimension_radial"
    DIMENSION_ANGULAR = "dimension_angular"
    SYMBOL = "symbol"


class AnnotationItem(QGraphicsItem):
    """Abstract base class for all annotation items in the redline scene."""

    def __init__(self, annotation_type: AnnotationType, parent=None):
        super().__init__(parent)
        self.annotation_id: str = str(uuid.uuid4())
        self.annotation_type: AnnotationType = annotation_type
        self.page_number: int = 0
        self.locked: bool = False
        self.created_at: str = datetime.now(UTC).isoformat()
        self.modified_at: str = self.created_at

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    def touch(self):
        """Update modified timestamp."""
        self.modified_at = datetime.now(UTC).isoformat()

    def serialize(self) -> dict:
        """Serialize this annotation to a dict for project save."""
        return {
            "id": self.annotation_id,
            "type": self.annotation_type.value,
            "page": self.page_number,
            "position": {"x": self.pos().x(), "y": self.pos().y()},
            "rotation": self.rotation(),
            "z_index": self.zValue(),
            "locked": self.locked,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
        }

    def deserialize_base(self, data: dict):
        """Restore base properties from serialized data."""
        self.annotation_id = data.get("id", self.annotation_id)
        self.page_number = data.get("page", 0)
        pos = data.get("position", {})
        self.setPos(pos.get("x", 0), pos.get("y", 0))
        self.setRotation(data.get("rotation", 0))
        self.setZValue(data.get("z_index", 0))
        self.locked = data.get("locked", False)
        self.created_at = data.get("created_at", self.created_at)
        self.modified_at = data.get("modified_at", self.modified_at)
        if self.locked:
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)

    def snap_points(self) -> list[QPointF]:
        """Return snap points in scene coordinates. Override in subclasses."""
        return []
