import json
import logging
from pathlib import Path

from qtpy.QtCore import QMimeData, Qt
from qtpy.QtGui import QKeySequence, QShortcut
from qtpy.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from pdfredline.annotations.base import AnnotationItem
from pdfredline.annotations.registry import deserialize_annotation
from pdfredline.canvas.pdf_renderer import PdfRenderer, RenderResult
from pdfredline.canvas.view import RedlineView
from pdfredline.commands.undo import (
    AddAnnotationCommand,
    RemoveAnnotationCommand,
    UndoStack,
)
from pdfredline.io.pdf_export import export_pdf
from pdfredline.io.print_handler import print_scene
from pdfredline.io.project import load_project, save_project
from pdfredline.panels.properties import PropertiesPanel
from pdfredline.panels.symbol_browser import SymbolBrowserPanel
from pdfredline.ribbon import setup_ribbon
from pdfredline.symbols.library import SymbolLibrary
from pdfredline.tools.dimension_tool import (
    AlignedDimensionTool,
    AngularDimensionTool,
    LinearDimensionTool,
    RadialDimensionTool,
)
from pdfredline.tools.select_tool import SelectTool
from pdfredline.tools.shape_tools import (
    CircleTool,
    FreehandTool,
    LineTool,
    OvalTool,
    RectTool,
    TriangleTool,
)
from pdfredline.tools.symbol_tool import SymbolTool
from pdfredline.tools.text_tool import TextTool
from pdfredline.tools.tool_manager import ToolManager

logger = logging.getLogger("pdfredline.app")


