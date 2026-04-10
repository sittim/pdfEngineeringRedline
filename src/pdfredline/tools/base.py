from collections.abc import Callable

from qtpy.QtCore import QEvent


class Tool:
    """Abstract base class for all interaction tools."""

    def __init__(self, scene, undo_stack):
        self.scene = scene
        self.undo_stack = undo_stack
        # Optional callback fired by creation tools after they commit an
        # annotation. The application uses this to auto-revert to Pointer Mode
        # so the user doesn't have to manually click "Select" between actions.
        self.on_finish: Callable[[], None] | None = None

    def activate(self):
        """Called when this tool becomes the active tool."""

    def deactivate(self):
        """Called when this tool is replaced by another tool."""

    def finish(self):
        """Notify the application that this tool has completed its action."""
        if self.on_finish is not None:
            self.on_finish()

    def mouse_press(self, event: QEvent):
        pass

    def mouse_move(self, event: QEvent):
        pass

    def mouse_release(self, event: QEvent):
        pass

    def key_press(self, event: QEvent):
        pass
