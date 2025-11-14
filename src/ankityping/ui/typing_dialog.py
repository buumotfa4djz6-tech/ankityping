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
from .components.settings_panel import SettingsPanel


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
        self._setup_card_monitor()
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

        # Remove pause functionality as it conflicts with spacebar typing
        # pause_action = QAction("Pause/Resume", self)
        # pause_action.setShortcut(QKeySequence("Space"))
        # pause_action.triggered.connect(self._toggle_pause)
        # practice_menu.addAction(pause_action)

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

    def _setup_card_monitor(self) -> None:
        """Setup monitoring for card changes in the main Anki window."""
        try:
            self._last_card_id = None
            self._card_monitor_timer = QTimer()
            self._card_monitor_timer.timeout.connect(self._check_card_change)
            self._card_monitor_timer.start(1000)  # Check every second
            print("DEBUG: Card change monitor started")
        except Exception as e:
            print(f"DEBUG: Failed to setup card monitor: {e}")

    def _check_card_change(self) -> None:
        """Check if the card has changed in the main Anki window."""
        try:
            if not self.anki_integration.is_reviewer_active():
                return

            current_card_data = self.anki_integration.get_current_card_data()
            if not current_card_data:
                return

            current_card_id = getattr(current_card_data, 'card_id', None)

            # Initialize last card ID if this is the first check
            if self._last_card_id is None:
                self._last_card_id = current_card_id
                return

            # Check if card has changed
            if current_card_id != self._last_card_id:
                print(f"DEBUG: Card changed detected in main window: {self._last_card_id} -> {current_card_id}")
                self._last_card_id = current_card_id

                # Force update the typing interface regardless of practice state
                print("DEBUG: Force updating typing interface with new card")
                self._force_update_card(current_card_data)

        except Exception as e:
            print(f"DEBUG: Error checking card change: {e}")

    def _force_update_card(self, new_card_data) -> None:
        """Force update the typing interface with new card data."""
        try:
            print("DEBUG: Force updating card components")

            # End current practice session if running
            if self.stats_collector.is_running():
                print("DEBUG: Ending current practice session")
                self.stats_collector.end_session()
            self.stats_collector.reset()

            # Update card data
            self.card_data = new_card_data

            # Reinitialize all components with new card data
            print(f"DEBUG: Creating new typing engine for: {self.card_data.target[:50]}...")

            # Create input processing configuration
            from ..utils import InputProcessingConfig
            input_config = InputProcessingConfig(
                handle_punctuation=self.config.input_processing.handle_punctuation,
                auto_punctuation=self.config.input_processing.auto_punctuation,
                ignore_punctuation_errors=self.config.input_processing.ignore_punctuation_errors,
                handle_whitespace=self.config.input_processing.handle_whitespace,
                ignore_extra_spaces=self.config.input_processing.ignore_extra_spaces,
                auto_correct_spaces=self.config.input_processing.auto_correct_spaces,
                case_sensitive=self.config.input_processing.case_sensitive,
                auto_correct_case=self.config.input_processing.auto_correct_case,
                handle_diacritics=self.config.input_processing.handle_diacritics,
                ignore_diacritic_errors=self.config.input_processing.ignore_diacritic_errors,
            )

            self.typing_engine = TypingEngine(
                self.card_data.target,
                self.config.behavior.input_mode,
                input_config
            )
            self.hint_manager = HintManager(self.card_data.target)

            # Update the typing display
            print("DEBUG: Updating typing display")
            self.typing_display.set_typing_engine(self.typing_engine)
            self.typing_display.refresh()

            # Update UI elements
            print("DEBUG: Updating UI elements")
            self.prompt_label.setText(self.card_data.prompt)
            self.prompt_label.repaint()  # Force immediate repaint

            # Update status bar
            self.stats_label.setText("Ready to start typing...")
            self.stats_label.repaint()

            # Update window title
            self.setWindowTitle(f"Typing Practice - {self.card_data.note_type or 'Card'}")

            # Force UI update
            self.update()
            self.repaint()

            print(f"DEBUG: Card update completed - New target: {self.card_data.target[:30]}...")

            # Auto focus if enabled
            if self.config.behavior.auto_focus:
                QTimer.singleShot(100, self._focus_typing_area)

        except Exception as e:
            print(f"ERROR: Failed to force update card: {e}")
            import traceback
            traceback.print_exc()

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
            # Get deck manager for field mappings
            from ..utils import get_deck_manager
            deck_manager = get_deck_manager(self.config)

            # Check if reviewer is active and get card data
            if self.anki_integration.is_reviewer_active():
                # Review mode: get current displayed card
                new_card_data = self.anki_integration.get_current_card_data(deck_manager=deck_manager)
                print("DEBUG: Loaded card from active reviewer")
            else:
                # Non-review mode: get next card from current deck
                new_card_data = self.anki_integration.get_next_card_from_deck(deck_manager=deck_manager)
                if new_card_data:
                    print("DEBUG: Loaded card from deck in non-review mode")
                else:
                    print("DEBUG: No cards available in current deck - closing dialog")
                    self.close()
                    return

            if not new_card_data or not new_card_data.target.strip():
                print("DEBUG: No card data or empty target - session might be complete")
                self.close()
                return

            print(f"DEBUG: Loading card ID: {new_card_data.card_id}")

            # Always update components to ensure UI is fresh
            print(f"DEBUG: Updating components with card data")
            self.card_data = new_card_data

            # Update deck information and card count
            current_deck_info = deck_manager.get_current_deck_info()
            if current_deck_info:
                print(f"DEBUG: Current deck: {current_deck_info.deck_name}")
                # Update deck card count if needed
                deck_manager.update_card_count(current_deck_info.deck_name, 1)

            # Reset stats
            if self.stats_collector.is_running():
                self.stats_collector.end_session()
            self.stats_collector.reset()

            # Create input processing configuration
            from ..utils import InputProcessingConfig
            input_config = InputProcessingConfig(
                handle_punctuation=self.config.input_processing.handle_punctuation,
                auto_punctuation=self.config.input_processing.auto_punctuation,
                ignore_punctuation_errors=self.config.input_processing.ignore_punctuation_errors,
                handle_whitespace=self.config.input_processing.handle_whitespace,
                ignore_extra_spaces=self.config.input_processing.ignore_extra_spaces,
                auto_correct_spaces=self.config.input_processing.auto_correct_spaces,
                case_sensitive=self.config.input_processing.case_sensitive,
                auto_correct_case=self.config.input_processing.auto_correct_case,
                handle_diacritics=self.config.input_processing.handle_diacritics,
                ignore_diacritic_errors=self.config.input_processing.ignore_diacritic_errors,
            )

            # Initialize components with new card data
            self.typing_engine = TypingEngine(
                self.card_data.target,
                self.config.behavior.input_mode,
                input_config
            )
            self.hint_manager = HintManager(self.card_data.target)

            # Set up the typing display
            self.typing_display.set_typing_engine(self.typing_engine)

            # Update UI
            print(f"DEBUG: Updating UI with prompt: {self.card_data.prompt[:30]}...")
            self.prompt_label.setText(self.card_data.prompt)
            self.prompt_label.update()  # Force update
            self.typing_display.refresh()

            # Update status bar
            self.stats_label.setText("Ready to start typing...")
            self.stats_label.update()  # Force update

            # Update window title
            self.setWindowTitle(f"Typing Practice - {self.card_data.note_type or 'Card'}")

            # Play audio if configured
            if self.config.behavior.auto_play_audio and self.card_data.audio:
                self.anki_integration.play_audio(self.card_data.audio)

            # Update monitor's last card ID
            if hasattr(self, '_last_card_id'):
                self._last_card_id = self.card_data.card_id

            # Force complete UI refresh
            self.update()
            print(f"DEBUG: Card load completed - Target: {self.card_data.target[:30]}...")

            # Auto focus if enabled
            if self.config.behavior.auto_focus:
                QTimer.singleShot(100, self._focus_typing_area)

            # Mark practice as active
            self.is_practice_active = True

        except Exception as e:
            print(f"ERROR: Failed to load card: {e}")
            import traceback
            traceback.print_exc()
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
        print("DEBUG: _finish_practice called")

        # Prevent duplicate calls
        if hasattr(self, '_finishing') and self._finishing:
            print("DEBUG: Already finishing, preventing duplicate call")
            return
        self._finishing = True

        if not self.stats_collector.is_running():
            print("DEBUG: Stats collector not running, returning")
            self._finishing = False
            return

        # End statistics collection
        self.stats_collector.end_session()
        print("DEBUG: Stats collection ended")

        # Calculate final stats
        time_seconds = self.stats_collector.get_elapsed_time()
        error_count = self.stats_collector.get_error_count()
        hint_count = self.stats_collector.get_hint_count()
        score = self.stats_collector.calculate_final_score()

        print(f"DEBUG: Stats - Time: {time_seconds}s, Errors: {error_count}, Score: {score}")

        # Create practice stats
        practice_stats = PracticeStats(
            time_seconds=time_seconds,
            error_count=error_count,
            hint_count=hint_count,
            score=score
        )

        # Calculate rating
        rating = self.anki_integration._calculate_rating(practice_stats)
        print(f"DEBUG: Calculated rating: {rating}")

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

        # Submit to Anki or handle based on reviewer state
        print("DEBUG: Starting card completion...")
        try:
            if self.anki_integration.is_reviewer_active():
                # Review mode: submit card to Anki
                print("DEBUG: Submitting card in review mode")
                self.anki_integration.answer_card_and_next(rating)
                print("DEBUG: Card submitted to Anki")

                # Write stats to card
                print("DEBUG: Writing stats to card...")
                self.anki_integration._write_stats_to_card(practice_stats, "TypingStats")
                print("DEBUG: Stats written to card")
            else:
                # Non-review mode: just log the practice
                print("DEBUG: Practice completed in non-review mode - no submission to Anki")
                # Could potentially save practice stats elsewhere if needed

        except Exception as e:
            print(f"ERROR: Could not complete card submission: {e}")
            import traceback
            traceback.print_exc()
            if self.anki_integration.is_reviewer_active():
                QMessageBox.warning(self, "Warning", f"Could not submit card to Anki: {e}")
            else:
                print("WARNING: Error in non-review mode completion - continuing anyway")

        # Emit completion signal
        self.card_completed.emit(rating)
        print("DEBUG: Completion signal emitted")

        # Load next card immediately
        print("DEBUG: Loading next card...")
        self._load_next_card()
        print("DEBUG: _finish_practice completed")
        self._finishing = False

    def _load_next_card(self) -> None:
        """Load the next card after Anki has handled the transition."""
        print("DEBUG: _load_next_card called")
        try:
            # Add longer delay to ensure Anki has fully processed the card transition
            import time
            time.sleep(0.5)

            # Reset stats before loading new card
            print("DEBUG: Resetting stats collector")
            self.stats_collector.reset()

            # Multiple attempts to get the correct card data
            max_attempts = 3
            for attempt in range(max_attempts):
                print(f"DEBUG: Loading new card from Anki (attempt {attempt + 1}/{max_attempts})")

                # Store previous card ID for comparison
                previous_card_id = getattr(self.card_data, 'card_id', None) if hasattr(self, 'card_data') else None

                # Load current card data
                self._load_current_card()

                # Check if we got a different card
                current_card_id = getattr(self.card_data, 'card_id', None) if hasattr(self, 'card_data') else None

                if current_card_id and current_card_id != previous_card_id:
                    print(f"DEBUG: SUCCESS - Got new card ID: {current_card_id} (was: {previous_card_id})")
                    break
                else:
                    print(f"DEBUG: Still same card ID: {current_card_id}, waiting and retrying...")
                    if attempt < max_attempts - 1:
                        time.sleep(0.3)

            print("DEBUG: _load_current_card completed")

            # Check if we have a valid new card
            if hasattr(self, 'card_data') and self.card_data and self.card_data.target.strip():
                print("DEBUG: New card loaded successfully")
                # Practice will be marked as active in _load_current_card
            else:
                print("DEBUG: No valid new card available - session might be complete")

        except Exception as e:
            print(f"ERROR: Failed to load next card: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Warning", f"Could not load next card: {e}")
            # Mark practice as inactive to prevent loops
            self.is_practice_active = False

    def _next_card(self) -> None:
        """Skip to next card with 'Again' rating."""
        try:
            # End current session if running
            if self.stats_collector.is_running():
                self.stats_collector.end_session()

            # Handle card progression differently based on reviewer state
            if self.anki_integration.is_reviewer_active():
                # Review mode: answer current card and let Anki handle progression
                print("DEBUG: Answering card in review mode")
                self.anki_integration.answer_card_and_next(1)

                # Add delay to ensure Anki processes the transition
                import time
                time.sleep(0.3)
            else:
                # Non-review mode: just load next card from deck
                print("DEBUG: Moving to next card in non-review mode")
                # No need to answer card since we're not in review mode

            # Reset stats and load new card
            self.stats_collector.reset()
            self._load_current_card()

        except Exception as e:
            print(f"Failed to skip to next card: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load next card: {e}")

    def _toggle_pause(self) -> None:
        """Toggle pause state - DISABLED to avoid spacebar conflicts."""
        # This method is disabled to prevent conflicts with spacebar typing
        pass

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

    def _open_settings(self) -> None:
        """Open the settings panel."""
        try:
            # Create settings dialog with proper parameters (config, parent)
            settings_dialog = SettingsPanel(self.config, self)

            # Show as modal dialog
            settings_dialog.exec()

            # Reload configuration after settings change
            print("DEBUG: Reloading configuration after settings change")
            self.config = get_config()

            # Update UI elements that depend on configuration
            self._update_ui_after_settings_change()

        except Exception as e:
            print(f"DEBUG: Error opening settings: {e}")
            QMessageBox.critical(self, "Settings Error", f"Failed to open settings: {e}")

    def _update_ui_after_settings_change(self) -> None:
        """Update UI elements after configuration changes."""
        try:
            # Update status bar mode label
            if hasattr(self, 'mode_label'):
                self.mode_label.setText(f"Mode: {self.config.behavior.input_mode.capitalize()}")

            # Update window flags for always on top setting
            current_flags = self.windowFlags()
            if self.config.ui.always_on_top:
                if not (current_flags & Qt.WindowType.WindowStaysOnTopHint):
                    self.setWindowFlags(current_flags | Qt.WindowType.WindowStaysOnTopHint)
                    self.show()  # Required to apply window flag changes
            else:
                if current_flags & Qt.WindowType.WindowStaysOnTopHint:
                    self.setWindowFlags(current_flags & ~Qt.WindowType.WindowStaysOnTopHint)
                    self.show()  # Required to apply window flag changes

            # Update theme
            self._apply_theme()

            # Reload current card if available to apply new field/input processing settings
            if self.card_data:
                print("DEBUG: Reloading current card with new settings")
                self._load_current_card()

        except Exception as e:
            print(f"DEBUG: Error updating UI after settings change: {e}")

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
            print(f"DEBUG: Typing complete detected, calling _finish_practice")
            # Mark practice as inactive to prevent additional key processing
            self.is_practice_active = False
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
        # Stop card monitor
        if hasattr(self, '_card_monitor_timer'):
            self._card_monitor_timer.stop()
            print("DEBUG: Card change monitor stopped")

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