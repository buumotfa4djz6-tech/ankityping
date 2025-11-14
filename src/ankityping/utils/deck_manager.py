"""Deck management utilities for storing and retrieving deck preferences."""

from __future__ import annotations

import json
import os
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    from aqt import mw
except ImportError:
    mw = None


@dataclass
class DeckFieldMapping:
    """Field mapping configuration for a specific deck."""
    deck_name: str
    deck_id: int
    prompt_field: str
    target_field: str
    audio_field: Optional[str] = None
    last_used: Optional[str] = None  # ISO timestamp
    card_count: int = 0
    field_names: list[str] = None  # Available fields in this deck

    def __post_init__(self):
        if self.field_names is None:
            self.field_names = []


class DeckManager:
    """Manages deck-specific configurations and preferences."""

    def __init__(self):
        self.decks_file = Path(__file__).parent.parent.parent.parent / "data" / "decks.json"
        self.decks_file.parent.mkdir(parents=True, exist_ok=True)
        self._decks_cache: Dict[str, DeckFieldMapping] = {}
        self._config = None  # Main plugin config
        self._load_decks()

    def set_config(self, config) -> None:
        """Set the main plugin config object."""
        self._config = config
        # Load deck settings from main config
        self._load_from_config()

    def _load_from_config(self) -> None:
        """Load deck settings from the main config object."""
        if not self._config:
            return

        try:
            # Load deck settings from main config
            if hasattr(self._config, 'deck_settings') and self._config.deck_settings:
                for deck_name, deck_data in self._config.deck_settings.items():
                    deck_mapping = DeckFieldMapping(
                        deck_name=deck_name,
                        deck_id=deck_data.get('deck_id', 0),
                        prompt_field=deck_data.get('prompt_field', 'Front'),
                        target_field=deck_data.get('target_field', 'Back'),
                        audio_field=deck_data.get('audio_field', 'Audio'),
                        field_names=deck_data.get('field_names', []),
                        card_count=deck_data.get('card_count', 0),
                        last_used=self._parse_last_used(deck_data.get('last_used'))
                    )
                    self._decks_cache[deck_name] = deck_mapping
                print(f"DEBUG: Loaded {len(self._decks_cache)} deck configurations from main config")

        except Exception as e:
            print(f"DEBUG: Error loading deck settings from config: {e}")

    def _save_to_config(self) -> None:
        """Save deck settings to the main config object."""
        if not self._config:
            return

        try:
            # Convert deck cache to config format
            deck_settings = {}
            for deck_name, deck_mapping in self._decks_cache.items():
                deck_settings[deck_name] = {
                    'deck_id': deck_mapping.deck_id,
                    'prompt_field': deck_mapping.prompt_field,
                    'target_field': deck_mapping.target_field,
                    'audio_field': deck_mapping.audio_field,
                    'field_names': deck_mapping.field_names,
                    'card_count': deck_mapping.card_count,
                    'last_used': self._format_last_used(deck_mapping.last_used)
                }

            # Save to config object
            self._config.deck_settings = deck_settings

            # Mark config as dirty so it gets saved
            try:
                from ..config import save_config
                save_config(self._config)
            except ImportError:
                try:
                    from ankityping.config import save_config
                    save_config(self._config)
                except ImportError as e:
                    print(f"DEBUG: Failed to import save_config in deck_manager: {e}")
                    # Continue without saving - better than crashing
                    return

            print(f"DEBUG: Saved {len(deck_settings)} deck configurations to main config")

        except Exception as e:
            print(f"DEBUG: Error saving deck settings to config: {e}")

    def _parse_last_used(self, last_used_str: Optional[str]) -> Optional[datetime]:
        """Parse last used string to datetime."""
        if not last_used_str:
            return None
        try:
            return datetime.fromisoformat(last_used_str)
        except:
            return None

    def _format_last_used(self, last_used_dt: Optional[datetime]) -> Optional[str]:
        """Format datetime to string."""
        if not last_used_dt:
            return None
        return last_used_dt.isoformat()

    def _load_decks(self) -> None:
        """Load deck configurations from file."""
        try:
            if self.decks_file.exists():
                with open(self.decks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for deck_data in data.get('decks', []):
                        deck_mapping = DeckFieldMapping(**deck_data)
                        self._decks_cache[deck_mapping.deck_name] = deck_mapping
                print(f"DEBUG: Loaded {len(self._decks_cache)} deck configurations")
            else:
                print("DEBUG: No decks configuration file found")
        except Exception as e:
            print(f"DEBUG: Error loading decks configuration: {e}")
            self._decks_cache = {}

    def _save_decks(self) -> None:
        """Save deck configurations to file."""
        try:
            data = {
                'decks': [asdict(deck) for deck in self._decks_cache.values()],
                'last_updated': self._get_timestamp()
            }
            with open(self.decks_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("DEBUG: Saved deck configurations")
        except Exception as e:
            print(f"DEBUG: Error saving decks configuration: {e}")

    def _get_timestamp(self) -> str:
        """Get current ISO timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()

    def get_current_deck_info(self) -> Optional[DeckFieldMapping]:
        """Get information about the currently selected deck."""
        if not mw or not mw.col:
            print("DEBUG: No Anki collection available")
            return None

        try:
            # Get current deck
            current_deck_id = mw.col.conf.get('curDeck', None)
            if current_deck_id is None:
                print("DEBUG: No current deck selected")
                return None

            # Get deck name
            deck = mw.col.decks.get(current_deck_id)
            if not deck:
                print(f"DEBUG: Deck with ID {current_deck_id} not found")
                return None

            deck_name = deck['name']
            print(f"DEBUG: Current deck: {deck_name} (ID: {current_deck_id})")

            # Return existing configuration or create new one
            if deck_name in self._decks_cache:
                deck_mapping = self._decks_cache[deck_name]
                deck_mapping.last_used = self._get_timestamp()
                return deck_mapping
            else:
                # Create new deck configuration
                deck_mapping = DeckFieldMapping(
                    deck_name=deck_name,
                    deck_id=current_deck_id,
                    prompt_field="Front",
                    target_field="Back",
                    audio_field="Audio",
                    last_used=self._get_timestamp(),
                    field_names=self._get_deck_field_names(current_deck_id)
                )
                self._decks_cache[deck_name] = deck_mapping
                print(f"DEBUG: Created new configuration for deck: {deck_name}")
                return deck_mapping

        except Exception as e:
            print(f"DEBUG: Error getting current deck info: {e}")
            return None

    def _get_deck_field_names(self, deck_id: int) -> list[str]:
        """Get all field names available in a deck."""
        if not mw or not mw.col:
            return []

        try:
            # Get all note types used in this deck
            deck = mw.col.decks.get(deck_id)
            if not deck:
                return []

            field_names = set()

            # Get all cards in this deck and collect their note types
            card_ids = mw.col.find_cards(f"did:{deck_id}")
            for cid in card_ids:
                card = mw.col.get_card(cid)
                if card:
                    note = card.note()
                    note_type = note.note_type()  # Use note_type() instead of deprecated model()
                    if hasattr(note_type, 'flds'):
                        for field_info in note_type['flds']:
                            if isinstance(field_info, dict):
                                field_name = field_info.get('name', field_info.get('fldName', ''))
                                if field_name:
                                    field_names.add(field_name)

            return sorted(list(field_names))
        except Exception as e:
            print(f"DEBUG: Error getting deck field names: {e}")
            return []

    def update_deck_mapping(self, deck_name: str, prompt_field: str, target_field: str, audio_field: str = None) -> bool:
        """Update field mapping for a deck."""
        if deck_name not in self._decks_cache:
            print(f"DEBUG: Deck {deck_name} not found in cache")
            return False

        deck_mapping = self._decks_cache[deck_name]
        deck_mapping.prompt_field = prompt_field
        deck_mapping.target_field = target_field
        deck_mapping.audio_field = audio_field
        deck_mapping.last_used = self._get_timestamp()

        # Save to main config instead of separate file
        self._save_to_config()
        print(f"DEBUG: Updated field mapping for deck: {deck_name}")
        return True

    def get_last_used_deck(self) -> Optional[DeckFieldMapping]:
        """Get the most recently used deck."""
        if not self._decks_cache:
            return None

        # Sort by last_used timestamp
        sorted_decks = sorted(
            self._decks_cache.values(),
            key=lambda d: d.last_used or "",
            reverse=True
        )

        return sorted_decks[0] if sorted_decks else None

    def get_all_decks(self) -> list[DeckFieldMapping]:
        """Get all configured decks."""
        return list(self._decks_cache.values())

    def get_deck_for_card(self, card_id: int) -> Optional[DeckFieldMapping]:
        """Get deck configuration for a specific card."""
        if not mw or not mw.col:
            return None

        try:
            card = mw.col.get_card(card_id)
            if not card:
                return None

            # Get note from card to find note type and deck info
            try:
                note = card.note()
                if not note:
                    print(f"DEBUG: Card {card_id} has no note")
                    return None
            except Exception as note_error:
                print(f"DEBUG: Error getting note from card {card_id}: {note_error}")
                return None

            # Find which deck this card belongs to using card's did
            try:
                deck_id = getattr(card, 'did', None)
                if deck_id is None:
                    print(f"DEBUG: Card {card_id} has no deck ID")
                    return None

                deck = mw.col.decks.get(deck_id)
                if not deck:
                    print(f"DEBUG: Deck {deck_id} not found for card {card_id}")
                    return None

                deck_name = deck.get('name', f'Unknown Deck {deck_id}')
                print(f"DEBUG: Card {card_id} belongs to deck: {deck_name}")

                # Return cached mapping or create temporary one
                if deck_name in self._decks_cache:
                    return self._decks_cache[deck_name]
                else:
                    # Create temporary mapping
                    return DeckFieldMapping(
                        deck_name=deck_name,
                        deck_id=deck_id,
                        prompt_field="Front",
                        target_field="Back",
                        audio_field="Audio",
                        field_names=self._get_deck_field_names(deck_id)
                    )

            except Exception as deck_error:
                print(f"DEBUG: Error finding deck for card {card_id}: {deck_error}")
                return None

        except Exception as e:
            print(f"DEBUG: Error getting deck for card {card_id}: {e}")
            return None

    def update_card_count(self, deck_name: str, count: int) -> None:
        """Update the card count for a deck."""
        if deck_name in self._decks_cache:
            self._decks_cache[deck_name].card_count = count

    def export_decks(self) -> Dict[str, Any]:
        """Export deck configurations for backup."""
        return {
            'decks': {name: asdict(deck) for name, deck in self._decks_cache.items()},
            'export_timestamp': self._get_timestamp(),
            'total_decks': len(self._decks_cache)
        }

    def import_decks(self, data: Dict[str, Any]) -> bool:
        """Import deck configurations from backup."""
        try:
            if 'decks' not in data:
                print("DEBUG: No decks data in import")
                return False

            imported_count = 0
            for deck_name, deck_data in data['decks'].items():
                deck_mapping = DeckFieldMapping(**deck_data)
                self._decks_cache[deck_name] = deck_mapping
                imported_count += 1

            self._save_decks()
            print(f"DEBUG: Imported {imported_count} deck configurations")
            return True

        except Exception as e:
            print(f"DEBUG: Error importing decks: {e}")
            return False


# Global instance
_deck_manager: Optional[DeckManager] = None


def get_deck_manager(config=None) -> DeckManager:
    """Get the global deck manager instance."""
    global _deck_manager
    if _deck_manager is None:
        _deck_manager = DeckManager()
    # Set config if provided and not already set
    if config and not _deck_manager._config:
        _deck_manager.set_config(config)
    return _deck_manager