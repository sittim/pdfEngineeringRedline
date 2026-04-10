from qtpy.QtCore import Qt
from qtpy.QtWidgets import QGraphicsView

from pdfredline.annotations.symbols import SymbolAnnotation
from pdfredline.commands.undo import AddAnnotationCommand
from pdfredline.symbols.library import SymbolDefinition
from pdfredline.tools.base import Tool


class SymbolTool(Tool):
    """Click to place a symbol annotation."""

    def __init__(self, scene, undo_stack, view: QGraphicsView,
                 symbol_def: SymbolDefinition, parameters: dict[str, str] | None = None):
        super().__init__(scene, undo_stack)
        self._view = view
        self.symbol_def = symbol_def
        self.parameters = parameters or {
            p["id"]: p.get("default", "") for p in symbol_def.parameters
        }

    def activate(self):
        self._view.setCursor(Qt.CursorShape.CrossCursor)
        self._view.setDragMode(QGraphicsView.DragMode.NoDrag)

    def deactivate(self):
        self._view.setCursor(Qt.CursorShape.ArrowCursor)

    def mouse_press(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = self._view.mapToScene(event.position().toPoint())
        item = SymbolAnnotation(
            svg_path=self.symbol_def.svg_path,
            symbol_name=self.symbol_def.name,
            parameters=dict(self.parameters),
        )
        item.setPos(pos)
        item.setZValue(40)
        self.undo_stack.push(AddAnnotationCommand(self.scene, item, "Place Symbol"))
        self.finish()
