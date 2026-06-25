"""Textual TUI application for Groq account switching."""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static


class GroqSwitcherApp(App):
    """Main Textual application for managing multiple Groq API accounts."""

    TITLE = "Groq Account Switcher"
    SUB_TITLE = "Switch between Groq API keys with ease"

    CSS = """
    Screen {
        align: center middle;
    }

    #placeholder {
        width: auto;
        height: auto;
        padding: 2 4;
        border: round $primary;
        content-align: center middle;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        """Build the initial UI layout."""
        yield Header()
        yield Static(
            "🔑  Groq Account Switcher\n\n"
            "Account list will appear here.\n"
            "Select an account to activate its API key across all config files.",
            id="placeholder",
        )
        yield Footer()
