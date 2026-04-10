"""Dimension annotations — linear, aligned, radial, angular."""
from __future__ import annotations

import math

from qtpy.QtCore import QPointF, QRectF
from qtpy.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF

from pdfredline.annotations.base import AnnotationItem, AnnotationType
from pdfredline.annotations.registry import register_annotation

ARROW_SIZE = 8
DIM_COLOR = [0, 0, 200, 255]
DIM_LINE_WIDTH = 1.5
OFFSET_DEFAULT = 30.0


def _draw_arrow(painter: QPainter, tip: QPointF, angle: float, size: float = ARROW_SIZE):
    """Draw an arrowhead at tip pointing in direction angle (radians)."""
    p1 = QPointF(
        tip.x() - size * math.cos(angle - 0.35),
        tip.y() - size * math.sin(angle - 0.35),
    )
    p2 = QPointF(
        tip.x() - size * math.cos(angle + 0.35),
        tip.y() - size * math.sin(angle + 0.35),
    )
    path = QPainterPath()
    path.addPolygon(QPolygonF([tip, p1, p2, tip]))
    painter.fillPath(path, painter.pen().color())


class DimensionBase(AnnotationItem):
    """Base class for dimension annotations."""

    def __init__(self, annotation_type: AnnotationType, parent=None):
        super().__init__(annotation_type, parent)
        self.units: str = "mm"
        self.precision: int = 2
        self.offset: float = OFFSET_DEFAULT
        self.dim_color: list[int] = list(DIM_COLOR)
        # Snap references (annotation_id, snap_index) — stored for serialization
        self.source_ref: tuple[str, int] | None = None
        self.target_ref: tuple[str, int] | None = None
        # Actual points in scene coords
        self.source_pt: QPointF = QPointF(0, 0)
        self.target_pt: QPointF = QPointF(100, 0)

    def _pen(self) -> QPen:
        return QPen(QColor(*self.dim_color), DIM_LINE_WIDTH)

    def _pts_to_inches(self, pts: float) -> float:
        return pts / 72.0

    def _format_value(self, pts: float) -> str:
        inches = self._pts_to_inches(pts)
        val = inches * 25.4 if self.units == "mm" else inches
        return f"{val:.{self.precision}f}"

    def _base_serialize(self) -> dict:
        data = super().serialize()
        data["units"] = self.units
        data["precision"] = self.precision
        data["offset"] = self.offset
        data["dim_color"] = self.dim_color
        data["source_ref"] = list(self.source_ref) if self.source_ref else None
        data["target_ref"] = list(self.target_ref) if self.target_ref else None
        data["source_pt"] = [self.source_pt.x(), self.source_pt.y()]
        data["target_pt"] = [self.target_pt.x(), self.target_pt.y()]
        return data

    def _base_deserialize(self, data: dict):
        self.deserialize_base(data)
        self.units = data.get("units", "mm")
        self.precision = data.get("precision", 2)
        self.offset = data.get("offset", OFFSET_DEFAULT)
        self.dim_color = data.get("dim_color", list(DIM_COLOR))
        sr = data.get("source_ref")
        self.source_ref = tuple(sr) if sr else None
        tr = data.get("target_ref")
        self.target_ref = tuple(tr) if tr else None
        sp = data.get("source_pt", [0, 0])
        self.source_pt = QPointF(sp[0], sp[1])
        tp = data.get("target_pt", [100, 0])
        self.target_pt = QPointF(tp[0], tp[1])


