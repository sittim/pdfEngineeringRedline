import os

import numpy as np

from pdfredline.canvas.pdf_renderer import (
    PdfRenderer,
    _adaptive_pool,
    _mean_pool,
    _min_pool,
)

SAMPLE_PDF = os.path.join(os.path.dirname(__file__), "fixtures", "sample.pdf")


# -- _min_pool unit tests --


def test_min_pool_preserves_dark_pixel():
    """A single dark pixel in a white field must survive a min-pool downsample.
    This is the property that makes thin lines visible at low zoom: even if a
    line covers only 1 pixel of a 20x20 source block, the output pixel for
    that block becomes the line's dark value, not the surrounding white."""
    arr = np.full((4, 4, 3), 255, dtype=np.uint8)
    arr[1, 1] = [0, 0, 0]  # one black pixel in the top-left block
    out = _min_pool(arr, 2)
    assert out.shape == (2, 2, 3)
    assert out[0, 0].tolist() == [0, 0, 0]
    assert out[0, 1].tolist() == [255, 255, 255]
    assert out[1, 0].tolist() == [255, 255, 255]
    assert out[1, 1].tolist() == [255, 255, 255]


def test_min_pool_block_one_is_identity():
    arr = np.array([[[10, 20, 30], [40, 50, 60]]], dtype=np.uint8)
    out = _min_pool(arr, 1)
    assert np.array_equal(out, arr)


def test_min_pool_trims_unaligned_dimensions():
    """Input dimensions that aren't a multiple of block_size are trimmed,
    not padded — at most block-1 rows/cols are dropped from the bottom/right."""
    arr = np.full((5, 5, 3), 100, dtype=np.uint8)
    out = _min_pool(arr, 2)
    assert out.shape == (2, 2, 3)


def test_min_pool_handles_rgba():
    arr = np.full((4, 4, 4), 200, dtype=np.uint8)
    arr[0, 0] = [10, 20, 30, 40]
    out = _min_pool(arr, 2)
    assert out.shape == (2, 2, 4)
    assert out[0, 0].tolist() == [10, 20, 30, 40]


# -- _mean_pool unit tests --


def test_mean_pool_averages_block():
    """Mean-pool produces the per-channel average of each block. This is the
    standard antialiased downsample — preserves text edges as midtones."""
    arr = np.array(
        [[[100, 100, 100], [200, 200, 200]],
         [[100, 100, 100], [200, 200, 200]]],
        dtype=np.uint8,
    )
    out = _mean_pool(arr, 2)
    assert out.shape == (1, 1, 3)
    assert out[0, 0].tolist() == [150, 150, 150]


def test_mean_pool_block_one_is_identity():
    arr = np.array([[[10, 20, 30], [40, 50, 60]]], dtype=np.uint8)
    out = _mean_pool(arr, 1)
    assert np.array_equal(out, arr)


# -- _adaptive_pool unit tests --


def test_adaptive_pool_preserves_text_edges():
    """At a block where the mean-pooled pixel is a midtone (not near-white),
    no rescue is needed: the output matches mean-pool exactly. This is what
    keeps text strokes smooth — they appear as midtones, not as sub-pixel
    thin features that need rescuing."""
    # 2x2 block representing an antialiased text edge: half white, half dark.
    arr = np.array(
        [[[255, 255, 255], [255, 255, 255]],
         [[ 50,  50,  50], [ 50,  50,  50]]],
        dtype=np.uint8,
    )
    out = _adaptive_pool(arr, 2)
    # Mean = (255+255+50+50)/4 = 152.5 — midtone, NOT near-white
    # No rescue → output is the mean
    assert out.shape == (1, 1, 3)
    assert 150 <= out[0, 0, 0] <= 153


def test_adaptive_pool_rescues_thin_dark_feature():
    """A 4x4 block that is mostly white with one dark pixel: mean-pool would
    average to ~239 (near-white) and erase the feature. Adaptive should
    detect this and substitute the min-pool value (the dark pixel)."""
    arr = np.full((4, 4, 3), 255, dtype=np.uint8)
    arr[2, 2] = [0, 0, 0]
    out = _adaptive_pool(arr, 4)
    assert out.shape == (1, 1, 3)
    # Mean ≈ 239 (>210, near-white), Min = 0 (<120, dark) → rescue
    assert out[0, 0].tolist() == [0, 0, 0]


def test_adaptive_pool_no_rescue_when_mean_is_dark():
    """If the mean-pool result is already dark (a thick stroke), no rescue
    is needed and the output is the mean-pool value, preserving any
    midtone gradient at the edges."""
    arr = np.array(
        [[[ 50,  50,  50], [ 60,  60,  60]],
         [[ 70,  70,  70], [ 80,  80,  80]]],
        dtype=np.uint8,
    )
    out = _adaptive_pool(arr, 2)
    # Mean = 65 (NOT > 210), so no rescue
    assert out.shape == (1, 1, 3)
    assert out[0, 0].tolist() == [65, 65, 65]


