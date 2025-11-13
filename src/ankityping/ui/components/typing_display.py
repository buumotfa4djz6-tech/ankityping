"""Beautiful typing display component for the ankityping plugin."""

from __future__ import annotations

from typing import List, Optional
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QPalette, QColor, QPainter, QTextOption

from ...core.typing_engine import TypingEngine, CharacterState, CharacterInfo


class TypingDisplayWidget(QWidget):
    """A beautiful, responsive typing display component."""

    # Signals
    animation_completed = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.typing_engine: Optional[TypingEngine] = None
        self.char_spacing = 2  # 像素
        self.word_spacing = 12  # 像素
        self.line_height = 1.8  # 行高倍数
        self.animation_duration = 150  # 动画持续时间（毫秒）

        self._setup_ui()
        self._setup_animations()

    def _setup_ui(self) -> None:
        """Setup the user interface."""
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)
        self.setLayout(layout)

        # Add stretch to center content
        layout.addStretch()

        # Word container for centered content
        self.word_container = QWidget()
        self.word_layout = QHBoxLayout()
        self.word_layout.setSpacing(0)
        self.word_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.word_container.setLayout(self.word_layout)
        layout.addWidget(self.word_container)

        # Add stretch to center content
        layout.addStretch()

        # Set default font
        self._update_font()

    def _setup_animations(self) -> None:
        """Setup animation properties."""
        self._error_animation = QPropertyAnimation(self, b"")
        self._error_animation.setDuration(200)
        self._error_animation.setEasingCurve(QEasingCurve.Type.InQuad)

        self._success_animation = QPropertyAnimation(self, b"")
        self._success_animation.setDuration(100)
        self._success_animation.setEasingCurve(QEasingCurve.Type.OutQuad)

    def _update_font(self) -> None:
        """Update font settings for better readability."""
        font = QFont()
        font.setFamily("SF Pro Display, Segoe UI, Roboto, Arial, sans-serif")
        font.setPointSize(16)
        font.setWeight(QFont.Weight.Medium)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, self.char_spacing)
        font.setWordSpacing(self.word_spacing)

        # Apply to all child labels
        for child in self.findChildren(QLabel):
            child.setFont(font)

    def set_typing_engine(self, engine: Optional[TypingEngine]) -> None:
        """Set the typing engine and update display."""
        self.typing_engine = engine
        self._update_display()

    def set_spacing(self, char_spacing: int = 2, word_spacing: int = 12) -> None:
        """Set character and word spacing."""
        self.char_spacing = char_spacing
        self.word_spacing = word_spacing
        self._update_font()

    def set_font_size(self, size: int) -> None:
        """Set font size."""
        font = self.font()
        font.setPointSize(size)

        for child in self.findChildren(QLabel):
            child.setFont(font)

    def _update_display(self) -> None:
        """Update the display based on current typing engine state."""
        if not self.typing_engine:
            return

        # Clear existing widgets
        for i in reversed(range(self.word_layout.count())):
            child = self.word_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        # Get character information
        characters = self.typing_engine._characters
        if not characters:
            return

        # Group characters into words
        words = self._group_into_words(characters)

        # Create word widgets
        for word_chars in words:
            word_widget = self._create_word_widget(word_chars)
            self.word_layout.addWidget(word_widget)

    def _group_into_words(self, characters: List[CharacterInfo]) -> List[List[CharacterInfo]]:
        """Group characters into words based on spaces."""
        words = []
        current_word = []

        for char_info in characters:
            if char_info.char == " ":
                if current_word:
                    words.append(current_word)
                    current_word = []
                # Add space as separator
                words.append([char_info])
            else:
                current_word.append(char_info)

        if current_word:
            words.append(current_word)

        return words

    def _create_word_widget(self, characters: List[CharacterInfo]) -> QWidget:
        """Create a widget for a word or space."""
        word_widget = QWidget()
        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Check if this is just a space
        if len(characters) == 1 and characters[0].char == " ":
            space_label = QLabel(" ")
            space_label.setFont(self._get_font())
            layout.addWidget(space_label)
        else:
            # Create character labels for the word
            for char_info in characters:
                char_label = self._create_character_label(char_info)
                layout.addWidget(char_label)

        word_widget.setLayout(layout)
        return word_widget

    def _create_character_label(self, char_info: CharacterInfo) -> QLabel:
        """Create a label for a single character."""
        char_label = QLabel(char_info.char)
        char_label.setFont(self._get_font())

        # Set styling based on character state and input mode
        style = self._get_character_style(char_info)
        char_label.setStyleSheet(style)

        # Set alignment and properties
        char_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        char_label.setMinimumSize(1, 1)  # Allow proper sizing

        return char_label

    def _get_font(self) -> QFont:
        """Get the configured font."""
        font = QFont()
        font.setFamily("SF Pro Display, Segoe UI, Roboto, Arial, sans-serif")
        font.setPointSize(16)
        font.setWeight(QFont.Weight.Medium)
        return font

    def _get_character_style(self, char_info: CharacterInfo) -> str:
        """Get CSS style for a character based on its state."""
        char = char_info.char
        state = char_info.state

        # Base styles
        if self.typing_engine and self.typing_engine.input_mode == "progressive":
            if state == CharacterState.CORRECT:
                return """
                    QLabel {
                        color: #4CAF50;
                        font-weight: bold;
                        background: rgba(76, 175, 80, 0.1);
                        border-radius: 3px;
                        padding: 2px 4px;
                    }
                """
            elif state == CharacterState.CURRENT:
                return """
                    QLabel {
                        color: #FF9800;
                        font-weight: bold;
                        text-decoration: underline;
                        background: rgba(255, 152, 0, 0.2);
                        border-radius: 3px;
                        padding: 2px 4px;
                    }
                """
            elif state == CharacterState.ERROR:
                return """
                    QLabel {
                        color: #F44336;
                        font-weight: bold;
                        background: rgba(244, 67, 54, 0.2);
                        border-radius: 3px;
                        padding: 2px 4px;
                    }
                """
            else:  # UNDEFINED
                return """
                    QLabel {
                        color: #999999;
                        font-weight: normal;
                    }
                """
        else:  # accompanying mode
            if state == CharacterState.CORRECT:
                return """
                    QLabel {
                        color: #4CAF50;
                        font-weight: bold;
                    }
                """
            elif state == CharacterState.CURRENT:
                return """
                    QLabel {
                        color: #212121;
                        background-color: #FFEB3B;
                        font-weight: bold;
                        border-radius: 3px;
                        padding: 2px 4px;
                    }
                """
            elif state == CharacterState.ERROR:
                return """
                    QLabel {
                        color: #F44336;
                        font-weight: bold;
                        background: rgba(244, 67, 54, 0.2);
                        border-radius: 3px;
                        padding: 2px 4px;
                    }
                """
            else:  # UNDEFINED
                return """
                    QLabel {
                        color: #999999;
                        font-weight: normal;
                    }
                """

        return ""

    def refresh(self) -> None:
        """Refresh the display."""
        self._update_display()

    def flash_error(self) -> None:
        """Flash error feedback."""
        if not self.isVisible():
            return

        original_style = self.styleSheet()
        self.setStyleSheet("background-color: rgba(244, 67, 54, 0.1);")

        # Use QTimer to reset after delay
        QTimer.singleShot(200, lambda: self.setStyleSheet(original_style))

    def flash_success(self) -> None:
        """Flash success feedback for completed word/sentence."""
        if not self.isVisible():
            return

        original_style = self.styleSheet()
        self.setStyleSheet("background-color: rgba(76, 175, 80, 0.1);")

        # Use QTimer to reset after delay
        QTimer.singleShot(300, lambda: self.setStyleSheet(original_style))

    def highlight_progress(self) -> None:
        """Highlight the current progress."""
        # This can be used for additional visual feedback
        pass

    def resizeEvent(self, event) -> None:
        """Handle resize events to maintain proper spacing."""
        super().resizeEvent(event)
        self._update_display()

    def paintEvent(self, event) -> None:
        """Custom paint event for additional visual enhancements."""
        super().paintEvent(event)

        # Could add custom drawing here if needed
        pass