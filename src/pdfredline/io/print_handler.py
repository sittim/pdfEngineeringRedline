"""Print the annotated PDF using QPrinter."""
from __future__ import annotations

from qtpy.QtCore import QRectF
from qtpy.QtGui import QPainter
from qtpy.QtPrintSupport import QPrintDialog, QPrinter

from pdfredline.canvas.scene import RedlineScene


def print_scene(scene: RedlineScene, parent=None):
    """Open a print dialog and print the scene content."""
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    dialog = QPrintDialog(printer, parent)

    if dialog.exec() == QPrintDialog.DialogCode.Accepted:
        painter = QPainter(printer)
        scene_rect = scene.itemsBoundingRect()
        target_rect = QRectF(
            0, 0,
            painter.device().width(),
            painter.device().height(),
        )
        scene.render(painter, target_rect, scene_rect)
        painter.end()
