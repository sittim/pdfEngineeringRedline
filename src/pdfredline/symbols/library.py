"""Symbol library — scans directories for SVG+JSON symbol definitions."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SymbolDefinition:
    name: str
    category: str
    description: str
    svg_path: str
    parameters: list[dict] = field(default_factory=list)
    snap_points: list[dict] = field(default_factory=list)


class SymbolLibrary:
    """Loads symbol definitions from a directory tree."""

    def __init__(self):
        self.categories: dict[str, list[SymbolDefinition]] = {}

    def scan(self, base_dir: str | Path):
        """Scan base_dir for category subdirectories containing SVG+JSON pairs."""
        base = Path(base_dir)
        if not base.exists():
            return

        for category_dir in sorted(base.iterdir()):
            if not category_dir.is_dir():
                continue
            category_name = category_dir.name
            symbols = []
            for json_file in sorted(category_dir.glob("*.json")):
                svg_file = json_file.with_suffix(".svg")
                if not svg_file.exists():
                    continue
                with open(json_file) as f:
                    meta = json.load(f)
                sym = SymbolDefinition(
                    name=meta.get("name", json_file.stem),
                    category=meta.get("category", category_name),
                    description=meta.get("description", ""),
                    svg_path=str(svg_file),
                    parameters=meta.get("parameters", []),
                    snap_points=meta.get("snap_points", []),
                )
                symbols.append(sym)
            if symbols:
                self.categories[category_name] = symbols

    def all_symbols(self) -> list[SymbolDefinition]:
        result = []
        for syms in self.categories.values():
            result.extend(syms)
        return result

    def get_symbol(self, name: str) -> SymbolDefinition | None:
        for syms in self.categories.values():
            for s in syms:
                if s.name == name:
                    return s
        return None
