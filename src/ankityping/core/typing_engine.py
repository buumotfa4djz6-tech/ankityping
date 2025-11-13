"""Core typing engine for the ankityping plugin."""

from __future__ import annotations

from typing import List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class CharacterState(Enum):
    """State of a character in the typing exercise."""
    UNDEFINED = "undefined"  # Not typed yet
    CORRECT = "correct"      # Typed correctly
    CURRENT = "current"      # Current position to type
    ERROR = "error"          # Contains error


@dataclass
class CharacterInfo:
    """Information about a single character."""
    char: str
    state: CharacterState
    position: int


@dataclass
class TypingResult:
    """Result of a typing operation."""
    is_correct: bool
    is_complete: bool
    error_occurred: bool
    typed_text: str
    current_position: int
    characters: List[CharacterInfo]


class TypingEngine:
    """Core engine for managing typing practice."""

    def __init__(self, target_text: str):
        self.target_text = target_text
        self.typed_text = ""
        self.current_position = 0
        self.error_count = 0
        self.is_complete = False
        self._reset_state()

    def _reset_state(self) -> None:
        """Reset the internal state."""
        self.typed_text = ""
        self.current_position = 0
        self.error_count = 0
        self.is_complete = False
        self._characters = self._initialize_characters()

    def _initialize_characters(self) -> List[CharacterInfo]:
        """Initialize character states."""
        characters = []
        for i, char in enumerate(self.target_text):
            state = CharacterState.UNDEFINED
            if i == 0:
                state = CharacterState.CURRENT
            characters.append(CharacterInfo(char=char, state=state, position=i))
        return characters

    def process_input(self, input_char: str) -> TypingResult:
        """Process a single character input."""
        if self.is_complete:
            return self._create_result(is_correct=False, is_complete=True, error_occurred=False)

        # Handle backspace
        if input_char == "\b":
            return self._handle_backspace()

        # Handle other control characters (ignore them)
        if len(input_char) != 1 or ord(input_char) < 32:
            return self._create_result(is_correct=False, is_complete=False, error_occurred=False)

        # Check if current position is valid
        if self.current_position >= len(self.target_text):
            return self._create_result(is_correct=False, is_complete=False, error_occurred=False)

        target_char = self.target_text[self.current_position]
        is_correct = input_char == target_char

        if is_correct:
            return self._handle_correct_input(input_char)
        else:
            return self._handle_incorrect_input(input_char)

    def _handle_correct_input(self, input_char: str) -> TypingResult:
        """Handle correct character input."""
        # Update typed text and position
        self.typed_text += input_char
        self.current_position += 1

        # Update character states
        if self.current_position > 0:
            self._characters[self.current_position - 1].state = CharacterState.CORRECT

        if self.current_position < len(self._characters):
            self._characters[self.current_position].state = CharacterState.CURRENT

        # Check if complete
        self.is_complete = self.current_position >= len(self.target_text)

        return self._create_result(
            is_correct=True,
            is_complete=self.is_complete,
            error_occurred=False
        )

    def _handle_incorrect_input(self, input_char: str) -> TypingResult:
        """Handle incorrect character input."""
        self.error_count += 1

        # Flash error state for current character
        if self.current_position < len(self._characters):
            self._characters[self.current_position].state = CharacterState.ERROR

        # Reset to current state after brief error display
        # (UI layer will handle the visual feedback timing)

        return self._create_result(
            is_correct=False,
            is_complete=False,
            error_occurred=True
        )

    def _handle_backspace(self) -> TypingResult:
        """Handle backspace character."""
        if self.current_position == 0:
            return self._create_result(is_correct=False, is_complete=False, error_occurred=False)

        # Move position back
        self.current_position -= 1

        # Remove last character from typed text
        if self.typed_text:
            self.typed_text = self.typed_text[:-1]

        # Update character states
        if self.current_position < len(self._characters):
            self._characters[self.current_position].state = CharacterState.CURRENT

        if self.current_position + 1 < len(self._characters):
            self._characters[self.current_position + 1].state = CharacterState.UNDEFINED

        return self._create_result(
            is_correct=True,  # Backspace is always "correct" operation
            is_complete=False,
            error_occurred=False
        )

    def _create_result(self, is_correct: bool, is_complete: bool, error_occurred: bool) -> TypingResult:
        """Create a TypingResult object."""
        return TypingResult(
            is_correct=is_correct,
            is_complete=is_complete,
            error_occurred=error_occurred,
            typed_text=self.typed_text,
            current_position=self.current_position,
            characters=self._characters.copy()
        )

    def reset(self, mode: str = "sentence") -> None:
        """Reset the typing exercise."""
        if mode == "sentence":
            self._reset_state()
        elif mode == "word" and self._reset_current_word():
            pass  # Handled in _reset_current_word

    def _reset_current_word(self) -> bool:
        """Reset only the current word."""
        if self.current_position == 0:
            return False

        # Find start of current word
        word_start = self.current_position - 1
        while word_start > 0 and self.target_text[word_start - 1] != " ":
            word_start -= 1

        # Reset typed text and position to word start
        self.typed_text = self.typed_text[:word_start]
        self.current_position = word_start

        # Update character states
        for i in range(word_start, len(self._characters)):
            self._characters[i].state = CharacterState.UNDEFINED

        if self.current_position < len(self._characters):
            self._characters[self.current_position].state = CharacterState.CURRENT

        return True

    def get_formatted_text(self) -> str:
        """Get formatted text with HTML styling for display."""
        html_parts = []

        for char_info in self._characters:
            char = char_info.char
            state = char_info.state

            if char == " ":
                # Preserve spaces
                html_parts.append("&nbsp;")
            elif char == "<":
                html_parts.append("&lt;")
            elif char == ">":
                html_parts.append("&gt;")
            elif char == "&":
                html_parts.append("&amp;")
            else:
                # Apply styling based on state
                if state == CharacterState.CORRECT:
                    html_parts.append(f'<span style="color: #4CAF50; font-weight: bold;">{char}</span>')
                elif state == CharacterState.CURRENT:
                    html_parts.append(f'<span style="background-color: #FFEB3B; text-decoration: underline;">{char}</span>')
                elif state == CharacterState.ERROR:
                    html_parts.append(f'<span style="color: #F44336; font-weight: bold;">{char}</span>')
                else:  # UNDEFINED
                    html_parts.append(f'<span style="color: #999999;">{char}</span>')

        return "".join(html_parts)

    def get_progress_percentage(self) -> float:
        """Get progress as percentage (0.0 to 1.0)."""
        if not self.target_text:
            return 1.0
        return self.current_position / len(self.target_text)

    def get_words_per_minute(self, elapsed_seconds: float) -> float:
        """Calculate words per minute based on elapsed time."""
        if elapsed_seconds <= 0:
            return 0.0

        # Count words in target text (split by whitespace)
        word_count = len(self.target_text.split())
        minutes = elapsed_seconds / 60.0
        return word_count / minutes if minutes > 0 else 0.0

    def get_accuracy(self) -> float:
        """Get typing accuracy as percentage (0.0 to 1.0)."""
        if self.current_position == 0:
            return 1.0

        # Calculate accuracy based on errors vs total attempts
        total_attempts = self.current_position + self.error_count
        if total_attempts == 0:
            return 1.0

        correct_attempts = self.current_position - self.error_count
        return max(0.0, correct_attempts / total_attempts)

    def set_target_text(self, target_text: str) -> None:
        """Set new target text and reset state."""
        self.target_text = target_text
        self._reset_state()