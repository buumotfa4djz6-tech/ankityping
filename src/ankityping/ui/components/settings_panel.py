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
        self.deck_manager = get_deck_manager() if get_deck_manager else None

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

        # Current deck info
        info_group = QGroupBox("Current Deck Information")
        info_layout = QFormLayout(info_group)

        self.current_deck_label = QLabel("Loading...")
        self.deck_card_count_label = QLabel("0 cards")
        self.deck_last_used_label = QLabel("Never")

        info_layout.addRow("Deck:", self.current_deck_label)
        info_layout.addRow("Cards:", self.deck_card_count_label)
        info_layout.addRow("Last Used:", self.deck_last_used_label)

        layout.addWidget(info_group)

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

        window_layout.addRow("Always on Top:", self.always_on_top_checkbox)
        window_layout.addRow("Auto-focus:", self.auto_focus_checkbox)

        layout.addWidget(theme_group)
        layout.addWidget(window_group)

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

        # UI settings
        self.config.ui.theme = self.theme_combo.currentText()
        self.config.ui.always_on_top = self.always_on_top_checkbox.isChecked()
        self.config.behavior.auto_focus = self.auto_focus_checkbox.isChecked()

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
        """Save field mapping for current deck."""
        if not self.deck_manager:
            return

        deck_info = self.deck_manager.get_current_deck_info()
        if not deck_info:
            QMessageBox.warning(self, "No Deck", "No deck information available.")
            return

        prompt_field = self.prompt_field_combo.currentText()
        target_field = self.target_field_combo.currentText()
        audio_field = self.audio_field_combo.currentData() if self.audio_field_combo.currentData() else None

        if self.deck_manager.update_deck_mapping(deck_info.deck_name, prompt_field, target_field, audio_field):
            QMessageBox.information(self, "Settings Saved", f"Field mapping saved for deck: {deck_info.deck_name}")
            self.settings_changed.emit()
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
            # Save field processing settings
            self.config.field_processing.remove_html_tags = self.remove_html_tags_checkbox.isChecked()
            self.config.field_processing.preserve_line_breaks = self.preserve_line_breaks_checkbox.isChecked()
            self.config.field_processing.handle_html_entities = self.handle_html_entities_checkbox.isChecked()
            self.config.field_processing.replace_html_formatting = self.replace_formatting_checkbox.isChecked()
            self.config.field_processing.normalize_whitespace = self.normalize_whitespace_checkbox.isChecked()
            self.config.field_processing.remove_extra_spaces = self.remove_extra_spaces_checkbox.isChecked()

            # Save input processing settings
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
            self.config.ui.theme = self.theme_combo.currentText().lower()
            self.config.ui.font_family = self.font_family_combo.currentText()
            self.config.ui.font_size = self.font_size_spin.value()
            self.config.ui.window_width = self.window_width_spin.value()
            self.config.ui.window_height = self.window_height_spin.value()
            self.config.ui.always_on_top = self.always_on_top_checkbox.isChecked()
            self.config.ui.show_completion_popup = self.show_completion_popup_checkbox.isChecked()
            self.config.ui.auto_focus = self.auto_focus_checkbox.isChecked()
            self.config.ui.show_timer = self.show_timer_checkbox.isChecked()
            self.config.ui.show_errors = self.show_errors_checkbox.isChecked()
            self.config.behavior.input_mode = self.input_mode_combo.currentText().lower()
            self.config.behavior.auto_play_audio = self.auto_play_audio_checkbox.isChecked()

            # Save the config
            from ..config import save_config
            save_config(self.config)

            print("DEBUG: Settings saved successfully")
            self.settings_changed.emit()

            # Call parent accept to close the dialog
            super().accept()

        except Exception as e:
            print(f"ERROR: Failed to save settings: {e}")
            QMessageBox.critical(self, "Save Failed", f"Failed to save settings: {e}")

    def apply_settings(self) -> None:
        """Apply all settings and close the panel."""
        self.settings_changed.emit()
        self.close_requested.emit()