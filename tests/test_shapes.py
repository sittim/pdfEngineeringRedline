from pdfredline.annotations.registry import deserialize_annotation
from pdfredline.annotations.shapes import (
    CircleAnnotation,
    FreehandAnnotation,
    LineAnnotation,
    OvalAnnotation,
    RectAnnotation,
    ShapeStyle,
    TriangleAnnotation,
)


def test_shape_pen_is_cosmetic(qapp):
    """Annotation pens must be cosmetic so stroke width is in device pixels and
    lines remain visible at every zoom level. Without this, a 2 pt stroke at
    5% zoom becomes 0.1 device pixels and disappears."""
    pen = ShapeStyle().pen()
    assert pen.isCosmetic()


def test_line_serialize_roundtrip(qapp):
    item = LineAnnotation(10, 20, 100, 200)
    data = item.serialize()
    restored = LineAnnotation.from_data(data)
    assert restored.x1 == 10
    assert restored.y2 == 200
    assert restored.annotation_type.value == "line"


def test_line_snap_points(qapp):
    item = LineAnnotation(0, 0, 100, 0)
    snaps = item.snap_points()
    assert len(snaps) == 3  # start, end, midpoint


def test_rect_serialize_roundtrip(qapp):
    item = RectAnnotation(150, 80)
    data = item.serialize()
    restored = RectAnnotation.from_data(data)
    assert restored.width == 150
    assert restored.height == 80


def test_rect_snap_points(qapp):
    item = RectAnnotation(100, 50)
    snaps = item.snap_points()
    assert len(snaps) == 9  # 4 corners + 4 midpoints + center


def test_circle_serialize_roundtrip(qapp):
    item = CircleAnnotation(75)
    data = item.serialize()
    restored = CircleAnnotation.from_data(data)
    assert restored.radius == 75


def test_circle_snap_points(qapp):
    item = CircleAnnotation(50)
    snaps = item.snap_points()
    assert len(snaps) == 5  # center + 4 quadrants


def test_oval_serialize_roundtrip(qapp):
    item = OvalAnnotation(80, 40)
    data = item.serialize()
    restored = OvalAnnotation.from_data(data)
    assert restored.rx == 80
    assert restored.ry == 40


def test_triangle_serialize_roundtrip(qapp):
    pts = [(0, 0), (100, 0), (50, -80)]
    item = TriangleAnnotation(pts)
    data = item.serialize()
    restored = TriangleAnnotation.from_data(data)
    assert restored.points == pts


def test_triangle_snap_points(qapp):
    item = TriangleAnnotation([(0, 0), (100, 0), (50, -80)])
    snaps = item.snap_points()
    assert len(snaps) == 6  # 3 vertices + 3 midpoints


def test_freehand_serialize_roundtrip(qapp):
    pts = [(0, 0), (10, 5), (20, 3), (30, 10)]
    item = FreehandAnnotation(pts)
    data = item.serialize()
    restored = FreehandAnnotation.from_data(data)
    assert len(restored.points) == 4


def test_registry_deserialize(qapp):
    item = RectAnnotation(120, 60)
    data = item.serialize()
    restored = deserialize_annotation(data)
    assert restored is not None
    assert isinstance(restored, RectAnnotation)
