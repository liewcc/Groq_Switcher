# Groq Account Switcher
A terminal UI for managing and switching between multiple Groq API accounts.

## Project Overview
The Groq Account Switcher is a Python-based terminal UI application built with [Textual](https://textual.textualize.io/). It is designed to help users manage and switch between multiple Groq API accounts, making it easier to rotate free-tier keys.

## Key Features
* Displays available LLM / STT / TTS models from the active Groq account
* Shows per-model RPD and TPM quota remaining
* Manages multiple named accounts stored in `accounts.json`
* One-key account switching: updates the API key across four config files simultaneously
* Compact **copy bar** at the bottom for copying selected cell values
* Accounts table with Name, masked Key, Last used, and Status columns
* Validate API key before saving
* Add / Edit / Delete / Rename accounts via modal dialogs

## Key Bindings
The following key bindings are available:
* `Ctrl+C` — copy selected value to clipboard
* `q` — quit
* `r` — refresh quota for selected model
* `Enter` on accounts table — switch to that account

## Setup and Requirements
To set up the Groq Account Switcher, run the following batch files:
```bash
setup.bat   # creates venv, installs deps
run.bat     # activates venv and launches the TUI
```
The application requires:
* Python 3.11+
* `textual>=0.80.0`
* `httpx`
* `python-dotenv`

## File Layout
The project has the following file layout:
```
Groq_Switcher/
  switcher/
    app.py       # Textual TUI application
    config.py    # account store + config-file updater
  accounts.json  # persisted accounts (gitignored if sensitive)
  main.py        # entry point
  run.bat
  setup.bat
```
