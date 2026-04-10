from __future__ import annotations

from dataclasses import dataclass, field

from qtpy.QtCore import QPointF, QRectF, Qt
from qtpy.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPolygonF

from pdfredline.annotations.base import AnnotationItem, AnnotationType
from pdfredline.annotations.registry import register_annotation


@dataclass
class ShapeStyle:
    stroke_color: list[int] = field(default_factory=lambda: [255, 0, 0, 255])
    stroke_width: float = 2.0
    fill_color: list[int] | None = None
    line_style: str = "solid"

    def pen(self) -> QPen:
        pen = QPen(QColor(*self.stroke_color), self.stroke_width)
        if self.line_style == "dashed":
            pen.setStyle(Qt.PenStyle.DashLine)
        elif self.line_style == "dotted":
            pen.setStyle(Qt.PenStyle.DotLine)
        else:
            pen.setStyle(Qt.PenStyle.SolidLine)
        pen.setCosmetic(True)
        return pen

    def brush(self) -> QBrush:
        if self.fill_color:
            return QBrush(QColor(*self.fill_color))
        return QBrush(Qt.BrushStyle.NoBrush)

    def to_dict(self) -> dict:
        return {
            "stroke_color": self.stroke_color,
            "stroke_width": self.stroke_width,
            "fill_color": self.fill_color,
            "line_style": self.line_style,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ShapeStyle:
        return cls(
            stroke_color=data.get("stroke_color", [255, 0, 0, 255]),
            stroke_width=data.get("stroke_width", 2.0),
            fill_color=data.get("fill_color"),
            line_style=data.get("line_style", "solid"),
        )


class ShapeAnnotation(AnnotationItem):
    """Base for shape annotations with shared style."""

    def __init__(self, annotation_type: AnnotationType, parent=None):
        super().__init__(annotation_type, parent)
        self.style = ShapeStyle()

    def serialize(self) -> dict:
        data = super().serialize()
        data["style"] = self.style.to_dict()
        return data

    def deserialize_base(self, data: dict):
        super().deserialize_base(data)
        if "style" in data:
            self.style = ShapeStyle.from_dict(data["style"])


# -- Line --

class LineAnnotation(ShapeAnnotation):
    def __init__(self, x1=0.0, y1=0.0, x2=100.0, y2=0.0, parent=None):
        super().__init__(AnnotationType.LINE, parent)
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def boundingRect(self) -> QRectF:
        pad = self.style.stroke_width + 2
        return QRectF(
            min(self.x1, self.x2) - pad, min(self.y1, self.y2) - pad,
            abs(self.x2 - self.x1) + 2 * pad, abs(self.y2 - self.y1) + 2 * pad,
        )

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.moveTo(self.x1, self.y1)
        path.lineTo(self.x2, self.y2)
        stroker = QPainterPath()
        stroker.addPath(path)
        # Widen for easier hit-testing
        from qtpy.QtGui import QPainterPathStroker
        s = QPainterPathStroker()
        s.setWidth(max(self.style.stroke_width + 6, 8))
        return s.createStroke(path)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setPen(self.style.pen())
        painter.drawLine(QPointF(self.x1, self.y1), QPointF(self.x2, self.y2))

    def snap_points(self) -> list[QPointF]:
        p = self.pos()
        return [
            p + QPointF(self.x1, self.y1),
            p + QPointF(self.x2, self.y2),
            p + QPointF((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2),
        ]

    def serialize(self) -> dict:
        data = super().serialize()
        data["geometry"] = {"x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2}
        return data

    @classmethod
    def from_data(cls, data: dict) -> LineAnnotation:
        g = data.get("geometry", {})
        item = cls(g.get("x1", 0), g.get("y1", 0), g.get("x2", 100), g.get("y2", 0))
        item.deserialize_base(data)
        return item


# -- Rectangle --

class RectAnnotation(ShapeAnnotation):
    def __init__(self, width=100.0, height=60.0, parent=None):
        super().__init__(AnnotationType.RECT, parent)
        self.width = width
        self.height = height

    def boundingRect(self) -> QRectF:
        pad = self.style.stroke_width + 1
        return QRectF(-pad, -pad, self.width + 2 * pad, self.height + 2 * pad)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setPen(self.style.pen())
        painter.setBrush(self.style.brush())
        painter.drawRect(QRectF(0, 0, self.width, self.height))

    def snap_points(self) -> list[QPointF]:
        p = self.pos()
        w, h = self.width, self.height
        return [
            p, p + QPointF(w, 0), p + QPointF(w, h), p + QPointF(0, h),
            p + QPointF(w / 2, 0), p + QPointF(w, h / 2),
            p + QPointF(w / 2, h), p + QPointF(0, h / 2),
            p + QPointF(w / 2, h / 2),
        ]

    def serialize(self) -> dict:
        data = super().serialize()
        data["geometry"] = {"width": self.width, "height": self.height}
        return data

    @classmethod
    def from_data(cls, data: dict) -> RectAnnotation:
        g = data.get("geometry", {})
        item = cls(g.get("width", 100), g.get("height", 60))
        item.deserialize_base(data)
        return item


# -- Circle --

class CircleAnnotation(ShapeAnnotation):
    def __init__(self, radius=50.0, parent=None):
        super().__init__(AnnotationType.CIRCLE, parent)
        self.radius = radius

    def boundingRect(self) -> QRectF:
        pad = self.style.stroke_width + 1
        r = self.radius
        return QRectF(-r - pad, -r - pad, 2 * r + 2 * pad, 2 * r + 2 * pad)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setPen(self.style.pen())
        painter.setBrush(self.style.brush())
        painter.drawEllipse(QPointF(0, 0), self.radius, self.radius)

    def snap_points(self) -> list[QPointF]:
        p = self.pos()
        r = self.radius
        return [
            p,  # center
            p + QPointF(r, 0), p + QPointF(-r, 0),
            p + QPointF(0, r), p + QPointF(0, -r),
        ]

    def serialize(self) -> dict:
        data = super().serialize()
        data["geometry"] = {"radius": self.radius}
        return data

    @classmethod
    def from_data(cls, data: dict) -> CircleAnnotation:
        g = data.get("geometry", {})
        item = cls(g.get("radius", 50))
        item.deserialize_base(data)
        return item


# -- Oval --

class OvalAnnotation(ShapeAnnotation):
    def __init__(self, rx=60.0, ry=40.0, parent=None):
        super().__init__(AnnotationType.OVAL, parent)
        self.rx = rx
        self.ry = ry

    def boundingRect(self) -> QRectF:
        pad = self.style.stroke_width + 1
        return QRectF(-self.rx - pad, -self.ry - pad,
                       2 * self.rx + 2 * pad, 2 * self.ry + 2 * pad)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setPen(self.style.pen())
        painter.setBrush(self.style.brush())
        painter.drawEllipse(QPointF(0, 0), self.rx, self.ry)

    def snap_points(self) -> list[QPointF]:
        p = self.pos()
        return [
            p,
            p + QPointF(self.rx, 0), p + QPointF(-self.rx, 0),
            p + QPointF(0, self.ry), p + QPointF(0, -self.ry),
        ]

    def serialize(self) -> dict:
        data = super().serialize()
        data["geometry"] = {"rx": self.rx, "ry": self.ry}
        return data

    @classmethod
    def from_data(cls, data: dict) -> OvalAnnotation:
        g = data.get("geometry", {})
        item = cls(g.get("rx", 60), g.get("ry", 40))
        item.deserialize_base(data)
        return item


# -- Triangle --

class TriangleAnnotation(ShapeAnnotation):
    def __init__(self, points: list[tuple[float, float]] | None = None, parent=None):
        super().__init__(AnnotationType.TRIANGLE, parent)
        self.points = points or [(0, 0), (100, 0), (50, -80)]

    def boundingRect(self) -> QRectF:
        pad = self.style.stroke_width + 1
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        return QRectF(
            min(xs) - pad, min(ys) - pad,
            max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad,
        )

    def paint(self, painter: QPainter, option, widget=None):
        painter.setPen(self.style.pen())
        painter.setBrush(self.style.brush())
        polygon = QPolygonF([QPointF(x, y) for x, y in self.points])
        painter.drawPolygon(polygon)

    def snap_points(self) -> list[QPointF]:
        p = self.pos()
        pts = [p + QPointF(x, y) for x, y in self.points]
        # Add midpoints
        for i in range(3):
            j = (i + 1) % 3
            mid = (pts[i] + pts[j]) / 2
            pts.append(mid)
        return pts

    def serialize(self) -> dict:
        data = super().serialize()
        data["geometry"] = {"points": self.points}
        return data

    @classmethod
    def from_data(cls, data: dict) -> TriangleAnnotation:
        g = data.get("geometry", {})
        pts = g.get("points", [(0, 0), (100, 0), (50, -80)])
        item = cls([(p[0], p[1]) for p in pts])
        item.deserialize_base(data)
        return item


# -- Freehand --

class FreehandAnnotation(ShapeAnnotation):
    def __init__(self, points: list[tuple[float, float]] | None = None, parent=None):
        super().__init__(AnnotationType.FREEHAND, parent)
        self.points = points or []

    def boundingRect(self) -> QRectF:
        if not self.points:
            return QRectF()
        pad = self.style.stroke_width + 2
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        return QRectF(
            min(xs) - pad, min(ys) - pad,
            max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad,
        )

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        if self.points:
            path.moveTo(self.points[0][0], self.points[0][1])
            for x, y in self.points[1:]:
                path.lineTo(x, y)
        from qtpy.QtGui import QPainterPathStroker
        s = QPainterPathStroker()
        s.setWidth(max(self.style.stroke_width + 6, 8))
        return s.createStroke(path)

    def paint(self, painter: QPainter, option, widget=None):
        if len(self.points) < 2:
            return
        painter.setPen(self.style.pen())
        path = QPainterPath()
        path.moveTo(self.points[0][0], self.points[0][1])
        for x, y in self.points[1:]:
            path.lineTo(x, y)
        painter.drawPath(path)

    def snap_points(self) -> list[QPointF]:
        if not self.points:
            return []
        p = self.pos()
        return [
            p + QPointF(self.points[0][0], self.points[0][1]),
            p + QPointF(self.points[-1][0], self.points[-1][1]),
        ]

    def serialize(self) -> dict:
        data = super().serialize()
        data["geometry"] = {"points": self.points}
        return data

    @classmethod
    def from_data(cls, data: dict) -> FreehandAnnotation:
        g = data.get("geometry", {})
        pts = g.get("points", [])
        item = cls([(p[0], p[1]) for p in pts])
        item.deserialize_base(data)
        return item


# Register all shape types
register_annotation(AnnotationType.LINE.value, LineAnnotation)
register_annotation(AnnotationType.RECT.value, RectAnnotation)
register_annotation(AnnotationType.CIRCLE.value, CircleAnnotation)
register_annotation(AnnotationType.OVAL.value, OvalAnnotation)
register_annotation(AnnotationType.TRIANGLE.value, TriangleAnnotation)
register_annotation(AnnotationType.FREEHAND.value, FreehandAnnotation)
