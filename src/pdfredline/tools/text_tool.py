from qtpy.QtCore import Qt
from qtpy.QtWidgets import QGraphicsView

from pdfredline.annotations.text import TextAnnotation
from pdfredline.commands.undo import AddAnnotationCommand
from pdfredline.tools.base import Tool


class TextTool(Tool):
    """Click to place a text annotation and immediately enter edit mode."""

    def __init__(self, scene, undo_stack, view: QGraphicsView,
                 font_family="Arial", font_size=14, color=None):
        super().__init__(scene, undo_stack)
        self._view = view
        self.font_family = font_family
        self.font_size = font_size
        self.color = color or [255, 0, 0, 255]

    def activate(self):
        self._view.setCursor(Qt.CursorShape.IBeamCursor)
        self._view.setDragMode(QGraphicsView.DragMode.NoDrag)

    def deactivate(self):
        self._view.setCursor(Qt.CursorShape.ArrowCursor)

    def mouse_press(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = self._view.mapToScene(event.position().toPoint())
        item = TextAnnotation(
            content="Text",
            font_family=self.font_family,
            font_size=self.font_size,
            color=list(self.color),
        )
        item.setPos(pos)
        item.setZValue(20)
        self.undo_stack.push(AddAnnotationCommand(self.scene, item, "Add Text"))
        item.start_editing()
        self.finish()
