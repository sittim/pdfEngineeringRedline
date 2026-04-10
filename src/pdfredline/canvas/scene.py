from qtpy.QtCore import QRectF, Qt
from qtpy.QtWidgets import QGraphicsPixmapItem, QGraphicsScene

from pdfredline.canvas.pdf_renderer import RenderResult


class RedlineScene(QGraphicsScene):
    """Custom scene for PDF redlining. Uses PDF points (1/72 inch) as coordinate system."""

    DEFAULT_SCENE_RECT = QRectF(-1000, -1000, 12000, 12000)
    PDF_BACKGROUND_Z = 0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(self.DEFAULT_SCENE_RECT)

        self._pdf_background: QGraphicsPixmapItem | None = None
        self._page_width_pts: float = 0.0
        self._page_height_pts: float = 0.0

        # Per-page annotation storage: page_index -> list of serialized annotation dicts
        # Items on the current page live in the scene directly.
        self._page_annotations: dict[int, list] = {}
        self._current_page: int = 0
        # Optional back-reference to the application undo stack so annotations
        # (e.g. SymbolAnnotation inline editor) can push commands themselves.
        self._undo_stack = None

    def set_undo_stack(self, undo_stack):
        self._undo_stack = undo_stack

    @property
    def page_width_pts(self) -> float:
        return self._page_width_pts

    @property
    def page_height_pts(self) -> float:
        return self._page_height_pts

    @property
    def current_page(self) -> int:
        return self._current_page

    def set_pdf_pixmap(self, result: RenderResult):
        """Update the PDF background pixmap from a render result."""
        self._page_width_pts = result.page_width_pts
        self._page_height_pts = result.page_height_pts

        if self._pdf_background is None:
            self._pdf_background = QGraphicsPixmapItem()
            self._pdf_background.setZValue(self.PDF_BACKGROUND_Z)
            selectable = QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable
            self._pdf_background.setFlag(selectable, False)
            self._pdf_background.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable, False)
            self._pdf_background.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.addItem(self._pdf_background)

        self._pdf_background.setPixmap(result.pixmap)
        # Scale pixmap so it occupies the correct number of PDF points
        scale = 72.0 / result.dpi
        self._pdf_background.setScale(scale)
        self._pdf_background.setPos(0, 0)

    def switch_page(self, new_page: int):
        """Store current page annotations and prepare for new page."""
        self._store_current_annotations()
        self._current_page = new_page
        self._restore_annotations(new_page)

    def get_annotation_items(self) -> list:
        """Get all annotation items on the current scene (excluding PDF background)."""
        items = []
        for item in self.items():
            if item is not self._pdf_background and hasattr(item, "serialize"):
                items.append(item)
        return items

    def _store_current_annotations(self):
        """Serialize current page annotations and remove them from scene."""
        annotations = self.get_annotation_items()
        serialized = []
        for item in annotations:
            serialized.append(item.serialize())
            self.removeItem(item)
        self._page_annotations[self._current_page] = serialized

    def _restore_annotations(self, page: int):
        """Restore annotations for the given page. Requires annotation registry (Phase 3+)."""
        # Will be implemented when annotation deserialization is available
        pass

    def clear_annotations(self):
        """Remove all annotation items from the scene (keep PDF background)."""
        for item in self.get_annotation_items():
            self.removeItem(item)

    def set_page_rect(self):
        """Set scene rect to match the current PDF page with margin."""
        if self._page_width_pts > 0 and self._page_height_pts > 0:
            margin = 50
            self.setSceneRect(
                -margin, -margin,
                self._page_width_pts + 2 * margin,
                self._page_height_pts + 2 * margin,
            )

    def clear_pdf(self):
        """Remove the PDF background and all annotations."""
        if self._pdf_background is not None:
            self.removeItem(self._pdf_background)
            self._pdf_background = None
        self.clear_annotations()
        self._page_annotations.clear()
        self._current_page = 0
