from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QPainter
from qtpy.QtWidgets import QGraphicsView

from pdfredline.canvas.scene import RedlineScene
from pdfredline.tools.tool_manager import ToolManager

ZOOM_FACTOR = 1.15
ZOOM_MIN = 0.05
ZOOM_MAX = 50.0


class RedlineView(QGraphicsView):
    """Custom QGraphicsView with mouse-wheel zoom and middle-mouse-button pan."""

    zoom_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = RedlineScene(self)
        self.setScene(self._scene)

        self._zoom_level = 1.0
        self._panning = False
        self._tool_manager: ToolManager | None = None

        # SmoothPixmapTransform is intentionally OFF: bilinear filtering of the
        # PDF background pixmap averages thin features (rules, hairlines) into
        # the surrounding white at low zoom levels and makes them disappear.
        # The PdfRenderer re-rasterizes on both zoom-in and zoom-out so the
        # pixmap is always close to screen resolution; nearest-neighbor sampling
        # at that point preserves thin lines without visible aliasing.
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.TextAntialiasing
        )
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # Enable mouse tracking so click-click tools (Line, Triangle, dimensions)
        # receive mouse_move events between clicks without a button held down.
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

    @property
    def redline_scene(self) -> RedlineScene:
        return self._scene

    def set_tool_manager(self, tool_manager: ToolManager):
        self._tool_manager = tool_manager

    @property
    def zoom_level(self) -> float:
        return self._zoom_level

    def zoom_in(self):
        self._apply_zoom(ZOOM_FACTOR)

    def zoom_out(self):
        self._apply_zoom(1.0 / ZOOM_FACTOR)

    def fit_page(self):
        self.fitInView(self._scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom_level = self.transform().m11()
        self.zoom_changed.emit(self._zoom_level)

    def _apply_zoom(self, factor: float):
        new_zoom = self._zoom_level * factor
        if new_zoom < ZOOM_MIN or new_zoom > ZOOM_MAX:
            return
        self._zoom_level = new_zoom
        self.scale(factor, factor)
        self.zoom_changed.emit(self._zoom_level)

    # -- Event overrides --

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self._apply_zoom(ZOOM_FACTOR)
        elif delta < 0:
            self._apply_zoom(1.0 / ZOOM_FACTOR)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        if self._tool_manager:
            self._tool_manager.mouse_press(event)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.position().toPoint() - self._pan_start
            self._pan_start = event.position().toPoint()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return
        if self._tool_manager:
            self._tool_manager.mouse_move(event)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton and self._panning:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        if self._tool_manager:
            self._tool_manager.mouse_release(event)
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if self._tool_manager:
            self._tool_manager.key_press(event)
        super().keyPressEvent(event)
