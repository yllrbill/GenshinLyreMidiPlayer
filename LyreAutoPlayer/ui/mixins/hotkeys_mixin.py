# ui/mixins/hotkeys_mixin.py
# HotkeysMixin - Global hotkey registration and cleanup

from typing import TYPE_CHECKING

# Import keyboard library (may not be available)
try:
    import keyboard as kb
    _keyboard_error = None
except Exception as e:
    kb = None
    _keyboard_error = str(e)

if TYPE_CHECKING:
    from main import MainWindow


class HotkeysMixin:
    """Mixin for global hotkey registration and cleanup."""

    def _log_hotkey(self: "MainWindow", key_name: str):
        """Log a hotkey press to the diagnostics window if open (thread-safe via signal)."""
        if self.diagnostics_window is not None:
            # Use signal to safely emit from keyboard thread to Qt main thread
            self.diagnostics_window.sig_log_key.emit(key_name, "press", "hotkey")

    def _register_global_hotkeys(self: "MainWindow"):
        """Register global hotkeys using keyboard library.

        Using F-keys (F5-F12) instead of Ctrl combinations to avoid
        conflicts with games that capture Ctrl keys via DirectInput.

        Requires admin privileges to capture keys in games.
        """
        if kb is None:
            self.append_log(f"[WARN] 全局热键不可用: {_keyboard_error}")
            self.append_log("[INFO] 热键仅在本窗口聚焦时有效")
            return

        try:
            # Use on_press_key, more reliable than add_hotkey
            # F5: Toggle (start/pause/resume), F6: Stop, F7: Speed-, F8: Speed+
            # F9: Octave-, F10: Octave+, F11: Open, F12: Toggle Duration
            def make_hotkey_handler(signal, key_name):
                def handler(e):
                    self._log_hotkey(key_name)
                    signal.emit()
                return handler

            kb.on_press_key('f5', make_hotkey_handler(self.sig_toggle_play_pause, 'F5'), suppress=True)
            kb.on_press_key('f6', make_hotkey_handler(self.sig_stop, 'F6'), suppress=True)
            kb.on_press_key('f7', make_hotkey_handler(self.sig_speed_down, 'F7'), suppress=True)
            kb.on_press_key('f8', make_hotkey_handler(self.sig_speed_up, 'F8'), suppress=True)
            kb.on_press_key('f9', make_hotkey_handler(self.sig_octave_down, 'F9'), suppress=True)
            kb.on_press_key('f10', make_hotkey_handler(self.sig_octave_up, 'F10'), suppress=True)
            kb.on_press_key('f11', make_hotkey_handler(self.sig_open_midi, 'F11'), suppress=True)
            kb.on_press_key('f12', make_hotkey_handler(self.sig_toggle_duration, 'F12'), suppress=True)
            self.append_log("[OK] 全局热键已注册(F5-F12)")
            self.append_log("[INFO] 如热键在游戏中无效，请以管理员身份运行")
        except Exception as e:
            self.append_log(f"[WARN] 热键注册失败: {e}")
            self.append_log("[INFO] 热键仅在本窗口聚焦时有效")

    def _cleanup_hotkeys(self: "MainWindow"):
        """Cleanup global hotkeys on window close."""
        # Cleanup RegisterHotKey manager
        global _hotkey_manager
        try:
            from main import _hotkey_manager as hm
            if hm is not None:
                hm.stop()
        except Exception:
            pass

        # Cleanup keyboard library hooks
        if kb is not None:
            try:
                kb.unhook_all_hotkeys()
            except Exception:
                pass
