from pdfredline.annotations.base import AnnotationItem
from pdfredline.annotations.shapes import LineAnnotation, RectAnnotation
from pdfredline.app import MainWindow


def _annotation_count(window: MainWindow) -> int:
    return len([
        it for it in window.view.redline_scene.items()
        if isinstance(it, AnnotationItem)
    ])


def test_copy_paste_roundtrip(qapp):
    window = MainWindow()
    scene = window.view.redline_scene

    rect = RectAnnotation(120, 80)
    rect.setPos(50, 60)
    scene.addItem(rect)
    rect.setSelected(True)

    window._copy_selection()
    window._paste_clipboard()

    assert _annotation_count(window) == 2
    rects = [it for it in scene.items() if isinstance(it, RectAnnotation)]
    assert len(rects) == 2
    positions = sorted((r.pos().x(), r.pos().y()) for r in rects)
    # Original at (50, 60), pasted at (50 + 20, 60 + 20)
    assert positions[0] == (50.0, 60.0)
    assert positions[1] == (70.0, 80.0)
    window.close()


def test_cut_removes_original(qapp):
    window = MainWindow()
    scene = window.view.redline_scene

    rect = RectAnnotation(100, 50)
    rect.setPos(10, 10)
    scene.addItem(rect)
    rect.setSelected(True)

    window._cut_selection()
    assert _annotation_count(window) == 0

    # Paste should restore it (offset)
    window._paste_clipboard()
    assert _annotation_count(window) == 1
    window.close()


def test_select_all_selects_only_annotations(qapp):
    window = MainWindow()
    scene = window.view.redline_scene

    line = LineAnnotation(0, 0, 100, 100)
    rect = RectAnnotation(50, 50)
    scene.addItem(line)
    scene.addItem(rect)

    window._select_all()
    assert line.isSelected()
    assert rect.isSelected()
    window.close()


def test_delete_selection(qapp):
    window = MainWindow()
    scene = window.view.redline_scene

    rect1 = RectAnnotation(50, 50)
    rect2 = RectAnnotation(60, 60)
    scene.addItem(rect1)
    scene.addItem(rect2)

    rect1.setSelected(True)
    window._delete_selection()
    assert _annotation_count(window) == 1
    assert rect2.scene() is scene
    window.close()


def test_cut_undo_restores_items(qapp):
    window = MainWindow()
    scene = window.view.redline_scene

    rect = RectAnnotation(100, 50)
    scene.addItem(rect)
    rect.setSelected(True)

    window._cut_selection()
    assert _annotation_count(window) == 0

    # Macro should undo as a single step
    window._undo_stack.undo()
    assert _annotation_count(window) == 1
    window.close()
