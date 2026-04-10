import math

import numpy as np
import pypdfium2 as pdfium
from qtpy.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal, Slot
from qtpy.QtGui import QImage, QPixmap


def _min_pool(arr: np.ndarray, block: int) -> np.ndarray:
    """Min-pool downsample: each output pixel is the minimum (darkest) value
    of its ``block × block`` source region per channel. Used internally by
    :func:`_adaptive_pool` to compute the rescue values for thin features.

    Trims the bottom/right edge of the input if its dimensions are not exact
    multiples of ``block`` (at most ``block - 1`` rows/cols dropped).
    """
    if block <= 1:
        return arr
    h, w = arr.shape[:2]
    new_h = h // block
    new_w = w // block
    if new_h == 0 or new_w == 0:
        return arr
    arr = arr[: new_h * block, : new_w * block]
    if arr.ndim == 3:
        c = arr.shape[2]
        return arr.reshape(new_h, block, new_w, block, c).min(axis=(1, 3))
    return arr.reshape(new_h, block, new_w, block).min(axis=(1, 3))


def _mean_pool(arr: np.ndarray, block: int) -> np.ndarray:
    """Mean-pool downsample: each output pixel is the per-channel arithmetic
    mean of its ``block × block`` source region. This is the standard
    antialiased downsample — preserves text edges and gradients smoothly,
    but averages thin dark features into the background until they vanish.

    Used internally by :func:`_adaptive_pool` as the baseline that thin
    features are rescued *against*.
    """
    if block <= 1:
        return arr
    h, w = arr.shape[:2]
    new_h = h // block
    new_w = w // block
    if new_h == 0 or new_w == 0:
        return arr
    arr = arr[: new_h * block, : new_w * block]
    if arr.ndim == 3:
        c = arr.shape[2]
        return (
            arr.astype(np.float32)
            .reshape(new_h, block, new_w, block, c)
            .mean(axis=(1, 3))
            .astype(np.uint8)
        )
    return (
        arr.astype(np.float32)
        .reshape(new_h, block, new_w, block)
        .mean(axis=(1, 3))
        .astype(np.uint8)
    )


def _adaptive_pool(
    arr: np.ndarray,
    block: int,
    near_white_thresh: int = 210,
    dark_thresh: int = 120,
) -> np.ndarray:
    """Detail-preserving downsample. Mean-pool everywhere; rescue thin dark
    features that mean-pool would have erased.

    For each output block compute both downsamples:

    - **mean** — standard antialiased downsample (smooth, preserves text
      edges and gradients)
    - **min**  — darkest pixel of the block (preserves any dark feature)

    Where mean-pool produced a near-white pixel BUT min-pool found a dark
    pixel in the same block, substitute the min-pool value to rescue thin
    lines that mean-pool averaged into the background. Everywhere else use
    mean-pool, which keeps text and other antialiased content smooth.

    This is the technique behind Adobe Acrobat's "Enhance Thin Lines": apply
    the aggressive operator only where the smooth operator failed. Pure
    min-pool over-darkens text strokes by destroying their anti-aliased
    edges; pure mean-pool loses thin features. Adaptive rescue gives both.

    Empirical thresholds (validated on engineering documents): a pixel is
    rescued when mean-pool > 210 AND min-pool < 120.
    """
    if block <= 1:
        return arr
    me = _mean_pool(arr, block)
    mp = _min_pool(arr, block)
    if me.shape != mp.shape:
        return me

    # Build the rescue mask in grayscale, then broadcast back to channels.
    if me.ndim == 3:
        me_gray = me.mean(axis=2)
        mp_gray = mp.mean(axis=2)
    else:
        me_gray = me
        mp_gray = mp
    rescue = (me_gray > near_white_thresh) & (mp_gray < dark_thresh)
    if me.ndim == 3:
        rescue = rescue[..., None]
    return np.where(rescue, mp, me)


class RenderResult:
    """Result of a page render operation."""

    __slots__ = ("page_index", "pixmap", "dpi", "page_width_pts", "page_height_pts")

    def __init__(self, page_index: int, pixmap: QPixmap, dpi: float,
                 page_width_pts: float, page_height_pts: float):
        self.page_index = page_index
        self.pixmap = pixmap
        # The post-min-pool DPI — i.e. how many pixels-per-inch the bitmap
        # actually represents after downsampling. RedlineScene uses this to
        # scale the pixmap into PDF point space.
        self.dpi = dpi
        self.page_width_pts = page_width_pts
        self.page_height_pts = page_height_pts


class _RenderSignals(QObject):
    finished = Signal(object)  # RenderResult
    error = Signal(str)


