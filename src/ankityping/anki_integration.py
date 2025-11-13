"""Anki integration module for ankityping plugin."""

from __future__ import annotations

from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

try:
    from aqt import mw
    from aqt.sound import av_player
    from anki.cards import Card
    from anki.notes import Note
    from anki.collection import Collection
except ImportError:
    # Fallback for testing outside of Anki
    mw = None
    av_player = None
    Card = None
    Note = None
    Collection = None

from .config import Config, FieldMapping


@dataclass
class CardData:
    """Data extracted from an Anki card."""
    card_id: int
    note_id: int
    prompt: str
    target: str
    audio: Optional[str] = None
    note_type: Optional[str] = None


@dataclass
class PracticeStats:
    """Statistics from a typing practice session."""
    time_seconds: float
    error_count: int
    hint_count: int
    score: int


class AnkiIntegration:
    """Handles all interactions with Anki."""

    def __init__(self, config: Config):
        self.config = config
        self._ensure_anki_available()

    def _ensure_anki_available(self) -> None:
        """Ensure Anki is available."""
        if mw is None:
            raise RuntimeError("Anki integration is not available outside of Anki")

    def get_current_card_data(self) -> Optional[CardData]:
        """Extract data from the currently displayed card."""
        if not mw.reviewer.card:
            return None

        card = mw.reviewer.card
        note = card.note()
        field_mapping = self.config.field_mapping

        # Extract field values
        prompt = self._get_field_value(note, field_mapping.prompt)
        target = self._get_field_value(note, field_mapping.target)
        audio = self._get_field_value(note, field_mapping.audio) if field_mapping.audio else None

        # Clean audio field (remove sound tags if present)
        if audio and audio.startswith("[sound:"):
            audio = audio[7:-1]  # Remove [sound: and ]

        return CardData(
            card_id=card.id,
            note_id=note.id,
            prompt=prompt or "",
            target=target or "",
            audio=audio,
            note_type=note.model()["name"]
        )

    def _get_field_value(self, note: Note, field_name: str) -> Optional[str]:
        """Get value from a note field by name."""
        if not field_name:
            return None

        try:
            # Method 1: Try direct attribute access first (newer Anki versions)
            if hasattr(note, field_name):
                value = getattr(note, field_name)
                if value is not None:
                    return str(value)

            # Method 2: Try to get field index from model (traditional method)
            model = note.model()
            flds = model.get("flds", [])

            field_index = None
            for i, field_info in enumerate(flds):
                # Handle different field structure formats
                fname = None

                if isinstance(field_info, dict):
                    # Newer format: {'name': 'Front', 'ord': 0, ...}
                    fname = field_info.get("name") or field_info.get("fldName")
                elif isinstance(field_info, (list, tuple)) and len(field_info) >= 2:
                    # Older format: [fid, fname] or (fid, fname)
                    fname = field_info[1]
                elif isinstance(field_info, str):
                    # Simple string format
                    fname = field_info

                if fname and fname.lower() == field_name.lower():
                    field_index = i
                    break

            if field_index is not None and field_index < len(note.fields):
                return note.fields[field_index]

            # Method 3: Fallback - try to find field by index in note.model()['flds'] with different approach
            if hasattr(note, 'model') and 'flds' in note.model():
                for i, field_info in enumerate(note.model()['flds']):
                    if isinstance(field_info, dict):
                        field_name_from_model = field_info.get('name', field_info.get('fldName', ''))
                        if field_name_from_model.lower() == field_name.lower():
                            if i < len(note.fields):
                                return note.fields[i]

        except Exception as e:
            print(f"Error getting field value for '{field_name}': {e}")

        return None

    def play_audio(self, audio_path: Optional[str]) -> None:
        """Play audio file if available and enabled."""
        if not audio_path or not self.config.behavior.auto_play_audio:
            return

        try:
            if av_player:
                av_player.play_file(audio_path)
        except Exception as e:
            print(f"Failed to play audio {audio_path}: {e}")

    def submit_answer(self, rating: int) -> None:
        """Submit answer to Anki and move to next card."""
        if not mw.reviewer.card:
            return

        try:
            # Submit answer with rating
            mw.reviewer._answerCard(rating)
            # Move to next card
            mw.reviewer.nextCard()
        except Exception as e:
            print(f"Failed to submit answer: {e}")

    def submit_answer_with_stats(self, stats: PracticeStats,
                                stats_field: str = "TypingStats") -> None:
        """Submit answer and write stats to card field."""
        if not mw.reviewer.card:
            return

        # Calculate rating based on performance
        rating = self._calculate_rating(stats)

        # Write stats to card if configured
        self._write_stats_to_card(stats, stats_field)

        # Submit answer
        self.submit_answer(rating)

    def _calculate_rating(self, stats: PracticeStats) -> int:
        """Calculate Anki rating based on practice statistics."""
        # Rating mapping: 1=Again, 2=Hard, 3=Good, 4=Easy
        # Higher scores and fewer errors get better ratings

        if stats.error_count == 0 and stats.hint_count == 0:
            # Perfect performance
            if stats.score >= 90:
                return 4  # Easy
            elif stats.score >= 80:
                return 3  # Good
            else:
                return 2  # Hard
        elif stats.error_count <= 2 and stats.hint_count <= 1:
            # Good performance with minor issues
            return 3  # Good
        elif stats.error_count <= 5:
            # Acceptable performance
            return 2  # Hard
        else:
            # Poor performance
            return 1  # Again

    def _write_stats_to_card(self, stats: PracticeStats, stats_field: str) -> None:
        """Write practice statistics to a card field."""
        if not mw.reviewer.card:
            return

        try:
            card = mw.reviewer.card
            note = card.note()

            # Use the same robust field finding logic as _get_field_value
            field_index = self._find_field_index(note, stats_field)
            if field_index is None:
                return  # Field doesn't exist

            # Format stats as string
            stats_text = (
                f"Time: {stats.time_seconds:.1f}s, "
                f"Errors: {stats.error_count}, "
                f"Hints: {stats.hint_count}, "
                f"Score: {stats.score}"
            )

            # Update field
            if field_index < len(note.fields):
                note.fields[field_index] = stats_text
                note.flush()

        except Exception as e:
            print(f"Failed to write stats to card: {e}")

    def _find_field_index(self, note: Note, field_name: str) -> Optional[int]:
        """Find the index of a field by name using robust methods."""
        if not field_name:
            return None

        try:
            # Method 1: Check if field exists as attribute first
            if hasattr(note, field_name):
                # If attribute exists, try to find corresponding index in fields array
                value = getattr(note, field_name)
                if value is not None:
                    for i, field_value in enumerate(note.fields):
                        if str(field_value) == str(value):
                            return i

            # Method 2: Parse field structure from model
            model = note.model()
            flds = model.get("flds", [])

            for i, field_info in enumerate(flds):
                # Handle different field structure formats
                fname = None

                if isinstance(field_info, dict):
                    # Newer format: {'name': 'Front', 'ord': 0, ...}
                    fname = field_info.get("name") or field_info.get("fldName")
                elif isinstance(field_info, (list, tuple)) and len(field_info) >= 2:
                    # Older format: [fid, fname] or (fid, fname)
                    fname = field_info[1]
                elif isinstance(field_info, str):
                    # Simple string format
                    fname = field_info

                if fname and fname.lower() == field_name.lower():
                    return i

            # Method 3: Fallback - direct comparison in fields array
            # This is a last resort, may not be reliable but can help in some cases
            for i, field_value in enumerate(note.fields):
                if field_value and field_name.lower() in field_value.lower():
                    return i

        except Exception as e:
            print(f"Error finding field index for '{field_name}': {e}")

        return None

    def get_available_fields(self) -> list[str]:
        """Get list of available field names from current note type."""
        if not mw.reviewer.card:
            return []

        try:
            card = mw.reviewer.card
            note = card.note()
            model = note.model()
            flds = model.get("flds", [])

            field_names = []
            for field_info in flds:
                # Handle different field structure formats
                if isinstance(field_info, dict):
                    # Newer format: {'name': 'Front', 'ord': 0, ...}
                    name = field_info.get("name") or field_info.get("fldName")
                elif isinstance(field_info, (list, tuple)) and len(field_info) >= 2:
                    # Older format: [fid, fname] or (fid, fname)
                    name = field_info[1]
                elif isinstance(field_info, str):
                    # Simple string format
                    name = field_info
                else:
                    # Skip unknown format
                    continue

                if name:
                    field_names.append(name)

            return field_names

        except Exception as e:
            print(f"Failed to get available fields: {e}")
            return []

    def get_note_types(self) -> list[str]:
        """Get list of available note types."""
        if not mw.col:
            return []

        try:
            return [model["name"] for model in mw.col.models.all()]
        except Exception as e:
            print(f"Failed to get note types: {e}")
            return []

    def is_reviewer_active(self) -> bool:
        """Check if the reviewer is currently active."""
        return mw and mw.reviewer and mw.reviewer.card is not None

    def get_current_field_content(self, field_name: str) -> Optional[str]:
        """Get content of a specific field from the current card."""
        if not self.is_reviewer_active():
            return None

        try:
            card = mw.reviewer.card
            note = card.note()
            return self._get_field_value(note, field_name)
        except Exception as e:
            print(f"Failed to get field content: {e}")
            return None