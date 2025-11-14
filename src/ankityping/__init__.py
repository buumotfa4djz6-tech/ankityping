"""Main entry point for the ankityping Anki plugin."""

from __future__ import annotations

try:
    from aqt import QAction, mw
    from aqt.qt import QKeySequence, QMenu
except ImportError:
    # Fallback for testing outside of Anki
    mw = None
    QAction = None
    QMenu = None
    QKeySequence = None

from .ui.components.settings_panel import SettingsPanel
from .ui.typing_dialog import TypingDialog


def open_typing_practice() -> None:
    """Open the typing practice window."""
    if mw is None:
        print("AnkiTyping: Not running in Anki context")
        return

    try:
        print("AnkiTyping: Attempting to open typing practice dialog...")
        from .anki_integration import AnkiIntegration
        from .config import get_config
        from .utils import get_deck_manager

        config = get_config()
        anki_integration = AnkiIntegration(config)
        deck_manager = get_deck_manager(config)

        # Check if reviewer is active
        if anki_integration.is_reviewer_active():
            print("AnkiTyping: Reviewer is active, opening dialog with current card...")
        else:
            print(
                "AnkiTyping: Reviewer is not active, attempting to load last-used deck..."
            )

            # Try to get the last used deck
            last_deck = deck_manager.get_last_used_deck()
            if last_deck:
                print(f"AnkiTyping: Found last-used deck: {last_deck.deck_name}")
                # Switch to the last-used deck
                try:
                    # Anki deck selection
                    if mw.col is not None:
                        mw.col.decks.select(last_deck.deck_id)
                    print(f"AnkiTyping: Switched to deck: {last_deck.deck_name}")
                except Exception as deck_error:
                    print(f"AnkiTyping: Failed to switch to deck: {deck_error}")
            else:
                print("AnkiTyping: No last-used deck found, using current deck")

        dialog = TypingDialog(mw)
        dialog.show()
        print("AnkiTyping: Dialog opened successfully")
    except Exception as e:
        print(f"AnkiTyping: Error opening dialog: {e}")
        # Show error message
        from aqt.qt import QMessageBox

        QMessageBox.critical(
            mw, "AnkiTyping Error", f"Failed to open typing practice: {e}"
        )


def open_settings() -> None:
    """Open the settings dialog."""
    if mw is None:
        print("AnkiTyping: Not running in Anki context")
        return

    try:
        from .config import get_config

        config = get_config()
        dialog = SettingsPanel(config, mw)
        dialog.exec()
    except Exception as e:
        # Show error message
        from aqt.qt import QMessageBox

        QMessageBox.critical(
            mw, "AnkiTyping Settings Error", f"Failed to open settings: {e}"
        )


def add_menu_items() -> None:
    """Add menu items to Anki's Tools menu."""
    if mw is None:
        return

    try:
        # Create menu actions
        typing_action = QAction("Typing Practice", mw)
        if QKeySequence:
            typing_action.setShortcut(QKeySequence("Ctrl+Shift+T"))
        typing_action.triggered.connect(open_typing_practice)

        settings_action = QAction("Typing Practice Settings", mw)
        settings_action.triggered.connect(open_settings)

        # Add to Tools menu
        mw.form.menuTools.addAction(typing_action)
        mw.form.menuTools.addAction(settings_action)

        print("AnkiTyping: Menu items added successfully")

    except Exception as e:
        print(f"AnkiTyping: Failed to add menu items: {e}")


def setup_initial_config() -> None:
    """Setup initial configuration if needed."""
    if mw is None:
        return

    try:
        from .config import get_config

        config = get_config()
        print(f"AnkiTyping: Configuration loaded - Theme: {config.ui.theme}")
    except Exception as e:
        print(f"AnkiTyping: Failed to setup initial config: {e}")


def setup_global_shortcuts() -> None:
    """Setup global keyboard shortcuts."""
    if not mw:
        return

    try:
        from aqt.qt import QKeySequence, QShortcut

        # Ctrl+T to open typing practice
        typing_shortcut = QShortcut(QKeySequence("Ctrl+T"), mw)
        typing_shortcut.activated.connect(open_typing_practice)
        print("AnkiTyping: Ctrl+T shortcut registered")

    except Exception as e:
        print(f"AnkiTyping: Failed to setup global shortcuts: {e}")


# Plugin initialization
try:
    if mw:
        # Setup initial configuration
        setup_initial_config()

        # Add menu items
        add_menu_items()

        # Setup global shortcuts
        setup_global_shortcuts()

        print("AnkiTyping: Plugin loaded successfully")

except Exception as e:
    print(f"AnkiTyping: Failed to load plugin: {e}")


# For testing purposes
def _test_dialog() -> None:
    """Test function for dialog development."""
    try:
        import sys

        from aqt.qt import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        dialog = TypingDialog()
        dialog.show()
        app.exec()

    except Exception as e:
        print(f"AnkiTyping: Dialog test failed: {e}")
