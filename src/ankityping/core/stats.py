"""Statistics collection for the ankityping plugin."""

from __future__ import annotations

from typing import Optional, Callable
from dataclasses import dataclass
import time


@dataclass
class PracticeSession:
    """Statistics for a single practice session."""
    start_time: float
    end_time: Optional[float] = None
    error_count: int = 0
    hint_count: int = 0
    character_count: int = 0
    word_count: int = 0

    @property
    def duration_seconds(self) -> float:
        """Get session duration in seconds."""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    @property
    def words_per_minute(self) -> float:
        """Calculate words per minute."""
        duration_minutes = self.duration_seconds / 60.0
        if duration_minutes <= 0:
            return 0.0
        return self.word_count / duration_minutes

    @property
    def accuracy(self) -> float:
        """Calculate accuracy percentage (0.0 to 1.0)."""
        if self.character_count == 0:
            return 1.0
        # Simple accuracy: characters typed correctly / total target characters
        correct_chars = self.character_count - self.error_count
        return max(0.0, correct_chars / self.character_count)

    def calculate_score(self) -> int:
        """Calculate overall performance score (0-100)."""
        # Base score from accuracy (50% weight)
        accuracy_score = self.accuracy * 50

        # Speed bonus (30% weight)
        # WPM target: 20 WPM = 100% of speed score
        wpm_target = 20.0
        speed_score = min(30.0, (self.words_per_minute / wpm_target) * 30.0)

        # Penalty for hints (20% weight)
        hint_penalty = min(20.0, self.hint_count * 5.0)

        total_score = accuracy_score + speed_score - hint_penalty
        return max(0, min(100, int(total_score)))


class StatsCollector:
    """Collects and manages typing practice statistics."""

    def __init__(self, update_callback: Optional[Callable] = None):
        self.update_callback = update_callback
        self.session: Optional[PracticeSession] = None
        self._is_running = False

    def start_session(self, target_text: str) -> None:
        """Start a new practice session."""
        self.session = PracticeSession(
            start_time=time.time(),
            character_count=len(target_text),
            word_count=len(target_text.split())
        )
        self._is_running = True
        self._notify_update()

    def end_session(self) -> None:
        """End the current practice session."""
        if self.session and self._is_running:
            self.session.end_time = time.time()
            self._is_running = False
            self._notify_update()

    def increment_error_count(self) -> None:
        """Increment error counter."""
        if self.session:
            self.session.error_count += 1
            self._notify_update()

    def increment_hint_count(self) -> None:
        """Increment hint counter."""
        if self.session:
            self.session.hint_count += 1
            self._notify_update()

    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        if not self.session:
            return 0.0
        return self.session.duration_seconds

    def get_error_count(self) -> int:
        """Get current error count."""
        if not self.session:
            return 0
        return self.session.error_count

    def get_hint_count(self) -> int:
        """Get current hint count."""
        if not self.session:
            return 0
        return self.session.hint_count

    def get_words_per_minute(self) -> float:
        """Get current words per minute."""
        if not self.session:
            return 0.0
        return self.session.words_per_minute

    def get_accuracy(self) -> float:
        """Get current accuracy percentage."""
        if not self.session:
            return 1.0
        return self.session.accuracy

    def is_running(self) -> bool:
        """Check if session is currently running."""
        return self._is_running

    def get_formatted_time(self) -> str:
        """Get formatted elapsed time string."""
        elapsed = self.get_elapsed_time()
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def get_formatted_stats(self) -> str:
        """Get formatted statistics string."""
        if not self.session:
            return "No session in progress"

        parts = []
        if self.session.show_timer is not False:  # Default to showing timer
            parts.append(f"Time: {self.get_formatted_time()}")

        parts.append(f"Errors: {self.get_error_count()}")

        if self.get_hint_count() > 0:
            parts.append(f"Hints: {self.get_hint_count()}")

        parts.append(f"WPM: {self.get_words_per_minute():.1f}")
        parts.append(f"Accuracy: {self.get_accuracy():.1%}")

        return ", ".join(parts)

    def calculate_final_score(self) -> int:
        """Calculate final score for completed session."""
        if not self.session:
            return 0
        return self.session.calculate_score()

    def get_session_summary(self) -> dict:
        """Get complete session summary as dictionary."""
        if not self.session:
            return {}

        return {
            "duration_seconds": self.session.duration_seconds,
            "error_count": self.session.error_count,
            "hint_count": self.session.hint_count,
            "character_count": self.session.character_count,
            "word_count": self.session.word_count,
            "words_per_minute": self.session.words_per_minute,
            "accuracy": self.session.accuracy,
            "score": self.session.calculate_score(),
            "is_complete": self.session.end_time is not None
        }

    def reset(self) -> None:
        """Reset the statistics collector."""
        self.session = None
        self._is_running = False
        self._notify_update()

    def _notify_update(self) -> None:
        """Notify callback about statistics update."""
        if self.update_callback:
            try:
                self.update_callback()
            except Exception as e:
                print(f"Error in stats update callback: {e}")