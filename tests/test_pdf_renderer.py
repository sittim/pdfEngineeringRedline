import os

from pdfredline.canvas.pdf_renderer import PdfRenderer

SAMPLE_PDF = os.path.join(os.path.dirname(__file__), "fixtures", "sample.pdf")


def test_open_pdf(qapp, qtbot):
    renderer = PdfRenderer()
    with qtbot.waitSignal(renderer.render_ready, timeout=5000) as blocker:
        renderer.open(SAMPLE_PDF)
    result = blocker.args[0]
    assert result.page_index == 0
    assert not result.pixmap.isNull()
    assert result.page_width_pts > 0
    assert result.page_height_pts > 0
    assert renderer.page_count == 3


def test_page_count(qapp):
    renderer = PdfRenderer()
    assert renderer.page_count == 0
    # Open requires signal wait, tested above


def test_render_page(qapp, qtbot):
    renderer = PdfRenderer()
    with qtbot.waitSignal(renderer.render_ready, timeout=5000):
        renderer.open(SAMPLE_PDF)

    with qtbot.waitSignal(renderer.render_ready, timeout=5000) as blocker:
        renderer.render_page(1)
    result = blocker.args[0]
    assert result.page_index == 1
    assert not result.pixmap.isNull()
