from pathlib import Path

from pdfredline.annotations.symbols import SymbolAnnotation
from pdfredline.symbols.library import SymbolLibrary

SYMBOLS_DIR = Path(__file__).parent.parent / "src" / "pdfredline" / "symbols"


def test_library_scan(qapp):
    lib = SymbolLibrary()
    lib.scan(SYMBOLS_DIR)
    assert "welding" in lib.categories
    assert "gdt" in lib.categories
    assert "surface" in lib.categories
    assert len(lib.all_symbols()) >= 3


def test_library_get_symbol(qapp):
    lib = SymbolLibrary()
    lib.scan(SYMBOLS_DIR)
    sym = lib.get_symbol("Fillet Weld")
    assert sym is not None
    assert sym.category == "welding"
    assert len(sym.parameters) == 2


def test_symbol_annotation_serialize(qapp):
    lib = SymbolLibrary()
    lib.scan(SYMBOLS_DIR)
    sym = lib.get_symbol("Fillet Weld")
    assert sym is not None

    item = SymbolAnnotation(
        svg_path=sym.svg_path,
        symbol_name=sym.name,
        parameters={"size": "8", "process": "FCAW"},
    )
    data = item.serialize()
    restored = SymbolAnnotation.from_data(data)
    assert restored.symbol_name == "Fillet Weld"
    assert restored.parameters["size"] == "8"
    assert restored.parameters["process"] == "FCAW"


def test_symbol_text_positions_parsed(qapp):
    """Each editable <text id=...> in the SVG should be captured with its (x, y)."""
    lib = SymbolLibrary()
    lib.scan(SYMBOLS_DIR)
    sym = lib.get_symbol("Position")
    assert sym is not None
    item = SymbolAnnotation(
        svg_path=sym.svg_path,
        symbol_name=sym.name,
        parameters={"tolerance": "0.05", "datum_a": "A", "datum_b": "B"},
    )
    assert "tolerance" in item._text_positions
    assert "datum_a" in item._text_positions
    assert "datum_b" in item._text_positions
    tx, ty = item._text_positions["tolerance"]
    assert tx > 0 and ty > 0


def test_symbol_inline_edit_commit_changes_parameters(qapp):
    """Opening editors, changing values, and committing updates parameters and undo."""
    from pdfredline.canvas.scene import RedlineScene
    from pdfredline.commands.undo import UndoStack

    lib = SymbolLibrary()
    lib.scan(SYMBOLS_DIR)
    sym = lib.get_symbol("Position")
    assert sym is not None

    scene = RedlineScene()
    undo = UndoStack()
    scene.set_undo_stack(undo)

    item = SymbolAnnotation(
        svg_path=sym.svg_path,
        symbol_name=sym.name,
        parameters={"tolerance": "0.05", "datum_a": "A", "datum_b": "B"},
    )
    scene.addItem(item)

    item._open_inline_editors()
    assert item._editing is True
    assert "tolerance" in item._edit_proxies

    # Simulate the user changing the tolerance field
    proxy = item._edit_proxies["tolerance"]
    edit_widget = proxy.widget()
    edit_widget.setText("0.025")
    item._on_field_text_edited("tolerance", "0.025")

    # Commit
    item._commit_edits()
    assert item._editing is False
    assert item.parameters["tolerance"] == "0.025"
    assert undo.count() == 1

    # Undo restores the original
    undo.undo()
    assert item.parameters["tolerance"] == "0.05"

    # Redo reapplies
    undo.redo()
    assert item.parameters["tolerance"] == "0.025"


def test_symbol_inline_edit_cancel_reverts(qapp):
    """Cancelling restores original parameters and pushes nothing to undo stack."""
    from pdfredline.canvas.scene import RedlineScene
    from pdfredline.commands.undo import UndoStack

    lib = SymbolLibrary()
    lib.scan(SYMBOLS_DIR)
    sym = lib.get_symbol("Position")
    assert sym is not None

    scene = RedlineScene()
    undo = UndoStack()
    scene.set_undo_stack(undo)

    item = SymbolAnnotation(
        svg_path=sym.svg_path,
        symbol_name=sym.name,
        parameters={"tolerance": "0.05", "datum_a": "A", "datum_b": "B"},
    )
    scene.addItem(item)

    item._open_inline_editors()
    edit_widget = item._edit_proxies["tolerance"].widget()
    edit_widget.setText("0.999")
    item._on_field_text_edited("tolerance", "0.999")

    item._cancel_edits()
    assert item._editing is False
    assert item.parameters["tolerance"] == "0.05"
    assert undo.count() == 0
