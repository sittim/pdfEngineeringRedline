import os
import tempfile

from pdfredline.annotations.shapes import LineAnnotation, RectAnnotation
from pdfredline.io.project import compute_pdf_hash, load_project, save_project

SAMPLE_PDF = os.path.join(os.path.dirname(__file__), "fixtures", "sample.pdf")


def test_save_and_load_roundtrip(qapp):
    line = LineAnnotation(10, 20, 300, 400)
    rect = RectAnnotation(150, 80)
    rect.setPos(50, 100)

    pages = {
        0: [line.serialize(), rect.serialize()],
        1: [],
    }

    with tempfile.NamedTemporaryFile(suffix=".redline", delete=False) as f:
        project_path = f.name

    try:
        save_project(project_path, SAMPLE_PDF, pages)

        data = load_project(project_path)
        assert data["version"] == "1.0"
        assert data["hash_match"] is True
        assert len(data["pages"][0]) == 2
        assert isinstance(data["pages"][0][0], LineAnnotation)
        assert isinstance(data["pages"][0][1], RectAnnotation)
        assert data["pages"][0][1].width == 150
    finally:
        os.unlink(project_path)


def test_pdf_hash(qapp):
    h = compute_pdf_hash(SAMPLE_PDF)
    assert h.startswith("sha256:")
    assert len(h) > 10
