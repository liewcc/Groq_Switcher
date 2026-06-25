"""
Configuration helpers for the Groq Account Switcher.

Manages reading/writing GROQ_API_KEY in four target config files:

1. D:\\AI\\groq-mcp-server\\.env
2. C:\\Users\\cclie\\.gemini\\antigravity-cli\\mcp.json
       └─ mcpServers.groq-mcp.env.GROQ_API_KEY
3. C:\\Users\\cclie\\.gemini\\antigravity\\mcp_config.json
       └─ mcpServers.groq-mcp.env.GROQ_API_KEY
4. C:\\Users\\cclie\\AppData\\Roaming\\Claude\\claude_desktop_config.json
       └─ mcpServers.Groq.env.GROQ_API_KEY
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ACCOUNTS_FILE = Path(__file__).parent.parent / "accounts.json"

TARGET_DOTENV = Path(r"D:\AI\groq-mcp-server\.env")

TARGET_JSON_FILES: list[dict[str, Any]] = [
    {
        "path": Path(r"C:\Users\cclie\.gemini\antigravity-cli\mcp.json"),
        # Nested key path inside the JSON document
        "key_path": ["mcpServers", "groq-mcp", "env", "GROQ_API_KEY"],
    },
    {
        "path": Path(r"C:\Users\cclie\.gemini\antigravity\mcp_config.json"),
        "key_path": ["mcpServers", "groq-mcp", "env", "GROQ_API_KEY"],
    },
    {
        "path": Path(
            r"C:\Users\cclie\AppData\Roaming\Claude\claude_desktop_config.json"
        ),
        "key_path": ["mcpServers", "Groq", "env", "GROQ_API_KEY"],
    },
]


# ---------------------------------------------------------------------------
# Account store helpers
# ---------------------------------------------------------------------------


def load_accounts() -> dict:
    """Load the accounts list from *accounts.json*.

    Returns
    -------
    dict
        A dictionary with the following structure::

            {
                "accounts": [
                    {"name": "Account 1", "key": "gsk_..."},
                    ...
                ],
                "active": "Account 1"
            }

    Raises
    ------
    FileNotFoundError
        If ``accounts.json`` does not exist next to the project root.
    json.JSONDecodeError
        If the file is not valid JSON.
    """
    # TODO: implement
    raise NotImplementedError("load_accounts() is not yet implemented")


def save_accounts(data: dict) -> None:
    """Persist *data* back to *accounts.json*.

    Parameters
    ----------
    data:
        The full accounts dictionary (same shape as returned by
        :func:`load_accounts`).

    Notes
    -----
    * Writes with ``indent=2`` for human-readable formatting.
    * Creates the file if it does not already exist.
    """
    # TODO: implement
    raise NotImplementedError("save_accounts() is not yet implemented")


# ---------------------------------------------------------------------------
# Active-key helpers
# ---------------------------------------------------------------------------


def get_current_key() -> str:
    """Return the GROQ_API_KEY currently written in the ``.env`` file.

    Returns
    -------
    str
        The raw key string (e.g. ``"gsk_..."``), or an empty string if the
        variable is not present in the file.

    Notes
    -----
    Uses :mod:`python-dotenv` / manual parsing to read
    :data:`TARGET_DOTENV` without modifying the process environment.
    """
    # TODO: implement
    raise NotImplementedError("get_current_key() is not yet implemented")


def switch_account(name: str, key: str) -> None:
    """Activate *key* for the account named *name* across all config files.

    This function performs **four** writes:

    1. Updates ``GROQ_API_KEY=<key>`` in :data:`TARGET_DOTENV`.
    2. Sets ``mcpServers["groq-mcp"]["env"]["GROQ_API_KEY"]`` in
       ``antigravity-cli/mcp.json``.
    3. Sets the same path in ``antigravity/mcp_config.json``.
    4. Sets ``mcpServers["Groq"]["env"]["GROQ_API_KEY"]`` in
       ``claude_desktop_config.json``.

    After writing all files it calls :func:`save_accounts` to update
    ``accounts.json`` so ``"active"`` reflects the newly selected account.

    Parameters
    ----------
    name:
        Human-readable label of the account being activated (stored in
        ``accounts.json`` as ``"active"``).
    key:
        The raw Groq API key string (e.g. ``"gsk_..."``).

    Raises
    ------
    FileNotFoundError
        If any of the four target config files does not exist.
    KeyError
        If the expected JSON key-path is absent in a JSON config file.
    """
    # TODO: implement
    #
    # Suggested implementation steps:
    #   1. _update_dotenv(TARGET_DOTENV, key)
    #   2. for entry in TARGET_JSON_FILES: _update_json_key(entry, key)
    #   3. data = load_accounts()
    #      data["active"] = name
    #      save_accounts(data)
    raise NotImplementedError("switch_account() is not yet implemented")


# ---------------------------------------------------------------------------
# Private helpers (to be implemented)
# ---------------------------------------------------------------------------


def _update_dotenv(path: Path, key: str) -> None:
    """Rewrite the ``GROQ_API_KEY`` line inside a ``.env`` file.

    Parameters
    ----------
    path:
        Absolute path to the ``.env`` file.
    key:
        New API key value.
    """
    # TODO: Read the file line-by-line.
    #       Replace any line matching r'^GROQ_API_KEY\s*=.*' with
    #       f'GROQ_API_KEY={key}'.
    #       If no such line exists, append it.
    raise NotImplementedError("_update_dotenv() is not yet implemented")


def _update_json_key(entry: dict[str, Any], key: str) -> None:
    """Navigate *entry["key_path"]* inside the JSON file and set *key*.

    Parameters
    ----------
    entry:
        A dict with keys ``"path"`` (Path) and ``"key_path"`` (list[str]).
    key:
        New API key value.
    """
    # TODO: Load JSON → traverse key_path → set leaf → write back with indent=2.
    raise NotImplementedError("_update_json_key() is not yet implemented")
