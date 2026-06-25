# Groq Account Switcher

A Windows terminal UI (TUI) built with [Textual](https://textual.textualize.io/) for managing multiple Groq API accounts and switching between them instantly. Designed primarily to streamline free-tier key rotation and quota management across local development environments.

## Table of Contents

- [Free-Tier Rotation Use Case](#free-tier-rotation-use-case)
- [Features](#features)
  - [Accounts Table](#accounts-table)
  - [Models Table](#models-table)
  - [Copy Bar](#copy-bar)
  - [Key Bindings](#key-bindings)
- [MCP Server Compatibility](#mcp-server-compatibility)
- [Setup](#setup)
- [Project Structure](#project-structure)
- [Important Notes](#important-notes)

---

## Free-Tier Rotation Use Case

Groq's free tier enforces rate limits (Requests Per Day / Tokens Per Minute) per API key. This tool automates rotating between multiple accounts, allowing developers to distribute API calls across different keys. By instantly updating the active `GROQ_API_KEY` across your local configuration files, you can maximise available quota without manually editing environment variables or config files.

---

## Features

### Accounts Table

- **CRUD Operations:** Add, edit, delete, and rename accounts via modal dialogs.
- **Live Validation:** API keys are validated against Groq's endpoints before saving.
- **Metadata Display:** Shows account name, masked key (`gsk_****xxxx`), last used timestamp, and active/inactive status.
- **Instant Switching:** Press `Enter` on a selected row to activate the account.

### Models Table

- **Type Filtering:** Filter models by category using the toolbar dropdown — `LLM` / `STT` / `TTS`.
- **Quota Tracking:** Displays Model ID, Owner, Context window, RPD remaining, and TPM remaining.
- **Manual Refresh:** Press `r` to refresh quota for the selected model, or use the **Refresh All** button to scan all models in the current view.

### Copy Bar

- The value of the currently focused cell is always shown in a dedicated copy bar at the bottom of the terminal.
- Press `Ctrl+C` to copy the displayed value to your clipboard.

### Key Bindings

| Key | Action |
|-----|--------|
| `Enter` (accounts table) | Switch to the selected account |
| `r` | Refresh quota for the selected model |
| `Ctrl+C` | Copy focused value to clipboard |
| `q` | Quit the application |

---

## MCP Server Compatibility

This switcher is designed to work with Model Context Protocol (MCP) servers. Configure the `.env` file path in `config.py` to match your preferred server:

- **[Official Groq MCP Server](https://github.com/groq/groq-mcp-server)** — The standard, officially maintained MCP server by Groq.
- **[groq-agentic-mcp](https://github.com/liewcc/groq-agentic-mcp)** — A community fork that extends the official server with agentic tools and enhanced quota tracking.

---

## Setup

### Requirements

- Python 3.11+
- `textual >= 0.80.0`
- `httpx >= 0.27.0`
- `python-dotenv`

### Installation & Launch

```bat
setup.bat   :: Creates .venv, installs dependencies, initialises accounts.json
run.bat     :: Activates the virtual environment and launches the TUI
```

---

## Project Structure

```
Groq_Switcher/
  switcher/
    app.py       # Textual TUI application
    config.py    # Account store + config-file updater
  accounts.json  # Persisted account data (add to .gitignore if sensitive)
  main.py        # Entry point
  setup.bat
  run.bat
```

---

## Important Notes

- **Model selection is display-only.** Selecting a model in the models table does **not** change the active model in your chat. To use a specific model, explicitly instruct your AI assistant (e.g. *"use llama-3.3-70b"*).
- **Config files updated on switch:** Switching accounts writes the new `GROQ_API_KEY` to four locations simultaneously:
  1. `.env` file for your MCP server
  2. `~/.gemini/antigravity-cli/mcp.json`
  3. `~/.gemini/antigravity/mcp_config.json`
  4. `~/AppData/Roaming/Claude/claude_desktop_config.json`
- Adjust the paths in `config.py` if your local setup differs.
