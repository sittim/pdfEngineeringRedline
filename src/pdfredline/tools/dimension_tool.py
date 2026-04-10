"""Tools for placing dimension annotations with snap-to-point."""
from __future__ import annotations

from qtpy.QtCore import QPointF, Qt
from qtpy.QtGui import QColor, QPen
from qtpy.QtWidgets import QGraphicsEllipseItem, QGraphicsView

from pdfredline.annotations.dimensions import (
    AlignedDimension,
    AngularDimension,
    LinearDimension,
    RadialDimension,
)
from pdfredline.annotations.snap import SnapEngine
from pdfredline.commands.undo import AddAnnotationCommand
from pdfredline.tools.base import Tool

SNAP_INDICATOR_SIZE = 6


class _DimToolBase(Tool):
    """Base for dimension tools with snap support."""

    def __init__(self, scene, undo_stack, view: QGraphicsView,
                 units="mm", precision=2):
        super().__init__(scene, undo_stack)
        self._view = view
        self._snap_engine = SnapEngine(scene)
        self._snap_indicator: QGraphicsEllipseItem | None = None
        self.units = units
        self.precision = precision

    def activate(self):
        self._view.setCursor(Qt.CursorShape.CrossCursor)
        self._view.setDragMode(QGraphicsView.DragMode.NoDrag)

    def deactivate(self):
        self._remove_snap_indicator()
        self._view.setCursor(Qt.CursorShape.ArrowCursor)

    def _scene_pos(self, event) -> QPointF:
        return self._view.mapToScene(event.position().toPoint())

    def _show_snap_indicator(self, pos: QPointF):
        if self._snap_indicator is None:
            s = SNAP_INDICATOR_SIZE
            self._snap_indicator = QGraphicsEllipseItem(-s, -s, 2 * s, 2 * s)
            self._snap_indicator.setPen(QPen(QColor(0, 200, 0), 1.5))
            self._snap_indicator.setBrush(QColor(0, 200, 0, 80))
            self._snap_indicator.setZValue(50)
            self.scene.addItem(self._snap_indicator)
        self._snap_indicator.setPos(pos)

    def _remove_snap_indicator(self):
        if self._snap_indicator and self._snap_indicator.scene():
            self.scene.removeItem(self._snap_indicator)
        self._snap_indicator = None

    def _snap_pos(self, event) -> tuple[QPointF, object | None]:
        """Get snapped position. Returns (pos, snap_result_or_None)."""
        pos = self._scene_pos(event)
        result = self._snap_engine.find_nearest(pos)
        if result:
            self._show_snap_indicator(result.point)
            return result.point, result
        self._remove_snap_indicator()
        return pos, None

    def key_press(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._remove_snap_indicator()


class LinearDimensionTool(_DimToolBase):
    def __init__(self, scene, undo_stack, view, units="mm", precision=2):
        super().__init__(scene, undo_stack, view, units, precision)
        self._first_pt: QPointF | None = None
        self._first_snap = None

    def mouse_press(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos, snap = self._snap_pos(event)
        if self._first_pt is None:
            self._first_pt = pos
            self._first_snap = snap
        else:
            dim = LinearDimension()
            dim.source_pt = self._first_pt
            dim.target_pt = pos
            dim.horizontal = abs(pos.x() - self._first_pt.x()) >= abs(
                pos.y() - self._first_pt.y()
            )
            dim.units = self.units
            dim.precision = self.precision
            dim.setPos(QPointF(0, 0))
            dim.setZValue(30)
            if self._first_snap:
                dim.source_ref = (self._first_snap.annotation.annotation_id,
                                  self._first_snap.snap_index)
            if snap:
                dim.target_ref = (snap.annotation.annotation_id, snap.snap_index)
            self.undo_stack.push(AddAnnotationCommand(self.scene, dim, "Add Linear Dimension"))
            self._first_pt = None
            self._first_snap = None
            self._remove_snap_indicator()
            self.finish()

    def mouse_move(self, event):
        self._snap_pos(event)


class AlignedDimensionTool(_DimToolBase):
    def __init__(self, scene, undo_stack, view, units="mm", precision=2):
        super().__init__(scene, undo_stack, view, units, precision)
        self._first_pt: QPointF | None = None
        self._first_snap = None

    def mouse_press(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos, snap = self._snap_pos(event)
        if self._first_pt is None:
            self._first_pt = pos
            self._first_snap = snap
        else:
            dim = AlignedDimension()
            dim.source_pt = self._first_pt
            dim.target_pt = pos
            dim.units = self.units
            dim.precision = self.precision
            dim.setPos(QPointF(0, 0))
            dim.setZValue(30)
            if self._first_snap:
                dim.source_ref = (self._first_snap.annotation.annotation_id,
                                  self._first_snap.snap_index)
            if snap:
                dim.target_ref = (snap.annotation.annotation_id, snap.snap_index)
            self.undo_stack.push(AddAnnotationCommand(self.scene, dim, "Add Aligned Dimension"))
            self._first_pt = None
            self._first_snap = None
            self._remove_snap_indicator()
            self.finish()

    def mouse_move(self, event):
        self._snap_pos(event)


class RadialDimensionTool(_DimToolBase):
    def mouse_press(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos, snap = self._snap_pos(event)
        committed = False
        if snap:
            from pdfredline.annotations.shapes import CircleAnnotation, OvalAnnotation
            ann = snap.annotation
            if isinstance(ann, CircleAnnotation):
                dim = RadialDimension()
                dim.source_pt = ann.pos()
                dim.radius_value = ann.radius
                dim.units = self.units
                dim.precision = self.precision
                dim.setPos(QPointF(0, 0))
                dim.setZValue(30)
                self.undo_stack.push(
                    AddAnnotationCommand(self.scene, dim, "Add Radial Dimension")
                )
                committed = True
            elif isinstance(ann, OvalAnnotation):
                dim = RadialDimension()
                dim.source_pt = ann.pos()
                dim.radius_value = ann.rx
                dim.units = self.units
                dim.precision = self.precision
                dim.setPos(QPointF(0, 0))
                dim.setZValue(30)
                self.undo_stack.push(
                    AddAnnotationCommand(self.scene, dim, "Add Radial Dimension")
                )
                committed = True
        self._remove_snap_indicator()
        if committed:
            self.finish()

    def mouse_move(self, event):
        self._snap_pos(event)


class AngularDimensionTool(_DimToolBase):
    def __init__(self, scene, undo_stack, view, units="mm", precision=2):
        super().__init__(scene, undo_stack, view, units, precision)
        self._clicks: list[tuple[QPointF, object | None]] = []

    def mouse_press(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos, snap = self._snap_pos(event)
        self._clicks.append((pos, snap))

        if len(self._clicks) == 3:
            # 3 clicks: vertex, source, target
            vertex = self._clicks[0][0]
            source = self._clicks[1][0]
            target = self._clicks[2][0]

            dim = AngularDimension()
            dim.vertex_pt = vertex
            dim.source_pt = source
            dim.target_pt = target
            dim.units = self.units
            dim.precision = self.precision
            dim.setPos(QPointF(0, 0))
            dim.setZValue(30)
            self.undo_stack.push(AddAnnotationCommand(self.scene, dim, "Add Angular Dimension"))
            self._clicks = []
            self._remove_snap_indicator()
            self.finish()

    def mouse_move(self, event):
        self._snap_pos(event)
