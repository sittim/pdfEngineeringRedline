from qtpy.QtCore import Qt
from qtpy.QtGui import QPainter, QPixmap

from pdfredline.app import MainWindow
from pdfredline.canvas.pdf_renderer import RenderResult
from pdfredline.canvas.scene import RedlineScene
from pdfredline.canvas.view import RedlineView


def test_main_window_creates(qapp):
    window = MainWindow()
    assert window.windowTitle() == "PDF Redline"
    assert isinstance(window.view, RedlineView)
    window.close()


def test_scene_has_scene_rect(qapp):
    scene = RedlineScene()
    rect = scene.sceneRect()
    assert rect.width() > 0
    assert rect.height() > 0


def test_view_initial_zoom(qapp):
    view = RedlineView()
    assert view.zoom_level == 1.0
    view.close()


def test_zoom_in(qapp):
    view = RedlineView()
    initial = view.zoom_level
    view.zoom_in()
    assert view.zoom_level > initial
    view.close()


def test_zoom_out(qapp):
    view = RedlineView()
    initial = view.zoom_level
    view.zoom_out()
    assert view.zoom_level < initial
    view.close()


def test_view_uses_smooth_pixmap_transform(qapp):
    """The view must enable SmoothPixmapTransform so the always-2:1
    bitmap-to-screen downsample is bilinear (smooth) instead of
    nearest-neighbor (which makes text and line edges look broken).
    See canvas/view.py for the full explanation."""
    view = RedlineView()
    hints = view.renderHints()
    assert bool(hints & QPainter.RenderHint.SmoothPixmapTransform)
    view.close()


def test_pdf_background_uses_smooth_transformation(qapp):
    """Belt-and-braces: also set Qt.SmoothTransformation per-item on the
    pixmap, because some Qt platform plugins respect the per-item setting
    but not the view-wide render hint."""
    scene = RedlineScene()
    # Drive set_pdf_pixmap with a synthetic RenderResult so the background
    # item gets created exactly the way the real pipeline would.
    pixmap = QPixmap(10, 10)
    pixmap.fill()
    scene.set_pdf_pixmap(RenderResult(0, pixmap, 144.0, 612.0, 792.0))
    bg = scene._pdf_background
    assert bg is not None
    assert bg.transformationMode() == Qt.TransformationMode.SmoothTransformation
