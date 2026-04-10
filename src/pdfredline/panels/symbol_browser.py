"""Symbol library browser panel."""
from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pdfredline.symbols.library import SymbolDefinition, SymbolLibrary

if TYPE_CHECKING:
    pass


class SymbolBrowserPanel(QDockWidget):
    """Dock widget for browsing and selecting symbols from the library."""

    symbol_selected = Signal(object)  # SymbolDefinition
    place_symbol = Signal(object, dict)  # SymbolDefinition, parameters

    def __init__(self, library: SymbolLibrary, parent=None):
        super().__init__("Symbol Library", parent)
        self._library = library
        self._current_def: SymbolDefinition | None = None
        self._param_edits: dict[str, QLineEdit] = {}
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )

        container = QWidget()
        layout = QVBoxLayout(container)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # Category tree
        self._tree = QTreeWidget()
        self._tree.setHeaderLabel("Symbols")
        self._populate_tree()
        self._tree.itemClicked.connect(self._on_item_clicked)
        splitter.addWidget(self._tree)

        # Parameter editor
        self._param_widget = QWidget()
        self._param_layout = QVBoxLayout(self._param_widget)
        self._param_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        splitter.addWidget(self._param_widget)

        layout.addWidget(splitter)

        # Place button
        self._place_btn = QPushButton("Place Symbol")
        self._place_btn.setEnabled(False)
        self._place_btn.clicked.connect(self._on_place)
        layout.addWidget(self._place_btn)

        self.setWidget(container)

    def _populate_tree(self):
        self._tree.clear()
        for category, symbols in self._library.categories.items():
            cat_item = QTreeWidgetItem([category.upper()])
            for sym in symbols:
                child = QTreeWidgetItem([sym.name])
                child.setData(0, Qt.ItemDataRole.UserRole, sym)
                cat_item.addChild(child)
            self._tree.addTopLevelItem(cat_item)
            cat_item.setExpanded(True)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        sym = item.data(0, Qt.ItemDataRole.UserRole)
        if sym is None:
            return
        self._current_def = sym
        self._place_btn.setEnabled(True)
        self._build_param_editor(sym)

    def _build_param_editor(self, sym: SymbolDefinition):
        # Clear existing
        while self._param_layout.count():
            child = self._param_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._param_edits.clear()

        self._param_layout.addWidget(QLabel(f"Parameters: {sym.name}"))
        for param in sym.parameters:
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.addWidget(QLabel(param["label"] + ":"))
            edit = QLineEdit(param.get("default", ""))
            self._param_edits[param["id"]] = edit
            h.addWidget(edit)
            self._param_layout.addWidget(row)

    def _on_place(self):
        if self._current_def is None:
            return
        params = {k: e.text() for k, e in self._param_edits.items()}
        self.place_symbol.emit(self._current_def, params)
