"""Export annotations as vector PDF overlaid on the original PDF."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pikepdf
from qtpy.QtCore import QMarginsF, QRectF, QSizeF
from qtpy.QtGui import QPageSize, QPainter, QPdfWriter

from pdfredline.canvas.scene import RedlineScene


def export_pdf(scene: RedlineScene, original_pdf_path: str, output_path: str,
               page_annotations: dict[int, list], renderer):
    """Export annotated PDF by rendering annotations via QPdfWriter then merging with pikepdf.

    Args:
        scene: The RedlineScene (used for current page annotations).
        original_pdf_path: Path to the original PDF.
        output_path: Path for the output PDF.
        page_annotations: Dict of page_index -> list of serialized annotation dicts.
        renderer: PdfRenderer instance for page info.
    """
    import pypdfium2 as pdfium

    original = pikepdf.Pdf.open(original_pdf_path)
    num_pages = len(original.pages)

    # Collect current page annotations
    current_items = scene.get_annotation_items()
    all_pages = dict(page_annotations)
    if current_items:
        all_pages[scene.current_page] = current_items

    # For each page that has annotations, render annotations to a temp PDF
    overlay_pdfs: dict[int, str] = {}

    for page_idx in range(num_pages):
        items = all_pages.get(page_idx, [])
        if not items:
            continue

        # Get page size from the original PDF
        doc = pdfium.PdfDocument(original_pdf_path)
        page = doc[page_idx]
        page_w_pts = page.get_width()
        page_h_pts = page.get_height()
        page.close()
        doc.close()

        # Create a temp PDF with just the annotations
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        writer = QPdfWriter(tmp_path)
        page_size = QPageSize(QSizeF(page_w_pts, page_h_pts), QPageSize.Unit.Point)
        writer.setPageSize(page_size)
        writer.setPageMargins(QMarginsF(0, 0, 0, 0))
        # Resolution: 72 DPI so 1 point = 1 device pixel
        writer.setResolution(72)

        painter = QPainter(writer)

        # If items are QGraphicsItems (current page), render them directly
        if items and hasattr(items[0], "paint"):
            scene_rect = QRectF(0, 0, page_w_pts, page_h_pts)
            target_rect = QRectF(0, 0, page_w_pts, page_h_pts)
            # Temporarily hide the PDF background
            bg = scene._pdf_background
            if bg:
                bg.setVisible(False)
            scene.render(painter, target_rect, scene_rect)
            if bg:
                bg.setVisible(True)
        painter.end()

        overlay_pdfs[page_idx] = tmp_path

    # Merge overlays onto original pages using pikepdf
    for page_idx, overlay_path in overlay_pdfs.items():
        overlay_pdf = pikepdf.Pdf.open(overlay_path)
        if len(overlay_pdf.pages) > 0:
            # Get the Form XObject from the overlay
            original_page = original.pages[page_idx]
            original.pages[page_idx] = original_page

            # Stamp overlay content onto original page
            stamp = pikepdf.Pdf.open(overlay_path)
            original_page = original.pages[page_idx]

            # Use pikepdf's page overlay approach
            stamp_page = stamp.pages[0]
            stamp_page_obj = stamp_page.as_form_xobject()
            new_xobj = original.copy_foreign(stamp_page_obj)

            resources = original_page.get("/Resources", pikepdf.Dictionary())
            xobjects = resources.get("/XObject", pikepdf.Dictionary())
            xobj_name = pikepdf.Name(f"/RedlineOverlay{page_idx}")
            xobjects[xobj_name] = new_xobj
            resources["/XObject"] = xobjects
            original_page["/Resources"] = resources

            # Append a content stream that draws the overlay
            content = f"q {xobj_name} Do Q\n".encode()
            new_stream = pikepdf.Stream(original, content)
            existing = original_page.get("/Contents")
            if isinstance(existing, pikepdf.Array):
                existing.append(new_stream)
            elif existing is not None:
                original_page["/Contents"] = pikepdf.Array([existing, new_stream])
            else:
                original_page["/Contents"] = new_stream

            stamp.close()
        overlay_pdf.close()
        Path(overlay_path).unlink(missing_ok=True)

    original.save(output_path)
    original.close()
