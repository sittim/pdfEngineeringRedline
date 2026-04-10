from qtpy.QtCore import QPointF

from pdfredline.annotations.shapes import CircleAnnotation, LineAnnotation
from pdfredline.annotations.snap import SnapEngine
from pdfredline.canvas.scene import RedlineScene


def test_snap_finds_endpoint(qapp):
    scene = RedlineScene()
    line = LineAnnotation(0, 0, 100, 0)
    line.setPos(50, 50)
    scene.addItem(line)

    engine = SnapEngine(scene, snap_radius=20)
    # Near start point (50, 50)
    result = engine.find_nearest(QPointF(55, 52))
    assert result is not None
    assert result.annotation is line


def test_snap_no_match_when_far(qapp):
    scene = RedlineScene()
    line = LineAnnotation(0, 0, 100, 0)
    line.setPos(50, 50)
    scene.addItem(line)

    engine = SnapEngine(scene, snap_radius=5)
    result = engine.find_nearest(QPointF(500, 500))
    assert result is None


def test_snap_finds_circle_center(qapp):
    scene = RedlineScene()
    circle = CircleAnnotation(30)
    circle.setPos(100, 100)
    scene.addItem(circle)

    engine = SnapEngine(scene, snap_radius=15)
    result = engine.find_nearest(QPointF(102, 101))
    assert result is not None
    assert result.snap_index == 0  # center is first snap point