def test_adaptive_pool_no_rescue_when_min_is_not_dark():
    """If the min-pool result is just a slightly grayer pixel (e.g. 150),
    that's antialiasing, not a vanishing thin feature — no rescue."""
    arr = np.full((4, 4, 3), 250, dtype=np.uint8)
    arr[2, 2] = [150, 150, 150]
    out = _adaptive_pool(arr, 4)
    # Mean ≈ 244 (>210), Min = 150 (NOT < 120) → no rescue
    assert out.shape == (1, 1, 3)
    assert out[0, 0, 0] >= 240  # close to mean, not the 150


def test_adaptive_pool_block_one_is_identity():
    arr = np.array([[[10, 20, 30], [40, 50, 60]]], dtype=np.uint8)
    out = _adaptive_pool(arr, 1)
    assert np.array_equal(out, arr)


# -- _compute_render_params unit tests --


def test_compute_params_zoom_one():
    """At zoom=1 with SUPERSAMPLE=1, output_dpi=BASE_DPI=144 and the render
    DPI matches exactly — no supersample, no downsample, no adaptive pool.
    Behavior identical to v0.2.0 to keep text crisp at the common viewing
    zoom."""
    renderer = PdfRenderer()
    render_dpi, output_dpi, block = renderer._compute_render_params(1.0)
    assert output_dpi == 144.0
    assert render_dpi == 144.0
    assert block == 1


def test_compute_params_extreme_zoom_out():
    """At zoom=0.05 the screen DPI is 7.2, but we still need to render at
    BASE_DPI=144 for PDFium to draw thin features. Block size becomes 20."""
    renderer = PdfRenderer()
    render_dpi, output_dpi, block = renderer._compute_render_params(0.05)
    assert abs(output_dpi - 7.2) < 0.001
    assert render_dpi == 144.0
    assert block == 20


def test_compute_params_moderate_zoom_out():
    renderer = PdfRenderer()
    render_dpi, output_dpi, block = renderer._compute_render_params(0.5)
    assert output_dpi == 72.0
    assert render_dpi == 144.0
    assert block == 2


def test_compute_params_zoom_in():
    """At zoom=2 with SUPERSAMPLE=1, output_dpi=288 already exceeds the
    BASE_DPI floor so render_dpi matches it exactly — no downsample needed.
    Thin features are intrinsically visible at high zoom anyway."""
    renderer = PdfRenderer()
    render_dpi, output_dpi, block = renderer._compute_render_params(2.0)
    assert output_dpi == 288.0
    assert render_dpi == 288.0
    assert block == 1


def test_compute_params_extreme_zoom_in():
    """When output_dpi alone exceeds MAX_DPI, render at MAX_DPI with no
    min-pool and let Qt scale up — thin features are visible at high zoom
    regardless."""
    renderer = PdfRenderer()
    render_dpi, output_dpi, block = renderer._compute_render_params(10.0)
    assert render_dpi == PdfRenderer.MAX_DPI
    assert output_dpi == PdfRenderer.MAX_DPI
    assert block == 1


def test_compute_params_block_size_capped():
    """At absurdly low zoom, block_size is capped at MAX_BLOCK_SIZE so we
    don't degenerate into a 1-pixel bitmap."""
    renderer = PdfRenderer()
    _, _, block = renderer._compute_render_params(0.001)
    assert block <= PdfRenderer.MAX_BLOCK_SIZE


# -- End-to-end render tests --


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
    """Zooming out should re-rasterize and emit render_ready. The output DPI
    should drop below BASE_DPI to match the visible screen size, but the
    underlying render is still at BASE_DPI with min-pool downsampling so
    thin features are preserved."""
    renderer = PdfRenderer()
    with qtbot.waitSignal(renderer.render_ready, timeout=5000):
        renderer.open(SAMPLE_PDF)

    with qtbot.waitSignal(renderer.render_ready, timeout=5000) as blocker:
        renderer.request_rerender(0.1)
    result = blocker.args[0]
    assert result.dpi < PdfRenderer.BASE_DPI
    assert not result.pixmap.isNull()


def test_rerender_fires_on_zoom_in(qapp, qtbot):
    renderer = PdfRenderer()
    with qtbot.waitSignal(renderer.render_ready, timeout=5000):
        renderer.open(SAMPLE_PDF)

    with qtbot.waitSignal(renderer.render_ready, timeout=5000) as blocker:
        renderer.request_rerender(4.0)
    result = blocker.args[0]
    assert result.dpi > PdfRenderer.BASE_DPI
    assert result.dpi <= PdfRenderer.MAX_DPI
