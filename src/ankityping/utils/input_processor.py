"""Input processing utilities for ankityping plugin."""

from __future__ import annotations

import re
from typing import Optional, Dict, List, Tuple, Set
from dataclasses import dataclass


@dataclass
class InputProcessingConfig:
    """Configuration for input processing."""
    # Punctuation handling
    handle_punctuation: bool = True
    auto_punctuation: bool = True  # Auto-add punctuation when needed
    ignore_punctuation_errors: bool = False  # Don't count punctuation as errors

    # Whitespace handling
    handle_whitespace: bool = True
    ignore_extra_spaces: bool = True
    auto_correct_spaces: bool = True  # Auto-correct spacing after punctuation

    # Case sensitivity
    case_sensitive: bool = True
    auto_correct_case: bool = False

    # Special characters
    handle_diacritics: bool = True
    ignore_diacritic_errors: bool = False

    # Language-specific settings
    language: str = "en"  # Can be "en", "zh", "ja", etc.


class InputProcessor:
    """Processes user input during typing practice."""

    def __init__(self, config: Optional[InputProcessingConfig] = None):
        self.config = config or InputProcessingConfig()

        # Define punctuation that should be auto-added
        self.auto_punctuation_marks = {'.', ',', '!', '?', ';', ':', ')', ']', '}', '"', "'"}

        # Define punctuation that should have spaces after them
        self.space_after_punctuation = {'.', '!', '?', ';', ':', ',', ')', ']', '}'}

        # Common punctuation pairs
        self.punctuation_pairs = {
            '"': '"',
            "'": "'",
            '(': ')',
            '[': ']',
            '{': '}',
            '<': '>'
        }

    def process_input(self, user_input: str, expected_text: str, current_position: int) -> Tuple[str, bool, str]:
        """
        Process user input and return corrected input, whether to accept, and status message.

        Args:
            user_input: The raw input from user
            expected_text: The expected text at current position
            current_position: Current position in the text

        Returns:
            Tuple of (processed_input, should_accept, status_message)
        """
        if not user_input:
            return user_input, True, ""

        print(f"DEBUG: Processing input: '{user_input}' expected: '{expected_text}' at pos {current_position}")

        # Handle auto-punctuation
        if self.config.auto_punctuation and self.config.handle_punctuation:
            processed_input, auto_added = self._handle_auto_punctuation(user_input, expected_text, current_position)
            if auto_added:
                return processed_input, True, f"Auto-added punctuation: {auto_added}"

        # Handle punctuation tolerance
        if self.config.handle_punctuation and self.config.ignore_punctuation_errors:
            processed_input, is_valid, message = self._handle_punctuation_tolerance(user_input, expected_text)
            if is_valid:
                return processed_input, True, message or "Punctuation tolerance applied"

        # Handle whitespace
        if self.config.handle_whitespace:
            processed_input, whitespace_result = self._handle_whitespace(user_input, expected_text)
            if whitespace_result:
                return processed_input, True, whitespace_result

        # Handle case sensitivity
        if not self.config.case_sensitive:
            processed_input = user_input.lower()
            expected_lower = expected_text.lower()
            if processed_input == expected_lower:
                return processed_input, True, "Case-insensitive match"

        # Default: accept as-is
        return user_input, True, ""

    def _handle_auto_punctuation(self, user_input: str, expected_text: str, current_position: int) -> Tuple[str, Optional[str]]:
        """Handle automatic punctuation addition."""
        if not expected_text:
            return user_input, None

        # Check if the expected text starts with punctuation and user didn't type it
        if expected_text and expected_text[0] in self.auto_punctuation_marks:
            if not user_input or (user_input and user_input[0] != expected_text[0]):
                # Auto-add the punctuation
                auto_punc = expected_text[0]
                return auto_punc + user_input, auto_punc

        # Check for paired punctuation
        if expected_text and expected_text[0] in self.punctuation_pairs:
            opening_char = expected_text[0]
            closing_char = self.punctuation_pairs[opening_char]

            # If user typed opening, check if closing is expected soon
            if user_input == opening_char:
                # Look ahead to see if closing punctuation is expected
                remaining_text = expected_text[1:]
                if closing_char in remaining_text[:10]:  # Look ahead 10 chars
                    return user_input + closing_char, closing_char

        return user_input, None

    def _handle_punctuation_tolerance(self, user_input: str, expected_text: str) -> Tuple[str, bool, Optional[str]]:
        """Handle punctuation tolerance - accept input that differs only in punctuation."""
        if not user_input or not expected_text:
            return user_input, False, None

        # Remove punctuation from both strings and compare
        user_clean = re.sub(r'[^\w\s]', '', user_input)
        expected_clean = re.sub(r'[^\w\s]', '', expected_text)

        if user_clean == expected_clean and user_clean:
            return user_input, True, "Punctuation differences ignored"

        return user_input, False, None

    def _handle_whitespace(self, user_input: str, expected_text: str) -> Tuple[str, Optional[str]]:
        """Handle whitespace processing."""
        if not expected_text:
            return user_input, None

        # Auto-add space after punctuation if needed
        if self.config.auto_correct_spaces and expected_text.startswith(' '):
            if user_input and user_input[-1] in self.space_after_punctuation:
                # Add space after punctuation automatically
                return user_input + ' ', "Auto-added space after punctuation"

        # Ignore extra spaces
        if self.config.ignore_extra_spaces:
            user_normalized = re.sub(r' +', ' ', user_input.strip())
            expected_normalized = re.sub(r' +', ' ', expected_text.strip())

            if user_normalized == expected_normalized:
                return user_input, "Extra spaces ignored"

        return user_input, None

    def get_character_info(self, char: str) -> Dict[str, bool]:
        """Get information about a character."""
        return {
            'is_punctuation': bool(re.match(r'^[^\w\s]$', char)),
            'is_whitespace': bool(re.match(r'^\s$', char)),
            'is_letter': bool(re.match(r'^[a-zA-Z]$', char)),
            'is_digit': bool(re.match(r'^\d$', char)),
            'is_diacritic': len(char) > 1 and ord(char) > 127,  # Simplified diacritic detection
            'requires_space_after': char in self.space_after_punctuation,
            'is_paired_open': char in self.punctuation_pairs,
            'is_paired_close': char in self.punctuation_pairs.values(),
        }

    def validate_input_sequence(self, user_input: str, expected_sequence: str) -> Tuple[bool, str]:
        """
        Validate an input sequence against expected sequence.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(user_input) > len(expected_sequence):
            return False, "Input is longer than expected"

        for i, (user_char, expected_char) in enumerate(zip(user_input, expected_sequence)):
            # Handle punctuation tolerance
            if self.config.handle_punctuation and self.config.ignore_punctuation_errors:
                user_info = self.get_character_info(user_char)
                expected_info = self.get_character_info(expected_char)

                # If both are punctuation, ignore differences
                if user_info['is_punctuation'] and expected_info['is_punctuation']:
                    continue

                # If one is punctuation and the other is not, skip the punctuation
                if user_info['is_punctuation'] != expected_info['is_punctuation']:
                    # Skip the punctuation character
                    if expected_info['is_punctuation']:
                        expected_sequence = expected_sequence[:i] + expected_sequence[i+1:]
                    else:
                        return False, f"Expected '{expected_char}' but got punctuation '{user_char}'"
                    continue

            # Handle case sensitivity
            if not self.config.case_sensitive:
                if user_char.lower() != expected_char.lower():
                    return False, f"Expected '{expected_char}' but got '{user_char}'"
            else:
                if user_char != expected_char:
                    return False, f"Expected '{expected_char}' but got '{user_char}'"

        return True, ""

    def get_punctuation_statistics(self, text: str) -> Dict[str, int]:
        """Get statistics about punctuation in text."""
        stats = {
            'total_punctuation': 0,
            'periods': 0,
            'commas': 0,
            'exclamations': 0,
            'questions': 0,
            'quotes': 0,
            'parentheses': 0,
            'brackets': 0,
            'braces': 0,
        }

        for char in text:
            char_info = self.get_character_info(char)
            if char_info['is_punctuation']:
                stats['total_punctuation'] += 1

                if char == '.':
                    stats['periods'] += 1
                elif char == ',':
                    stats['commas'] += 1
                elif char == '!':
                    stats['exclamations'] += 1
                elif char == '?':
                    stats['questions'] += 1
                elif char in ['"', "'"]:
                    stats['quotes'] += 1
                elif char in ['(', ')']:
                    stats['parentheses'] += 1
                elif char in ['[', ']']:
                    stats['brackets'] += 1
                elif char in ['{', '}']:
                    stats['braces'] += 1

        return stats


# Convenience function for common usage
def process_typing_input(user_input: str, expected_text: str) -> Tuple[str, bool]:
    """
    Quick function to process typing input with default settings.

    Args:
        user_input: Input from user
        expected_text: Expected text

    Returns:
        Tuple of (processed_input, should_accept)
    """
    config = InputProcessingConfig()
    processor = InputProcessor(config)
    processed, should_accept, message = processor.process_input(user_input, expected_text, 0)
    return processed, should_accept