class _RenderWorker(QRunnable):
    """Background worker that rasterizes a PDF page at a high render DPI and
    min-pool downsamples to the requested output DPI. The two-stage approach
    preserves thin features that would otherwise be lost when a low-resolution
    bitmap is displayed at low zoom."""

    def __init__(self, pdf_path: str, page_index: int,
                 render_dpi: float, output_dpi: float, block_size: int):
        super().__init__()
        self.pdf_path = pdf_path
        self.page_index = page_index
        self.render_dpi = render_dpi
        self.output_dpi = output_dpi
        self.block_size = block_size
        self.signals = _RenderSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        try:
            doc = pdfium.PdfDocument(self.pdf_path)
            page = doc[self.page_index]
            width_pts = page.get_width()
            height_pts = page.get_height()

            scale = self.render_dpi / 72.0
            bitmap = page.render(scale=scale, optimize_mode="lcd")

            # Copy out of PDFium's bitmap buffer the safest way possible:
            # bitmap.buffer is a `(c_ubyte * N)` ctypes array; bytes() invokes
            # the Python buffer protocol and produces a fresh, fully Python-
            # owned bytes object via a single memcpy. No numpy strided iter,
            # no aliasing, no platform-specific allocator quirks. This avoids
            # both the macOS heisensegfault (v0.3.0) and the Windows heap
            # corruption (v0.3.1) that surfaced when the previous code copied
            # via numpy's .copy() / reshape().
            h_px = bitmap.height
            w_px = bitmap.width
            n_ch = bitmap.n_channels
            stride = bitmap.stride
            raw = bytes(bitmap.buffer)

            bitmap.close()
            page.close()
            doc.close()

            # Reconstruct a numpy array on top of the Python-owned bytes.
            # frombuffer is a zero-copy view into the bytes object, kept alive
            # via arr.base. Handle stride padding (pdfium aligns rows to 4
            # bytes; for some widths this leaves trailing padding per row).
            if stride == w_px * n_ch:
                arr = np.frombuffer(raw, dtype=np.uint8).reshape(h_px, w_px, n_ch)
            else:
                # Strip per-row padding by viewing as (H, stride) then slicing.
                arr = (
                    np.frombuffer(raw, dtype=np.uint8)
                    .reshape(h_px, stride)[:, : w_px * n_ch]
                    .reshape(h_px, w_px, n_ch)
                )
            # frombuffer returns a read-only array; promote to writable so the
            # min-pool path (or QImage construction) can operate on it freely.
            arr = arr.copy()

            if self.block_size > 1:
                arr = _adaptive_pool(arr, self.block_size)
            arr = np.ascontiguousarray(arr)

            h, w = arr.shape[:2]
            channels = arr.shape[2] if arr.ndim == 3 else 1
            fmt = QImage.Format.Format_RGBA8888 if channels == 4 else QImage.Format.Format_RGB888

            qimage = QImage(arr.data, w, h, arr.strides[0], fmt).copy()
            pixmap = QPixmap.fromImage(qimage)

            result = RenderResult(
                self.page_index, pixmap, self.output_dpi, width_pts, height_pts
            )
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))


