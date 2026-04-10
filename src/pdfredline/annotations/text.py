from qtpy.QtCore import QPointF, QRectF, Qt
from qtpy.QtGui import QColor, QFont, QPainter
from qtpy.QtWidgets import QGraphicsTextItem, QStyleOptionGraphicsItem

from pdfredline.annotations.base import AnnotationItem, AnnotationType
from pdfredline.annotations.registry import register_annotation


class TextAnnotation(AnnotationItem):
    """Editable text annotation rendered as vector text."""

    def __init__(self, content="", font_family="Arial", font_size=14,
                 color=None, parent=None):
        super().__init__(AnnotationType.TEXT, parent)
        self._content = content
        self._font_family = font_family
        self._font_size = font_size
        self._color = color or [255, 0, 0, 255]

        # Internal QGraphicsTextItem for rendering and editing
        self._text_item = QGraphicsTextItem(self)
        self._text_item.setPlainText(content)
        self._text_item.setDefaultTextColor(QColor(*self._color))
        self._text_item.setFont(QFont(font_family, font_size))
        self._text_item.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable, False)
        self._text_item.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable, False)

        self._editing = False

    @property
    def content(self) -> str:
        return self._text_item.toPlainText()

    @content.setter
    def content(self, value: str):
        self._content = value
        self._text_item.setPlainText(value)

    @property
    def font_family(self) -> str:
        return self._font_family

    @font_family.setter
    def font_family(self, value: str):
        self._font_family = value
        self._text_item.setFont(QFont(value, self._font_size))

    @property
    def font_size(self) -> int:
        return self._font_size

    @font_size.setter
    def font_size(self, value: int):
        self._font_size = value
        self._text_item.setFont(QFont(self._font_family, value))

    @property
    def color(self) -> list[int]:
        return self._color

    @color.setter
    def color(self, value: list[int]):
        self._color = value
        self._text_item.setDefaultTextColor(QColor(*value))

    def start_editing(self):
        """Enter inline text editing mode."""
        self._editing = True
        self._text_item.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        self._text_item.setFocus()

    def stop_editing(self) -> str:
        """Exit inline editing mode. Returns the new content."""
        self._editing = False
        self._text_item.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self._content = self._text_item.toPlainText()
        return self._content

    def boundingRect(self) -> QRectF:
        return self._text_item.boundingRect()

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        # The child QGraphicsTextItem handles its own painting
        if self.isSelected() and not self._editing:
            painter.setPen(Qt.PenStyle.DashLine)
            painter.drawRect(self.boundingRect())

    def mouseDoubleClickEvent(self, event):
        self.start_editing()

    def focusOutEvent(self, event):
        if self._editing:
            self.stop_editing()
        super().focusOutEvent(event)

    def snap_points(self) -> list[QPointF]:
        return [self.pos()]

    def serialize(self) -> dict:
        data = super().serialize()
        data["content"] = self.content
        data["font_family"] = self._font_family
        data["font_size"] = self._font_size
        data["color"] = self._color
        return data

    @classmethod
    def from_data(cls, data: dict) -> "TextAnnotation":
        item = cls(
            content=data.get("content", ""),
            font_family=data.get("font_family", "Arial"),
            font_size=data.get("font_size", 14),
            color=data.get("color", [255, 0, 0, 255]),
        )
        item.deserialize_base(data)
        return item


register_annotation(AnnotationType.TEXT.value, TextAnnotation)