class LinearDimension(DimensionBase):
    """Horizontal or vertical distance between two points."""

    def __init__(self, parent=None):
        super().__init__(AnnotationType.DIMENSION_LINEAR, parent)
        self.horizontal: bool = True

    def _compute(self):
        if self.horizontal:
            return abs(self.target_pt.x() - self.source_pt.x())
        return abs(self.target_pt.y() - self.source_pt.y())

    def boundingRect(self) -> QRectF:
        sp, tp = self.source_pt - self.pos(), self.target_pt - self.pos()
        xs = [sp.x(), tp.x()]
        ys = [sp.y(), tp.y(), sp.y() - self.offset, tp.y() - self.offset]
        pad = 20
        return QRectF(min(xs) - pad, min(ys) - pad,
                       max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setPen(self._pen())
        sp = self.source_pt - self.pos()
        tp = self.target_pt - self.pos()

        if self.horizontal:
            y = min(sp.y(), tp.y()) - self.offset
            p1 = QPointF(sp.x(), y)
            p2 = QPointF(tp.x(), y)
            # Extension lines
            painter.drawLine(sp, QPointF(sp.x(), y))
            painter.drawLine(tp, QPointF(tp.x(), y))
        else:
            x = min(sp.x(), tp.x()) - self.offset
            p1 = QPointF(x, sp.y())
            p2 = QPointF(x, tp.y())
            painter.drawLine(sp, QPointF(x, sp.y()))
            painter.drawLine(tp, QPointF(x, tp.y()))

        # Dimension line
        painter.drawLine(p1, p2)

        # Arrows
        angle = math.atan2(p2.y() - p1.y(), p2.x() - p1.x())
        _draw_arrow(painter, p1, angle)
        _draw_arrow(painter, p2, angle + math.pi)

        # Text
        dist = self._compute()
        text = self._format_value(dist)
        mid = (p1 + p2) / 2
        painter.drawText(mid + QPointF(-15, -5), text)

    def serialize(self) -> dict:
        data = self._base_serialize()
        data["horizontal"] = self.horizontal
        return data

    @classmethod
    def from_data(cls, data: dict) -> LinearDimension:
        item = cls()
        item._base_deserialize(data)
        item.horizontal = data.get("horizontal", True)
        return item


class AlignedDimension(DimensionBase):
    """Distance along the line connecting two points."""

    def __init__(self, parent=None):
        super().__init__(AnnotationType.DIMENSION_ALIGNED, parent)

    def _compute(self):
        dx = self.target_pt.x() - self.source_pt.x()
        dy = self.target_pt.y() - self.source_pt.y()
        return math.hypot(dx, dy)

    def boundingRect(self) -> QRectF:
        sp, tp = self.source_pt - self.pos(), self.target_pt - self.pos()
        pad = self.offset + 25
        xs = [sp.x(), tp.x()]
        ys = [sp.y(), tp.y()]
        return QRectF(min(xs) - pad, min(ys) - pad,
                       max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setPen(self._pen())
        sp = self.source_pt - self.pos()
        tp = self.target_pt - self.pos()

        dx = tp.x() - sp.x()
        dy = tp.y() - sp.y()
        length = math.hypot(dx, dy)
        if length < 1:
            return

        # Normal direction for offset
        nx = -dy / length * self.offset
        ny = dx / length * self.offset

        p1 = QPointF(sp.x() + nx, sp.y() + ny)
        p2 = QPointF(tp.x() + nx, tp.y() + ny)

        # Extension lines
        painter.drawLine(sp, p1)
        painter.drawLine(tp, p2)
        # Dimension line
        painter.drawLine(p1, p2)

        angle = math.atan2(p2.y() - p1.y(), p2.x() - p1.x())
        _draw_arrow(painter, p1, angle)
        _draw_arrow(painter, p2, angle + math.pi)

        text = self._format_value(length)
        mid = (p1 + p2) / 2
        painter.drawText(mid + QPointF(-15, -5), text)

    def serialize(self) -> dict:
        return self._base_serialize()

    @classmethod
    def from_data(cls, data: dict) -> AlignedDimension:
        item = cls()
        item._base_deserialize(data)
        return item


class RadialDimension(DimensionBase):
    """Radius of a circle/oval."""

    def __init__(self, parent=None):
        super().__init__(AnnotationType.DIMENSION_RADIAL, parent)
        self.radius_value: float = 0.0

    def boundingRect(self) -> QRectF:
        sp = self.source_pt - self.pos()
        pad = self.radius_value + 30
        return QRectF(sp.x() - pad, sp.y() - pad, 2 * pad, 2 * pad)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setPen(self._pen())
        center = self.source_pt - self.pos()
        end = QPointF(center.x() + self.radius_value, center.y())

        painter.drawLine(center, end)
        angle = 0.0
        _draw_arrow(painter, end, angle + math.pi)

        text = "R" + self._format_value(self.radius_value)
        mid = (center + end) / 2
        painter.drawText(mid + QPointF(-15, -15), text)

    def serialize(self) -> dict:
        data = self._base_serialize()
        data["radius_value"] = self.radius_value
        return data

    @classmethod
    def from_data(cls, data: dict) -> RadialDimension:
        item = cls()
        item._base_deserialize(data)
        item.radius_value = data.get("radius_value", 0)
        return item


class AngularDimension(DimensionBase):
    """Angle between two lines sharing a common point."""

    def __init__(self, parent=None):
        super().__init__(AnnotationType.DIMENSION_ANGULAR, parent)
        self.vertex_pt: QPointF = QPointF(0, 0)

    def _compute(self) -> float:
        """Returns angle in degrees."""
        sp = self.source_pt - self.vertex_pt
        tp = self.target_pt - self.vertex_pt
        a1 = math.atan2(sp.y(), sp.x())
        a2 = math.atan2(tp.y(), tp.x())
        angle = abs(math.degrees(a2 - a1))
        if angle > 180:
            angle = 360 - angle
        return angle

    def boundingRect(self) -> QRectF:
        pts = [self.source_pt - self.pos(), self.target_pt - self.pos(),
               self.vertex_pt - self.pos()]
        xs = [p.x() for p in pts]
        ys = [p.y() for p in pts]
        pad = 30
        return QRectF(min(xs) - pad, min(ys) - pad,
                       max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setPen(self._pen())
        vp = self.vertex_pt - self.pos()
        sp = self.source_pt - self.pos()
        tp = self.target_pt - self.pos()

        # Draw the two reference lines
        painter.drawLine(vp, sp)
        painter.drawLine(vp, tp)

        # Draw arc
        angle = self._compute()
        a1 = math.degrees(math.atan2(sp.y() - vp.y(), sp.x() - vp.x()))
        radius = min(
            math.hypot(sp.x() - vp.x(), sp.y() - vp.y()),
            math.hypot(tp.x() - vp.x(), tp.y() - vp.y()),
        ) * 0.5

        arc_rect = QRectF(vp.x() - radius, vp.y() - radius, 2 * radius, 2 * radius)
        span = self._compute()
        painter.drawArc(arc_rect, int(-a1 * 16), int(-span * 16))

        # Text
        mid_angle = math.radians(a1 + span / 2)
        text_pos = QPointF(
            vp.x() + (radius + 10) * math.cos(-mid_angle),
            vp.y() + (radius + 10) * math.sin(-mid_angle),
        )
        painter.drawText(text_pos, f"{angle:.{self.precision}f} deg")

    def serialize(self) -> dict:
        data = self._base_serialize()
        data["vertex_pt"] = [self.vertex_pt.x(), self.vertex_pt.y()]
        return data

    @classmethod
    def from_data(cls, data: dict) -> AngularDimension:
        item = cls()
        item._base_deserialize(data)
        vp = data.get("vertex_pt", [0, 0])
        item.vertex_pt = QPointF(vp[0], vp[1])
        return item


register_annotation(AnnotationType.DIMENSION_LINEAR.value, LinearDimension)
register_annotation(AnnotationType.DIMENSION_ALIGNED.value, AlignedDimension)
register_annotation(AnnotationType.DIMENSION_RADIAL.value, RadialDimension)
register_annotation(AnnotationType.DIMENSION_ANGULAR.value, AngularDimension)
