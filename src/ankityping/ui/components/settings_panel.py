"""Settings panel component for typing practice dialog."""

from __future__ import annotations

from typing import Optional, Dict, Any, Callable
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox,
    QSpinBox, QGroupBox, QTabWidget, QTextEdit, QPushButton, QFormLayout,
    QScrollArea, QMessageBox, QProgressBar, QGridLayout, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor

try:
    from ...utils import get_deck_manager, DeckManager
except ImportError:
    try:
        from ..utils import get_deck_manager, DeckManager
    except ImportError:
        get_deck_manager = None
        DeckManager = None


class SettingsPanel(QDialog):
    """Integrated settings dialog for typing practice."""

    # Signals
    settings_changed = pyqtSignal()

    def __init__(self, config, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.config = config

        # Initialize deck manager
        try:
            self.deck_manager = get_deck_manager(config) if get_deck_manager else None
            if not self.deck_manager and DeckManager:
                print("DEBUG: Creating new deck manager instance")
                self.deck_manager = DeckManager()
                self.deck_manager.set_config(config)
        except Exception as e:
            print(f"DEBUG: Error initializing deck manager: {e}")
            self.deck_manager = None

        self.setWindowTitle("Anki Typing Practice - Settings")
        self.setModal(True)
        self.resize(600, 700)

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Setup the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create tabs
        self._create_deck_settings_tab()
        self._create_field_processing_tab()
        self._create_input_processing_tab()
        self._create_ui_settings_tab()
        self._create_about_tab()

        # Add dialog buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        close_button.setDefault(True)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def _create_deck_settings_tab(self) -> None:
        """Create deck settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Deck selection
        deck_group = QGroupBox("Deck Configuration")
        deck_layout = QVBoxLayout(deck_group)

        # Deck selector
        deck_selector_layout = QHBoxLayout()
        deck_selector_layout.addWidget(QLabel("Select Deck:"))

        self.deck_combo = QComboBox()
        self.deck_combo.setMinimumWidth(200)
        deck_selector_layout.addWidget(self.deck_combo)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh_decks)
        deck_selector_layout.addWidget(refresh_button)

        deck_layout.addLayout(deck_selector_layout)

        # Deck info
        self.current_deck_label = QLabel("No deck selected")
        self.deck_card_count_label = QLabel("0 cards")
        self.deck_last_used_label = QLabel("Never")

        deck_info_layout = QFormLayout()
        deck_info_layout.addRow("Selected:", self.current_deck_label)
        deck_info_layout.addRow("Cards:", self.deck_card_count_label)
        deck_info_layout.addRow("Last Used:", self.deck_last_used_label)

        deck_layout.addLayout(deck_info_layout)

        layout.addWidget(deck_group)

        # Field mapping
        mapping_group = QGroupBox("Field Mapping")
        mapping_layout = QFormLayout(mapping_group)

        self.prompt_field_combo = QComboBox()
        self.target_field_combo = QComboBox()
        self.audio_field_combo = QComboBox()

        mapping_layout.addRow("Prompt Field:", self.prompt_field_combo)
        mapping_layout.addRow("Target Field:", self.target_field_combo)
        mapping_layout.addRow("Audio Field (Optional):", self.audio_field_combo)

        # Add "None" option for audio field
        self.audio_field_combo.addItem("None", "")

        # Save mapping button
        save_button = QPushButton("Save Field Mapping")
        save_button.clicked.connect(self._save_deck_mapping)
        mapping_layout.addRow("", save_button)

        layout.addWidget(mapping_group)

        # Deck management
        management_group = QGroupBox("Deck Management")
        management_layout = QVBoxLayout(management_group)

        # Refresh decks button
        refresh_button = QPushButton("Refresh Deck Information")
        refresh_button.clicked.connect(self._refresh_deck_info)
        management_layout.addWidget(refresh_button)

        # Export/Import buttons
        buttons_layout = QHBoxLayout()
        export_button = QPushButton("Export Settings")
        import_button = QPushButton("Import Settings")
        export_button.clicked.connect(self._export_settings)
        import_button.clicked.connect(self._import_settings)

        buttons_layout.addWidget(export_button)
        buttons_layout.addWidget(import_button)
        management_layout.addLayout(buttons_layout)

        layout.addWidget(management_group)

        # Add stretch
        layout.addStretch()

        self.tab_widget.addTab(widget, "Deck Settings")

    def _create_field_processing_tab(self) -> None:
        """Create field processing settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # HTML processing
        html_group = QGroupBox("HTML Processing")
        html_layout = QGridLayout(html_group)

        self.remove_html_tags_checkbox = QCheckBox("Remove HTML tags")
        self.remove_html_tags_checkbox.setChecked(self.config.field_processing.remove_html_tags)
        self.preserve_line_breaks_checkbox = QCheckBox("Preserve line breaks")
        self.preserve_line_breaks_checkbox.setChecked(self.config.field_processing.preserve_line_breaks)
        self.handle_html_entities_checkbox = QCheckBox("Handle HTML entities (&nbsp;, &lt;, etc.)")
        self.handle_html_entities_checkbox.setChecked(self.config.field_processing.handle_html_entities)
        self.replace_formatting_checkbox = QCheckBox("Replace formatting (e.g., <b>text</b> → text)")
        self.replace_formatting_checkbox.setChecked(self.config.field_processing.replace_html_formatting)

        html_layout.addWidget(self.remove_html_tags_checkbox, 0, 0, 1, 1)
        html_layout.addWidget(self.preserve_line_breaks_checkbox, 0, 1, 1, 1)
        html_layout.addWidget(self.handle_html_entities_checkbox, 1, 0, 1, 1)
        html_layout.addWidget(self.replace_formatting_checkbox, 1, 1, 1, 1)

        layout.addWidget(html_group)

        # Text cleaning
        cleaning_group = QGroupBox("Text Cleaning")
        cleaning_layout = QGridLayout(cleaning_group)

        self.normalize_whitespace_checkbox = QCheckBox("Normalize whitespace")
        self.normalize_whitespace_checkbox.setChecked(self.config.field_processing.normalize_whitespace)
        self.remove_extra_spaces_checkbox = QCheckBox("Remove extra spaces")
        self.remove_extra_spaces_checkbox.setChecked(self.config.field_processing.remove_extra_spaces)

        cleaning_layout.addWidget(self.normalize_whitespace_checkbox, 0, 0, 1, 1)
        cleaning_layout.addWidget(self.remove_extra_spaces_checkbox, 0, 1, 1, 1)

        layout.addWidget(cleaning_group)

        layout.addStretch()
        self.tab_widget.addTab(widget, "Field Processing")

    def _create_input_processing_tab(self) -> None:
        """Create input processing settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Punctuation handling
        punctuation_group = QGroupBox("Punctuation Handling")
        punctuation_layout = QGridLayout(punctuation_group)

        self.handle_punctuation_checkbox = QCheckBox("Enable punctuation processing")
        self.handle_punctuation_checkbox.setChecked(self.config.input_processing.handle_punctuation)
        self.auto_punctuation_checkbox = QCheckBox("Auto-add punctuation")
        self.auto_punctuation_checkbox.setChecked(self.config.input_processing.auto_punctuation)
        self.ignore_punctuation_errors_checkbox = QCheckBox("Ignore punctuation errors")
        self.ignore_punctuation_errors_checkbox.setChecked(self.config.input_processing.ignore_punctuation_errors)

        punctuation_layout.addWidget(self.handle_punctuation_checkbox, 0, 0, 1, 1)
        punctuation_layout.addWidget(self.auto_punctuation_checkbox, 0, 1, 1, 1)
        punctuation_layout.addWidget(self.ignore_punctuation_errors_checkbox, 1, 0, 1, 1)

        layout.addWidget(punctuation_group)

        # Whitespace handling
        whitespace_group = QGroupBox("Whitespace Handling")
        whitespace_layout = QGridLayout(whitespace_group)

        self.handle_whitespace_checkbox = QCheckBox("Enable whitespace processing")
        self.handle_whitespace_checkbox.setChecked(self.config.input_processing.handle_whitespace)
        self.ignore_extra_spaces_checkbox = QCheckBox("Ignore extra spaces")
        self.ignore_extra_spaces_checkbox.setChecked(self.config.input_processing.ignore_extra_spaces)
        self.auto_correct_spaces_checkbox = QCheckBox("Auto-correct spacing after punctuation")
        self.auto_correct_spaces_checkbox.setChecked(self.config.input_processing.auto_correct_spaces)

        whitespace_layout.addWidget(self.handle_whitespace_checkbox, 0, 0, 1, 1)
        whitespace_layout.addWidget(self.ignore_extra_spaces_checkbox, 0, 1, 1, 1)
        whitespace_layout.addWidget(self.auto_correct_spaces_checkbox, 1, 0, 1, 1)

        layout.addWidget(whitespace_group)

        # Case sensitivity
        case_group = QGroupBox("Case Sensitivity")
        case_layout = QGridLayout(case_group)

        self.case_sensitive_checkbox = QCheckBox("Case-sensitive typing")
        self.case_sensitive_checkbox.setChecked(self.config.input_processing.case_sensitive)
        self.auto_correct_case_checkbox = QCheckBox("Auto-correct case")
        self.auto_correct_case_checkbox.setChecked(self.config.input_processing.auto_correct_case)

        case_layout.addWidget(self.case_sensitive_checkbox, 0, 0, 1, 1)
        case_layout.addWidget(self.auto_correct_case_checkbox, 0, 1, 1, 1)

        layout.addWidget(case_group)

        # Diacritics handling
        diacritics_group = QGroupBox("Diacritics Handling")
        diacritics_layout = QGridLayout(diacritics_group)

        self.handle_diacritics_checkbox = QCheckBox("Enable diacritics processing")
        self.handle_diacritics_checkbox.setChecked(self.config.input_processing.handle_diacritics)
        self.ignore_diacritic_errors_checkbox = QCheckBox("Ignore diacritic errors")
        self.ignore_diacritic_errors_checkbox.setChecked(self.config.input_processing.ignore_diacritic_errors)

        diacritics_layout.addWidget(self.handle_diacritics_checkbox, 0, 0, 1, 1)
        diacritics_layout.addWidget(self.ignore_diacritic_errors_checkbox, 0, 1, 1, 1)

        layout.addWidget(diacritics_group)

        layout.addStretch()
        self.tab_widget.addTab(widget, "Input Processing")

    def _create_ui_settings_tab(self) -> QWidget:
        """Create UI settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Theme
        theme_group = QGroupBox("Theme")
        theme_layout = QFormLayout(theme_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["light", "dark"])
        self.theme_combo.setCurrentText(self.config.ui.theme)

        theme_layout.addRow("Theme:", self.theme_combo)

        # Window behavior
        window_group = QGroupBox("Window Behavior")
        window_layout = QFormLayout(window_group)

        self.always_on_top_checkbox = QCheckBox("Always on top")
        self.always_on_top_checkbox.setChecked(self.config.ui.always_on_top)
        self.auto_focus_checkbox = QCheckBox("Auto-focus on load")
        self.auto_focus_checkbox.setChecked(self.config.behavior.auto_focus)
        self.show_completion_popup_checkbox = QCheckBox("Show completion popup")
        self.show_completion_popup_checkbox.setChecked(self.config.behavior.show_completion_popup)

        window_layout.addRow("Always on Top:", self.always_on_top_checkbox)
        window_layout.addRow("Auto-focus:", self.auto_focus_checkbox)
        window_layout.addRow("Completion Popup:", self.show_completion_popup_checkbox)

        layout.addWidget(theme_group)
        layout.addWidget(window_group)

        # Font settings
        font_group = QGroupBox("Font Settings")
        font_layout = QFormLayout(font_group)

        self.font_family_combo = QComboBox()
        self.font_family_combo.addItems(["Arial", "Consolas", "Courier New", "Monaco", "Menlo", "Verdana", "Tahoma"])
        self.font_family_combo.setCurrentText(self.config.ui.font_family)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 48)
        self.font_size_spin.setValue(self.config.ui.font_size)

        font_layout.addRow("Font Family:", self.font_family_combo)
        font_layout.addRow("Font Size:", self.font_size_spin)

        layout.addWidget(font_group)

        # Window size
        size_group = QGroupBox("Window Size")
        size_layout = QFormLayout(size_group)

        self.window_width_spin = QSpinBox()
        self.window_width_spin.setRange(400, 2000)
        self.window_width_spin.setValue(self.config.ui.window_width)

        self.window_height_spin = QSpinBox()
        self.window_height_spin.setRange(300, 1500)
        self.window_height_spin.setValue(self.config.ui.window_height)

        size_layout.addRow("Width:", self.window_width_spin)
        size_layout.addRow("Height:", self.window_height_spin)

        layout.addWidget(size_group)

        # Behavior settings
        behavior_group = QGroupBox("Behavior Settings")
        behavior_layout = QFormLayout(behavior_group)

        self.input_mode_combo = QComboBox()
        self.input_mode_combo.addItems(["progressive", "accompanying"])
        self.input_mode_combo.setCurrentText(self.config.behavior.input_mode)

        self.auto_play_audio_checkbox = QCheckBox("Auto-play audio")
        self.auto_play_audio_checkbox.setChecked(self.config.behavior.auto_play_audio)

        self.show_timer_checkbox = QCheckBox("Show timer")
        self.show_timer_checkbox.setChecked(self.config.behavior.show_timer)

        self.show_errors_checkbox = QCheckBox("Show errors")
        self.show_errors_checkbox.setChecked(self.config.behavior.show_errors)

        behavior_layout.addRow("Input Mode:", self.input_mode_combo)
        behavior_layout.addRow("Auto-play Audio:", self.auto_play_audio_checkbox)
        behavior_layout.addRow("Show Timer:", self.show_timer_checkbox)
        behavior_layout.addRow("Show Errors:", self.show_errors_checkbox)

        layout.addWidget(behavior_group)

        layout.addStretch()
        self.tab_widget.addTab(widget, "UI Settings")

    def _create_about_tab(self) -> QWidget:
        """Create about tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # About information
        about_group = QGroupBox("About AnkiTyping")
        about_layout = QVBoxLayout(about_group)

        about_text = QTextEdit()
        about_text.setReadOnly(True)
        about_text.setHtml("""
        <h3>AnkiTyping v1.1.0</h3>
        <p>A comprehensive typing practice plugin for Anki.</p>

        <h4>Features:</h4>
        <ul>
            <li>HTML tag removal and text cleaning</li>
            <li>Smart punctuation and whitespace handling</li>
            <li>Deck-specific field mappings</li>
            <li>Real-time typing feedback</li>
        </ul>

        <h4>Keyboard Shortcuts:</h4>
        <ul>
            <li><b>Ctrl+T</b> - Open typing practice</li>
            <li><b>Esc</b> - Give up current practice</li>
            <li><b>Ctrl+H</b> - Show hint</li>
            <li><b>Ctrl+N</b> - Skip to next card</li>
        </ul>

        <p><small>Created with ❤️ for Anki users.</small></p>
        """)

        about_layout.addWidget(about_text)
        layout.addWidget(about_group)

        layout.addStretch()
        self.tab_widget.addTab(widget, "About")

    def _connect_signals(self) -> None:
        """Connect signals."""
        # Field processing
        self.remove_html_tags_checkbox.toggled.connect(self._update_config)
        self.preserve_line_breaks_checkbox.toggled.connect(self._update_config)
        self.handle_html_entities_checkbox.toggled.connect(self._update_config)
        self.replace_formatting_checkbox.toggled.connect(self._update_config)
        self.normalize_whitespace_checkbox.toggled.connect(self._update_config)
        self.remove_extra_spaces_checkbox.toggled.connect(self._update_config)

        # Input processing
        self.handle_punctuation_checkbox.toggled.connect(self._update_config)
        self.auto_punctuation_checkbox.toggled.connect(self._update_config)
        self.ignore_punctuation_errors_checkbox.toggled.connect(self._update_config)
        self.handle_whitespace_checkbox.toggled.connect(self._update_config)
        self.ignore_extra_spaces_checkbox.toggled.connect(self._update_config)
        self.auto_correct_spaces_checkbox.toggled.connect(self._update_config)
        self.case_sensitive_checkbox.toggled.connect(self._update_config)
        self.auto_correct_case_checkbox.toggled.connect(self._update_config)
        self.handle_diacritics_checkbox.toggled.connect(self._update_config)
        self.ignore_diacritic_errors_checkbox.toggled.connect(self._update_config)

        # Deck selection
        self.deck_combo.currentIndexChanged.connect(self._on_deck_changed)

        # UI settings
        self.theme_combo.currentTextChanged.connect(self._update_config)
        self.always_on_top_checkbox.toggled.connect(self._update_config)
        self.auto_focus_checkbox.toggled.connect(self._update_config)

    def _update_config(self) -> None:
        """Update configuration from UI controls."""
        # Field processing
        self.config.field_processing.remove_html_tags = self.remove_html_tags_checkbox.isChecked()
        self.config.field_processing.preserve_line_breaks = self.preserve_line_breaks_checkbox.isChecked()
        self.config.field_processing.handle_html_entities = self.handle_html_entities_checkbox.isChecked()
        self.config.field_processing.replace_html_formatting = self.replace_formatting_checkbox.isChecked()
        self.config.field_processing.normalize_whitespace = self.normalize_whitespace_checkbox.isChecked()
        self.config.field_processing.remove_extra_spaces = self.remove_extra_spaces_checkbox.isChecked()

        # Input processing
        self.config.input_processing.handle_punctuation = self.handle_punctuation_checkbox.isChecked()
        self.config.input_processing.auto_punctuation = self.auto_punctuation_checkbox.isChecked()
        self.config.input_processing.ignore_punctuation_errors = self.ignore_punctuation_errors_checkbox.isChecked()
        self.config.input_processing.handle_whitespace = self.handle_whitespace_checkbox.isChecked()
        self.config.input_processing.ignore_extra_spaces = self.ignore_extra_spaces_checkbox.isChecked()
        self.config.input_processing.auto_correct_spaces = self.auto_correct_spaces_checkbox.isChecked()
        self.config.input_processing.case_sensitive = self.case_sensitive_checkbox.isChecked()
        self.config.input_processing.auto_correct_case = self.auto_correct_case_checkbox.isChecked()
        self.config.input_processing.handle_diacritics = self.handle_diacritics_checkbox.isChecked()
        self.config.input_processing.ignore_diacritic_errors = self.ignore_diacritic_errors_checkbox.isChecked()

        # UI settings
        self.config.ui.theme = self.theme_combo.currentText().lower()
        self.config.ui.font_family = self.font_family_combo.currentText()
        self.config.ui.font_size = self.font_size_spin.value()
        self.config.ui.window_width = self.window_width_spin.value()
        self.config.ui.window_height = self.window_height_spin.value()
        self.config.ui.always_on_top = self.always_on_top_checkbox.isChecked()

        # Behavior settings
        self.config.behavior.auto_focus = self.auto_focus_checkbox.isChecked()
        self.config.behavior.show_completion_popup = self.show_completion_popup_checkbox.isChecked()
        self.config.behavior.show_timer = self.show_timer_checkbox.isChecked()
        self.config.behavior.show_errors = self.show_errors_checkbox.isChecked()
        self.config.behavior.input_mode = self.input_mode_combo.currentText().lower()
        self.config.behavior.auto_play_audio = self.auto_play_audio_checkbox.isChecked()

        # Emit signal
        self.settings_changed.emit()

    def load_deck_info(self) -> None:
        """Load current deck information."""
        if not self.deck_manager:
            return

        deck_info = self.deck_manager.get_current_deck_info()
        if deck_info:
            self.current_deck_label.setText(deck_info.deck_name)
            self.deck_card_count_label.setText(str(deck_info.card_count))
            self.deck_last_used_label.setText(deck_info.last_used or "Never")

            # Update field combos
            self._update_field_combos(deck_info.field_names)

            # Set current mapping
            self.prompt_field_combo.setCurrentText(deck_info.prompt_field)
            self.target_field_combo.setCurrentText(deck_info.target_field)
            audio_text = deck_info.audio_field or "None"
            index = self.audio_field_combo.findText(audio_text)
            if index >= 0:
                self.audio_field_combo.setCurrentIndex(index)

    def _update_field_combos(self, field_names: list[str]) -> None:
        """Update field combo boxes with available fields."""
        # Save current selections
        current_prompt = self.prompt_field_combo.currentText()
        current_target = self.target_field_combo.currentText()
        current_audio = self.audio_field_combo.currentText()

        # Clear and repopulate
        self.prompt_field_combo.clear()
        self.target_field_combo.clear()
        self.audio_field_combo.clear()

        # Add "None" option first for audio
        self.audio_field_combo.addItem("None", "")

        # Add all field names
        for field_name in field_names:
            self.prompt_field_combo.addItem(field_name)
            self.target_field_combo.addItem(field_name)
            self.audio_field_combo.addItem(field_name)

        # Restore selections if they still exist
        if current_prompt:
            index = self.prompt_field_combo.findText(current_prompt)
            if index >= 0:
                self.prompt_field_combo.setCurrentIndex(index)

        if current_target:
            index = self.target_field_combo.findText(current_target)
            if index >= 0:
                self.target_field_combo.setCurrentIndex(index)

        if current_audio:
            index = self.audio_field_combo.findText(current_audio)
            if index >= 0:
                self.audio_field_combo.setCurrentIndex(index)

    def _save_deck_mapping(self) -> None:
        """Save field mapping for selected deck."""
        if not self.deck_manager:
            return

        current_index = self.deck_combo.currentIndex()
        if current_index < 0:
            QMessageBox.warning(self, "No Deck", "Please select a deck first.")
            return

        deck_data = self.deck_combo.itemData(current_index)
        if not deck_data:
            QMessageBox.warning(self, "No Deck", "No deck selected.")
            return

        prompt_field = self.prompt_field_combo.currentText()
        target_field = self.target_field_combo.currentText()
        audio_field = self.audio_field_combo.currentText()

        if audio_field == "None" or not audio_field.strip():
            audio_field = None

        if self.deck_manager.update_deck_mapping(deck_data.deck_name, prompt_field, target_field, audio_field):
            QMessageBox.information(self, "Settings Saved", f"Field mapping saved for deck: {deck_data.deck_name}")
            self.settings_changed.emit()
            # Update the deck data in combo box
            updated_deck_data = self.deck_manager._decks_cache.get(deck_data.deck_name)
            if updated_deck_data:
                self.deck_combo.setItemData(current_index, updated_deck_data)
        else:
            QMessageBox.warning(self, "Save Failed", "Failed to save field mapping.")

    def _refresh_deck_info(self) -> None:
        """Refresh deck information and field lists."""
        if not self.deck_manager:
            return

        deck_info = self.deck_manager.get_current_deck_info()
        if deck_info:
            # Update field names (this might change if note types change)
            deck_info.field_names = self.deck_manager._get_deck_field_names(deck_info.deck_id)
            self._update_field_combos(deck_info.field_names)

        self.load_deck_info()

    def _export_settings(self) -> None:
        """Export settings to file."""
        try:
            from datetime import datetime
            filename = f"ankityping_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            # Create export data
            export_data = {
                'config': self.config.to_dict(),
                'deck_settings': self.deck_manager.export_decks() if self.deck_manager else None,
                'export_timestamp': datetime.now().isoformat(),
                'version': '1.1.0'
            }

            # Save to file
            from PyQt6.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Settings", filename, "JSON Files (*.json);;All Files (*)"
            )

            if file_path:
                import json
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "Export Complete", f"Settings exported to: {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export settings: {e}")

    def _import_settings(self) -> None:
        """Import settings from file."""
        try:
            from PyQt6.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Import Settings", "", "JSON Files (*.json);;All Files (*)"
            )

            if file_path:
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)

                # Import deck settings
                if self.deck_manager and 'deck_settings' in import_data:
                    self.deck_manager.import_decks(import_data['deck_settings'])

                # Import config settings (basic implementation)
                # This would need to be more sophisticated for real use
                QMessageBox.information(self, "Import Complete", f"Settings imported from: {file_path}")

                # Refresh UI
                self.load_deck_info()
                self.settings_changed.emit()

        except Exception as e:
            QMessageBox.critical(self, "Import Failed", f"Failed to import settings: {e}")

    def accept(self) -> None:
        """Save all settings and close the dialog."""
        try:
            print("DEBUG: Starting settings save process...")

            # Save field processing settings
            print("DEBUG: Saving field processing settings...")
            self.config.field_processing.remove_html_tags = self.remove_html_tags_checkbox.isChecked()
            self.config.field_processing.preserve_line_breaks = self.preserve_line_breaks_checkbox.isChecked()
            self.config.field_processing.handle_html_entities = self.handle_html_entities_checkbox.isChecked()
            self.config.field_processing.replace_html_formatting = self.replace_formatting_checkbox.isChecked()
            self.config.field_processing.normalize_whitespace = self.normalize_whitespace_checkbox.isChecked()
            self.config.field_processing.remove_extra_spaces = self.remove_extra_spaces_checkbox.isChecked()

            # Save input processing settings
            print("DEBUG: Saving input processing settings...")
            self.config.input_processing.handle_punctuation = self.handle_punctuation_checkbox.isChecked()
            self.config.input_processing.auto_punctuation = self.auto_punctuation_checkbox.isChecked()
            self.config.input_processing.ignore_punctuation_errors = self.ignore_punctuation_errors_checkbox.isChecked()
            self.config.input_processing.handle_whitespace = self.handle_whitespace_checkbox.isChecked()
            self.config.input_processing.ignore_extra_spaces = self.ignore_extra_spaces_checkbox.isChecked()
            self.config.input_processing.auto_correct_spaces = self.auto_correct_spaces_checkbox.isChecked()
            self.config.input_processing.case_sensitive = self.case_sensitive_checkbox.isChecked()
            self.config.input_processing.auto_correct_case = self.auto_correct_case_checkbox.isChecked()
            self.config.input_processing.handle_diacritics = self.handle_diacritics_checkbox.isChecked()
            self.config.input_processing.ignore_diacritic_errors = self.ignore_diacritic_errors_checkbox.isChecked()

            # Save UI settings
            print("DEBUG: Saving UI settings...")
            self.config.ui.theme = self.theme_combo.currentText().lower()
            self.config.ui.font_family = self.font_family_combo.currentText()
            self.config.ui.font_size = self.font_size_spin.value()
            self.config.ui.window_width = self.window_width_spin.value()
            self.config.ui.window_height = self.window_height_spin.value()
            self.config.ui.always_on_top = self.always_on_top_checkbox.isChecked()

            # Save behavior settings
            print("DEBUG: Saving behavior settings...")
            self.config.behavior.show_completion_popup = self.show_completion_popup_checkbox.isChecked()
            self.config.behavior.auto_focus = self.auto_focus_checkbox.isChecked()
            self.config.behavior.show_timer = self.show_timer_checkbox.isChecked()
            self.config.behavior.show_errors = self.show_errors_checkbox.isChecked()
            self.config.behavior.input_mode = self.input_mode_combo.currentText().lower()
            self.config.behavior.auto_play_audio = self.auto_play_audio_checkbox.isChecked()

            # Save the config
            print("DEBUG: Attempting to save config...")
            try:
                from ..config import save_config
                print("DEBUG: Imported save_config successfully with relative import")
                save_config(self.config)
                print("DEBUG: save_config completed successfully")
            except ImportError as import_error:
                print(f"DEBUG: Import error for save_config: {import_error}")
                # Fallback - try absolute import
                try:
                    from ankityping.config import save_config
                    print("DEBUG: Imported save_config with absolute import")
                    save_config(self.config)
                    print("DEBUG: save_config completed with absolute import")
                except ImportError as fallback_error:
                    print(f"DEBUG: Fallback import also failed: {fallback_error}")
                    raise Exception(f"Unable to import save_config: {fallback_error}")

            print("DEBUG: Settings saved successfully")
            self.settings_changed.emit()

            # Call parent accept to close the dialog
            print("DEBUG: Calling parent accept...")
            super().accept()

        except Exception as e:
            import traceback
            print(f"ERROR: Failed to save settings: {e}")
            print("DEBUG: Full traceback:")
            traceback.print_exc()
            QMessageBox.critical(self, "Save Failed", f"Failed to save settings: {e}")

    def apply_settings(self) -> None:
        """Apply all settings and close the panel."""
        self.settings_changed.emit()
        self.close_requested.emit()

    def _refresh_decks(self) -> None:
        """Refresh the list of available decks."""
        try:
            if not self.deck_manager:
                print("DEBUG: Deck manager not available")
                return

            print("DEBUG: Refreshing deck list...")

            # Get current deck info and add to cache if not present
            current_deck = self.deck_manager.get_current_deck_info()
            if current_deck:
                print(f"DEBUG: Current deck found: {current_deck.deck_name}")

            # Get all available decks
            decks = self.deck_manager.get_all_decks()

            # Clear and repopulate combo box
            self.deck_combo.clear()

            deck_items = []
            for deck in decks:
                deck_text = f"{deck.deck_name} ({deck.card_count} cards)"
                deck_items.append((deck_text, deck))

            # Sort by deck name
            deck_items.sort(key=lambda x: x[1].deck_name)

            for deck_text, deck in deck_items:
                self.deck_combo.addItem(deck_text, deck)

            print(f"DEBUG: Loaded {len(deck_items)} decks into combo box")

            # Select the current deck or last used deck
            selected_deck = current_deck or self.deck_manager.get_last_used_deck()
            if selected_deck:
                print(f"DEBUG: Selecting deck: {selected_deck.deck_name}")
                for i in range(self.deck_combo.count()):
                    deck_data = self.deck_combo.itemData(i)
                    if deck_data and deck_data.deck_name == selected_deck.deck_name:
                        self.deck_combo.setCurrentIndex(i)
                        self._on_deck_changed(i)  # Update field mappings
                        break

        except Exception as e:
            print(f"DEBUG: Error refreshing decks: {e}")
            QMessageBox.critical(self, "Error", f"Failed to refresh decks: {e}")

    def _on_deck_changed(self, index: int) -> None:
        """Handle deck selection change."""
        try:
            if index < 0 or not self.deck_manager:
                self.current_deck_label.setText("No deck selected")
                self.deck_card_count_label.setText("0 cards")
                self.deck_last_used_label.setText("Never")
                # Clear field combos
                self.prompt_field_combo.clear()
                self.target_field_combo.clear()
                self.audio_field_combo.clear()
                return

            deck_data = self.deck_combo.itemData(index)
            if not deck_data:
                return

            # Update deck info
            self.current_deck_label.setText(deck_data.deck_name)
            self.deck_card_count_label.setText(f"{deck_data.card_count} cards")
            # Handle both datetime and string formats for last_used
            if deck_data.last_used:
                try:
                    if hasattr(deck_data.last_used, 'strftime'):
                        last_used_text = deck_data.last_used.strftime("%Y-%m-%d %H:%M")
                    else:
                        last_used_text = str(deck_data.last_used)
                except:
                    last_used_text = "Unknown"
            else:
                last_used_text = "Never"
            self.deck_last_used_label.setText(last_used_text)

            print(f"DEBUG: Selected deck: {deck_data.deck_name}")

            # Update field combos
            self.prompt_field_combo.clear()
            self.target_field_combo.clear()
            self.audio_field_combo.clear()

            # Add common field names plus deck-specific fields
            common_fields = ["Front", "Back", "Expression", "Meaning", "Reading", "Sentence", "Translation", "Audio", "Sound", "Notes", "Extra"]
            all_fields = list(set(common_fields + deck_data.field_names))
            all_fields.sort()  # Sort alphabetically

            for field_name in all_fields:
                self.prompt_field_combo.addItem(field_name)
                self.target_field_combo.addItem(field_name)
                self.audio_field_combo.addItem(field_name)

            # Set current selections if deck has saved mapping
            if deck_data.prompt_field:
                self.prompt_field_combo.setCurrentText(deck_data.prompt_field)
            if deck_data.target_field:
                self.target_field_combo.setCurrentText(deck_data.target_field)
            if deck_data.audio_field:
                self.audio_field_combo.setCurrentText(deck_data.audio_field)

        except Exception as e:
            print(f"DEBUG: Error handling deck change: {e}")

    def showEvent(self, event) -> None:
        """Initialize when the dialog is shown."""
        super().showEvent(event)
        # Refresh decks on first show
        if hasattr(self, 'deck_combo'):
            self._refresh_decks()