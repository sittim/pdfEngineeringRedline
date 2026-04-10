"""Ribbon toolbar setup using pyqtribbon. Single 'Home' tab with stacked buttons."""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

import qtawesome as qta
from pyqtribbon import RibbonBar
from pyqtribbon.category import RibbonCategory
from pyqtribbon.panel import RibbonPanel
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFontComboBox,
    QHBoxLayout,
    QLabel,
    QMenuBar,
    QSpinBox,
    QWidget,
)

from pdfredline.panels.properties import ColorButton

if TYPE_CHECKING:
    from pdfredline.app import MainWindow

ButtonKind = Literal["small", "medium", "large"]

RIBBON_STYLE = """
QMenuBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #fafafa, stop:1 #e8e8e8);
    border-bottom: 1px solid #c0c0c0;
}
RibbonCategory, RibbonNormalCategory {
    background: #f5f5f5;
}
RibbonPanel {
    background: #fafafa;
    border: 1px solid #d4d4d4;
    border-radius: 4px;
    margin: 2px;
}
RibbonToolButton {
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 3px;
    background: transparent;
    color: #2a2a2a;
}
RibbonToolButton:hover {
    background: #d8e6f5;
    border: 1px solid #7ba7d9;
}
RibbonToolButton:pressed {
    background: #b8d0ec;
    border: 1px solid #5a8ac0;
}
QLabel {
    color: #404040;
    font-size: 11px;
}
QDoubleSpinBox, QSpinBox, QComboBox, QFontComboBox {
    border: 1px solid #b0b0b0;
    border-radius: 3px;
    padding: 1px 4px;
    background: white;
    min-height: 18px;
}
QDoubleSpinBox:hover, QSpinBox:hover, QComboBox:hover, QFontComboBox:hover {
    border-color: #7ba7d9;
}
"""


def setup_ribbon(window: MainWindow) -> RibbonBar:
    ribbon = RibbonBar()
    # Disable native macOS menu bar handling so the ribbon stays in-window.
    QMenuBar.setNativeMenuBar(ribbon, False)
    ribbon.setStyleSheet(RIBBON_STYLE)

    cat = ribbon.addCategory("Home")
    _add_file_panel(cat, window)
    _add_edit_panel(cat, window)
    _add_view_panel(cat, window)
    _add_tools_panel(cat, window)
    _add_style_panel(cat, window)

    return ribbon


# -- Helpers --

def _btn(panel: RibbonPanel, kind: ButtonKind, name: str,
         icon_name: str, slot: Callable, tooltip: str | None = None):
    """Add a button to a panel with an icon and slot."""
    icon = qta.icon(icon_name) if icon_name else QIcon()
    method = {
        "small": panel.addSmallButton,
        "medium": panel.addMediumButton,
        "large": panel.addLargeButton,
    }[kind]
    return method(name, icon, slot=slot, tooltip=tooltip or name)


def _label_widget(label_text: str, widget: QWidget) -> QWidget:
    """Wrap a widget with a label to its left, suitable for addSmallWidget."""
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(2, 0, 2, 0)
    layout.setSpacing(4)
    layout.addWidget(QLabel(label_text))
    layout.addWidget(widget)
    return container


# -- Panels --

def _add_file_panel(cat: RibbonCategory, window: MainWindow):
    panel = cat.addPanel("File")
    _btn(panel, "large", "Open\nPDF", "fa6s.folder-open", window._open_file)
    _btn(panel, "small", "Save", "fa6s.floppy-disk", window._save_project)
    _btn(panel, "small", "Save As", "fa6s.copy", window._save_project_as)
    _btn(panel, "small", "Open Project", "fa6s.folder-tree", window._open_project)
    _btn(panel, "small", "Export PDF", "fa6s.file-export", window._export_pdf)
    _btn(panel, "small", "Print", "fa6s.print", window._print_document)


def _add_edit_panel(cat: RibbonCategory, window: MainWindow):
    panel = cat.addPanel("Edit")
    _btn(panel, "large", "Undo", "fa6s.rotate-left", window._undo_stack.undo)
    _btn(panel, "large", "Redo", "fa6s.rotate-right", window._undo_stack.redo)
    _btn(panel, "small", "Cut", "fa6s.scissors", window._cut_selection)
    _btn(panel, "small", "Copy", "fa6s.copy", window._copy_selection)
    _btn(panel, "small", "Paste", "fa6s.paste", window._paste_clipboard)
    _btn(panel, "small", "Select All", "fa6s.object-group", window._select_all)
    _btn(panel, "small", "Delete", "fa6s.trash", window._delete_selection)


def _add_view_panel(cat: RibbonCategory, window: MainWindow):
    panel = cat.addPanel("View")
    _btn(panel, "large", "Zoom\nIn", "fa6s.magnifying-glass-plus", window.view.zoom_in)
    _btn(panel, "large", "Zoom\nOut", "fa6s.magnifying-glass-minus", window.view.zoom_out)
    _btn(panel, "small", "Fit Page", "fa6s.expand", window.view.fit_page)
    _btn(panel, "small", "Prev Page", "fa6s.chevron-left", window._prev_page)
    _btn(panel, "small", "Next Page", "fa6s.chevron-right", window._next_page)


