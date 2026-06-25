"""Entry point for Groq Account Switcher TUI."""

from switcher.app import GroqSwitcherApp


def main() -> None:
    """Launch the Groq Switcher Textual application."""
    GroqSwitcherApp().run()


if __name__ == "__main__":
    main()
