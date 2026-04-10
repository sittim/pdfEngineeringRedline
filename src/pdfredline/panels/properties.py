from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDockWidget,
    QDoubleSpinBox,
    QFontComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pdfredline.annotations.shapes import ShapeStyle


class ColorButton(QPushButton):
    """Button that displays a color and opens a color dialog on click."""

    color_changed = Signal(list)

    def __init__(self, color: list[int] | None = None, parent=None):
        super().__init__(parent)
        self._color = color or [255, 0, 0, 255]
        self.setFixedSize(28, 28)
        self._update_style()
        self.clicked.connect(self._pick_color)

    @property
    def color(self) -> list[int]:
        return self._color

    @color.setter
    def color(self, value: list[int]):
        self._color = value
        self._update_style()

    def _update_style(self):
        c = QColor(*self._color)
        self.setStyleSheet(
            f"background-color: {c.name()}; border: 1px solid #888; border-radius: 3px;"
        )

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(*self._color), self, "Choose Color")
        if c.isValid():
            self._color = [c.red(), c.green(), c.blue(), c.alpha()]
            self._update_style()
            self.color_changed.emit(self._color)


class PropertiesPanel(QDockWidget):
    """Dock widget for editing annotation properties."""

    style_changed = Signal(object)  # ShapeStyle
    font_changed = Signal(str, int, list)  # family, size, color

    def __init__(self, parent=None):
        super().__init__("Properties", parent)
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # -- Shape properties --
        layout.addWidget(QLabel("Shape Style"))

        row = QHBoxLayout()
        row.addWidget(QLabel("Stroke:"))
        self._stroke_color_btn = ColorButton([255, 0, 0, 255])
        row.addWidget(self._stroke_color_btn)
        layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Width:"))
        self._stroke_width = QDoubleSpinBox()
        self._stroke_width.setRange(0.5, 20.0)
        self._stroke_width.setValue(2.0)
        self._stroke_width.setSingleStep(0.5)
        row.addWidget(self._stroke_width)
        layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Fill:"))
        self._fill_color_btn = ColorButton([255, 255, 255, 0])
        self._fill_enabled = QPushButton("None")
        self._fill_enabled.setCheckable(True)
        self._fill_enabled.setChecked(False)
        row.addWidget(self._fill_color_btn)
        row.addWidget(self._fill_enabled)
        layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Line:"))
        self._line_style = QComboBox()
        self._line_style.addItems(["solid", "dashed", "dotted"])
        row.addWidget(self._line_style)
        layout.addLayout(row)

        # -- Text properties --
        layout.addWidget(QLabel("Text Style"))

        row = QHBoxLayout()
        row.addWidget(QLabel("Font:"))
        self._font_combo = QFontComboBox()
        row.addWidget(self._font_combo)
        layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Size:"))
        self._font_size = QSpinBox()
        self._font_size.setRange(6, 200)
        self._font_size.setValue(14)
        row.addWidget(self._font_size)
        row.addWidget(QLabel("Color:"))
        self._text_color_btn = ColorButton([255, 0, 0, 255])
        row.addWidget(self._text_color_btn)
        layout.addLayout(row)

        self.setWidget(container)

        # Connect signals
        self._stroke_color_btn.color_changed.connect(self._emit_style)
        self._stroke_width.valueChanged.connect(self._emit_style)
        self._fill_color_btn.color_changed.connect(self._emit_style)
        self._fill_enabled.toggled.connect(self._on_fill_toggled)
        self._line_style.currentTextChanged.connect(self._emit_style)
        self._font_combo.currentFontChanged.connect(self._emit_font)
        self._font_size.valueChanged.connect(self._emit_font)
        self._text_color_btn.color_changed.connect(self._emit_font)

    def current_style(self) -> ShapeStyle:
        fill = self._fill_color_btn.color if self._fill_enabled.isChecked() else None
        return ShapeStyle(
            stroke_color=self._stroke_color_btn.color,
            stroke_width=self._stroke_width.value(),
            fill_color=fill,
            line_style=self._line_style.currentText(),
        )

    def current_font_family(self) -> str:
        return self._font_combo.currentFont().family()

    def current_font_size(self) -> int:
        return self._font_size.value()

    def current_text_color(self) -> list[int]:
        return self._text_color_btn.color

    def _on_fill_toggled(self, checked: bool):
        self._fill_enabled.setText("Fill" if checked else "None")
        self._emit_style()

    def _emit_style(self, *_args):
        self.style_changed.emit(self.current_style())

    def _emit_font(self, *_args):
        self.font_changed.emit(
            self.current_font_family(),
            self.current_font_size(),
            self.current_text_color(),
        )