def _add_tools_panel(cat: RibbonCategory, window: MainWindow):
    panel = cat.addPanel("Tools")
    _btn(panel, "large", "Select", "fa6s.arrow-pointer", window._set_select_tool)
    # Shape stack 1
    _btn(panel, "small", "Line", "fa6s.slash", window._set_line_tool)
    _btn(panel, "small", "Rectangle", "fa6s.square", window._set_rect_tool)
    _btn(panel, "small", "Circle", "fa6s.circle", window._set_circle_tool)
    # Shape stack 2
    _btn(panel, "small", "Oval", "fa6s.circle", window._set_oval_tool)
    _btn(panel, "small", "Triangle", "fa6s.play", window._set_triangle_tool)
    _btn(panel, "small", "Freehand", "fa6s.pencil", window._set_freehand_tool)
    # Annotation stack
    _btn(panel, "small", "Text", "fa6s.font", window._set_text_tool)
    _btn(panel, "small", "Symbol", "fa6s.shapes", window._open_symbol_browser)
    # Dimensions stack 1
    _btn(panel, "small", "Linear Dim", "fa6s.ruler-horizontal",
         lambda: window._set_dimension_tool("linear"))
    _btn(panel, "small", "Aligned Dim", "fa6s.ruler",
         lambda: window._set_dimension_tool("aligned"))
    _btn(panel, "small", "Radial Dim", "fa6s.compass-drafting",
         lambda: window._set_dimension_tool("radial"))
    # Dimensions stack 2 (only one entry)
    _btn(panel, "small", "Angular Dim", "fa6s.angle-up",
         lambda: window._set_dimension_tool("angular"))


def _add_style_panel(cat: RibbonCategory, window: MainWindow):
    panel = cat.addPanel("Style")

    # Stroke color
    window._ribbon_stroke_color = ColorButton([255, 0, 0, 255])
    panel.addSmallWidget(_label_widget("Stroke:", window._ribbon_stroke_color))

    # Stroke width
    window._ribbon_stroke_width = QDoubleSpinBox()
    window._ribbon_stroke_width.setRange(0.5, 20.0)
    window._ribbon_stroke_width.setValue(2.0)
    window._ribbon_stroke_width.setSingleStep(0.5)
    window._ribbon_stroke_width.setMaximumWidth(70)
    panel.addSmallWidget(_label_widget("Width:", window._ribbon_stroke_width))

    # Line style
    window._ribbon_line_style = QComboBox()
    window._ribbon_line_style.addItems(["solid", "dashed", "dotted"])
    window._ribbon_line_style.setMaximumWidth(80)
    panel.addSmallWidget(_label_widget("Line:", window._ribbon_line_style))

    # Font
    window._ribbon_font_combo = QFontComboBox()
    window._ribbon_font_combo.setMaximumWidth(140)
    panel.addSmallWidget(_label_widget("Font:", window._ribbon_font_combo))

    # Font size
    window._ribbon_font_size = QSpinBox()
    window._ribbon_font_size.setRange(6, 200)
    window._ribbon_font_size.setValue(14)
    window._ribbon_font_size.setMaximumWidth(60)
    panel.addSmallWidget(_label_widget("Size:", window._ribbon_font_size))

    # Text color
    window._ribbon_text_color = ColorButton([255, 0, 0, 255])
    panel.addSmallWidget(_label_widget("Text:", window._ribbon_text_color))

    # Dimension units
    window._ribbon_dim_units = QComboBox()
    window._ribbon_dim_units.addItems(["mm", "inches"])
    window._ribbon_dim_units.setMaximumWidth(80)
    panel.addSmallWidget(_label_widget("Units:", window._ribbon_dim_units))

    # Dimension precision
    window._ribbon_dim_precision = QSpinBox()
    window._ribbon_dim_precision.setRange(0, 6)
    window._ribbon_dim_precision.setValue(2)
    window._ribbon_dim_precision.setMaximumWidth(50)
    panel.addSmallWidget(_label_widget("Precision:", window._ribbon_dim_precision))

    # Wire sync handlers
    window._ribbon_stroke_color.color_changed.connect(lambda _c: _sync_style(window))
    window._ribbon_stroke_width.valueChanged.connect(lambda: _sync_style(window))
    window._ribbon_line_style.currentTextChanged.connect(lambda: _sync_style(window))
    window._ribbon_font_combo.currentFontChanged.connect(lambda: _sync_text(window))
    window._ribbon_font_size.valueChanged.connect(lambda: _sync_text(window))
    window._ribbon_text_color.color_changed.connect(lambda _c: _sync_text(window))


def _sync_style(window: MainWindow):
    p = window.props_panel
    p._stroke_color_btn.color = window._ribbon_stroke_color.color
    p._stroke_color_btn._update_style()
    p._stroke_width.setValue(window._ribbon_stroke_width.value())
    p._line_style.setCurrentText(window._ribbon_line_style.currentText())


def _sync_text(window: MainWindow):
    p = window.props_panel
    p._font_combo.setCurrentFont(window._ribbon_font_combo.currentFont())
    p._font_size.setValue(window._ribbon_font_size.value())
    p._text_color_btn.color = window._ribbon_text_color.color
    p._text_color_btn._update_style()
