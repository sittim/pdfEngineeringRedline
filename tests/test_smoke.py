from pdfredline.app import MainWindow
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
