"""Snap engine — finds nearest snap points on annotations."""
from __future__ import annotations

from qtpy.QtCore import QPointF
from qtpy.QtWidgets import QGraphicsScene

from pdfredline.annotations.base import AnnotationItem


class SnapResult:
    __slots__ = ("point", "annotation", "snap_index", "distance")

    def __init__(self, point: QPointF, annotation: AnnotationItem,
                 snap_index: int, distance: float):
        self.point = point
        self.annotation = annotation
        self.snap_index = snap_index
        self.distance = distance


class SnapEngine:
    """Queries annotations in a scene for snap points and finds the nearest one."""

    def __init__(self, scene: QGraphicsScene, snap_radius: float = 15.0):
        self.scene = scene
        self.snap_radius = snap_radius

    def find_nearest(self, pos: QPointF, exclude=None) -> SnapResult | None:
        """Find the nearest snap point within snap_radius of pos.

        Args:
            pos: Position in scene coordinates.
            exclude: Optional item to exclude from snap search.
        """
        best: SnapResult | None = None

        for item in self.scene.items():
            if not isinstance(item, AnnotationItem):
                continue
            if item is exclude:
                continue
            for i, snap_pt in enumerate(item.snap_points()):
                dx = snap_pt.x() - pos.x()
                dy = snap_pt.y() - pos.y()
                dist = (dx * dx + dy * dy) ** 0.5
                if dist <= self.snap_radius and (best is None or dist < best.distance):
                    best = SnapResult(snap_pt, item, i, dist)

        return best
