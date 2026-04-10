from qtpy.QtCore import QPointF
from qtpy.QtGui import QUndoCommand, QUndoStack
from qtpy.QtWidgets import QGraphicsScene

from pdfredline.annotations.base import AnnotationItem


class AddAnnotationCommand(QUndoCommand):
    def __init__(self, scene: QGraphicsScene, item: AnnotationItem, text: str = "Add Annotation"):
        super().__init__(text)
        self._scene = scene
        self._item = item

    def redo(self):
        self._scene.addItem(self._item)

    def undo(self):
        self._scene.removeItem(self._item)


class RemoveAnnotationCommand(QUndoCommand):
    def __init__(self, scene: QGraphicsScene, item: AnnotationItem,
                 text: str = "Remove Annotation"):
        super().__init__(text)
        self._scene = scene
        self._item = item

    def redo(self):
        self._scene.removeItem(self._item)

    def undo(self):
        self._scene.addItem(self._item)


class MoveAnnotationCommand(QUndoCommand):
    def __init__(self, item: AnnotationItem, old_pos: QPointF, new_pos: QPointF,
                 text: str = "Move Annotation"):
        super().__init__(text)
        self._item = item
        self._old_pos = old_pos
        self._new_pos = new_pos

    def redo(self):
        self._item.setPos(self._new_pos)

    def undo(self):
        self._item.setPos(self._old_pos)


class ModifyAnnotationCommand(QUndoCommand):
    """Generic property modification command. Stores old/new values for any attribute."""

    def __init__(self, item: AnnotationItem, attr: str, old_value, new_value,
                 text: str = "Modify Annotation"):
        super().__init__(text)
        self._item = item
        self._attr = attr
        self._old_value = old_value
        self._new_value = new_value

    def redo(self):
        setattr(self._item, self._attr, self._new_value)
        self._item.update()

    def undo(self):
        setattr(self._item, self._attr, self._old_value)
        self._item.update()


class EditSymbolParametersCommand(QUndoCommand):
    """Replace all parameter values on a SymbolAnnotation in one undo step."""

    def __init__(self, item, old_params: dict, new_params: dict,
                 text: str = "Edit Symbol Parameters"):
        super().__init__(text)
        self._item = item
        self._old = dict(old_params)
        self._new = dict(new_params)

    def redo(self):
        self._item.parameters = dict(self._new)
        self._item._update_renderer()
        self._item.prepareGeometryChange()
        self._item.update()

    def undo(self):
        self._item.parameters = dict(self._old)
        self._item._update_renderer()
        self._item.prepareGeometryChange()
        self._item.update()


class UndoStack(QUndoStack):
    """Thin wrapper over QUndoStack for the application."""

    def __init__(self, parent=None):
        super().__init__(parent)
