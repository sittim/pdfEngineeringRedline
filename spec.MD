# PDF Redline Application Specification

## 1. Purpose

A cross-platform PDF redlining application that allows users to open PDF documents and annotate them with markup including text, geometric primitives, dimensions, and parameterized engineering symbols (welding, GD&T, etc.).

## 2. Technology Requirements

- **Language:** High-level, rapid application development language with strong cross-platform GUI support
- **Target Platforms:** macOS, Linux, Windows — single codebase, cross-compiled
- **Framework:** Must provide native-feeling UI with ribbon-style toolbar, PDF rendering, and 2D drawing canvas
- **Tooling:** Modern build system, dependency management, and packaging for all three OS targets

## 3. User Interface

### 3.1 Layout

- Microsoft Word-style ribbon toolbar across the top
- Central canvas area displaying the loaded PDF document
- Contextual property panels (color, font size, symbol parameters) that appear based on the active tool

### 3.2 Ribbon Tabs and Groups

| Tab        | Groups / Controls                                                        |
|------------|--------------------------------------------------------------------------|
| File       | Open, Save, Export, Print                                                |
| View       | Zoom In (+), Zoom Out (-), Fit Page, Fit Width, Page Navigation         |
| Draw       | Line, Circle, Oval, Rectangle, Triangle, Freehand Line                  |
| Text       | Add Text, Font Family, Font Size, Text Color                            |
| Dimensions | Linear Dimension, Aligned Dimension, Radial Dimension, Angular Dimension|
| Symbols    | Symbol Library Browser (welding, GD&T, custom)                          |

## 4. PDF Viewing and Navigation

### 4.1 Zoom

- **Mouse wheel** scrolls to zoom in/out centered on the cursor position
- **Plus (+) button** in the ribbon and keyboard shortcut zoom in
- **Minus (-) button** in the ribbon and keyboard shortcut zoom out
- Zoom level indicator displayed in the status bar

### 4.2 Pan

- **Middle mouse button press + drag** pans the PDF document across the canvas
- Scrollbars available as a secondary pan mechanism

### 4.3 Page Navigation

- Page up / page down controls for multi-page PDFs
- Page number indicator and direct page entry

## 5. Annotation Tools

### 5.1 Text Annotations

- User clicks a location on the PDF to place a text box
- Properties before or during placement:
  - **Font family** — selectable from system fonts
  - **Font size** — numeric entry or preset list
  - **Color** — color picker (preset palette + custom RGB/Hex)
- Text is editable after placement by double-clicking

### 5.2 Geometric Primitives

All primitives share these properties:
- **Stroke color** — color picker
- **Stroke width** — numeric entry
- **Fill color** — optional, color picker (none by default)

| Primitive  | Drawing Interaction                                                         |
|------------|-----------------------------------------------------------------------------|
| Line       | Click start point, click end point                                          |
| Rectangle  | Click one corner, drag to opposite corner                                   |
| Circle     | Click center, drag to set radius                                            |
| Oval       | Click center, drag to set horizontal and vertical radii                     |
| Triangle   | Click three vertices sequentially                                           |
| Freehand   | Press and drag to draw a free-form polyline                                 |

### 5.3 Dimensions

Dimension annotations display measured distances or angles between snap points on existing geometry.

#### Snap Points

Dimensions snap to the following geometric features:

| Geometry   | Snap Points                                      |
|------------|--------------------------------------------------|
| Line       | Endpoints, midpoint                              |
| Circle     | Center, quadrant points (0, 90, 180, 270)        |
| Oval       | Center, quadrant points                          |
| Rectangle  | Corners, edge midpoints, center                  |
| Triangle   | Vertices, edge midpoints                         |

#### Dimension Types

- **Linear** — horizontal or vertical distance between two snap points
- **Aligned** — distance along the line connecting two snap points
- **Radial** — radius or diameter of a circle or oval
- **Angular** — angle between two lines sharing a common snap point

#### Dimension Display

- Dimension value rendered as text along or beside the dimension line
- Leader lines and arrows at measurement endpoints
- Units and precision configurable (mm, inches, decimal places)

### 5.4 Symbol Blocks

Predefined engineering symbol blocks that the user places onto the PDF.

#### Symbol Architecture

- Each symbol is a **self-contained definition** with:
  - A graphical representation (vector drawing)
  - One or more **parameterized text fields** that the user can edit
- Symbols are loaded from a **symbol library directory** at startup
- Adding a new symbol requires only adding a new definition file to the library directory — no application code changes

#### Built-in Symbol Categories

| Category | Example Symbols                                                    |
|----------|--------------------------------------------------------------------|
| Welding  | Fillet weld, groove weld, plug weld — parameters: size, length, pitch, process |
| GD&T     | Feature control frame — parameters: characteristic, tolerance, datum references |
| Surface  | Surface finish — parameters: roughness value, method, direction    |

#### Symbol Placement Workflow

1. User opens the symbol library browser from the Symbols ribbon tab
2. User selects a symbol from the categorized library
3. A property panel displays the symbol's editable text parameters
4. User fills in or adjusts the parameter values
5. User clicks the desired location on the PDF to place the symbol
6. Placed symbols can be selected, moved, and have parameters re-edited

## 6. Annotation Management

- All annotations are objects that can be **selected, moved, resized, and deleted** after placement
- Multi-select via Shift+click or drag selection box
- Undo / Redo stack for all annotation operations
- Annotations are stored as a separate layer — the original PDF is not modified
- Export merges annotations into a new PDF file (flattened or as PDF annotation objects)

## 7. File Operations

| Operation | Behavior                                                                        |
|-----------|---------------------------------------------------------------------------------|
| Open      | Load a PDF file and display the first page                                      |
| Save      | Save the current annotation state to a project file (PDF path + annotation data)|
| Export    | Produce a new PDF with annotations baked in                                     |
| Print     | Print the PDF with annotations rendered                                         |

## 8. Cross-Platform Build

- Single codebase compiles to native executables for:
  - **macOS** — .app bundle or .dmg
  - **Linux** — AppImage, .deb, or .rpm
  - **Windows** — .exe installer or portable .exe
- CI/CD pipeline builds all three targets from one repository
- Platform-specific behavior (file dialogs, fonts, DPI scaling) handled by the framework

## 9. Extensibility

### 9.1 Symbol Library Extension

- Symbol definitions stored as individual files in a known directory
- File format is declarative (defines geometry + parameter schema)
- Users or third parties add symbols by dropping new files into the directory
- Application scans the directory on startup and populates the library browser

### 9.2 Future Extension Points

- Additional annotation tool types
- Custom dimension styles
- Plugin API for third-party tool integration
