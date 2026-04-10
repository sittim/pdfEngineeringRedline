from qtpy.QtCore import QPointF

from pdfredline.annotations.dimensions import (
    AlignedDimension,
    AngularDimension,
    LinearDimension,
    RadialDimension,
)


def test_linear_dimension_serialize(qapp):
    dim = LinearDimension()
    dim.source_pt = QPointF(10, 20)
    dim.target_pt = QPointF(110, 20)
    dim.horizontal = True
    dim.units = "mm"
    dim.precision = 2

    data = dim.serialize()
    restored = LinearDimension.from_data(data)
    assert restored.source_pt.x() == 10
    assert restored.target_pt.x() == 110
    assert restored.horizontal is True
    assert restored.units == "mm"


def test_aligned_dimension_compute(qapp):
    dim = AlignedDimension()
    dim.source_pt = QPointF(0, 0)
    dim.target_pt = QPointF(72, 0)  # 72 pts = 1 inch
    assert abs(dim._compute() - 72) < 0.01


def test_radial_dimension_serialize(qapp):
    dim = RadialDimension()
    dim.source_pt = QPointF(50, 50)
    dim.radius_value = 36.0

    data = dim.serialize()
    restored = RadialDimension.from_data(data)
    assert restored.radius_value == 36.0


def test_angular_dimension_compute(qapp):
    dim = AngularDimension()
    dim.vertex_pt = QPointF(0, 0)
    dim.source_pt = QPointF(100, 0)  # 0 degrees
    dim.target_pt = QPointF(0, 100)  # 90 degrees
    angle = dim._compute()
    assert abs(angle - 90) < 0.1
