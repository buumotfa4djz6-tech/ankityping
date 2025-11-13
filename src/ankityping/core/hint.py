"""Hint management for the ankityping plugin."""

from __future__ import annotations

from typing import List, Optional
from dataclasses import dataclass
from enum import Enum


class HintLevel(Enum):
    """Levels of hints available."""
    NONE = "none"
    CURRENT_CHARACTER = "character"
    CURRENT_WORD = "word"
    FULL_SENTENCE = "sentence"


@dataclass
class HintInfo:
    """Information about a hint."""
    level: HintLevel
    content: str
    position: int
    word_start: int
    word_end: int


class HintManager:
    """Manages hints for typing practice."""

    def __init__(self, target_text: str):
        self.target_text = target_text
        self.hint_level = HintLevel.NONE
        self._word_boundaries = self._find_word_boundaries()

    def _find_word_boundaries(self) -> List[tuple[int, int]]:
        """Find the start and end indices of each word."""
        boundaries = []
        word_start = 0
        in_word = False

        for i, char in enumerate(self.target_text):
            if char.isspace():
                if in_word:
                    boundaries.append((word_start, i))
                    in_word = False
            else:
                if not in_word:
                    word_start = i
                    in_word = True

        # Handle last word
        if in_word:
            boundaries.append((word_start, len(self.target_text)))

        return boundaries

    def get_current_word_boundary(self, position: int) -> tuple[int, int]:
        """Get the start and end indices of the current word."""
        for start, end in self._word_boundaries:
            if position >= start and position < end:
                return start, end

        # If not in a word (e.g., at a space), find next word
        for start, end in self._word_boundaries:
            if position < start:
                return start, end

        # If no word found, return position
        return position, position

    def get_hint(self, position: int, level: HintLevel = None) -> Optional[HintInfo]:
        """Get hint at specified position and level."""
        if level is None:
            level = self.hint_level

        if level == HintLevel.NONE:
            return None

        if position >= len(self.target_text):
            return None

        word_start, word_end = self.get_current_word_boundary(position)

        if level == HintLevel.CURRENT_CHARACTER:
            return HintInfo(
                level=HintLevel.CURRENT_CHARACTER,
                content=self.target_text[position],
                position=position,
                word_start=word_start,
                word_end=word_end
            )

        elif level == HintLevel.CURRENT_WORD:
            word_text = self.target_text[word_start:word_end]
            current_char_pos = position - word_start
            hint_content = (
                word_text[:current_char_pos] +
                "[" + self.target_text[position] + "]" +
                word_text[current_char_pos + 1:]
            )
            return HintInfo(
                level=HintLevel.CURRENT_WORD,
                content=hint_content,
                position=position,
                word_start=word_start,
                word_end=word_end
            )

        elif level == HintLevel.FULL_SENTENCE:
            # Show full sentence with brackets around current character
            current_char = self.target_text[position]
            hint_content = (
                self.target_text[:position] +
                "[" + current_char + "]" +
                self.target_text[position + 1:]
            )
            return HintInfo(
                level=HintLevel.FULL_SENTENCE,
                content=hint_content,
                position=position,
                word_start=word_start,
                word_end=word_end
            )

        return None

    def get_next_hint_level(self) -> HintLevel:
        """Get the next available hint level."""
        levels = [
            HintLevel.NONE,
            HintLevel.CURRENT_CHARACTER,
            HintLevel.CURRENT_WORD,
            HintLevel.FULL_SENTENCE
        ]

        current_index = levels.index(self.hint_level)
        next_index = min(current_index + 1, len(levels) - 1)
        return levels[next_index]

    def set_hint_level(self, level: HintLevel) -> None:
        """Set the current hint level."""
        self.hint_level = level

    def cycle_hint_level(self) -> HintLevel:
        """Cycle to the next hint level and return it."""
        self.hint_level = self.get_next_hint_level()
        return self.hint_level

    def reset(self) -> None:
        """Reset hint manager."""
        self.hint_level = HintLevel.NONE

    def format_hint_display(self, hint: HintInfo) -> str:
        """Format hint for display."""
        if hint.level == HintLevel.CURRENT_CHARACTER:
            return f"Next character: <b>[{hint.content}]</b>"
        elif hint.level == HintLevel.CURRENT_WORD:
            return f"Current word: <b>{hint.content}</b>"
        elif hint.level == HintLevel.FULL_SENTENCE:
            return f"Full sentence: <b>{hint.content}</b>"
        else:
            return ""

    def get_hint_text_for_position(self, position: int) -> str:
        """Get formatted hint text for current position."""
        hint = self.get_hint(position)
        if hint:
            return self.format_hint_display(hint)
        return ""

    def is_hint_available(self, level: HintLevel) -> bool:
        """Check if hint level is available."""
        return level in HintLevel and self.target_text and len(self.target_text) > 0

    def get_hint_level_description(self, level: HintLevel) -> str:
        """Get human-readable description of hint level."""
        descriptions = {
            HintLevel.NONE: "No hints",
            HintLevel.CURRENT_CHARACTER: "Show current character",
            HintLevel.CURRENT_WORD: "Show current word",
            HintLevel.FULL_SENTENCE: "Show full sentence"
        }
        return descriptions.get(level, "Unknown")

    def calculate_hint_penalty(self, level: HintLevel) -> int:
        """Calculate penalty score for using hint level."""
        penalties = {
            HintLevel.NONE: 0,
            HintLevel.CURRENT_CHARACTER: 2,
            HintLevel.CURRENT_WORD: 5,
            HintLevel.FULL_SENTENCE: 10
        }
        return penalties.get(level, 0)

    def get_hint_recommendation(self, position: int, error_count: int) -> HintLevel:
        """Get recommended hint level based on current state."""
        # If no errors, no hint needed
        if error_count == 0:
            return HintLevel.NONE

        # If many errors, suggest stronger hint
        if error_count >= 3:
            return HintLevel.CURRENT_WORD
        elif error_count >= 1:
            return HintLevel.CURRENT_CHARACTER

        return HintLevel.NONE