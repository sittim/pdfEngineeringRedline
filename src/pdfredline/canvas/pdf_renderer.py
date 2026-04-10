import pypdfium2 as pdfium
from qtpy.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal, Slot
from qtpy.QtGui import QImage, QPixmap


class RenderResult:
    """Result of a page render operation."""

    __slots__ = ("page_index", "pixmap", "dpi", "page_width_pts", "page_height_pts")

    def __init__(self, page_index: int, pixmap: QPixmap, dpi: float,
                 page_width_pts: float, page_height_pts: float):
        self.page_index = page_index
        self.pixmap = pixmap
        self.dpi = dpi
        self.page_width_pts = page_width_pts
        self.page_height_pts = page_height_pts


class _RenderSignals(QObject):
    finished = Signal(object)  # RenderResult
    error = Signal(str)


class _RenderWorker(QRunnable):
    """Background worker that renders a PDF page at a given DPI."""

    def __init__(self, pdf_path: str, page_index: int, dpi: float):
        super().__init__()
        self.pdf_path = pdf_path
        self.page_index = page_index
        self.dpi = dpi
        self.signals = _RenderSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        try:
            doc = pdfium.PdfDocument(self.pdf_path)
            page = doc[self.page_index]
            width_pts = page.get_width()
            height_pts = page.get_height()

            scale = self.dpi / 72.0
            bitmap = page.render(scale=scale)
            arr = bitmap.to_numpy()
            bitmap.close()
            page.close()
            doc.close()

            h, w, channels = arr.shape
            fmt = QImage.Format.Format_RGBA8888 if channels == 4 else QImage.Format.Format_RGB888

            # QImage needs data to stay alive, so we keep a reference via .copy()
            qimage = QImage(arr.data, w, h, arr.strides[0], fmt).copy()
            pixmap = QPixmap.fromImage(qimage)

            result = RenderResult(self.page_index, pixmap, self.dpi, width_pts, height_pts)
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))


class PdfRenderer(QObject):
    """Manages PDF document loading and page rendering with adaptive DPI."""

    render_ready = Signal(object)  # RenderResult
    render_error = Signal(str)

    BASE_DPI = 144.0
    MAX_DPI = 600.0
    RERENDER_THRESHOLD = 1.5
    DEBOUNCE_MS = 200

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pdf_path: str | None = None
        self._page_count: int = 0
        self._current_page: int = 0
        self._current_dpi: float = self.BASE_DPI
        self._rendered_dpi: float = 0.0
        self._thread_pool = QThreadPool.globalInstance()

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._do_render)

        self._pending_dpi: float = 0.0

    @property
    def pdf_path(self) -> str | None:
        return self._pdf_path

    @property
    def page_count(self) -> int:
        return self._page_count

    @property
    def current_page(self) -> int:
        return self._current_page

    def open(self, path: str):
        doc = pdfium.PdfDocument(path)
        self._page_count = len(doc)
        doc.close()
        self._pdf_path = path
        self._current_page = 0
        self._rendered_dpi = 0.0
        self.render_page(0)

    def render_page(self, page_index: int, dpi: float | None = None):
        if self._pdf_path is None or page_index < 0 or page_index >= self._page_count:
            return
        self._current_page = page_index
        target_dpi = dpi or self.BASE_DPI
        self._current_dpi = target_dpi
        self._rendered_dpi = target_dpi
        self._submit_render(page_index, target_dpi)

    def request_rerender(self, zoom_level: float):
        """Called when zoom changes. Debounces and re-renders at higher DPI if needed."""
        if self._pdf_path is None:
            return
        effective_dpi = self.BASE_DPI * zoom_level
        if effective_dpi > self.MAX_DPI:
            effective_dpi = self.MAX_DPI

        if self._rendered_dpi > 0 and effective_dpi > self._rendered_dpi * self.RERENDER_THRESHOLD:
            self._pending_dpi = effective_dpi
            self._debounce_timer.start(self.DEBOUNCE_MS)

    def _do_render(self):
        if self._pending_dpi > 0:
            self._rendered_dpi = self._pending_dpi
            self._submit_render(self._current_page, self._pending_dpi)
            self._pending_dpi = 0.0

    def _submit_render(self, page_index: int, dpi: float):
        worker = _RenderWorker(str(self._pdf_path), page_index, dpi)
        worker.signals.finished.connect(self._on_render_finished)
        worker.signals.error.connect(self._on_render_error)
        self._thread_pool.start(worker)

    def _on_render_finished(self, result: RenderResult):
        self.render_ready.emit(result)

    def _on_render_error(self, error_msg: str):
        self.render_error.emit(error_msg)
