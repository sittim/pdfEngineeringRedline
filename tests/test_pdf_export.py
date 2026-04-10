import os
import tempfile

import pikepdf

from pdfredline.annotations.shapes import LineAnnotation, RectAnnotation
from pdfredline.canvas.scene import RedlineScene
from pdfredline.io.pdf_export import export_pdf

SAMPLE_PDF = os.path.join(os.path.dirname(__file__), "fixtures", "sample.pdf")


def test_export_creates_pdf(qapp):
    scene = RedlineScene()

    # Add annotations to scene
    line = LineAnnotation(10, 20, 300, 200)
    line.setPos(50, 50)
    line.setZValue(10)
    scene.addItem(line)

    rect = RectAnnotation(100, 60)
    rect.setPos(100, 100)
    rect.setZValue(10)
    scene.addItem(rect)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        output_path = f.name

    try:
        export_pdf(scene, SAMPLE_PDF, output_path, {}, None)

        # Verify output exists and is a valid PDF
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0

        doc = pikepdf.Pdf.open(output_path)
        assert len(doc.pages) == 3  # Same as original
        doc.close()
    finally:
        os.unlink(output_path)
