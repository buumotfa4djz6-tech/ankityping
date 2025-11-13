"""Main entry point for the ankityping Anki plugin."""

from __future__ import annotations

try:
    from aqt import mw, QAction
    from aqt.qt import QMenu, QKeySequence
except ImportError:
    # Fallback for testing outside of Anki
    mw = None
    QAction = None
    QMenu = None
    QKeySequence = None

from .ui.typing_dialog import TypingDialog
from .ui.config_dialog import ConfigDialog


def open_typing_practice() -> None:
    """Open the typing practice window."""
    if mw is None:
        print("AnkiTyping: Not running in Anki context")
        return

    try:
        print("AnkiTyping: Attempting to open typing practice dialog...")
        from .anki_integration import AnkiIntegration
        from .config import get_config

        config = get_config()
        anki_integration = AnkiIntegration(config)

        # Test reviewer status
        if anki_integration.is_reviewer_active():
            print("AnkiTyping: Reviewer is active, opening dialog...")
        else:
            print("AnkiTyping: Reviewer is not active, will show warning...")

        dialog = TypingDialog(mw)
        dialog.show()
        print("AnkiTyping: Dialog opened successfully")
    except Exception as e:
        print(f"AnkiTyping: Error opening dialog: {e}")
        # Show error message
        from aqt.qt import QMessageBox
        QMessageBox.critical(
            mw,
            "AnkiTyping Error",
            f"Failed to open typing practice: {e}"
        )


def open_settings() -> None:
    """Open the settings dialog."""
    if mw is None:
        print("AnkiTyping: Not running in Anki context")
        return

    try:
        dialog = ConfigDialog(mw)
        dialog.exec()
    except Exception as e:
        # Show error message
        from aqt.qt import QMessageBox
        QMessageBox.critical(
            mw,
            "AnkiTyping Settings Error",
            f"Failed to open settings: {e}"
        )


def add_menu_items() -> None:
    """Add menu items to Anki's Tools menu."""
    if mw is None:
        return

    try:
        # Create menu actions
        typing_action = QAction("Typing Practice", mw)
        if QKeySequence:
            typing_action.setShortcut(QKeySequence("Ctrl+T"))
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
        from aqt.qt import QShortcut, QKeySequence

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
        from aqt.qt import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        dialog = TypingDialog()
        dialog.show()
        app.exec()

    except Exception as e:
        print(f"AnkiTyping: Dialog test failed: {e}")