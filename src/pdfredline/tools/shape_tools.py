from qtpy.QtCore import QPointF, Qt
from qtpy.QtWidgets import QGraphicsView

from pdfredline.annotations.shapes import (
    CircleAnnotation,
    FreehandAnnotation,
    LineAnnotation,
    OvalAnnotation,
    RectAnnotation,
    ShapeStyle,
    TriangleAnnotation,
)
from pdfredline.commands.undo import AddAnnotationCommand
from pdfredline.tools.base import Tool


class _ShapeToolBase(Tool):
    """Base for tools that draw shapes with a preview."""

    def __init__(self, scene, undo_stack, view: QGraphicsView):
        super().__init__(scene, undo_stack)
        self._view = view
        self._preview = None
        self.style = ShapeStyle()

    def activate(self):
        self._view.setCursor(Qt.CursorShape.CrossCursor)
        self._view.setDragMode(QGraphicsView.DragMode.NoDrag)

    def deactivate(self):
        self._remove_preview()
        self._view.setCursor(Qt.CursorShape.ArrowCursor)

    def _scene_pos(self, event) -> QPointF:
        return self._view.mapToScene(event.position().toPoint())

    def _remove_preview(self):
        if self._preview and self._preview.scene():
            self.scene.removeItem(self._preview)
        self._preview = None


