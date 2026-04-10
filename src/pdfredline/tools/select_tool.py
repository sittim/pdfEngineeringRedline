from qtpy.QtCore import QPointF, Qt
from qtpy.QtWidgets import QGraphicsView

from pdfredline.annotations.base import AnnotationItem
from pdfredline.commands.undo import MoveAnnotationCommand, RemoveAnnotationCommand
from pdfredline.tools.base import Tool


class SelectTool(Tool):
    """Default tool for selecting, moving, and deleting annotations."""

    def __init__(self, scene, undo_stack, view: QGraphicsView):
        super().__init__(scene, undo_stack)
        self._view = view
        self._moving_items: list[tuple[AnnotationItem, QPointF]] = []

    def activate(self):
        self._view.setCursor(Qt.CursorShape.ArrowCursor)
        self._view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

    def deactivate(self):
        self._view.setDragMode(QGraphicsView.DragMode.NoDrag)

    def mouse_press(self, event):
        scene_pos = self._view.mapToScene(event.position().toPoint())
        item = self.scene.itemAt(scene_pos, self._view.transform())

        if item and isinstance(item, AnnotationItem):
            if not item.isSelected():
                if not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                    self.scene.clearSelection()
                item.setSelected(True)
            # Record positions for move tracking
            self._moving_items = [
                (it, it.pos()) for it in self.scene.selectedItems()
                if isinstance(it, AnnotationItem)
            ]
        elif not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.scene.clearSelection()
            self._moving_items = []

    def mouse_release(self, event):
        # Check if any selected items actually moved
        for item, old_pos in self._moving_items:
            if item.pos() != old_pos:
                cmd = MoveAnnotationCommand(item, old_pos, item.pos())
                self.undo_stack.push(cmd)
        self._moving_items = []

    def key_press(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            selected = [
                it for it in self.scene.selectedItems()
                if isinstance(it, AnnotationItem)
            ]
            for item in selected:
                cmd = RemoveAnnotationCommand(self.scene, item)
                self.undo_stack.push(cmd)
        elif event.key() == Qt.Key.Key_Escape:
            self.scene.clearSelection()