class MainWindow(QMainWindow):
    """Main application window for PDF Redline."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDF Redline")
        self.resize(1280, 800)
        self._log_path: Path | None = None

        self._view = RedlineView(self)

        self._renderer = PdfRenderer(self)
        self._undo_stack = UndoStack(self)
        self._tool_manager = ToolManager(self)
        self._view.set_tool_manager(self._tool_manager)
        self._view.redline_scene.set_undo_stack(self._undo_stack)

        self._props_panel = PropertiesPanel(self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._props_panel)

        # Symbol library
        self._symbol_library = SymbolLibrary()
        symbols_dir = Path(__file__).parent / "symbols"
        self._symbol_library.scan(symbols_dir)
        self._symbol_browser = SymbolBrowserPanel(self._symbol_library, self)
        self._symbol_browser.setVisible(False)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._symbol_browser)
        self._symbol_browser.place_symbol.connect(self._on_place_symbol)

        self._project_path: str | None = None

        self._select_tool = SelectTool(
            self._view.redline_scene, self._undo_stack, self._view
        )
        self._tool_manager.set_tool(self._select_tool)

        self._setup_status_bar()
        self._ribbon = setup_ribbon(self)

        # Compose central widget: ribbon on top, canvas below.
        # The ribbon is NOT installed via setMenuBar() because that routes it
        # to the macOS native menu bar (invisible inside the window).
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._ribbon)
        layout.addWidget(self._view, 1)
        self.setCentralWidget(container)
        # QMenuBar-derived widgets default to hidden when not installed via
        # setMenuBar(); force show so the ribbon appears in the layout.
        self._ribbon.show()

        self._setup_shortcuts()
        self._connect_signals()

    @property
    def view(self) -> RedlineView:
        return self._view

    @property
    def renderer(self) -> PdfRenderer:
        return self._renderer

    @property
    def undo_stack(self) -> UndoStack:
        return self._undo_stack

    @property
    def tool_manager(self) -> ToolManager:
        return self._tool_manager

    @property
    def props_panel(self) -> PropertiesPanel:
        return self._props_panel

    def set_log_path(self, path: Path):
        self._log_path = path
        self.statusBar().showMessage(f"Log: {path}", 5000)

    # -- Setup --

    def _setup_status_bar(self):
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)

        self._zoom_label = QLabel("100%")
        self._zoom_label.setMinimumWidth(60)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_bar.addPermanentWidget(self._zoom_label)

        self._page_label = QLabel("")
        self._page_label.setMinimumWidth(100)
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_bar.addPermanentWidget(self._page_label)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key.Key_PageDown), self, self._next_page)
        QShortcut(QKeySequence(Qt.Key.Key_PageUp), self, self._prev_page)
        QShortcut(QKeySequence(Qt.Key.Key_Plus), self, self._view.zoom_in)
        QShortcut(QKeySequence(Qt.Key.Key_Minus), self, self._view.zoom_out)
        QShortcut(QKeySequence.StandardKey.Undo, self, self._undo_stack.undo)
        QShortcut(QKeySequence.StandardKey.Redo, self, self._undo_stack.redo)
        QShortcut(QKeySequence.StandardKey.Open, self, self._open_file)
        QShortcut(QKeySequence.StandardKey.Save, self, self._save_project)
        QShortcut(QKeySequence.StandardKey.SaveAs, self, self._save_project_as)
        QShortcut(QKeySequence.StandardKey.Cut, self, self._cut_selection)
        QShortcut(QKeySequence.StandardKey.Copy, self, self._copy_selection)
        QShortcut(QKeySequence.StandardKey.Paste, self, self._paste_clipboard)
        QShortcut(QKeySequence.StandardKey.SelectAll, self, self._select_all)

    def _connect_signals(self):
        self._view.zoom_changed.connect(self._on_zoom_changed)
        self._renderer.render_ready.connect(self._on_render_ready)
        self._renderer.render_error.connect(self._on_render_error)
        self._view.zoom_changed.connect(self._renderer.request_rerender)
        self._props_panel.style_changed.connect(self._on_style_changed)

    # -- Tool setters --

    def _make_shape_tool(self, tool_cls):
        tool = tool_cls(self._view.redline_scene, self._undo_stack, self._view)
        tool.style = self._props_panel.current_style()
        tool.on_finish = self._set_select_tool
        return tool

    def _set_select_tool(self):
        self._tool_manager.set_tool(self._select_tool)

    def _set_line_tool(self):
        self._tool_manager.set_tool(self._make_shape_tool(LineTool))

    def _set_rect_tool(self):
        self._tool_manager.set_tool(self._make_shape_tool(RectTool))

    def _set_circle_tool(self):
        self._tool_manager.set_tool(self._make_shape_tool(CircleTool))

    def _set_oval_tool(self):
        self._tool_manager.set_tool(self._make_shape_tool(OvalTool))

    def _set_triangle_tool(self):
        self._tool_manager.set_tool(self._make_shape_tool(TriangleTool))

    def _set_freehand_tool(self):
        self._tool_manager.set_tool(self._make_shape_tool(FreehandTool))

    def _set_text_tool(self):
        tool = TextTool(
            self._view.redline_scene, self._undo_stack, self._view,
            font_family=self._props_panel.current_font_family(),
            font_size=self._props_panel.current_font_size(),
            color=self._props_panel.current_text_color(),
        )
        tool.on_finish = self._set_select_tool
        self._tool_manager.set_tool(tool)

    def _set_dimension_tool(self, dim_type: str):
        units = getattr(self, "_ribbon_dim_units", None)
        prec = getattr(self, "_ribbon_dim_precision", None)
        u = units.currentText() if units else "mm"
        p = prec.value() if prec else 2

        tool_map = {
            "linear": LinearDimensionTool,
            "aligned": AlignedDimensionTool,
            "radial": RadialDimensionTool,
            "angular": AngularDimensionTool,
        }
        cls = tool_map.get(dim_type)
        if cls:
            tool = cls(self._view.redline_scene, self._undo_stack, self._view, u, p)
            tool.on_finish = self._set_select_tool
            self._tool_manager.set_tool(tool)

    def _open_symbol_browser(self):
        self._symbol_browser.setVisible(not self._symbol_browser.isVisible())

    def _on_place_symbol(self, sym_def, params):
        tool = SymbolTool(
            self._view.redline_scene, self._undo_stack, self._view, sym_def, params
        )
        tool.on_finish = self._set_select_tool
        self._tool_manager.set_tool(tool)

    # -- Slots --

    def _on_zoom_changed(self, zoom_level: float):
        self._zoom_label.setText(f"{zoom_level * 100:.0f}%")

    def _on_render_ready(self, result: RenderResult):
        self._view.redline_scene.set_pdf_pixmap(result)
        self._view.redline_scene.set_page_rect()
        self._update_page_label()

    def _on_render_error(self, error_msg: str):
        logger.error("PDF render error: %s", error_msg)
        QMessageBox.warning(self, "Render Error", f"Failed to render PDF page:\n{error_msg}")

    def _on_style_changed(self, style):
        tool = self._tool_manager.active_tool
        if hasattr(tool, "style"):
            tool.style = style

    def _update_page_label(self):
        if self._renderer.page_count > 0:
            self._page_label.setText(
                f"Page {self._renderer.current_page + 1} / {self._renderer.page_count}"
            )
        else:
            self._page_label.setText("")

    # -- Actions --

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF", "", "PDF Files (*.pdf);;All Files (*)"
        )
        if not path:
            logger.info("Open PDF cancelled by user")
            return
        logger.info("Opening PDF: %s", path)
        try:
            self._view.redline_scene.clear_pdf()
            self._renderer.open(path)
            self.setWindowTitle(f"PDF Redline - {path.split('/')[-1]}")
        except Exception as e:
            logger.exception("Failed to open PDF: %s", path)
            QMessageBox.warning(self, "Open Error", f"Failed to open PDF:\n{e}")

    def _save_project(self):
        if self._renderer.pdf_path is None:
            self.statusBar().showMessage("No PDF loaded", 3000)
            return
        if self._project_path is None:
            self._save_project_as()
            return
        self._do_save(self._project_path)

    def _save_project_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project", "", "Redline Files (*.redline);;All Files (*)"
        )
        if path:
            if not path.endswith(".redline"):
                path += ".redline"
            self._project_path = path
            self._do_save(path)

    def _do_save(self, path: str):
        logger.info("Saving project: %s", path)
        try:
            scene = self._view.redline_scene
            current_items = scene.get_annotation_items()
            all_pages = dict(scene._page_annotations)
            all_pages[scene.current_page] = [it.serialize() for it in current_items]
            save_project(path, self._renderer.pdf_path, all_pages)
            self._undo_stack.setClean()
            self.setWindowTitle(f"PDF Redline - {Path(path).stem}")
            self.statusBar().showMessage(f"Saved to {path}", 3000)
            logger.info("Project saved successfully")
        except Exception as e:
            logger.exception("Failed to save project: %s", path)
            QMessageBox.warning(self, "Save Error", f"Failed to save project:\n{e}")

    def _open_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "Redline Files (*.redline);;All Files (*)"
        )
        if not path:
            return
        data = load_project(path)
        pdf_path = data["pdf_path"]

        if not Path(pdf_path).exists():
            QMessageBox.warning(self, "PDF Not Found", f"Cannot find PDF:\n{pdf_path}")
            return

        if not data["hash_match"]:
            QMessageBox.warning(
                self, "PDF Changed",
                "The PDF file has been modified since this project was saved."
            )

        self._view.redline_scene.clear_pdf()
        self._renderer.open(pdf_path)
        self._project_path = path

        # Restore annotations for each page
        scene = self._view.redline_scene
        for page_idx, items in data["pages"].items():
            if page_idx == 0:
                for item in items:
                    item.setZValue(item.zValue() or 10)
                    scene.addItem(item)
            else:
                scene._page_annotations[page_idx] = [it.serialize() for it in items]

        self.setWindowTitle(f"PDF Redline - {Path(path).stem}")

    def _export_pdf(self):
        if self._renderer.pdf_path is None:
            self.statusBar().showMessage("No PDF loaded", 3000)
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PDF", "", "PDF Files (*.pdf);;All Files (*)"
        )
        if not path:
            return
        if not path.endswith(".pdf"):
            path += ".pdf"
        logger.info("Exporting PDF: %s", path)
        try:
            scene = self._view.redline_scene
            export_pdf(
                scene, self._renderer.pdf_path, path,
                scene._page_annotations, self._renderer
            )
            self.statusBar().showMessage(f"Exported to {path}", 3000)
            logger.info("PDF exported successfully")
        except Exception as e:
            logger.exception("Failed to export PDF: %s", path)
            QMessageBox.warning(self, "Export Error", f"Failed to export PDF:\n{e}")

    def _print_document(self):
        print_scene(self._view.redline_scene, self)

    # -- Edit / clipboard --

    CLIPBOARD_MIME = "application/x-pdfredline-annotations"
    PASTE_OFFSET = 20.0

    def _selected_annotations(self) -> list[AnnotationItem]:
        return [
            it for it in self._view.redline_scene.selectedItems()
            if isinstance(it, AnnotationItem)
        ]

    def _copy_selection(self):
        items = self._selected_annotations()
        if not items:
            return
        payload = json.dumps([it.serialize() for it in items])
        mime = QMimeData()
        mime.setData(self.CLIPBOARD_MIME, payload.encode("utf-8"))
        QApplication.clipboard().setMimeData(mime)
        self.statusBar().showMessage(f"Copied {len(items)} annotation(s)", 2000)

    def _cut_selection(self):
        items = self._selected_annotations()
        if not items:
            return
        self._copy_selection()
        scene = self._view.redline_scene
        self._undo_stack.beginMacro(f"Cut {len(items)} annotation(s)")
        for item in items:
            self._undo_stack.push(RemoveAnnotationCommand(scene, item))
        self._undo_stack.endMacro()

    def _paste_clipboard(self):
        mime = QApplication.clipboard().mimeData()
        if not mime.hasFormat(self.CLIPBOARD_MIME):
            return
        try:
            payload = bytes(mime.data(self.CLIPBOARD_MIME)).decode("utf-8")
            data_list = json.loads(payload)
        except (ValueError, UnicodeDecodeError):
            return

        scene = self._view.redline_scene
        scene.clearSelection()
        new_items = []
        for data in data_list:
            item = deserialize_annotation(data)
            if item is None:
                continue
            item.setPos(item.pos().x() + self.PASTE_OFFSET,
                       item.pos().y() + self.PASTE_OFFSET)
            new_items.append(item)

        if not new_items:
            return
        self._undo_stack.beginMacro(f"Paste {len(new_items)} annotation(s)")
        for item in new_items:
            self._undo_stack.push(AddAnnotationCommand(scene, item))
            item.setSelected(True)
        self._undo_stack.endMacro()
        self.statusBar().showMessage(f"Pasted {len(new_items)} annotation(s)", 2000)

    def _select_all(self):
        scene = self._view.redline_scene
        for item in scene.items():
            if isinstance(item, AnnotationItem):
                item.setSelected(True)

    def _delete_selection(self):
        items = self._selected_annotations()
        if not items:
            return
        scene = self._view.redline_scene
        self._undo_stack.beginMacro(f"Delete {len(items)} annotation(s)")
        for item in items:
            self._undo_stack.push(RemoveAnnotationCommand(scene, item))
        self._undo_stack.endMacro()

    def _next_page(self):
        if self._renderer.page_count == 0:
            return
        new_page = self._renderer.current_page + 1
        if new_page < self._renderer.page_count:
            self._view.redline_scene.switch_page(new_page)
            self._renderer.render_page(new_page)

    def _prev_page(self):
        if self._renderer.page_count == 0:
            return
        new_page = self._renderer.current_page - 1
        if new_page >= 0:
            self._view.redline_scene.switch_page(new_page)
            self._renderer.render_page(new_page)
