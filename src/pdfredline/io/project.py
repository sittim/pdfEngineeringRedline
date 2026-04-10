"""Save and load .redline project files (JSON)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

# Ensure annotation types are registered
import pdfredline.annotations.shapes  # noqa: F401
import pdfredline.annotations.text  # noqa: F401
from pdfredline.annotations.registry import deserialize_annotation


def compute_pdf_hash(pdf_path: str) -> str:
    h = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def save_project(path: str, pdf_path: str, pages: dict[int, list[dict]]):
    """Save project to a .redline JSON file.

    Args:
        path: Output .redline file path.
        pdf_path: Path to the original PDF.
        pages: Dict mapping page index -> list of serialized annotation dicts.
    """
    data = {
        "version": "1.0",
        "pdf_path": pdf_path,
        "pdf_hash": compute_pdf_hash(pdf_path),
        "pages": {str(k): v for k, v in pages.items()},
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_project(path: str) -> dict:
    """Load a .redline project file.

    Returns dict with keys: version, pdf_path, pdf_hash, pages.
    pages is dict[int, list[AnnotationItem]].
    """
    with open(path) as f:
        data = json.load(f)

    pdf_path = data["pdf_path"]

    # Try to find the PDF
    if not Path(pdf_path).exists():
        # Look next to the .redline file
        redline_dir = Path(path).parent
        pdf_name = Path(pdf_path).name
        alt_path = redline_dir / pdf_name
        if alt_path.exists():
            pdf_path = str(alt_path)

    # Verify hash
    hash_match = True
    if Path(pdf_path).exists():
        actual_hash = compute_pdf_hash(pdf_path)
        hash_match = actual_hash == data.get("pdf_hash", "")

    # Deserialize annotations
    pages: dict[int, list] = {}
    for page_str, ann_list in data.get("pages", {}).items():
        page_idx = int(page_str)
        items = []
        for ann_data in ann_list:
            item = deserialize_annotation(ann_data)
            if item is not None:
                items.append(item)
        pages[page_idx] = items

    return {
        "version": data.get("version", "1.0"),
        "pdf_path": pdf_path,
        "pdf_hash": data.get("pdf_hash", ""),
        "hash_match": hash_match,
        "pages": pages,
    }
