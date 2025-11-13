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
from .utils import FieldProcessor, ProcessingConfig


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
        # Initialize field processor
        field_proc_config = ProcessingConfig(
            remove_html_tags=config.field_processing.remove_html_tags,
            preserve_line_breaks=config.field_processing.preserve_line_breaks,
            handle_html_entities=config.field_processing.handle_html_entities,
            normalize_whitespace=config.field_processing.normalize_whitespace,
            remove_extra_spaces=config.field_processing.remove_extra_spaces,
            keep_important_formatting=config.field_processing.keep_important_formatting,
            replace_html_formatting=config.field_processing.replace_html_formatting,
        )
        self.field_processor = FieldProcessor(field_proc_config)

    def _ensure_anki_available(self) -> None:
        """Ensure Anki is available."""
        if mw is None:
            raise RuntimeError("Anki integration is not available outside of Anki")

    def get_current_card_data(self, deck_manager=None) -> Optional[CardData]:
        """Extract data from the currently displayed card."""
        if not mw.reviewer.card:
            return None

        card = mw.reviewer.card
        note = card.note()

        # Get deck-specific field mapping if available
        if deck_manager:
            deck_info = deck_manager.get_deck_for_card(card.id)
            if deck_info:
                field_mapping = deck_info
                print(f"DEBUG: Using deck-specific field mapping for {deck_info.deck_name}")
            else:
                field_mapping = self.config.field_mapping
                print("DEBUG: Using default field mapping")
        else:
            field_mapping = self.config.field_mapping

        # Extract field values - handle both FieldMapping and DeckFieldMapping types
        if hasattr(field_mapping, 'prompt_field'):
            # DeckFieldMapping type
            prompt_field = field_mapping.prompt_field
            target_field = field_mapping.target_field
            audio_field = field_mapping.audio_field
        else:
            # FieldMapping type (legacy)
            prompt_field = field_mapping.prompt
            target_field = field_mapping.target
            audio_field = field_mapping.audio

        print(f"DEBUG: Extracting fields - Prompt: {prompt_field}, Target: {target_field}, Audio: {audio_field}")

        # Debug: List all available fields in this note
        try:
            if hasattr(note, 'note_type'):
                model = note.note_type()
            else:
                model = note.model()

            available_fields = []
            if hasattr(model, 'flds'):
                for field_info in model.flds:
                    if isinstance(field_info, dict):
                        field_name = field_info.get('name', field_info.get('fldName', ''))
                    else:
                        field_name = str(field_info)
                    available_fields.append(field_name)
                print(f"DEBUG: Available fields in note: {available_fields}")

            # Also show note.fields count
            if hasattr(note, 'fields'):
                print(f"DEBUG: Note has {len(note.fields)} fields")
                for i, field_val in enumerate(note.fields):
                    print(f"DEBUG: Field {i}: '{field_val}'")

        except Exception as debug_error:
            print(f"DEBUG: Error listing available fields: {debug_error}")

        raw_prompt = self._get_field_value(note, prompt_field)
        raw_target = self._get_field_value(note, target_field)
        raw_audio = self._get_field_value(note, audio_field) if audio_field else None

        print(f"DEBUG: Raw field values - Prompt: '{raw_prompt}', Target: '{raw_target}', Audio: '{raw_audio}'")

        # Process field content to remove HTML tags and clean text
        prompt = self.field_processor.process_field_content(raw_prompt) if raw_prompt else ""
        target = self.field_processor.process_field_content(raw_target) if raw_target else ""
        audio = raw_audio  # Audio field doesn't need processing

        print(f"DEBUG: Processed field values - Prompt: '{prompt}', Target: '{target}', Audio: '{audio}'")

        # Clean audio field (remove sound tags if present)
        if audio and audio.startswith("[sound:"):
            audio = audio[7:-1]  # Remove [sound: and ]

        return CardData(
            card_id=card.id,
            note_id=note.id,
            prompt=prompt or "",
            target=target or "",
            audio=audio,
            note_type=(note.note_type()["name"] if hasattr(note, 'note_type') else note.model()["name"])
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

            # Method 2: Try to get field index from note_type (traditional method)
            if hasattr(note, 'note_type'):
                model = note.note_type()
            else:
                model = note.model()  # Fallback for older versions
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

            # Method 3: Fallback - try to find field by index in note_type()['flds'] with different approach
            if hasattr(note, 'note_type'):
                note_model = note.note_type()
            else:
                note_model = note.model()
            if 'flds' in note_model:
                for i, field_info in enumerate(note_model['flds']):
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

    def answer_card_and_next(self, rating: int) -> None:
        """Submit answer using the correct Anki API flow."""
        print(f"DEBUG: answer_card_and_next called with rating {rating}")

        if not mw.reviewer.card:
            print("DEBUG: No current card in reviewer")
            return

        try:
            # Get current card before answering
            current_card = mw.reviewer.card
            print(f"DEBUG: Submitting current card ID: {getattr(current_card, 'id', 'unknown')} with rating {rating}")

            # The key insight: In Anki 25.x, we need to use the reviewer's public API
            # _answerCard is internal and might not properly trigger the full flow
            try:
                print("DEBUG: Using Anki 25.x correct API flow")

                # Method: Use reviewer's answerCard (not _answerCard) if available
                if hasattr(mw.reviewer, 'answerCard'):
                    print("DEBUG: Found reviewer.answerCard method")
                    mw.reviewer.answerCard(rating)
                elif hasattr(mw.reviewer, '_answerCard'):
                    print("DEBUG: Using reviewer._answerCard method")
                    mw.reviewer._answerCard(rating)
                else:
                    print("DEBUG: No answerCard method found, trying collection scheduler")
                    # Fallback to collection scheduler
                    if hasattr(mw, 'col') and mw.col and hasattr(mw.col, 'sched'):
                        mw.col.sched.answerCard(current_card, rating)
                    else:
                        raise Exception("No valid answerCard method found")

                print("DEBUG: Answer submitted successfully")

                # Now ensure the reviewer moves to next card
                import time
                time.sleep(0.1)

                # Check if Anki automatically moved to next card
                new_card = mw.reviewer.card
                if new_card and new_card != current_card:
                    print(f"DEBUG: SUCCESS - Auto-transitioned to card ID: {getattr(new_card, 'id', 'unknown')}")
                    return

                # If not, explicitly call nextCard
                print("DEBUG: Auto-transition didn't happen, calling nextCard()")
                if hasattr(mw.reviewer, 'nextCard'):
                    print("DEBUG: About to call mw.reviewer.nextCard()")
                    mw.reviewer.nextCard()
                    print("DEBUG: nextCard() call completed")
                    time.sleep(0.2)  # Give more time for transition

                    # Check final result with more robust comparison
                    final_card = mw.reviewer.card
                    if final_card:
                        final_id = getattr(final_card, 'id', None)
                        current_id = getattr(current_card, 'id', None)
                        print(f"DEBUG: Card comparison - Before: {current_id}, After: {final_id}")

                        if final_id and final_id != current_id:
                            print(f"DEBUG: SUCCESS - Forced transition to card ID: {final_id}")
                            return
                        else:
                            print(f"DEBUG: Still on same card after nextCard() - ID: {final_id}")

                            # Try additional steps that might be needed
                            print("DEBUG: Trying additional refresh steps")
                            try:
                                # Force UI refresh
                                if hasattr(mw.reviewer, 'refresh_if_needed'):
                                    mw.reviewer.refresh_if_needed()
                                    time.sleep(0.1)

                                # Try calling nextCard again after refresh
                                mw.reviewer.nextCard()
                                time.sleep(0.2)

                                # Check again
                                after_refresh_card = mw.reviewer.card
                                after_refresh_id = getattr(after_refresh_card, 'id', None)
                                print(f"DEBUG: After refresh - Before: {current_id}, After: {after_refresh_id}")

                                if after_refresh_id and after_refresh_id != current_id:
                                    print(f"DEBUG: SUCCESS - Refresh+nextCard worked, card ID: {after_refresh_id}")
                                    return
                                else:
                                    print("DEBUG: Even refresh+nextCard didn't work")

                            except Exception as refresh_error:
                                print(f"DEBUG: Refresh attempt failed: {refresh_error}")
                    else:
                        print("DEBUG: No card after nextCard() call")

            except Exception as api_error:
                print(f"DEBUG: API method failed: {api_error}")

            # Alternative method: Try to simulate the complete user interaction flow
            print("DEBUG: Trying to simulate complete user interaction flow")
            try:
                # Simulate what happens when user answers and clicks "Show Answer" then ease button
                from aqt.reviewer import Reviewer

                # Step 1: Ensure the answer is shown (in case it's still in question state)
                if hasattr(mw.reviewer, '_showAnswer'):
                    print("DEBUG: Step 1 - Calling _showAnswer")
                    mw.reviewer._showAnswer()
                    time.sleep(0.1)

                # Step 2: Answer the card properly
                ease_rating = rating  # Anki uses ease ratings 1-4 (Again=1, Hard=2, Good=3, Easy=4)
                if hasattr(mw.reviewer, '_answerCard'):
                    print(f"DEBUG: Step 2 - Answering with ease rating: {ease_rating}")
                    mw.reviewer._answerCard(ease_rating)
                    time.sleep(0.2)  # Give more time for processing

                    # Step 3: Check if we need to explicitly call nextCard or if it happened automatically
                    new_card = mw.reviewer.card
                    if new_card and new_card != current_card:
                        print(f"DEBUG: SUCCESS - Auto transition after answer, card ID: {getattr(new_card, 'id', 'unknown')}")
                        return
                    else:
                        print("DEBUG: No auto transition, calling nextCard() explicitly")
                        mw.reviewer.nextCard()
                        time.sleep(0.2)

                        # Check final result
                        final_card = mw.reviewer.card
                        if final_card and final_card != current_card:
                            print(f"DEBUG: SUCCESS - Answer + nextCard worked, card ID: {getattr(final_card, 'id', 'unknown')}")
                            return
                        else:
                            print("DEBUG: Even answer + nextCard didn't work")

            except Exception as sim_error:
                print(f"DEBUG: User simulation failed: {sim_error}")

            # Alternative method 2: Try using the collection's scheduler directly
            print("DEBUG: Trying collection scheduler method")
            try:
                if hasattr(mw, 'col') and mw.col and hasattr(mw.col, 'sched'):
                    sched = mw.col.sched

                    # Answer using collection scheduler
                    print(f"DEBUG: Answering via collection scheduler with rating: {rating}")
                    sched.answerCard(current_card, rating)
                    time.sleep(0.1)

                    # Force the reviewer to update
                    print("DEBUG: Forcing reviewer update")
                    if hasattr(mw.reviewer, 'refresh_if_needed'):
                        mw.reviewer.refresh_if_needed()

                    # Then get next card
                    print("DEBUG: Getting next card via reviewer")
                    mw.reviewer.nextCard()
                    time.sleep(0.2)

                    # Check result
                    final_card = mw.reviewer.card
                    if final_card and final_card != current_card:
                        print(f"DEBUG: SUCCESS - Collection scheduler method worked, card ID: {getattr(final_card, 'id', 'unknown')}")
                        return
                    else:
                        print("DEBUG: Collection scheduler method also didn't work")

            except Exception as sched_error:
                print(f"DEBUG: Collection scheduler method failed: {sched_error}")

            # Final diagnostic: Check if we're in a learning session or special state
            print("DEBUG: Performing final diagnostics")
            try:
                # Check card state
                if hasattr(current_card, 'queue'):
                    print(f"DEBUG: Card queue: {current_card.queue}")
                if hasattr(current_card, 'type'):
                    print(f"DEBUG: Card type: {current_card.type}")

                # Check reviewer state
                if hasattr(mw.reviewer, 'state'):
                    print(f"DEBUG: Reviewer state: {mw.reviewer.state}")
                if hasattr(mw.reviewer, 'cardCount'):
                    remaining = mw.reviewer.cardCount()
                    print(f"DEBUG: Cards remaining: {remaining}")

                # Check if this might be the last card
                if hasattr(mw.reviewer, 'remainingCount'):
                    try:
                        remaining = mw.reviewer.remainingCount()
                        print(f"DEBUG: Reviewer remainingCount: {remaining}")
                        if remaining <= 0:
                            print("DEBUG: This appears to be the last card in the session")
                    except:
                        pass

            except Exception as diag_error:
                print(f"DEBUG: Diagnostic failed: {diag_error}")

            final_card = mw.reviewer.card
            if final_card and final_card != current_card:
                print(f"DEBUG: FINAL SUCCESS - Card changed to ID: {getattr(final_card, 'id', 'unknown')}")
            else:
                print(f"DEBUG: FINAL STATUS - Card remains: {getattr(current_card, 'id', 'unknown')}")

        except Exception as e:
            print(f"ERROR: Critical failure: {e}")
            import traceback
            traceback.print_exc()

    def force_next_card(self) -> None:
        """Force move to next card without answering current one."""
        print("DEBUG: force_next_card called - forcing transition without answering")

        if not mw.reviewer.card:
            print("DEBUG: No current card in reviewer")
            return

        try:
            current_card = mw.reviewer.card
            print(f"DEBUG: Forcing transition from card ID: {getattr(current_card, 'id', 'unknown')}")

            # Force next card
            mw.reviewer.nextCard()

            # Check result
            import time
            time.sleep(0.1)

            new_card = mw.reviewer.card
            if new_card and new_card != current_card:
                print(f"DEBUG: SUCCESS - Forced transition to card ID: {getattr(new_card, 'id', 'unknown')}")
            else:
                print("DEBUG: No transition occurred (possibly no more cards)")

        except Exception as e:
            print(f"ERROR: Failed to force next card: {e}")

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

            # Method 2: Parse field structure from note_type
            if hasattr(note, 'note_type'):
                model = note.note_type()
            else:
                model = note.model()  # Fallback for older versions
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
            if hasattr(note, 'note_type'):
                model = note.note_type()
            else:
                model = note.model()  # Fallback for older versions
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
        try:
            if not mw:
                print("Anki mw is None")
                return False
            if not mw.reviewer:
                print("Anki reviewer is None")
                return False
            if not mw.reviewer.card:
                print("Anki reviewer.card is None")
                return False

            # Additional check: verify card has valid ID
            if not hasattr(mw.reviewer.card, 'id') or not mw.reviewer.card.id:
                print("Anki card has no valid ID")
                return False

            print(f"Reviewer is active with card ID: {mw.reviewer.card.id}")
            return True
        except Exception as e:
            print(f"Error checking reviewer activity: {e}")
            return False

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

    def get_next_card_from_deck(self, deck_manager=None) -> Optional[CardData]:
        """Get the next card from the current deck when not in review mode."""
        if not mw or not mw.col:
            print("DEBUG: No Anki collection available")
            return None

        try:
            # Get current deck ID
            current_deck_id = mw.col.conf.get('curDeck', None)
            if current_deck_id is None:
                print("DEBUG: No current deck selected")
                return None

            # Get card IDs from current deck (new cards first, then due cards)
            new_card_ids = mw.col.find_cards(f"did:{current_deck_id} is:new")
            due_card_ids = mw.col.find_cards(f"did:{current_deck_id} is:due")

            # Combine lists, prioritizing new cards
            card_ids = new_card_ids + due_card_ids

            if not card_ids:
                print("DEBUG: No cards found in current deck")
                return None

            print(f"DEBUG: Found {len(card_ids)} cards in current deck")

            # Get the first card that hasn't been recently practiced
            # For now, just take the first card
            card_id = card_ids[0]
            card = mw.col.get_card(card_id)

            if not card:
                print(f"DEBUG: Could not get card with ID {card_id}")
                return None

            note = card.note()

            # Get deck-specific field mapping if available
            if deck_manager:
                deck_info = deck_manager.get_deck_for_card(card.id)
                if deck_info:
                    field_mapping = deck_info
                    print(f"DEBUG: Using deck-specific field mapping for {deck_info.deck_name}")
                else:
                    from ..config import get_config
                    config = get_config()
                    field_mapping = config.field_mapping
                    print("DEBUG: Using default field mapping")
            else:
                from ..config import get_config
                config = get_config()
                field_mapping = config.field_mapping

            # Extract field values - handle both FieldMapping and DeckFieldMapping types
            if hasattr(field_mapping, 'prompt_field'):
                # DeckFieldMapping type
                prompt_field = field_mapping.prompt_field
                target_field = field_mapping.target_field
                audio_field = field_mapping.audio_field
            else:
                # FieldMapping type (legacy)
                prompt_field = field_mapping.prompt
                target_field = field_mapping.target
                audio_field = field_mapping.audio

            raw_prompt = self._get_field_value(note, prompt_field)
            raw_target = self._get_field_value(note, target_field)
            raw_audio = self._get_field_value(note, audio_field) if audio_field else None

            # Process field content
            prompt = self.field_processor.process_field_content(raw_prompt) if raw_prompt else ""
            target = self.field_processor.process_field_content(raw_target) if raw_target else ""
            audio = raw_audio

            # Clean audio field
            if audio and audio.startswith("[sound:"):
                audio = audio[7:-1]

            print(f"DEBUG: Loaded card from deck - Prompt: {prompt[:30]}..., Target: {target[:30]}...")

            return CardData(
                card_id=card.id,
                note_id=note.id,
                prompt=prompt or "",
                target=target or "",
                audio=audio,
                note_type=(note.note_type()["name"] if hasattr(note, 'note_type') else note.model()["name"])
            )

        except Exception as e:
            print(f"DEBUG: Error getting next card from deck: {e}")
            return None