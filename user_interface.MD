# PDF Redline — User Interface Specification

## 1. Philosophy

The mouse interaction model is inspired by **Inkscape** and other modern vector editors (Affinity Designer, Figma). The user is always in one of two macro-modes:

1. **Pointer Mode** (the default) — the cursor is an arrow. Nothing new is created when you click. Instead, every click selects, manipulates, or edits an *existing* annotation.
2. **Tool Mode** — the user has explicitly picked a creation tool from the ribbon (Line, Rect, Text, Linear Dim, Symbol, etc.). The cursor is a crosshair or tool-specific shape. Clicking creates new annotations.

After a tool finishes its job (e.g. the line is drawn, the symbol is placed), the app **automatically returns to Pointer Mode**. This is the Inkscape pattern: tools are transient, selection is the resting state. The user never has to manually click "Select" after drawing one shape.

## 2. The Two Modes

### 2.1 Pointer Mode (default)

**Cursor:** standard arrow.

**Activated by:**
- Pressing the **Select** button in the ribbon
- Pressing **Esc** while in any tool mode
- Automatically after any creation tool finishes a single placement

**Mouse actions on the canvas:**

| Action | Result |
|--------|--------|
| **Single click** on an annotation | Select that annotation. Previous selection cleared (unless Shift held). Selection handles appear. |
| **Single click** on empty area | Deselect everything. |
| **Shift + click** on an annotation | Add to / remove from current selection (toggle). |
| **Click + drag** on a selected annotation | Move all selected annotations. |
| **Click + drag** on a selection handle | Resize the annotation (corner = uniform, edge = single axis). |
| **Click + drag** on empty area | Rubber-band selection — every annotation fully inside the rectangle becomes selected. |
| **Double click** on an annotation | Enter the annotation's **edit mode** (see §4). |
| **Right click** on an annotation | Context menu: Cut, Copy, Delete, Bring to Front, Send to Back, Properties, Edit (same as double-click). |

### 2.2 Tool Mode

**Cursor:** crosshair (or tool-specific glyph).

**Activated by:** clicking a creation button in the ribbon — Line, Rectangle, Circle, Oval, Triangle, Freehand, Text, Linear/Aligned/Radial/Angular Dimension, or any Symbol.

**Mouse actions on the canvas:** depend on the active tool. See §3.

**Exit:** automatic after one placement (returns to Pointer Mode), or **Esc** to cancel mid-placement.

## 3. Tool Mode Interaction Patterns

Each creation tool follows one of three patterns. The pattern is consistent across the entire application.

### 3.1 Click-Click pattern (Line, Linear Dim, Aligned Dim, Angular Dim)

1. **First click** anchors the start point. A live rubber-band preview attaches to the cursor.
2. The user **moves the mouse** without holding any button — the preview tracks the cursor in real time.
3. **Second click** finalizes the end point. The annotation is committed to the undo stack.
4. The app returns to **Pointer Mode** automatically.

For Angular Dim, this is extended to **three clicks**: vertex, then two endpoints.

**Esc** at any time cancels the in-progress placement and returns to Pointer Mode.

### 3.2 Click-Drag pattern (Rectangle, Circle, Oval, Freehand)

1. **Press** to anchor the first corner / center / first freehand point. The cursor changes to indicate dragging.
2. **Drag** with the button held — the preview grows with the cursor in real time.
3. **Release** to commit. The annotation is added to the undo stack.
4. The app returns to **Pointer Mode** automatically.

**Esc** during the drag cancels.

### 3.3 Single-click pattern (Text, Symbol Placement, Radial Dim)

1. **Click once** at the desired location. The annotation is placed and immediately selected.
2. The app returns to **Pointer Mode** automatically.
3. For Text, the new text annotation is also opened in inline edit mode (see §4.1).
4. For Symbol, the new symbol is selected so the user can reposition it.
5. For Radial Dim, the click must land on a circle/oval; otherwise it does nothing.

## 4. Edit Mode (the double-click experience)

**This is the core of the requested feature.** Each annotation type has its own *edit mode*, entered by double-clicking the annotation while in Pointer Mode. Edit mode is what makes the parameter values on a GD&T symbol (or any other parameterized object) directly modifiable.

