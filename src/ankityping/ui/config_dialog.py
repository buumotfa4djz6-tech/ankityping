"""Configuration dialog for the ankityping plugin."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLabel, QComboBox, QCheckBox, QRadioButton, QPushButton,
    QSpinBox, QMessageBox, QWidget, QButtonGroup
)
from PyQt6.QtCore import Qt

from ..anki_integration import AnkiIntegration
from ..config import Config, UIConfig, BehaviorConfig, FieldMapping, get_config, save_config


class ConfigDialog(QDialog):
    """Configuration dialog for the ankityping plugin."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.config = get_config()
        self.anki_integration = AnkiIntegration(self.config)

        self.setWindowTitle("Anki Typing Practice - Settings")
        self.setModal(True)
        self.resize(500, 600)

        self._setup_ui()
        self._load_current_config()

    def _setup_ui(self) -> None:
        """Setup the user interface."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Field mapping group
        field_group = QGroupBox("Field Mapping")
        field_layout = QFormLayout()
        field_group.setLayout(field_layout)

        # Get available fields from current card
        available_fields = self._get_available_fields()

        # Prompt field
        self.prompt_field_combo = QComboBox()
        self.prompt_field_combo.setEditable(True)
        self.prompt_field_combo.addItems(available_fields)
        field_layout.addRow("Prompt Field:", self.prompt_field_combo)

        # Target field
        self.target_field_combo = QComboBox()
        self.target_field_combo.setEditable(True)
        self.target_field_combo.addItems(available_fields)
        field_layout.addRow("Target Field:", self.target_field_combo)

        # Audio field
        self.audio_field_combo = QComboBox()
        self.audio_field_combo.setEditable(True)
        self.audio_field_combo.addItems([""] + available_fields)
        field_layout.addRow("Audio Field (optional):", self.audio_field_combo)

        layout.addWidget(field_group)

        # Behavior group
        behavior_group = QGroupBox("Behavior")
        behavior_layout = QFormLayout()
        behavior_group.setLayout(behavior_layout)

        # Reset mode
        reset_layout = QHBoxLayout()
        self.reset_sentence_radio = QRadioButton("Reset Sentence")
        self.reset_word_radio = QRadioButton("Reset Current Word")
        reset_layout.addWidget(self.reset_sentence_radio)
        reset_layout.addWidget(self.reset_word_radio)
        behavior_layout.addRow("Reset Mode:", reset_layout)

        self.reset_button_group = QButtonGroup()
        self.reset_button_group.addButton(self.reset_sentence_radio)
        self.reset_button_group.addButton(self.reset_word_radio)

        # Input mode
        input_layout = QHBoxLayout()
        self.progressive_radio = QRadioButton("Progressive Mode")
        self.accompanying_radio = QRadioButton("Accompanying Mode")
        input_layout.addWidget(self.progressive_radio)
        input_layout.addWidget(self.accompanying_radio)
        behavior_layout.addRow("Input Mode:", input_layout)

        self.input_button_group = QButtonGroup()
        self.input_button_group.addButton(self.progressive_radio)
        self.input_button_group.addButton(self.accompanying_radio)

        # Checkboxes
        self.auto_focus_checkbox = QCheckBox("Auto-focus on Start")
        behavior_layout.addRow(self.auto_focus_checkbox)

        self.show_completion_popup_checkbox = QCheckBox("Show Completion Popup")
        behavior_layout.addRow(self.show_completion_popup_checkbox)

        self.sound_enabled_checkbox = QCheckBox("Enable Sound Effects")
        behavior_layout.addRow(self.sound_enabled_checkbox)

        self.auto_play_audio_checkbox = QCheckBox("Auto-play Audio on Start")
        behavior_layout.addRow(self.auto_play_audio_checkbox)

        self.show_timer_checkbox = QCheckBox("Show Timer")
        behavior_layout.addRow(self.show_timer_checkbox)

        self.show_errors_checkbox = QCheckBox("Show Error Count")
        behavior_layout.addRow(self.show_errors_checkbox)

        layout.addWidget(behavior_group)

        # UI group
        ui_group = QGroupBox("User Interface")
        ui_layout = QFormLayout()
        ui_group.setLayout(ui_layout)

        # Theme
        theme_layout = QHBoxLayout()
        self.light_theme_radio = QRadioButton("Light")
        self.dark_theme_radio = QRadioButton("Dark")
        theme_layout.addWidget(self.light_theme_radio)
        theme_layout.addWidget(self.dark_theme_radio)
        ui_layout.addRow("Theme:", theme_layout)

        self.theme_button_group = QButtonGroup()
        self.theme_button_group.addButton(self.light_theme_radio)
        self.theme_button_group.addButton(self.dark_theme_radio)

        # Window size
        size_layout = QHBoxLayout()
        self.window_width_spinbox = QSpinBox()
        self.window_width_spinbox.setMinimum(400)
        self.window_width_spinbox.setMaximum(1200)
        self.window_width_spinbox.setSuffix(" px")
        size_layout.addWidget(QLabel("Width:"))
        size_layout.addWidget(self.window_width_spinbox)

        self.window_height_spinbox = QSpinBox()
        self.window_height_spinbox.setMinimum(300)
        self.window_height_spinbox.setMaximum(800)
        self.window_height_spinbox.setSuffix(" px")
        size_layout.addWidget(QLabel("Height:"))
        size_layout.addWidget(self.window_height_spinbox)

        ui_layout.addRow("Window Size:", size_layout)

        # Always on top
        self.always_on_top_checkbox = QCheckBox("Always on Top")
        ui_layout.addRow(self.always_on_top_checkbox)

        layout.addWidget(ui_group)

        # Buttons
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self._save_and_close)
        button_layout.addWidget(self.ok_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.clicked.connect(self._reset_to_defaults)
        button_layout.addWidget(self.reset_button)

        # Set OK as default
        self.ok_button.setDefault(True)

    def _get_available_fields(self) -> list[str]:
        """Get list of available fields from current note type."""
        try:
            fields = self.anki_integration.get_available_fields()
            if not fields:
                # Fallback to common field names
                return ["Front", "Back", "Expression", "Meaning", "Reading", "Audio", "Sound"]
            return fields
        except Exception:
            # Fallback to common field names
            return ["Front", "Back", "Expression", "Meaning", "Reading", "Audio", "Sound"]

    def _load_current_config(self) -> None:
        """Load current configuration into the UI."""
        # Field mapping
        self._set_combo_text(self.prompt_field_combo, self.config.field_mapping.prompt)
        self._set_combo_text(self.target_field_combo, self.config.field_mapping.target)
        self._set_combo_text(self.audio_field_combo, self.config.field_mapping.audio)

        # Behavior
        if self.config.behavior.reset_mode == "sentence":
            self.reset_sentence_radio.setChecked(True)
        else:
            self.reset_word_radio.setChecked(True)

        if self.config.behavior.input_mode == "progressive":
            self.progressive_radio.setChecked(True)
        else:
            self.accompanying_radio.setChecked(True)

        self.auto_focus_checkbox.setChecked(self.config.behavior.auto_focus)
        self.show_completion_popup_checkbox.setChecked(self.config.behavior.show_completion_popup)
        self.sound_enabled_checkbox.setChecked(self.config.behavior.sound_enabled)
        self.auto_play_audio_checkbox.setChecked(self.config.behavior.auto_play_audio)
        self.show_timer_checkbox.setChecked(self.config.behavior.show_timer)
        self.show_errors_checkbox.setChecked(self.config.behavior.show_errors)

        # UI
        if self.config.ui.theme == "light":
            self.light_theme_radio.setChecked(True)
        else:
            self.dark_theme_radio.setChecked(True)

        self.window_width_spinbox.setValue(self.config.ui.window_width)
        self.window_height_spinbox.setValue(self.config.ui.window_height)
        self.always_on_top_checkbox.setChecked(self.config.ui.always_on_top)

    def _set_combo_text(self, combo: QComboBox, text: str) -> None:
        """Set combobox text, adding it if not present."""
        index = combo.findText(text)
        if index >= 0:
            combo.setCurrentIndex(index)
        else:
            combo.addItem(text)
            combo.setCurrentText(text)

    def _save_config(self) -> bool:
        """Save configuration from UI."""
        try:
            # Validate field mappings
            prompt_field = self.prompt_field_combo.currentText().strip()
            target_field = self.target_field_combo.currentText().strip()
            audio_field = self.audio_field_combo.currentText().strip()

            if not prompt_field:
                QMessageBox.warning(self, "Invalid Configuration",
                                   "Prompt field cannot be empty.")
                return False

            if not target_field:
                QMessageBox.warning(self, "Invalid Configuration",
                                   "Target field cannot be empty.")
                return False

            # Create new config object
            new_config = Config()

            # Field mapping
            new_config.field_mapping.prompt = prompt_field
            new_config.field_mapping.target = target_field
            new_config.field_mapping.audio = audio_field

            # Behavior
            new_config.behavior.reset_mode = (
                "sentence" if self.reset_sentence_radio.isChecked() else "word"
            )
            new_config.behavior.input_mode = (
                "progressive" if self.progressive_radio.isChecked() else "accompanying"
            )
            new_config.behavior.auto_focus = self.auto_focus_checkbox.isChecked()
            new_config.behavior.show_completion_popup = self.show_completion_popup_checkbox.isChecked()
            new_config.behavior.sound_enabled = self.sound_enabled_checkbox.isChecked()
            new_config.behavior.auto_play_audio = self.auto_play_audio_checkbox.isChecked()
            new_config.behavior.show_timer = self.show_timer_checkbox.isChecked()
            new_config.behavior.show_errors = self.show_errors_checkbox.isChecked()

            # UI
            new_config.ui.theme = "light" if self.light_theme_radio.isChecked() else "dark"
            new_config.ui.window_width = self.window_width_spinbox.value()
            new_config.ui.window_height = self.window_height_spinbox.value()
            new_config.ui.always_on_top = self.always_on_top_checkbox.isChecked()

            # Save configuration
            save_config(new_config)
            self.config = new_config
            return True

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {e}")
            return False

    def _save_and_close(self) -> None:
        """Save configuration and close dialog."""
        if self._save_config():
            self.accept()

    def _reset_to_defaults(self) -> None:
        """Reset configuration to defaults."""
        reply = QMessageBox.question(
            self, "Reset to Defaults",
            "Are you sure you want to reset all settings to their default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.config = Config()
            self._load_current_config()
            QMessageBox.information(self, "Reset Complete",
                                   "Settings have been reset to defaults. Click OK to save them.")

    def get_config(self) -> Config:
        """Get the current configuration."""
        return self.config