class LineTool(_ShapeToolBase):
    """Click start point, click end point."""

    def __init__(self, scene, undo_stack, view):
        super().__init__(scene, undo_stack, view)
        self._start: QPointF | None = None

    def mouse_press(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = self._scene_pos(event)
        if self._start is None:
            self._start = pos
            # Item lives at scene pos = start. Local coords go from (0,0) to delta.
            self._preview = LineAnnotation(0, 0, 0, 0)
            self._preview.style = ShapeStyle(**self.style.to_dict())
            self._preview.setPos(pos)
            self._preview.setOpacity(0.5)
            self._preview.setZValue(10)
            self.scene.addItem(self._preview)
        else:
            start = self._start
            self._remove_preview()
            item = LineAnnotation(0, 0, pos.x() - start.x(), pos.y() - start.y())
            item.style = ShapeStyle(**self.style.to_dict())
            item.setPos(start)
            item.setZValue(10)
            self.undo_stack.push(AddAnnotationCommand(self.scene, item, "Draw Line"))
            self._start = None
            self.finish()

    def mouse_move(self, event):
        if self._preview and self._start:
            pos = self._scene_pos(event)
            self._preview.prepareGeometryChange()
            self._preview.x2 = pos.x() - self._start.x()
            self._preview.y2 = pos.y() - self._start.y()
            self._preview.update()

    def key_press(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._remove_preview()
            self._start = None


class RectTool(_ShapeToolBase):
    """Click one corner, drag to opposite corner."""

    def __init__(self, scene, undo_stack, view):
        super().__init__(scene, undo_stack, view)
        self._start: QPointF | None = None
        self._dragging = False

    def mouse_press(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._start = self._scene_pos(event)
        self._dragging = True
        self._preview = RectAnnotation(0, 0)
        self._preview.style = ShapeStyle(**self.style.to_dict())
        self._preview.setOpacity(0.5)
        self._preview.setZValue(10)
        self._preview.setPos(self._start)
        self.scene.addItem(self._preview)

    def mouse_move(self, event):
        if self._dragging and self._preview and self._start:
            pos = self._scene_pos(event)
            x = min(self._start.x(), pos.x())
            y = min(self._start.y(), pos.y())
            w = abs(pos.x() - self._start.x())
            h = abs(pos.y() - self._start.y())
            self._preview.prepareGeometryChange()
            self._preview.setPos(x, y)
            self._preview.width = w
            self._preview.height = h
            self._preview.update()

    def mouse_release(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self._dragging:
            return
        self._dragging = False
        if self._preview and self._preview.width > 1 and self._preview.height > 1:
            pos = self._preview.pos()
            w, h = self._preview.width, self._preview.height
            self._remove_preview()
            item = RectAnnotation(w, h)
            item.style = ShapeStyle(**self.style.to_dict())
            item.setPos(pos)
            item.setZValue(10)
            self.undo_stack.push(AddAnnotationCommand(self.scene, item, "Draw Rectangle"))
            self._start = None
            self.finish()
            return
        self._remove_preview()
        self._start = None

    def key_press(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._remove_preview()
            self._start = None
            self._dragging = False


class CircleTool(_ShapeToolBase):
    """Click center, drag to set radius."""

    def __init__(self, scene, undo_stack, view):
        super().__init__(scene, undo_stack, view)
        self._center: QPointF | None = None
        self._dragging = False

    def mouse_press(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._center = self._scene_pos(event)
        self._dragging = True
        self._preview = CircleAnnotation(0)
        self._preview.style = ShapeStyle(**self.style.to_dict())
        self._preview.setOpacity(0.5)
        self._preview.setZValue(10)
        self._preview.setPos(self._center)
        self.scene.addItem(self._preview)

    def mouse_move(self, event):
        if self._dragging and self._preview and self._center:
            pos = self._scene_pos(event)
            dx = pos.x() - self._center.x()
            dy = pos.y() - self._center.y()
            import math
            r = math.hypot(dx, dy)
            self._preview.prepareGeometryChange()
            self._preview.radius = r
            self._preview.update()

    def mouse_release(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self._dragging:
            return
        self._dragging = False
        if self._preview and self._preview.radius > 1:
            r = self._preview.radius
            center = self._center
            self._remove_preview()
            item = CircleAnnotation(r)
            item.style = ShapeStyle(**self.style.to_dict())
            item.setPos(center)
            item.setZValue(10)
            self.undo_stack.push(AddAnnotationCommand(self.scene, item, "Draw Circle"))
            self._center = None
            self.finish()
            return
        self._remove_preview()
        self._center = None

    def key_press(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._remove_preview()
            self._center = None
            self._dragging = False


class OvalTool(_ShapeToolBase):
    """Click center, drag to set horizontal and vertical radii."""

    def __init__(self, scene, undo_stack, view):
        super().__init__(scene, undo_stack, view)
        self._center: QPointF | None = None
        self._dragging = False

    def mouse_press(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._center = self._scene_pos(event)
        self._dragging = True
        self._preview = OvalAnnotation(0, 0)
        self._preview.style = ShapeStyle(**self.style.to_dict())
        self._preview.setOpacity(0.5)
        self._preview.setZValue(10)
        self._preview.setPos(self._center)
        self.scene.addItem(self._preview)

    def mouse_move(self, event):
        if self._dragging and self._preview and self._center:
            pos = self._scene_pos(event)
            self._preview.prepareGeometryChange()
            self._preview.rx = abs(pos.x() - self._center.x())
            self._preview.ry = abs(pos.y() - self._center.y())
            self._preview.update()

    def mouse_release(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self._dragging:
            return
        self._dragging = False
        if self._preview and self._preview.rx > 1 and self._preview.ry > 1:
            rx, ry = self._preview.rx, self._preview.ry
            center = self._center
            self._remove_preview()
            item = OvalAnnotation(rx, ry)
            item.style = ShapeStyle(**self.style.to_dict())
            item.setPos(center)
            item.setZValue(10)
            self.undo_stack.push(AddAnnotationCommand(self.scene, item, "Draw Oval"))
            self._center = None
            self.finish()
            return
        self._remove_preview()
        self._center = None

    def key_press(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._remove_preview()
            self._center = None
            self._dragging = False


class TriangleTool(_ShapeToolBase):
    """Click three vertices sequentially."""

    def __init__(self, scene, undo_stack, view):
        super().__init__(scene, undo_stack, view)
        self._vertices: list[QPointF] = []

    def _update_preview(self, cursor_pos: QPointF):
        """Rebuild the preview triangle/line from the current vertices + cursor."""
        self._remove_preview()
        if not self._vertices:
            return
        origin = self._vertices[0]
        if len(self._vertices) == 1:
            # Show rubber-band line from first vertex to cursor
            preview = LineAnnotation(0, 0, cursor_pos.x() - origin.x(),
                                      cursor_pos.y() - origin.y())
        else:
            # Two vertices placed; show triangle with cursor as third point
            pts = [(v.x() - origin.x(), v.y() - origin.y()) for v in self._vertices]
            pts.append((cursor_pos.x() - origin.x(), cursor_pos.y() - origin.y()))
            preview = TriangleAnnotation(pts)
        preview.style = ShapeStyle(**self.style.to_dict())
        preview.setPos(origin)
        preview.setOpacity(0.5)
        preview.setZValue(10)
        self.scene.addItem(preview)
        self._preview = preview

    def mouse_press(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = self._scene_pos(event)
        self._vertices.append(pos)

        if len(self._vertices) == 3:
            origin = self._vertices[0]
            pts = [(v.x() - origin.x(), v.y() - origin.y()) for v in self._vertices]
            self._remove_preview()
            item = TriangleAnnotation(pts)
            item.style = ShapeStyle(**self.style.to_dict())
            item.setPos(origin)
            item.setZValue(10)
            self.undo_stack.push(AddAnnotationCommand(self.scene, item, "Draw Triangle"))
            self._vertices = []
            self.finish()
        else:
            self._update_preview(pos)

    def mouse_move(self, event):
        if self._vertices:
            self._update_preview(self._scene_pos(event))

    def key_press(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._remove_preview()
            self._vertices = []


class FreehandTool(_ShapeToolBase):
    """Press and drag to draw a free-form polyline."""

    def __init__(self, scene, undo_stack, view):
        super().__init__(scene, undo_stack, view)
        self._drawing = False
        self._origin: QPointF | None = None

    def mouse_press(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = self._scene_pos(event)
        self._origin = pos
        self._drawing = True
        self._preview = FreehandAnnotation([(0, 0)])
        self._preview.style = ShapeStyle(**self.style.to_dict())
        self._preview.setOpacity(0.5)
        self._preview.setZValue(10)
        self._preview.setPos(pos)
        self.scene.addItem(self._preview)

    def mouse_move(self, event):
        if self._drawing and self._preview and self._origin:
            pos = self._scene_pos(event)
            self._preview.points.append(
                (pos.x() - self._origin.x(), pos.y() - self._origin.y())
            )
            self._preview.prepareGeometryChange()
            self._preview.update()

    def mouse_release(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self._drawing:
            return
        self._drawing = False
        if self._preview and len(self._preview.points) > 2:
            pts = list(self._preview.points)
            origin = self._origin
            self._remove_preview()
            item = FreehandAnnotation(pts)
            item.style = ShapeStyle(**self.style.to_dict())
            item.setPos(origin)
            item.setZValue(10)
            self.undo_stack.push(AddAnnotationCommand(self.scene, item, "Draw Freehand"))
            self._origin = None
            self.finish()
            return
        self._remove_preview()
        self._origin = None

    def key_press(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._remove_preview()
            self._drawing = False
            self._origin = None
