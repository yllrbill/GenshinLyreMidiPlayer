# ui/mixins/playback_mixin.py
# PlaybackMixin - Playback control methods

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMessageBox

from player import PlayerThread
from i18n import tr

if TYPE_CHECKING:
    from main import MainWindow


class PlaybackMixin:
    """Mixin for playback control methods."""

    def on_start(self: "MainWindow"):
        """Start playback."""
        if not self.events:
            QMessageBox.information(self, tr("no_midi", self.lang), tr("load_midi_first", self.lang))
            return
        if self.thread and self.thread.isRunning():
            return

        cfg = self.collect_cfg()
        self.thread = PlayerThread(self.events, cfg)
        self.thread.log.connect(self.append_log)
        self.thread.finished.connect(self.on_finished)
        self.thread.paused.connect(self._on_thread_paused)

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        # Update floating controller playback state
        if self.floating_controller:
            self.floating_controller.update_playback_state(True)
        self.append_log(tr("starting", self.lang))
        self.thread.start()

    def on_toggle_play_pause(self: "MainWindow"):
        """Toggle between play/pause states (for F5 hotkey).

        Behavior:
        - Not playing -> start playback
        - Playing -> request pause (at bar end)
        - Pause pending -> cancel pause request
        - Paused -> resume playback
        """
        if not self.thread or not self.thread.isRunning():
            # Not playing -> start playback
            self.on_start()
        else:
            # Playing -> toggle pause state
            if self.thread.is_paused():
                # Currently paused -> resume
                self.on_pause()
                if self.floating_controller:
                    self.floating_controller.update_playback_state(True, is_paused=False, is_pending=False)
            elif self.thread.is_pause_pending():
                # Pause pending -> cancel (resume call will cancel)
                self.on_pause()
                if self.floating_controller:
                    self.floating_controller.update_playback_state(True, is_paused=False, is_pending=False)
            else:
                # Playing -> request pause (will happen at bar end)
                self.on_pause()
                if self.floating_controller:
                    self.floating_controller.update_playback_state(True, is_paused=False, is_pending=True)

    def on_stop(self: "MainWindow"):
        """Stop playback."""
        if self.thread and self.thread.isRunning():
            self.thread.stop()
            self.append_log(tr("stopping", self.lang))
            # Reset playback state in floating controller
            if self.floating_controller:
                self.floating_controller.update_playback_state(False)
            # Notify diagnostics window of playback stop
            if self.diagnostics_window:
                self.diagnostics_window.on_playback_stopped()

    def on_pause(self: "MainWindow") -> bool:
        """Toggle pause/resume playback. Returns True if now paused, False if resumed."""
        if not self.thread or not self.thread.isRunning():
            return False

        if self.thread.is_paused():
            self.thread.resume()
            return False
        else:
            self.thread.pause()
            return True

    def on_finished(self: "MainWindow"):
        """Called when playback finishes."""
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        # Reset playback state in floating controller
        if self.floating_controller:
            self.floating_controller.update_playback_state(False)

    def _on_thread_paused(self: "MainWindow"):
        """Called when playback thread actually pauses (at bar end)."""
        if self.floating_controller:
            self.floating_controller.update_playback_state(True, is_paused=True)

    def on_octave_up(self: "MainWindow"):
        """Shortcut handler: increase octave shift."""
        idx = self.cmb_octave.currentIndex()
        if idx < self.cmb_octave.count() - 1:
            self.cmb_octave.setCurrentIndex(idx + 1)
            self.append_log(f"Octave: {self.cmb_octave.currentData():+d}")

    def on_octave_down(self: "MainWindow"):
        """Shortcut handler: decrease octave shift."""
        idx = self.cmb_octave.currentIndex()
        if idx > 0:
            self.cmb_octave.setCurrentIndex(idx - 1)
            self.append_log(f"Octave: {self.cmb_octave.currentData():+d}")

    def on_toggle_midi_duration(self: "MainWindow"):
        """Shortcut handler: toggle smart MIDI duration mode."""
        self.chk_midi_duration.setChecked(not self.chk_midi_duration.isChecked())
        state = "ON" if self.chk_midi_duration.isChecked() else "OFF"
        self.append_log(f"Smart MIDI duration: {state}")

    def on_speed_up(self: "MainWindow"):
        """Shortcut handler: increase playback speed by 0.05."""
        current = self.sp_speed.value()
        new_val = min(current + 0.05, self.sp_speed.maximum())
        self.sp_speed.setValue(new_val)
        self.append_log(f"Speed: {new_val:.2f}x")

    def on_speed_down(self: "MainWindow"):
        """Shortcut handler: decrease playback speed by 0.05."""
        current = self.sp_speed.value()
        new_val = max(current - 0.05, self.sp_speed.minimum())
        self.sp_speed.setValue(new_val)
        self.append_log(f"Speed: {new_val:.2f}x")

    def _on_speed_changed(self: "MainWindow", value: float):
        """Sync floating controller speed display."""
        if self.floating_controller:
            self.floating_controller.sync_speed(value)

    def _on_octave_range_mode_changed(self: "MainWindow", state: int):
        """Sync octave range mode and enable/disable inputs."""
        auto_enabled = state == 2
        self.sp_octave_min.setEnabled(not auto_enabled)
        self.sp_octave_max.setEnabled(not auto_enabled)
        if self.floating_controller:
            self.floating_controller.sync_octave_range_mode(auto_enabled)

    def _on_octave_range_changed(self: "MainWindow", *_args):
        """Sync octave range values to floating controller."""
        if self.floating_controller:
            self.floating_controller.sync_octave_range(
                self.sp_octave_min.value(),
                self.sp_octave_max.value()
            )

    def on_show_floating(self: "MainWindow"):
        """Show or toggle the floating controller window."""
        from ui import FloatingController

        if self.floating_controller is None:
            self.floating_controller = FloatingController(self, self.lang)
            # Position near the main window
            main_pos = self.pos()
            self.floating_controller.move(main_pos.x() + self.width() + 10, main_pos.y())
        if self.floating_controller.isVisible():
            self.floating_controller.hide()
        else:
            self.floating_controller._sync_from_main()
            self.floating_controller.show()
            self.floating_controller.raise_()
            self.floating_controller.activateWindow()

    def on_show_diagnostics(self: "MainWindow"):
        """Show or toggle the diagnostics window."""
        from ui import DiagnosticsWindow

        if self.diagnostics_window is None:
            self.diagnostics_window = DiagnosticsWindow(self, self.lang)
            # Position near the main window
            main_pos = self.pos()
            self.diagnostics_window.move(main_pos.x() + self.width() + 10, main_pos.y() + 100)
        if self.diagnostics_window.isVisible():
            self.diagnostics_window.hide()
        else:
            self.diagnostics_window.show()
            self.diagnostics_window.raise_()
            self.diagnostics_window.activateWindow()
