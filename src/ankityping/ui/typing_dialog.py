"""Typing practice dialog for the ankityping plugin."""

from __future__ import annotations

from typing import Optional
import sys

from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QMessageBox, QWidget, QMenuBar, QMenu,
    QApplication, QStatusBar, QSplitter, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPalette, QColor, QAction, QKeySequence
from PyQt6.QtWidgets import QAbstractButton

from ..anki_integration import AnkiIntegration, CardData, PracticeStats
from ..config import get_config, Config
from ..core.typing_engine import TypingEngine, CharacterState
from ..core.stats import StatsCollector
from ..core.hint import HintManager, HintLevel
from .components.typing_display import TypingDisplayWidget


class TypingDialog(QMainWindow):
    """Main typing practice window."""

    # Signal for card completion
    card_completed = pyqtSignal(int)  # rating as parameter

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.config = get_config()
        self.anki_integration = AnkiIntegration(self.config)
        self.typing_engine: Optional[TypingEngine] = None
        self.stats_collector = StatsCollector(self._on_stats_update)
        self.hint_manager: Optional[HintManager] = None
        self.card_data: Optional[CardData] = None
        self.is_practice_active = False

        # Timers
        self._error_flash_timer = QTimer()
        self._error_flash_timer.setSingleShot(True)
        self._error_flash_timer.timeout.connect(self._clear_error_flash)

        self._setup_ui()
        self._setup_menu_bar()
        self._setup_status_bar()
        self._setup_shortcuts()
        self._load_current_card()

    def _setup_ui(self) -> None:
        """Setup the user interface."""
        self.setWindowTitle("Anki Typing Practice")
        self.resize(self.config.ui.window_width, self.config.ui.window_height)

        if self.config.ui.always_on_top:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self._apply_theme()

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Create splitter for better layout management
        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter)

        # Top section - Prompt
        prompt_frame = QFrame()
        prompt_layout = QVBoxLayout()
        prompt_frame.setLayout(prompt_layout)

        self.prompt_label = QLabel("Loading...")
        self.prompt_label.setWordWrap(True)
        self.prompt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        prompt_font = QFont()
        prompt_font.setPointSize(14)
        prompt_font.setItalic(True)
        self.prompt_label.setFont(prompt_font)
        prompt_layout.addWidget(self.prompt_label)

        splitter.addWidget(prompt_frame)

        # Middle section - Typing area
        typing_frame = QFrame()
        typing_layout = QVBoxLayout()
        typing_frame.setLayout(typing_layout)

        # Create scroll area for long sentences
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setMinimumHeight(150)

        # Use the new TypingDisplayWidget
        self.typing_display = TypingDisplayWidget()
        self.typing_display.setMinimumHeight(120)
        scroll_area.setWidget(self.typing_display)
        typing_layout.addWidget(scroll_area)

        # Hint label
        self.hint_label = QLabel("")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setWordWrap(True)
        hint_font = QFont()
        hint_font.setPointSize(12)
        hint_font.setItalic(True)
        self.hint_label.setFont(hint_font)
        typing_layout.addWidget(self.hint_label)

        splitter.addWidget(typing_frame)

        # Bottom section - Controls
        control_frame = QFrame()
        control_layout = QHBoxLayout()
        control_frame.setLayout(control_layout)

        self.hint_button = QPushButton("Show Hint")
        self.hint_button.clicked.connect(self._show_hint)
        control_layout.addWidget(self.hint_button)

        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self._reset_practice)
        control_layout.addWidget(self.reset_button)

        self.give_up_button = QPushButton("Give Up")
        self.give_up_button.clicked.connect(self._give_up)
        control_layout.addWidget(self.give_up_button)

        # Add buttons to main layout
        layout.addWidget(control_frame)

        # Set splitter sizes
        splitter.setSizes([100, 300, 80])  # Prompt, Typing, Controls

        # Enable focus for keyboard input
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _setup_menu_bar(self) -> None:
        """Setup the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        next_card_action = QAction("Next Card", self)
        next_card_action.setShortcut(QKeySequence("Ctrl+N"))
        next_card_action.triggered.connect(self._next_card)
        file_menu.addAction(next_card_action)

        file_menu.addSeparator()

        settings_action = QAction("Settings...", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Practice menu
        practice_menu = menubar.addMenu("Practice")

        pause_action = QAction("Pause/Resume", self)
        pause_action.setShortcut(QKeySequence("Space"))
        pause_action.triggered.connect(self._toggle_pause)
        practice_menu.addAction(pause_action)

        restart_action = QAction("Restart Card", self)
        restart_action.setShortcut(QKeySequence("Ctrl+R"))
        restart_action.triggered.connect(self._reset_practice)
        practice_menu.addAction(restart_action)

        practice_menu.addSeparator()

        # Mode submenu
        mode_menu = practice_menu.addMenu("Input Mode")

        progressive_action = QAction("Progressive Mode", self)
        progressive_action.setCheckable(True)
        progressive_action.triggered.connect(lambda: self._change_input_mode("progressive"))
        mode_menu.addAction(progressive_action)

        accompanying_action = QAction("Accompanying Mode", self)
        accompanying_action.setCheckable(True)
        accompanying_action.triggered.connect(lambda: self._change_input_mode("accompanying"))
        mode_menu.addAction(accompanying_action)

        # Set current mode checked
        if self.config.behavior.input_mode == "progressive":
            progressive_action.setChecked(True)
        else:
            accompanying_action.setChecked(True)

        # Help menu
        help_menu = menubar.addMenu("Help")

        shortcuts_action = QAction("Keyboard Shortcuts", self)
        shortcuts_action.triggered.connect(self._show_shortcuts)
        help_menu.addAction(shortcuts_action)

        help_menu.addSeparator()

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_status_bar(self) -> None:
        """Setup the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.stats_label = QLabel("Ready to start typing...")
        self.status_bar.addWidget(self.stats_label)

        # Add permanent widgets
        self.mode_label = QLabel(f"Mode: {self.config.behavior.input_mode.capitalize()}")
        self.status_bar.addPermanentWidget(self.mode_label)

    def _setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts."""
        # Escape to give up
        self.give_up_button.setShortcut("Esc")

        # Ctrl+H for hint
        self.hint_button.setShortcut("Ctrl+H")

    def _apply_theme(self) -> None:
        """Apply the configured theme."""
        if self.config.ui.theme == "dark":
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QTextEdit, TypingDisplayWidget {
                    background-color: #1e1e1e;
                    color: #ffffff;
                    border: 2px solid #404040;
                    padding: 10px;
                }
                QLabel {
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #404040;
                    color: #ffffff;
                    border: 1px solid #606060;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #505050;
                }
                QPushButton:pressed {
                    background-color: #353535;
                }
                QMenuBar {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QStatusBar {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QFrame {
                    background-color: #2b2b2b;
                }
            """)
        else:  # light theme
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #ffffff;
                    color: #000000;
                }
                QTextEdit, TypingDisplayWidget {
                    background-color: #f8f8f8;
                    color: #000000;
                    border: 2px solid #cccccc;
                    padding: 10px;
                }
                QLabel {
                    color: #000000;
                }
                QPushButton {
                    background-color: #e0e0e0;
                    color: #000000;
                    border: 1px solid #cccccc;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                }
                QPushButton:pressed {
                    background-color: #c0c0c0;
                }
                QMenuBar {
                    background-color: #ffffff;
                    color: #000000;
                }
                QStatusBar {
                    background-color: #f0f0f0;
                    color: #000000;
                }
                QFrame {
                    background-color: #ffffff;
                }
            """)

    def _load_current_card(self) -> None:
        """Load data from the current Anki card."""
        try:
            self.card_data = self.anki_integration.get_current_card_data()
            if not self.card_data:
                QMessageBox.warning(self, "No Card",
                                   "No card is currently displayed. Please open a card in the Anki reviewer first.")
                self.close()
                return

            # Initialize components
            self.typing_engine = TypingEngine(
                self.card_data.target,
                self.config.behavior.input_mode
            )
            self.hint_manager = HintManager(self.card_data.target)

            # Set up the typing display
            self.typing_display.set_typing_engine(self.typing_engine)

            # Update UI
            self.prompt_label.setText(self.card_data.prompt)
            self.typing_display.refresh()

            # Auto focus if enabled
            if self.config.behavior.auto_focus:
                QTimer.singleShot(100, self._focus_typing_area)

            # Play audio if configured
            if self.config.behavior.auto_play_audio and self.card_data.audio:
                self.anki_integration.play_audio(self.card_data.audio)

            # Mark practice as active
            self.is_practice_active = True

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load card: {e}")
            self.close()

    def _focus_typing_area(self) -> None:
        """Set focus to allow keyboard input."""
        self.setFocus()
        self.raise_()
        self.activateWindow()

    def _update_typing_display(self) -> None:
        """Update the typing display with current engine state."""
        if self.typing_display and self.typing_engine:
            self.typing_display.refresh()

    def _on_stats_update(self) -> None:
        """Handle statistics update."""
        if self.stats_collector.is_running():
            time_str = self.stats_collector.get_formatted_time()
            error_count = self.stats_collector.get_error_count()
            hint_count = self.stats_collector.get_hint_count()
            wpm = self.stats_collector.get_words_per_minute()

            stats_text = f"Time: {time_str}, Errors: {error_count}"
            if hint_count > 0:
                stats_text += f", Hints: {hint_count}"
            stats_text += f", WPM: {wpm:.1f}"

            self.stats_label.setText(stats_text)

    def _show_hint(self) -> None:
        """Show hint to user."""
        if not self.typing_engine or not self.hint_manager:
            return

        # Increment hint counter
        self.stats_collector.increment_hint_count()

        # Get next hint level and display hint
        current_pos = self.typing_engine.current_position
        hint_level = self.hint_manager.cycle_hint_level()
        hint = self.hint_manager.get_hint(current_pos, hint_level)

        if hint:
            hint_text = self.hint_manager.format_hint_display(hint)
            self.hint_label.setText(hint_text)
            self.hint_label.setStyleSheet("color: #FF9800;")  # Orange color for hints

            # Clear hint after 3 seconds
            QTimer.singleShot(3000, self._clear_hint)

    def _clear_hint(self) -> None:
        """Clear the hint display."""
        self.hint_label.setText("")
        self.hint_label.setStyleSheet("")

    def _reset_practice(self) -> None:
        """Reset the current practice session."""
        if not self.typing_engine or not self.hint_manager:
            return

        # Reset engine based on configuration
        self.typing_engine.reset(self.config.behavior.reset_mode)
        self.hint_manager.reset()

        # Reset stats
        self.stats_collector.reset()
        self.stats_collector.start_session(self.card_data.target if self.card_data else "")

        # Clear hint
        self._clear_hint()

        # Update display
        self._update_typing_display()

        # Refocus
        if self.config.behavior.auto_focus:
            self._focus_typing_area()

    def _give_up(self) -> None:
        """Give up and move to next card."""
        reply = QMessageBox.question(
            self, "Give Up?",
            "Are you sure you want to give up? This will count as a failed review.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._finish_practice(success=False)

    def _finish_practice(self, success: bool = True) -> None:
        """Finish the practice session and submit to Anki."""
        if not self.stats_collector.is_running():
            return

        # End statistics collection
        self.stats_collector.end_session()

        # Calculate final stats
        time_seconds = self.stats_collector.get_elapsed_time()
        error_count = self.stats_collector.get_error_count()
        hint_count = self.stats_collector.get_hint_count()
        score = self.stats_collector.calculate_final_score()

        # Create practice stats
        practice_stats = PracticeStats(
            time_seconds=time_seconds,
            error_count=error_count,
            hint_count=hint_count,
            score=score
        )

        # Calculate rating
        rating = self.anki_integration._calculate_rating(practice_stats)

        # Show completion message if enabled
        if self.config.behavior.show_completion_popup:
            if success:
                score_text = f"Score: {score}/100"
                stats_text = f"Time: {time_seconds:.1f}s, Errors: {error_count}, Hints: {hint_count}"
                QMessageBox.information(
                    self, "Practice Complete!",
                    f"Excellent work!\n\n{score_text}\n{stats_text}"
                )
            else:
                QMessageBox.information(self, "Practice Given Up",
                                       "Don't worry! Keep practicing and you'll improve.")

        # Submit to Anki with automatic card progression
        try:
            self.anki_integration.answer_card_and_next(rating)
            self.anki_integration._write_stats_to_card(practice_stats, "TypingStats")
        except Exception as e:
            print(f"Warning: Could not submit to Anki: {e}")
            # Don't show error dialog to avoid disrupting flow

        # Emit completion signal
        self.card_completed.emit(rating)

        # Load next card immediately
        self._load_next_card()

    def _load_next_card(self) -> None:
        """Load the next card without additional rating."""
        try:
            # Reset stats and load new card
            self.stats_collector.reset()
            self._load_current_card()

        except Exception as e:
            print(f"Warning: Failed to load next card: {e}")
            # Try to continue with current session
            QMessageBox.warning(self, "Warning", f"Could not load next card: {e}")

    def _next_card(self) -> None:
        """Skip to next card with 'Again' rating."""
        try:
            # Answer current card with 'Again' rating
            self.anki_integration.answer_card_and_next(1)

            # Reset stats and load new card
            self.stats_collector.reset()
            self._load_current_card()

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load next card: {e}")

    def _toggle_pause(self) -> None:
        """Toggle pause state."""
        if self.stats_collector.is_running():
            self.stats_collector.end_session()
            self.stats_label.setText("Paused - Press Space to resume")
        else:
            self.stats_collector.start_session(self.card_data.target if self.card_data else "")
            self._focus_typing_area()

    def _change_input_mode(self, mode: str) -> None:
        """Change the input mode."""
        if self.typing_engine and self.typing_engine.input_mode != mode:
            self.typing_engine.input_mode = mode
            self.typing_engine._reset_state()  # Reset state to apply new mode
            self._update_typing_display()
            self.mode_label.setText(f"Mode: {mode.capitalize()}")

    def _open_settings(self) -> None:
        """Open settings dialog."""
        try:
            from .config_dialog import ConfigDialog
            dialog = ConfigDialog(self)
            if dialog.exec() == QMessageBox.StandardButton.Accepted:
                # Reload config and apply changes
                self.config = get_config()
                self._apply_theme()
                if self.typing_engine:
                    self.typing_engine.input_mode = self.config.behavior.input_mode
                    self._update_typing_display()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open settings: {e}")

    def _show_shortcuts(self) -> None:
        """Show keyboard shortcuts dialog."""
        shortcuts_text = """
        <h3>Keyboard Shortcuts</h3>
        <table>
        <tr><td><b>Typing:</b></td><td>Start typing to begin practice</td></tr>
        <tr><td><b>Backspace:</b></td><td>Delete previous character</td></tr>
        <tr><td><b>Ctrl+H:</b></td><td>Show hint</td></tr>
        <tr><td><b>Ctrl+R:</b></td><td>Reset current practice</td></tr>
        <tr><td><b>Ctrl+N:</b></td><td>Next card</td></tr>
        <tr><td><b>Space:</b></td><td>Pause/Resume</td></tr>
        <tr><td><b>Esc:</b></td><td>Give up</td></tr>
        <tr><td><b>Ctrl+Q:</b></td><td>Exit</td></tr>
        </table>
        """
        QMessageBox.information(self, "Keyboard Shortcuts", shortcuts_text)

    def _show_about(self) -> None:
        """Show about dialog."""
        about_text = """
        <h3>Anki Typing Practice</h3>
        <p>Version 1.0.0</p>
        <p>An immersive typing practice plugin for Anki.</p>
        <p>Features:</p>
        <ul>
        <li>Real-time typing feedback</li>
        <li>Performance statistics</li>
        <li>Multiple input modes</li>
        <li>SRS integration</li>
        </ul>
        """
        QMessageBox.about(self, "About", about_text)

    def _flash_error(self) -> None:
        """Flash red background for error feedback."""
        if self.typing_display:
            self.typing_display.flash_error()

    def _clear_error_flash(self) -> None:
        """Clear error flash background."""
        # TypingDisplayWidget handles its own flash clearing
        pass

    def keyPressEvent(self, event) -> None:
        """Handle key press events."""
        if not self.typing_engine or not self.is_practice_active:
            super().keyPressEvent(event)
            return

        # Start session on first keypress
        if not self.stats_collector.is_running():
            self.stats_collector.start_session(self.card_data.target if self.card_data else "")

        key = event.key()
        text = event.text()

        # Handle backspace
        if key == Qt.Key.Key_Backspace:
            result = self.typing_engine.process_input("\b")
        # Handle other control characters (ignore them)
        elif text and text.isprintable():
            result = self.typing_engine.process_input(text)
        else:
            # Ignore other keys
            super().keyPressEvent(event)
            return

        # Update statistics
        if result.error_occurred:
            self.stats_collector.increment_error_count()
            if self.config.behavior.sound_enabled:
                # Could add error sound here
                pass
            self._flash_error()

        # Update display
        self._update_typing_display()

        # Check if complete
        if result.is_complete:
            self._finish_practice(success=True)
        else:
            super().keyPressEvent(event)

    def showEvent(self, event) -> None:
        """Handle window show event."""
        super().showEvent(event)

        # Auto focus when window is shown
        if self.config.behavior.auto_focus and self.is_practice_active:
            QTimer.singleShot(100, self._focus_typing_area)

    def resizeEvent(self, event) -> None:
        """Handle window resize event."""
        super().resizeEvent(event)

        # Save new window size to config
        self.config.ui.window_width = event.size().width()
        self.config.ui.window_height = event.size().height()

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        if self.stats_collector.is_running():
            reply = QMessageBox.question(
                self, "Close Without Finishing?",
                "Are you sure you want to close without completing the exercise?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()