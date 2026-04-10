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


def test_rerender_fires_on_zoom_out(qapp, qtbot):
    """Zooming out should re-rasterize at a lower DPI so thin features in the
    PDF do not get bilinear-averaged into the background and disappear.
    Without symmetric re-rendering this signal never fires on zoom-out."""
    renderer = PdfRenderer()
    with qtbot.waitSignal(renderer.render_ready, timeout=5000):
        renderer.open(SAMPLE_PDF)

    # Heavy zoom-out — should drop the rendered DPI well below BASE_DPI.
    with qtbot.waitSignal(renderer.render_ready, timeout=5000) as blocker:
        renderer.request_rerender(0.1)
    result = blocker.args[0]
    assert result.dpi < PdfRenderer.BASE_DPI
    assert result.dpi >= PdfRenderer.MIN_DPI
    assert not result.pixmap.isNull()


def test_rerender_respects_min_dpi(qapp, qtbot):
    """Even at absurd zoom-out, the renderer must not go below MIN_DPI — that
    keeps the bitmap resolution sensible and avoids producing 1-pixel pages."""
    renderer = PdfRenderer()
    with qtbot.waitSignal(renderer.render_ready, timeout=5000):
        renderer.open(SAMPLE_PDF)

    with qtbot.waitSignal(renderer.render_ready, timeout=5000) as blocker:
        renderer.request_rerender(0.001)
    assert blocker.args[0].dpi == PdfRenderer.MIN_DPI


def test_rerender_fires_on_zoom_in(qapp, qtbot):
    """Existing behavior — preserved by the symmetric rewrite of request_rerender."""
    renderer = PdfRenderer()
    with qtbot.waitSignal(renderer.render_ready, timeout=5000):
        renderer.open(SAMPLE_PDF)

    with qtbot.waitSignal(renderer.render_ready, timeout=5000) as blocker:
        renderer.request_rerender(4.0)
    result = blocker.args[0]
    assert result.dpi > PdfRenderer.BASE_DPI
    assert result.dpi <= PdfRenderer.MAX_DPI
