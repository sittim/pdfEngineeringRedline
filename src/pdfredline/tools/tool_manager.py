from qtpy.QtCore import QObject, Signal

from pdfredline.tools.base import Tool


class ToolManager(QObject):
    """Manages the currently active tool and forwards events."""

    tool_changed = Signal(str)  # emits tool class name

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_tool: Tool | None = None

    @property
    def active_tool(self) -> Tool | None:
        return self._active_tool

    def set_tool(self, tool: Tool):
        if self._active_tool is not None:
            self._active_tool.deactivate()
        self._active_tool = tool
        self._active_tool.activate()
        self.tool_changed.emit(type(tool).__name__)

    def mouse_press(self, event):
        if self._active_tool:
            self._active_tool.mouse_press(event)

    def mouse_move(self, event):
        if self._active_tool:
            self._active_tool.mouse_move(event)

    def mouse_release(self, event):
        if self._active_tool:
            self._active_tool.mouse_release(event)

    def key_press(self, event):
        if self._active_tool:
            self._active_tool.key_press(event)
