from qtpy.QtCore import QPointF, QRectF
from qtpy.QtGui import QPainter
from qtpy.QtWidgets import QStyleOptionGraphicsItem

from pdfredline.annotations.base import AnnotationItem, AnnotationType
from pdfredline.canvas.scene import RedlineScene
from pdfredline.commands.undo import (
    AddAnnotationCommand,
    MoveAnnotationCommand,
    RemoveAnnotationCommand,
    UndoStack,
)


class DummyAnnotation(AnnotationItem):
    """Minimal concrete annotation for testing."""

    def __init__(self):
        super().__init__(AnnotationType.RECT)

    def boundingRect(self):
        return QRectF(0, 0, 100, 50)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        painter.drawRect(self.boundingRect())

    @classmethod
    def from_data(cls, data: dict):
        item = cls()
        item.deserialize_base(data)
        return item


def test_add_and_undo(qapp):
    scene = RedlineScene()
    stack = UndoStack()
    item = DummyAnnotation()

    cmd = AddAnnotationCommand(scene, item)
    stack.push(cmd)
    assert item.scene() is scene

    stack.undo()
    assert item.scene() is None

    stack.redo()
    assert item.scene() is scene


def test_remove_and_undo(qapp):
    scene = RedlineScene()
    stack = UndoStack()
    item = DummyAnnotation()
    scene.addItem(item)

    cmd = RemoveAnnotationCommand(scene, item)
    stack.push(cmd)
    assert item.scene() is None

    stack.undo()
    assert item.scene() is scene


def test_move_and_undo(qapp):
    scene = RedlineScene()
    stack = UndoStack()
    item = DummyAnnotation()
    scene.addItem(item)
    item.setPos(10, 20)

    old_pos = QPointF(10, 20)
    new_pos = QPointF(100, 200)

    cmd = MoveAnnotationCommand(item, old_pos, new_pos)
    stack.push(cmd)
    assert item.pos() == new_pos

    stack.undo()
    assert item.pos() == old_pos