class PdfRenderer(QObject):
    """Manages PDF document loading and adaptive page rendering.

    Rendering pipeline:

    1. Compute the OUTPUT DPI that matches the display at the current zoom
       (``BASE_DPI * zoom_level``).
    2. Compute a RENDER DPI that is at least ``BASE_DPI`` (so PDFium itself
       has enough resolution to draw thin features without anti-aliasing
       them away) and an integer multiple of the output DPI.
    3. Rasterize at the render DPI via pypdfium2.
    4. If render_dpi > output_dpi, **adaptive-pool** down to output_dpi:
       mean-pool everywhere (preserves text antialiasing); min-pool only in
       blocks where mean-pool produced a near-white pixel but the source
       had a dark pixel (rescues thin features). This is the same trade-off
       Adobe Acrobat's "Enhance Thin Lines" makes.

    At zoom ≥ 1.0 the render DPI equals the output DPI and no downsampling
    happens at all — the bitmap goes straight from PDFium to QPixmap, which
    matches the v0.2.0 behavior the user was satisfied with for text.
    """

    render_ready = Signal(object)  # RenderResult
    render_error = Signal(str)

    BASE_DPI = 144.0          # Floor on the render DPI; PDFium needs this much
                              # resolution to draw thin features cleanly.
    MAX_DPI = 600.0           # Hard cap on render DPI to keep memory bounded.
    SUPERSAMPLE = 1           # Minimum oversample factor over the screen DPI.
                              # 1 means: at zoom >= 1, render at exact screen
                              # DPI (no supersample, no min-pool, no
                              # downsampling — matches v0.2.0).
    MAX_BLOCK_SIZE = 32       # Cap the adaptive-pool block size at extreme zoom-out.
    RERENDER_THRESHOLD = 1.5  # Re-render when output DPI moves by more than this.
    DEBOUNCE_MS = 200

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pdf_path: str | None = None
        self._page_count: int = 0
        self._current_page: int = 0
        self._rendered_output_dpi: float = 0.0
        self._thread_pool = QThreadPool.globalInstance()

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._do_render)

        self._pending_zoom: float = 0.0

    @property
    def pdf_path(self) -> str | None:
        return self._pdf_path

    @property
    def page_count(self) -> int:
        return self._page_count

    @property
    def current_page(self) -> int:
        return self._current_page

    def _compute_render_params(self, zoom_level: float) -> tuple[float, float, int]:
        """Returns (render_dpi, output_dpi, block_size) for a given zoom level.

        - ``output_dpi`` is the DPI the final bitmap represents — chosen to
          match the screen pixel size at the given zoom.
        - ``render_dpi`` is the DPI at which PDFium actually rasterizes —
          chosen to be a clean integer multiple of output_dpi while still
          giving PDFium enough resolution to draw thin features.
        - ``block_size`` = render_dpi / output_dpi, the min-pool factor.
        """
        if zoom_level <= 0:
            return self.BASE_DPI, self.BASE_DPI, 1

        output_dpi = self.BASE_DPI * zoom_level

        # Very high zoom: output already exceeds the cap. Render at MAX_DPI
        # without min-pool and let Qt scale up — thin features are visible
        # at high zoom regardless.
        if output_dpi >= self.MAX_DPI:
            return self.MAX_DPI, self.MAX_DPI, 1

        # Target render DPI: at least BASE_DPI (PDFium's thin-feature floor),
        # at least SUPERSAMPLE× the output DPI (so min-pool has something to
        # darken), at most MAX_DPI (memory cap).
        target_render = max(self.BASE_DPI, output_dpi * self.SUPERSAMPLE)
        target_render = min(target_render, self.MAX_DPI)

        block_size = max(1, round(target_render / output_dpi))
        block_size = min(block_size, self.MAX_BLOCK_SIZE)
        render_dpi = output_dpi * block_size

        # If rounding pushed us past MAX_DPI, step the block size down.
        if render_dpi > self.MAX_DPI:
            block_size = max(1, math.floor(self.MAX_DPI / output_dpi))
            render_dpi = output_dpi * block_size

        return render_dpi, output_dpi, block_size

    def open(self, path: str):
        doc = pdfium.PdfDocument(path)
        self._page_count = len(doc)
        doc.close()
        self._pdf_path = path
        self._current_page = 0
        self._rendered_output_dpi = 0.0
        self.render_page(0)

    def render_page(self, page_index: int, zoom_level: float = 1.0):
        if self._pdf_path is None or page_index < 0 or page_index >= self._page_count:
            return
        self._current_page = page_index
        render_dpi, output_dpi, block_size = self._compute_render_params(zoom_level)
        self._rendered_output_dpi = output_dpi
        self._submit_render(page_index, render_dpi, output_dpi, block_size)

    def request_rerender(self, zoom_level: float):
        """Called when zoom changes. Debounces and re-renders whenever the
        output DPI no longer matches the screen — in either direction.
        Without symmetric re-rendering, thin features in the PDF get
        downsampled out of existence on zoom-out."""
        if self._pdf_path is None or zoom_level <= 0:
            return

        _, new_output_dpi, _ = self._compute_render_params(zoom_level)
        if self._rendered_output_dpi <= 0:
            return
        ratio = new_output_dpi / self._rendered_output_dpi
        if ratio > self.RERENDER_THRESHOLD or ratio < (1.0 / self.RERENDER_THRESHOLD):
            self._pending_zoom = zoom_level
            self._debounce_timer.start(self.DEBOUNCE_MS)

    def _do_render(self):
        if self._pending_zoom > 0:
            zoom = self._pending_zoom
            self._pending_zoom = 0.0
            render_dpi, output_dpi, block_size = self._compute_render_params(zoom)
            self._rendered_output_dpi = output_dpi
            self._submit_render(self._current_page, render_dpi, output_dpi, block_size)

    def _submit_render(self, page_index: int, render_dpi: float,
                       output_dpi: float, block_size: int):
        worker = _RenderWorker(
            str(self._pdf_path), page_index, render_dpi, output_dpi, block_size
        )
        worker.signals.finished.connect(self._on_render_finished)
        worker.signals.error.connect(self._on_render_error)
        self._thread_pool.start(worker)

    def _on_render_finished(self, result: RenderResult):
        self.render_ready.emit(result)

    def _on_render_error(self, error_msg: str):
        self.render_error.emit(error_msg)
