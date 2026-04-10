import math

import numpy as np
import pypdfium2 as pdfium
from qtpy.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal, Slot
from qtpy.QtGui import QImage, QPixmap

# PDFium render flag — sets the print-mode rendering path which uses different
# stroke handling than the default screen path. Combined with optimize_mode="lcd"
# (FPDF_LCD_TEXT) via bitwise OR inside pypdfium2.
FPDF_PRINTING = 0x800


def _min_pool(arr: np.ndarray, block: int) -> np.ndarray:
    """Min-pool ("darkest of block") downsample an RGB(A) bitmap by an integer
    factor. Each output pixel takes the minimum (darkest) value of the
    corresponding ``block × block`` source region per channel.

    This is the technique used by Adobe Acrobat's "Enhance Thin Lines" feature
    and the standard fix for the problem that bilinear or mean downsampling
    averages thin dark features into the surrounding background and makes them
    disappear at low zoom levels. Min-pool guarantees that any dark pixel
    touching a block survives into the output.

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
            # optimize_mode="lcd" sets FPDF_LCD_TEXT for sharper text;
            # extra_flags=FPDF_PRINTING selects PDFium's print rendering path,
            # which uses less aggressive thin-feature anti-aliasing than the
            # default screen path.
            bitmap = page.render(
                scale=scale,
                optimize_mode="lcd",
                extra_flags=FPDF_PRINTING,
            )

            # CRITICAL: pypdfium2's bitmap.to_numpy() returns a *view* that
            # shares memory with PDFium's bitmap buffer. We must copy out of
            # that buffer (either explicitly or via min-pool, which produces
            # a fresh array) BEFORE calling bitmap.close(), otherwise we
            # have a use-after-free that segfaults the moment the allocator
            # recycles the freed buffer.
            arr_view = bitmap.to_numpy()
            # _min_pool's reshape().min() materialises a brand-new array that
            # owns its memory; .copy() does the same for the no-pool path.
            # Either way, after this line `arr` no longer aliases PDFium.
            arr = (
                _min_pool(arr_view, self.block_size)
                if self.block_size > 1
                else arr_view.copy()
            )
            arr = np.ascontiguousarray(arr)

            bitmap.close()
            page.close()
            doc.close()

            h, w = arr.shape[:2]
            channels = arr.shape[2] if arr.ndim == 3 else 1
            fmt = QImage.Format.Format_RGBA8888 if channels == 4 else QImage.Format.Format_RGB888

            # arr now owns its memory, so QImage can safely view it; .copy()
            # then gives the pixmap its own buffer.
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

    Rendering pipeline (the "Acrobat Enhance Thin Lines" approach):

    1. Compute the OUTPUT DPI that matches the display at the current zoom
       (``BASE_DPI * zoom_level``).
    2. Compute a RENDER DPI that is at least ``SUPERSAMPLE``× the output DPI
       AND at least ``BASE_DPI`` (so PDFium itself has enough resolution to
       draw thin features without anti-aliasing them away).
    3. Rasterize at the render DPI via pypdfium2.
    4. Min-pool downsample to the output DPI. Min-pool ("darkest pixel of
       block") preserves thin dark features that mean downsampling would erase.

    The result is a bitmap whose native pixel resolution matches the screen
    at the current zoom, with thin features intact.
    """

    render_ready = Signal(object)  # RenderResult
    render_error = Signal(str)

    BASE_DPI = 144.0          # Floor on the render DPI; PDFium needs this much
                              # resolution to draw thin features cleanly.
    MAX_DPI = 600.0           # Hard cap on render DPI to keep memory bounded.
    SUPERSAMPLE = 2           # Minimum oversample factor over the screen DPI.
    MAX_BLOCK_SIZE = 32       # Cap the min-pool block size at extreme zoom-out.
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
