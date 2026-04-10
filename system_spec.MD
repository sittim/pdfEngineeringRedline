# PDF Redline Application — System Specification

## 1. Technology Decision: Python + PySide6 (Qt)

### Why Python + Qt

Python was evaluated against JavaScript/Electron, C#/Avalonia, Dart/Flutter, and Rust/Tauri. Python + PySide6 wins on the combination of:

- **Rapid development** — Python is the fastest language to iterate in; Qt provides the richest desktop widget set
- **QGraphicsScene / QGraphicsView** — a retained-mode vector scene graph with built-in zoom, pan, selection, drag, z-ordering, and hit-testing. No other Python framework offers anything comparable. This is the single biggest differentiator.
- **All annotations are vector objects** — every line, shape, text box, and symbol lives as a `QGraphicsItem` in the scene graph. They remain individually selectable, editable, movable, and resizable at all times. Nothing is rasterized.
- **Cross-platform** — single codebase runs on macOS, Linux, Windows
- **LGPL license** (PySide6) — can be used in closed-source commercial applications

### Alternatives Considered and Rejected

| Option | Reason Rejected |
|--------|----------------|
| PyQt6 | GPL license requires commercial license (~500 GBP/yr) for closed-source distribution. Functionally identical to PySide6. |
| wxPython | Built-in `wx.ribbon.RibbonBar` is nice, but no scene-graph equivalent to QGraphicsView. Would require building the entire canvas/item system from scratch. |
| Tkinter | No affine transforms on canvas, no ribbon, no font dialog, poor performance with many items. |
| Dear PyGui | Immediate-mode GUI designed for dashboards, not document annotation. No scene graph. |
| Kivy | Touch/mobile-first. Fighting the framework for desktop mouse-driven workflows. |
| Electron + PDF.js | 150-300 MB RAM baseline per instance. Bundle size 100-200 MB. Good technically but heavy. |
| Flutter Desktop | No ribbon widget. PDF libraries are commercial. Desktop ecosystem is mobile-first. |
| Avalonia (C#) | Good fit but requires leaving Python. Ribbon only via commercial component vendors. |
| Tauri | WebView inconsistencies across Linux/Windows. Rust backend learning curve. |

## 2. Core Technology Stack

| Component | Package | Version | License | Purpose |
|-----------|---------|---------|---------|---------|
| Language | Python | 3.12+ | PSF | Application language |
| GUI Framework | PySide6 | 6.11.x | LGPL-3.0 | Widgets, canvas, dialogs, event loop |
| Qt Abstraction | qtpy | 2.4.x | MIT | Write once, run on PyQt5/6/PySide2/6 |
| PDF Rendering | pypdfium2 | 5.7.x | Apache-2.0 | Render PDF pages to pixel buffers for display |
| PDF Manipulation | pikepdf | 10.5.x | MPL-2.0 | Export annotations as vector PDF objects, flatten, merge |
| Ribbon Toolbar | pyqtribbon | 0.7.x | MIT | Microsoft Office-style ribbon UI |
| SVG Rendering | PySide6 QtSvg / QtSvgWidgets | (bundled) | LGPL-3.0 | Render symbol SVGs in scene at any zoom |
| SVG Creation | svgwrite | 1.4.x | MIT | Programmatic symbol SVG generation |
| Packaging | PyInstaller | 6.19.x | GPL-2.0 (tool only) | Build standalone executables for all platforms |

### Licensing Note

All runtime dependencies are LGPL, Apache-2.0, MPL-2.0, or MIT — all compatible with closed-source commercial distribution. PyInstaller is GPL but it is a build tool, not a runtime dependency, so it does not affect the application's license.

### Why pypdfium2 + pikepdf Instead of PyMuPDF

PyMuPDF has the best single-library API for PDF work, but its **AGPL-3.0** license requires either open-sourcing the entire application or purchasing a commercial license from Artifex. The pypdfium2 (Apache-2.0) + pikepdf (MPL-2.0) combination provides equivalent capability with no copyleft concern:

- **pypdfium2** — renders PDF pages to numpy arrays or PIL images at arbitrary DPI. Performance matches PyMuPDF. Based on Google's PDFium engine (same engine Chrome uses).
- **pikepdf** — writes annotation data as vector PDF objects during export. Handles flattening (`flatten_annotations()`), page manipulation, merge, encrypt. Based on the qpdf library.

## 3. Architecture Overview

```
+------------------------------------------------------------+
|                    Application Window                       |
|  +------------------------------------------------------+  |
|  |              Ribbon Toolbar (pyqtribbon)              |  |
|  |  [File] [View] [Draw] [Text] [Dimensions] [Symbols]  |  |
|  +------------------------------------------------------+  |
|  +------------------------------------------+  +--------+  |
|  |                                          |  |Property|  |
|  |          QGraphicsView                   |  | Panel  |  |
|  |  +------------------------------------+  |  |        |  |
|  |  |        QGraphicsScene              |  |  | Color  |  |
|  |  |                                    |  |  | Font   |  |
|  |  |  [PDF Page as QGraphicsPixmapItem] |  |  | Stroke |  |
|  |  |  [Line Items      ]  (vector)      |  |  | Fill   |  |
|  |  |  [Rect Items      ]  (vector)      |  |  | Params |  |
|  |  |  [Text Items      ]  (vector)      |  |  |        |  |
|  |  |  [Dimension Items  ]  (vector)      |  |  |        |  |
|  |  |  [Symbol SVG Items ]  (vector)      |  |  |        |  |
|  |  +------------------------------------+  |  |        |  |
|  +------------------------------------------+  +--------+  |
|  +------------------------------------------------------+  |
|  |              Status Bar (zoom %, page #)              |  |
|  +------------------------------------------------------+  |
+------------------------------------------------------------+
```

### Vector-First Design

Every annotation is a `QGraphicsItem` subclass living in the scene graph:

- **Lines, rectangles, circles, ovals, triangles** — stored as mathematical definitions (endpoints, center+radius, bounding rect, vertices). Rendered via QPainter vector paths. Editable at any time by selecting and modifying control points.
- **Text** — stored as `QGraphicsTextItem` with font, size, color properties. Double-click to re-edit content. Rendered as vector text at any zoom level.
- **Dimensions** — composite items (leader lines + arrowheads + measurement text). Recalculate when snap-point sources move.
- **Symbols** — `QGraphicsSvgItem` renders SVG at any scale without quality loss. Text parameters stored in the item and substituted into the SVG at render time.
- **PDF background** — rendered via pypdfium2 as a `QGraphicsPixmapItem` at a resolution matching the current zoom level. Re-rendered at higher DPI when zooming in to maintain sharpness. This is the only raster element; it exists purely for display of the underlying PDF.

On export, annotations are written as **native PDF vector objects** (paths, text runs) via pikepdf — not as rasterized images stamped onto the page.

## 4. Scene Graph and Annotation Model

### QGraphicsScene Layer Structure

| Z-Order | Layer | Contents |
|---------|-------|----------|
| 0 | PDF Background | `QGraphicsPixmapItem` — rasterized PDF page for display only |
| 10 | Geometric Primitives | Lines, rectangles, circles, ovals, triangles, freehand paths |
| 20 | Text Annotations | `QGraphicsTextItem` instances |
| 30 | Dimension Annotations | Composite items (lines + arrowheads + text) |
| 40 | Symbol Blocks | `QGraphicsSvgItem` instances with parameterized text |
| 50 | Snap Point Indicators | Temporary visual indicators shown during dimension placement |

### Annotation Data Model

Each annotation stores:

```
AnnotationBase:
    id:         UUID
    type:       enum (line, rect, circle, oval, triangle, freehand, text, dimension, symbol)
    position:   (x, y) in PDF coordinate space
    rotation:   degrees
    z_index:    int
    locked:     bool
    created_at: timestamp
    modified_at: timestamp

GeometricAnnotation(AnnotationBase):
    geometry:     type-specific (endpoints, center+radius, vertices, path points)
    stroke_color: RGBA
    stroke_width: float
    fill_color:   RGBA | None
    line_style:   solid | dashed | dotted

TextAnnotation(AnnotationBase):
    content:    string
    font_family: string
    font_size:  float
    color:      RGBA

DimensionAnnotation(AnnotationBase):
    dim_type:    linear | aligned | radial | angular
    snap_source: reference to source annotation + snap point
    snap_target: reference to target annotation + snap point
    offset:      perpendicular offset of dimension line from measured geometry
    units:       mm | inches
    precision:   int (decimal places)
    style:       arrow style, text placement

SymbolAnnotation(AnnotationBase):
    symbol_id:   reference to symbol definition
    parameters:  dict of {field_name: user_value}
    scale:       float
```

### Snap Point System

When the dimension tool is active, the system queries all annotations in the scene for their snap points:

| Annotation Type | Snap Points Provided |
|-----------------|---------------------|
| Line | Endpoints, midpoint |
| Rectangle | 4 corners, 4 edge midpoints, center |
| Circle | Center, 4 quadrant points (0, 90, 180, 270) |
| Oval | Center, 4 quadrant points |
| Triangle | 3 vertices, 3 edge midpoints |

Snap detection radius: configurable (default 10 pixels at current zoom). Visual indicator (small circle or crosshair) appears when cursor is within snap range.

## 5. PDF Rendering Pipeline

```
PDF File on Disk
       |
       v
pypdfium2.PdfDocument.open(path)
       |
       v
PdfPage.render(scale=current_zoom_dpi/72)
       |
       v
numpy array (RGB pixel buffer)
       |
       v
QImage(data, width, height, stride, QImage.Format_RGB888)
       |
       v
QPixmap.fromImage(qimage)
       |
       v
QGraphicsPixmapItem added to scene at z=0
```

**Adaptive re-rendering:** When the user zooms in beyond the current render resolution, the page is re-rendered at a higher DPI in a background thread (`QThread` or `QRunnable`) and the pixmap item is swapped. This keeps the PDF background sharp at all zoom levels without blocking the UI.

## 6. PDF Export Pipeline (Vector Output)

```
QGraphicsScene (all annotation items)
       |
       v
Iterate annotations, convert each to PDF objects:
  - Lines/Rects/Circles → PDF path operators (m, l, c, re, etc.)
  - Text → PDF text objects (BT/ET with Tf, Td, Tj operators)
  - Symbols → SVG paths converted to PDF path operators
       |
       v
pikepdf: open original PDF, add annotation objects to each page
       |
       v
pikepdf: save new PDF (original content untouched, annotations overlaid as vector)
```

Annotations are written as **PDF content stream operations** or **PDF annotation objects** — never as rasterized images. This preserves vector quality at any zoom in any PDF viewer.

## 7. Project File Format

The application saves its working state to a `.redline` project file (JSON):

```json
{
    "version": "1.0",
    "pdf_path": "/path/to/original.pdf",
    "pdf_hash": "sha256:...",
    "pages": {
        "1": {
            "annotations": [
                {
                    "id": "uuid",
                    "type": "line",
                    "geometry": {"x1": 100, "y1": 200, "x2": 300, "y2": 400},
                    "stroke_color": [255, 0, 0, 255],
                    "stroke_width": 2.0,
                    "line_style": "solid"
                },
                {
                    "id": "uuid",
                    "type": "text",
                    "position": {"x": 150, "y": 250},
                    "content": "CHECK THIS DIMENSION",
                    "font_family": "Arial",
                    "font_size": 14,
                    "color": [255, 0, 0, 255]
                }
            ]
        }
    }
}
```

The original PDF is never modified. The project file references it by path and verifies integrity via SHA-256 hash.

## 8. Symbol System Architecture

### Symbol Definition Format

Each symbol is an SVG file + a JSON metadata sidecar:

```
symbols/
├── welding/
│   ├── fillet_weld.svg          # Vector artwork with text placeholders
│   ├── fillet_weld.json         # Parameter schema + snap points
│   ├── groove_weld.svg
│   ├── groove_weld.json
│   └── ...
├── gdt/
│   ├── position_frf.svg
│   ├── position_frf.json
│   └── ...
└── surface/
    ├── surface_finish.svg
    ├── surface_finish.json
    └── ...
```

**JSON metadata example (`fillet_weld.json`):**

```json
{
    "name": "Fillet Weld",
    "category": "welding",
    "description": "AWS A2.4 fillet weld symbol",
    "parameters": [
        {"id": "size", "label": "Weld Size", "type": "text", "default": "6"},
        {"id": "length", "label": "Length", "type": "text", "default": ""},
        {"id": "pitch", "label": "Pitch", "type": "text", "default": ""},
        {"id": "process", "label": "Process", "type": "text", "default": "GMAW"}
    ],
    "snap_points": [
        {"id": "arrow_tip", "x": 0, "y": 50},
        {"id": "tail", "x": 100, "y": 50}
    ]
}
```

**SVG text placeholders:** The SVG contains `<text>` elements with IDs matching the JSON parameter IDs. At render time, the application parses the SVG with `xml.etree.ElementTree`, replaces placeholder text content with user-supplied values, and feeds the modified SVG to `QSvgRenderer` → `QGraphicsSvgItem`.

**Extensibility:** Drop a new `.svg` + `.json` pair into the appropriate category subdirectory. The application scans the `symbols/` directory tree at startup and populates the library browser. No code changes required.

## 9. Ribbon Toolbar Implementation

Using `pyqtribbon` 0.7.8, the ribbon replaces the standard `QMenuBar` + `QToolBar`:

| Tab | Panels | Key Controls |
|-----|--------|-------------|
| File | Document | Open, Save (.redline), Export (PDF), Print |
| View | Zoom | + button, - button, Fit Page, Fit Width, zoom % display |
| View | Navigate | Previous Page, Next Page, page number entry |
| Draw | Shapes | Line, Rectangle, Circle, Oval, Triangle, Freehand (large icon buttons) |
| Draw | Style | Stroke color picker, stroke width spinner, fill color picker, line style dropdown |
| Text | Insert | Add Text button |
| Text | Format | Font family combo, font size spinner, text color picker |
| Dimensions | Measure | Linear, Aligned, Radial, Angular (large icon buttons) |
| Dimensions | Settings | Units dropdown (mm/in), precision spinner |
| Symbols | Library | Symbol browser gallery, categorized by type |

## 10. Navigation Implementation

### Zoom (Mouse Wheel)

Override `QGraphicsView.wheelEvent`:
- Calculate zoom factor (e.g., 1.15x per wheel step)
- Apply `view.scale(factor, factor)` centered on cursor position via `setTransformationAnchor(AnchorUnderMouse)`
- Update status bar zoom percentage
- Trigger background PDF re-render if zoom exceeds current render DPI threshold

### Pan (Middle Mouse Drag)

Override `QGraphicsView.mousePressEvent` / `mouseMoveEvent` / `mouseReleaseEvent`:
- On middle button press: store starting position, set cursor to closed hand
- On move: translate the view by the mouse delta
- On release: restore cursor

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+= / Cmd+= | Zoom in |
| Ctrl+- / Cmd+- | Zoom out |
| Ctrl+0 / Cmd+0 | Fit page |
| Ctrl+Z / Cmd+Z | Undo |
| Ctrl+Shift+Z / Cmd+Shift+Z | Redo |
| Delete / Backspace | Delete selected annotations |
| Escape | Deselect / cancel current tool |
| Ctrl+S / Cmd+S | Save project |
| Ctrl+A / Cmd+A | Select all annotations |

## 11. Cross-Platform Packaging

| Platform | Output | Build Tool | Extras |
|----------|--------|-----------|--------|
| macOS | .app bundle inside .dmg | PyInstaller `--windowed` | `create-dmg` for disk image |
| Windows | .exe installer | PyInstaller `--onefile` or `--onedir` | NSIS or Inno Setup for installer |
| Linux | AppImage | PyInstaller | `appimagetool` or `linuxdeploy` for AppImage wrapping |

PyInstaller 6.19.x has built-in hooks for PySide6 — it automatically bundles Qt plugins, platform themes, and shared libraries.

**CI/CD:** GitHub Actions with macOS, Ubuntu, and Windows runners building all three targets from a single repository.

## 12. Dependency Summary

### Runtime (pip install)

```
PySide6>=6.11.0
qtpy>=2.4.0
pypdfium2>=5.7.0
pikepdf>=10.5.0
pyqtribbon>=0.7.8
svgwrite>=1.4.3
```

### Build / Dev

```
pyinstaller>=6.19.0
pytest>=8.0
ruff>=0.4.0
```
