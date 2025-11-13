"""Typing practice dialog for the ankityping plugin."""

from __future__ import annotations

from typing import Optional
import sys

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QMessageBox, QWidget
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor

from ..anki_integration import AnkiIntegration, CardData, PracticeStats
from ..config import get_config, Config
from ..core.typing_engine import TypingEngine, CharacterState
from ..core.stats import StatsCollector
from ..core.hint import HintManager, HintLevel


class TypingDialog(QDialog):
    """Main typing practice dialog."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.config = get_config()
        self.anki_integration = AnkiIntegration(self.config)
        self.typing_engine: Optional[TypingEngine] = None
        self.stats_collector = StatsCollector(self._on_stats_update)
        self.hint_manager: Optional[HintManager] = None
        self.card_data: Optional[CardData] = None

        self._error_flash_timer = QTimer()
        self._error_flash_timer.setSingleShot(True)
        self._error_flash_timer.timeout.connect(self._clear_error_flash)

        self._setup_ui()
        self._setup_shortcuts()
        self._load_current_card()

    def _setup_ui(self) -> None:
        """Setup the user interface."""
        self.setWindowTitle("Anki Typing Practice")
        self.setModal(True)
        self.resize(600, 400)

        if self.config.ui.always_on_top:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self._apply_theme()

        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Prompt label
        self.prompt_label = QLabel("Loading...")
        self.prompt_label.setWordWrap(True)
        self.prompt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        prompt_font = QFont()
        prompt_font.setPointSize(14)
        prompt_font.setItalic(True)
        self.prompt_label.setFont(prompt_font)
        layout.addWidget(self.prompt_label)

        # Typing display
        self.typing_display = QTextEdit()
        self.typing_display.setReadOnly(True)
        self.typing_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        typing_font = QFont()
        typing_font.setPointSize(18)
        typing_font.setFamily("Consolas, monospace")
        self.typing_display.setFont(typing_font)
        layout.addWidget(self.typing_display)

        # Stats label
        self.stats_label = QLabel("Ready to start typing...")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_font = QFont()
        stats_font.setPointSize(10)
        self.stats_label.setFont(stats_font)
        layout.addWidget(self.stats_label)

        # Hint label
        self.hint_label = QLabel("")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setWordWrap(True)
        hint_font = QFont()
        hint_font.setPointSize(12)
        hint_font.setItalic(True)
        self.hint_label.setFont(hint_font)
        layout.addWidget(self.hint_label)

        # Control buttons
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)

        self.hint_button = QPushButton("Show Hint")
        self.hint_button.clicked.connect(self._show_hint)
        button_layout.addWidget(self.hint_button)

        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self._reset_practice)
        button_layout.addWidget(self.reset_button)

        self.give_up_button = QPushButton("Give Up")
        self.give_up_button.clicked.connect(self._give_up)
        button_layout.addWidget(self.give_up_button)

        # Set button order correctly for RTL languages
        if sys.getdefaultencoding().lower().startswith('utf'):
            button_layout.setDirection(QHBoxLayout.Direction.RightToLeft)

    def _apply_theme(self) -> None:
        """Apply the configured theme."""
        if self.config.ui.theme == "dark":
            self.setStyleSheet("""
                QDialog {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QTextEdit {
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
            """)
        else:  # light theme
            self.setStyleSheet("""
                QDialog {
                    background-color: #ffffff;
                    color: #000000;
                }
                QTextEdit {
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
            """)

    def _setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts."""
        # Escape to give up
        self.give_up_button.setShortcut("Esc")

        # Ctrl+R to reset
        self.reset_button.setShortcut("Ctrl+R")

        # Ctrl+H for hint
        self.hint_button.setShortcut("Ctrl+H")

    def _load_current_card(self) -> None:
        """Load data from the current Anki card."""
        try:
            self.card_data = self.anki_integration.get_current_card_data()
            if not self.card_data:
                QMessageBox.warning(self, "No Card",
                                   "No card is currently displayed. Please open a card in the Anki reviewer first.")
                self.reject()
                return

            # Initialize components
            self.typing_engine = TypingEngine(self.card_data.target)
            self.hint_manager = HintManager(self.card_data.target)

            # Update UI
            self.prompt_label.setText(self.card_data.prompt)
            self._update_typing_display()

            # Play audio if configured
            if self.config.behavior.auto_play_audio and self.card_data.audio:
                self.anki_integration.play_audio(self.card_data.audio)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load card: {e}")
            self.reject()

    def _update_typing_display(self) -> None:
        """Update the typing display with current engine state."""
        if not self.typing_engine:
            return

        formatted_text = self.typing_engine.get_formatted_text()
        self.typing_display.setHtml(f"<div style='font-size: 18px; line-height: 1.5;'>{formatted_text}</div>")

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

    def _give_up(self) -> None:
        """Give up and close dialog."""
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

        # Show completion message
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

        # Submit to Anki
        try:
            self.anki_integration.submit_answer_with_stats(practice_stats)
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not submit to Anki: {e}")

        self.accept()

    def _flash_error(self) -> None:
        """Flash red background for error feedback."""
        self.typing_display.setStyleSheet("background-color: #ffebee;")  # Light red
        self._error_flash_timer.start(200)  # Flash for 200ms

    def _clear_error_flash(self) -> None:
        """Clear error flash background."""
        self._apply_theme()  # Reapply normal theme

    def keyPressEvent(self, event) -> None:
        """Handle key press events."""
        if not self.typing_engine or not self.stats_collector.is_running():
            return

        # Start session on first keypress
        if not self.stats_collector.is_running():
            self.stats_collector.start_session(self.card_data.target if self.card_data else "")

        key = event.key()
        text = event.text()

        # Handle backspace
        if key == Qt.Key.Key_Backspace:
            result = self.typing_engine.process_input("\b")
        # Handle normal characters
        elif text and text.isprintable():
            result = self.typing_engine.process_input(text)
        else:
            # Ignore other keys
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

    def closeEvent(self, event) -> None:
        """Handle dialog close event."""
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