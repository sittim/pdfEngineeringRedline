"""Symbol annotation — renders parameterized SVG symbols with inline editing."""
from __future__ import annotations

import xml.etree.ElementTree as ET

from qtpy.QtCore import QPointF, QRectF, Qt
from qtpy.QtGui import QPainter
from qtpy.QtSvg import QSvgRenderer
from qtpy.QtWidgets import QGraphicsProxyWidget, QLineEdit

from pdfredline.annotations.base import AnnotationItem, AnnotationType
from pdfredline.annotations.registry import register_annotation


class _ParameterLineEdit(QLineEdit):
    """QLineEdit that delegates key/focus events to a SymbolAnnotation owner."""

    def __init__(self, value: str, owner, parameter_id: str, parent=None):
        super().__init__(value, parent)
        self._owner = owner
        self._parameter_id = parameter_id

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self._owner._cancel_edits()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._owner._commit_edits()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        # Defer the commit so a click on a sibling field can take focus first
        from qtpy.QtCore import QTimer
        QTimer.singleShot(0, self._owner._commit_if_no_focus)


class SymbolAnnotation(AnnotationItem):
    """Annotation that renders an SVG symbol with parameterized text fields.

    Double-click on the symbol to edit its parameter values inline. Each
    parameter gets a QLineEdit positioned over its on-symbol text location.
    Press Enter or click outside to commit, Esc to cancel.
    """

    def __init__(self, svg_path: str = "", symbol_name: str = "",
                 parameters: dict[str, str] | None = None, parent=None):
        super().__init__(AnnotationType.SYMBOL, parent)
        self.svg_path = svg_path
        self.symbol_name = symbol_name
        self.parameters: dict[str, str] = parameters or {}
        self.symbol_scale: float = 1.0
        self._renderer: QSvgRenderer | None = None
        # SVG-coordinate (x, y) of each parameter's <text> element
        self._text_positions: dict[str, tuple[float, float]] = {}
        # SVG default size (set by _update_renderer)
        self._svg_size: tuple[float, float] = (1.0, 1.0)
        # Inline edit state
        self._editing: bool = False
        self._original_params: dict[str, str] | None = None
        self._edit_proxies: dict[str, QGraphicsProxyWidget] = {}
        self._update_renderer()

    # -- SVG rendering and parameter substitution --

    def _update_renderer(self):
        """Rebuild SVG renderer with current parameter values substituted."""
        if not self.svg_path:
            self._renderer = None
            return

        try:
            tree = ET.parse(self.svg_path)
            root = tree.getroot()

            # Capture text element positions (only on first parse — these don't
            # change). We do this by walking BEFORE substitution so we can read
            # the x/y attributes from the original SVG.
            if not self._text_positions:
                self._capture_text_positions(root)

            # Substitute parameter values into <text> elements
            for text_elem in root.iter("{http://www.w3.org/2000/svg}text"):
                elem_id = text_elem.get("id", "")
                if elem_id in self.parameters:
                    text_elem.text = self.parameters[elem_id]
            for text_elem in root.iter("text"):
                elem_id = text_elem.get("id", "")
                if elem_id in self.parameters:
                    text_elem.text = self.parameters[elem_id]

            svg_bytes = ET.tostring(root, encoding="unicode").encode("utf-8")
            self._renderer = QSvgRenderer(svg_bytes)
            if self._renderer.isValid():
                size = self._renderer.defaultSize()
                self._svg_size = (float(size.width()), float(size.height()))
        except Exception:
            self._renderer = None

    def _capture_text_positions(self, root):
        """Walk the SVG tree and record (x, y) of every editable <text id=...>."""
        for text_elem in root.iter("{http://www.w3.org/2000/svg}text"):
            self._capture_one(text_elem)
        for text_elem in root.iter("text"):
            self._capture_one(text_elem)

    def _capture_one(self, text_elem):
        eid = text_elem.get("id", "")
        if not eid:
            return
        try:
            x = float(text_elem.get("x", "0"))
            y = float(text_elem.get("y", "0"))
            self._text_positions[eid] = (x, y)
        except (TypeError, ValueError):
            pass

    def set_parameter(self, key: str, value: str):
        self.parameters[key] = value
        self.prepareGeometryChange()
        self._update_renderer()
        self.update()

    def boundingRect(self) -> QRectF:
        if self._renderer and self._renderer.isValid():
            size = self._renderer.defaultSize()
            w = size.width() * self.symbol_scale
            h = size.height() * self.symbol_scale
            return QRectF(0, 0, w, h)
        return QRectF(0, 0, 50, 50)

    def paint(self, painter: QPainter, option, widget=None):
        if self._renderer and self._renderer.isValid():
            self._renderer.render(painter, self.boundingRect())
        else:
            painter.drawRect(self.boundingRect())
            painter.drawText(self.boundingRect(), "?")
        # Highlight the symbol while editing
        if self._editing:
            from qtpy.QtGui import QColor, QPen
            pen = QPen(QColor(80, 140, 220, 200), 1.5, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.boundingRect().adjusted(-2, -2, 2, 2))

    def snap_points(self) -> list[QPointF]:
        return [self.pos()]

    # -- Inline parameter editing --

    def mouseDoubleClickEvent(self, event):
        if self._editing or not self.parameters:
            super().mouseDoubleClickEvent(event)
            return
        self._open_inline_editors()
        event.accept()

    def _svg_to_local(self, x_svg: float, y_svg: float) -> QPointF:
        """Map an SVG coordinate to the item's local coordinate space."""
        sw, sh = self._svg_size
        rect = self.boundingRect()
        scale_x = rect.width() / sw if sw else 1.0
        scale_y = rect.height() / sh if sh else 1.0
        return QPointF(x_svg * scale_x, y_svg * scale_y)

    def _open_inline_editors(self):
        self._editing = True
        self._original_params = dict(self.parameters)
        for pid, value in self.parameters.items():
            x_svg, y_svg = self._text_positions.get(pid, (0.0, 0.0))
            local = self._svg_to_local(x_svg, y_svg)
            edit = _ParameterLineEdit(value, self, pid)
            edit.setMaximumWidth(80)
            edit.setStyleSheet(
                "QLineEdit { background: rgba(255, 255, 200, 230); "
                "border: 1px solid #888; padding: 1px; font-size: 10px; }"
            )
            edit.textEdited.connect(
                lambda text, key=pid: self._on_field_text_edited(key, text)
            )
            proxy = QGraphicsProxyWidget(self)
            proxy.setWidget(edit)
            # Position so the line edit's vertical center is roughly on the
            # SVG text baseline (y in SVG text is the baseline, not the top)
            proxy.setPos(local.x() - 2, local.y() - 14)
            self._edit_proxies[pid] = proxy
        if self._edit_proxies:
            first_proxy = next(iter(self._edit_proxies.values()))
            first_widget = first_proxy.widget()
            if isinstance(first_widget, QLineEdit):
                first_widget.setFocus()
                first_widget.selectAll()
        self.update()

    def _on_field_text_edited(self, key: str, text: str):
        """Live-update the symbol as the user types so they see the change."""
        self.parameters[key] = text
        self._update_renderer()
        self.update()

    def _commit_edits(self):
        if not self._editing:
            return
        new_params: dict[str, str] = {}
        for pid, proxy in self._edit_proxies.items():
            widget = proxy.widget()
            new_params[pid] = widget.text() if isinstance(widget, QLineEdit) else \
                self.parameters.get(pid, "")
        old_params = dict(self._original_params or {})
        # Roll back to original first so the redo() applies cleanly through undo stack
        self.parameters = old_params
        self._update_renderer()
        self._close_editors()
        if new_params != old_params:
            self._push_edit_command(old_params, new_params)
        else:
            # No change — restore display
            self.update()

    def _push_edit_command(self, old_params: dict, new_params: dict):
        from pdfredline.commands.undo import EditSymbolParametersCommand
        scene = self.scene()
        undo_stack = getattr(scene, "_undo_stack", None) if scene else None
        cmd = EditSymbolParametersCommand(self, old_params, new_params)
        if undo_stack is not None:
            undo_stack.push(cmd)
        else:
            # No undo stack available — apply directly
            cmd.redo()

    def _cancel_edits(self):
        if not self._editing:
            return
        self.parameters = dict(self._original_params or {})
        self._update_renderer()
        self._close_editors()
        self.update()

    def _close_editors(self):
        for proxy in self._edit_proxies.values():
            proxy.setParentItem(None)
            scene = proxy.scene()
            if scene is not None:
                scene.removeItem(proxy)
        self._edit_proxies.clear()
        self._editing = False
        self._original_params = None

    def _commit_if_no_focus(self):
        if not self._editing:
            return
        for proxy in self._edit_proxies.values():
            widget = proxy.widget()
            if isinstance(widget, QLineEdit) and widget.hasFocus():
                return  # focus is still in our editor
        self._commit_edits()

    # -- Serialization --

    def serialize(self) -> dict:
        data = super().serialize()
        data["svg_path"] = self.svg_path
        data["symbol_name"] = self.symbol_name
        data["parameters"] = self.parameters
        data["symbol_scale"] = self.symbol_scale
        return data

    @classmethod
    def from_data(cls, data: dict) -> SymbolAnnotation:
        item = cls(
            svg_path=data.get("svg_path", ""),
            symbol_name=data.get("symbol_name", ""),
            parameters=data.get("parameters", {}),
        )
        item.symbol_scale = data.get("symbol_scale", 1.0)
        item.deserialize_base(data)
        return item


register_annotation(AnnotationType.SYMBOL.value, SymbolAnnotation)
