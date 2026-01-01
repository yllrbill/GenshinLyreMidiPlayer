# ui/mixins/logs_mixin.py
# LogsMixin - Log output handling

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainWindow


class LogsMixin:
    """Mixin for log output handling."""

    def append_log(self: "MainWindow", s: str):
        """Append message to log widget."""
        self.log.append(s)