When an annotation is in edit mode:
- A subtle highlight outline appears around it.
- Editable fields become live, in-place input widgets.
- Other interactions (selection of other items, panning, zooming) are temporarily suppressed.
- Pressing **Enter**, clicking elsewhere, or **Esc** commits or cancels the edit and returns the annotation to its normal selected state.

### 4.1 Text Annotation

Double-click → the text becomes a live editable text input directly on the canvas. The user types, the text reflows. Click outside or press **Esc** to commit. **Esc with no changes** discards.

### 4.2 Symbol Annotation (welding, GD&T, surface finish)

This is the GD&T case the user explicitly asked about.

A symbol like a position feature control frame contains parameter slots: tolerance value, datum A, datum B, etc. Each slot was set up when the symbol was first dropped onto the page, but the user must be able to change them later.

**Behavior:**
1. User double-clicks the symbol on the canvas.
2. The symbol's editable text fields become **inline `QLineEdit` overlays** positioned exactly over their on-symbol locations. The placeholder text is the current value.
3. The user **clicks any field** and types a new value. **Tab** moves between fields.
4. As the user types, the symbol's underlying SVG is re-rendered live so the user sees the new value in place.
5. **Enter** or clicking outside the symbol commits all changes to the undo stack as one entry ("Edit symbol parameters").
6. **Esc** cancels and reverts every field to the value it had when edit mode began.

**Optional pop-out form:** if a symbol has many fields or some are not text (e.g. a dropdown for "weld process"), a small floating panel appears below the symbol with proper labelled controls. The user can toggle between inline editing and the panel via a small icon at the corner of the highlight outline.

### 4.3 Geometric Shape (Line, Rect, Circle, Oval, Triangle, Freehand)

Double-click on a shape → enters **node edit mode**, similar to Inkscape's Node Tool.

| Shape | Edit handles |
|-------|--------------|
| Line | Two square handles at the endpoints. Drag a handle to move that endpoint. |
| Rectangle | 8 handles (4 corners + 4 edge midpoints). Corners resize uniformly with Shift held; edges resize one axis only. |
| Circle | One handle on the rim. Drag radially to change the radius. |
| Oval | Two handles (one on horizontal axis, one on vertical) — drag to change rx and ry independently. |
| Triangle | Three vertex handles, one per corner. |
| Freehand | A handle at every captured point. Drag to reshape; right-click a handle to delete it. |

**Esc** or click outside exits node edit mode and returns to plain selection.

### 4.4 Dimension Annotation

Double-click on a dimension → opens an inline editor for:
- The measured value text (in case the user wants to override the auto-computed value with a custom label like "≈ 50.0")
- The dimension's offset distance (drag the dimension line to a new perpendicular distance)

The snap source / snap target points cannot be changed via double-click — to re-anchor a dimension to different snap points, the user deletes it and creates a new one.

## 5. Universal Mouse Bindings (always active)

These work in **any** mode, regardless of tool selection.

| Binding | Action |
|---------|--------|
| **Mouse wheel** scroll | Zoom in / out, centered on cursor position |
| **Middle-button press + drag** | Pan the canvas |
| **Ctrl + scroll** *(future)* | Horizontal scroll |
| **Right-click** *(future)* | Context menu |

## 6. Keyboard Shortcuts (relevant to mouse interaction)

| Key | Action |
|-----|--------|
| **Esc** | Cancel current operation; return to Pointer Mode |
| **Enter** | Commit current edit |
| **Delete / Backspace** | Delete selected annotations |
| **Ctrl/Cmd + A** | Select all annotations on current page |
| **Ctrl/Cmd + Z / Shift+Z** | Undo / Redo |
| **Ctrl/Cmd + C / X / V** | Copy / Cut / Paste selected annotations |
| **+ / -** | Zoom in / out |
| **Page Up / Down** | Previous / next page |
| **Tab** *(in edit mode)* | Move to next editable field |

## 7. Visual Feedback

The cursor and on-screen indicators always tell the user what mode they are in.

