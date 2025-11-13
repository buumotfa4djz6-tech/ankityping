"""Configuration management for ankityping plugin."""

from __future__ import annotations

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import json

try:
    from aqt import mw
except ImportError:
    mw = None


@dataclass
class UIConfig:
    """UI configuration settings."""
    theme: str = "dark"  # "light" or "dark"
    window_width: int = 600
    window_height: int = 400
    always_on_top: bool = False


@dataclass
class BehaviorConfig:
    """Behavior configuration settings."""
    reset_mode: str = "sentence"  # "sentence" or "word"
    sound_enabled: bool = True
    auto_play_audio: bool = True
    show_timer: bool = True
    show_errors: bool = True
    input_mode: str = "progressive"  # "progressive" or "accompanying"
    auto_focus: bool = True
    show_completion_popup: bool = False


@dataclass
class FieldMapping:
    """Field mapping configuration."""
    prompt: str = "Front"
    target: str = "Back"
    audio: str = "Audio"  # optional, for dictation


@dataclass
class Config:
    """Main configuration class."""
    ui: UIConfig = field(default_factory=UIConfig)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)
    field_mapping: FieldMapping = field(default_factory=FieldMapping)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Config:
        """Create Config from dictionary."""
        config = cls()

        if "ui" in data:
            ui_data = data["ui"]
            config.ui.theme = ui_data.get("theme", config.ui.theme)
            config.ui.window_width = ui_data.get("window_width", config.ui.window_width)
            config.ui.window_height = ui_data.get("window_height", config.ui.window_height)
            config.ui.always_on_top = ui_data.get("always_on_top", config.ui.always_on_top)

        if "behavior" in data:
            behavior_data = data["behavior"]
            config.behavior.reset_mode = behavior_data.get("resetMode", config.behavior.reset_mode)
            config.behavior.sound_enabled = behavior_data.get("soundEnabled", config.behavior.sound_enabled)
            config.behavior.auto_play_audio = behavior_data.get("autoPlayAudio", config.behavior.auto_play_audio)
            config.behavior.show_timer = behavior_data.get("showTimer", config.behavior.show_timer)
            config.behavior.show_errors = behavior_data.get("showErrors", config.behavior.show_errors)
            config.behavior.input_mode = behavior_data.get("inputMode", config.behavior.input_mode)
            config.behavior.auto_focus = behavior_data.get("autoFocus", config.behavior.auto_focus)
            config.behavior.show_completion_popup = behavior_data.get("showCompletionPopup", config.behavior.show_completion_popup)

        if "fieldMapping" in data:
            field_data = data["fieldMapping"]
            config.field_mapping.prompt = field_data.get("prompt", config.field_mapping.prompt)
            config.field_mapping.target = field_data.get("target", config.field_mapping.target)
            config.field_mapping.audio = field_data.get("audio", config.field_mapping.audio)

        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convert Config to dictionary."""
        return {
            "ui": {
                "theme": self.ui.theme,
                "window_width": self.ui.window_width,
                "window_height": self.ui.window_height,
                "always_on_top": self.ui.always_on_top,
            },
            "behavior": {
                "resetMode": self.behavior.reset_mode,
                "soundEnabled": self.behavior.sound_enabled,
                "autoPlayAudio": self.behavior.auto_play_audio,
                "showTimer": self.behavior.show_timer,
                "showErrors": self.behavior.show_errors,
                "inputMode": self.behavior.input_mode,
                "autoFocus": self.behavior.auto_focus,
                "showCompletionPopup": self.behavior.show_completion_popup,
            },
            "fieldMapping": {
                "prompt": self.field_mapping.prompt,
                "target": self.field_mapping.target,
                "audio": self.field_mapping.audio,
            },
        }


class PluginConfigManager:
    """Manages plugin configuration using Anki's addon config system."""

    def __init__(self, addon_name: str = "ankityping"):
        self.addon_name = addon_name
        self._config: Optional[Config] = None

    def load_config(self) -> Config:
        """Load configuration from Anki's addon config."""
        if self._config is None:
            try:
                if mw and hasattr(mw, 'addonManager'):
                    addon_manager = mw.addonManager
                    config_dict = addon_manager.getConfig(self.addon_name) or {}
                    self._config = Config.from_dict(config_dict)
                else:
                    # Fallback for testing or outside Anki
                    self._config = Config()
            except Exception as e:
                print(f"Failed to load config, using defaults: {e}")
                self._config = Config()
        return self._config

    def save_config(self, config: Config) -> None:
        """Save configuration to Anki's addon config."""
        try:
            if mw and hasattr(mw, 'addonManager'):
                addon_manager = mw.addonManager
                config_dict = config.to_dict()
                addon_manager.writeConfig(self.addon_name, config_dict)
                self._config = config
            else:
                # Fallback: could save to file if needed
                print("Warning: Cannot save config outside of Anki")
        except Exception as e:
            print(f"Failed to save config: {e}")

    def get_config(self) -> Config:
        """Get current configuration."""
        return self.load_config()

    def update_config(self, **kwargs) -> None:
        """Update configuration with new values."""
        config = self.load_config()

        # Update UI settings
        if "ui" in kwargs:
            for key, value in kwargs["ui"].items():
                if hasattr(config.ui, key):
                    setattr(config.ui, key, value)

        # Update behavior settings
        if "behavior" in kwargs:
            for key, value in kwargs["behavior"].items():
                if hasattr(config.behavior, key):
                    setattr(config.behavior, key, value)

        # Update field mapping
        if "field_mapping" in kwargs:
            for key, value in kwargs["field_mapping"].items():
                if hasattr(config.field_mapping, key):
                    setattr(config.field_mapping, key, value)

        self.save_config(config)

    def reset_to_defaults(self) -> None:
        """Reset configuration to default values."""
        self._config = Config()
        self.save_config(self._config)


# Global config manager instance
config_manager = PluginConfigManager()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config_manager.get_config()


def save_config(config: Config) -> None:
    """Save the global configuration instance."""
    config_manager.save_config(config)