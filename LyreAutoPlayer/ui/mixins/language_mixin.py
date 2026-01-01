# ui/mixins/language_mixin.py
# LanguageMixin - Language change handling

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainWindow


class LanguageMixin:
    """Mixin for language change handling."""

    def on_language_changed(self: "MainWindow", new_lang: str):
        """Handle language change from UI.

        Note: apply_language() is kept in main.py because it directly
        accesses ~100+ widgets for setText() calls.
        """
        self.lang = new_lang
        self.apply_language()
        self.refresh_windows()
        # Update floating controller language
        if self.floating_controller:
            self.floating_controller.update_language(new_lang)