| State | Cursor | Visual indicator |
|-------|--------|------------------|
| Pointer Mode, hovering empty area | Arrow | None |
| Pointer Mode, hovering annotation | Arrow with subtle "selectable" highlight on the annotation under cursor | Faint outline |
| Pointer Mode, dragging annotation | Closed hand | Selected items move with cursor |
| Pointer Mode, rubber-banding | Arrow | Dashed selection rectangle |
| Tool Mode, awaiting first click | Crosshair | Tool name in status bar |
| Tool Mode, mid-placement (line, dim) | Crosshair | Live preview line/shape attached to cursor |
| Edit Mode, on text | I-beam | Blinking caret in text |
| Edit Mode, on symbol | Arrow | Symbol parameters become editable boxes |
| Edit Mode, on shape (node) | Arrow over handle = open hand; over body = move | Square handles drawn at each control point |
| Snap point in range (during dim placement) | Crosshair + small circle indicator | Green snap circle on the snap point |
| Middle-button pan in progress | Closed hand | None |

The status bar at the bottom always shows:
- Current tool name (`Pointer`, `Line`, `Linear Dimension`, `Edit: Symbol`, etc.)
- A short hint about the next action (`Click to place start point`, `Drag handle to resize`, `Press Enter to commit`)
- Current zoom percentage and page number

## 8. Inkscape Patterns We Adopt

| Inkscape behavior | Our equivalent |
|--------------------|----------------|
| Selector tool (S) is always one keystroke away | **Esc** at any time returns to Pointer Mode |
| Tools auto-revert to selector after one placement *(in some Inkscape modes)* | We always auto-revert |
| Double-click on text → edit inline | Same |
| Double-click on shape → switch to node tool to edit nodes | Same — we enter node edit mode without explicitly switching tools |
| Drag handles to resize, drag body to move, drag empty space to rubber-band | Same |
| Snap indicators (green circles, magenta lines) on snap points | Green circles on snap points during dimension placement |
| Status bar tells you what to do next | Same |
| Shift+click to add to selection | Same |

## 9. Patterns We Deliberately Differ From Inkscape

| Inkscape | Ours | Reason |
|----------|------|--------|
| Click on empty area selects nothing only on the *second* click | Single click on empty area always deselects | Simpler, more predictable for non-Inkscape users |
| Click selected → enters rotate mode | We do not support free rotation (engineering drawings rarely need it) | Simplicity |
| Many tools accessed via single-letter shortcuts | We expose tools only via the ribbon | Avoid overloading shortcuts; keep them for common verbs |
| Group/ungroup nesting | We do not group annotations | Annotations are flat per page |

## 10. Implementation Notes (for developers)

This section briefly maps the spec to the existing codebase to make implementation traceable.

| UI behavior | Existing code touchpoint |
|--------------|-------------------------|
| Pointer Mode | `pdfredline.tools.select_tool.SelectTool` |
| Auto-revert to Pointer Mode after a tool finishes | `MainWindow._set_select_tool` — call this from each tool's "I just committed" code path |
| Double-click on text → inline edit | Already implemented in `pdfredline.annotations.text.TextAnnotation.mouseDoubleClickEvent` |
| Double-click on symbol → parameter editor | New: `SymbolAnnotation.mouseDoubleClickEvent` should open inline edit overlays or a small floating form |
| Double-click on shape → node edit mode | New: a `NodeEditTool` activated automatically by `ShapeAnnotation.mouseDoubleClickEvent` |
| Selection handles | New: drawn by `SelectTool` for the currently selected items, hit-tested in its `mouse_press` |
| Snap indicators | Already implemented in `pdfredline.annotations.snap.SnapEngine` and `tools/dimension_tool.py` |
| Status bar mode + hint label | `MainWindow._setup_status_bar` already creates labels; add a `mode_label` and `hint_label` and update them from the tool manager |

The auto-revert behavior is the single biggest behavioral change from the current code: today, after drawing one line the user is still in line-tool mode and clicks again to draw a second line. Going forward, after drawing one line the app should call `_set_select_tool()` automatically, so the next click selects something instead of starting a new line. This matches Inkscape and matches the user's stated expectation that "you can actually click on the pointer for the mouse to be a pointer where the mouse can select any object."
