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
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

import httpx

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ACCOUNTS_FILE = Path(__file__).parent.parent / "accounts.json"

TARGET_DOTENV = Path(r"D:\AI\groq-mcp-server\.env")

TARGET_JSON_FILES: List[dict[str, Any]] = [
    {
        "path": Path(r"C:\Users\cclie\.gemini\antigravity-cli\mcp.json"),
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
        Structure ``{"accounts": [...], "active": ...}``. Returns a default
        structure when the file does not exist.
    """
    try:
        with ACCOUNTS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"accounts": [], "active": None}
    except json.JSONDecodeError:
        # Corrupt file – treat as empty
        return {"accounts": [], "active": None}


def save_accounts(data: dict) -> None:
    """Persist *data* back to *accounts.json*.

    Parameters
    ----------
    data: dict
        The full accounts dictionary.
    """
    ACCOUNTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with ACCOUNTS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ---------------------------------------------------------------------------
# Active-key helpers
# ---------------------------------------------------------------------------


def get_current_key() -> str:
    """Return the GROQ_API_KEY currently written in the ``.env`` file.

    Returns an empty string if the variable is not present or the file does not
    exist.
    """
    if not TARGET_DOTENV.is_file():
        return ""
    pattern = re.compile(r"^GROQ_API_KEY\s*=\s*(.+)$")
    try:
        with TARGET_DOTENV.open("r", encoding="utf-8") as f:
            for line in f:
                m = pattern.match(line.strip())
                if m:
                    return m.group(1).strip()
    except Exception:
        pass
    return ""


def switch_account(name: str, key: str) -> List[str]:
    """Activate *key* for the account named *name* across all config files.

    Returns a list of file paths that were skipped because they did not exist.
    """
    skipped: List[str] = []
    # Update .env
    _update_dotenv(TARGET_DOTENV, key)

    # Update JSON files
    for entry in TARGET_JSON_FILES:
        try:
            _update_json_key(entry, key)
        except FileNotFoundError:
            skipped.append(str(entry["path"]))
        except KeyError:
            skipped.append(str(entry["path"]))

    # Update accounts.json
    data = load_accounts()
    data["active"] = name
    now_iso = datetime.now(timezone.utc).isoformat()
    for acc in data.get("accounts", []):
        if acc.get("name") == name:
            acc["last_used"] = now_iso
            break
    else:
        # Account not present – add it
        data.setdefault("accounts", []).append({
            "name": name,
            "key": key,
            "last_used": now_iso,
            "model_quota": {},
        })
    save_accounts(data)
    return skipped


def mask_key(key: str) -> str:
    """Mask a Groq API key, showing only the last four characters.
    """
    if len(key) < 8:
        return key
    return f"gsk_****{key[-4:]}"


def ping_model_quota(key: str, model_id: str) -> dict | None:
    """Ping Groq API to retrieve rate‑limit headers for *model_id*.
    """
    url = "https://api.groq.com/openai/v1/models"
    headers = {"Authorization": f"Bearer {key}"}
    try:
        response = httpx.get(url, headers=headers, timeout=10.0)
        if response.status_code != 200:
            return None
        def _int(name: str) -> int | None:
            v = response.headers.get(name)
            return int(v) if v and v.isdigit() else None
        rpd_limit = _int("x-ratelimit-limit-requests")
        rpd_remaining = _int("x-ratelimit-remaining-requests")
        tpm_limit = _int("x-ratelimit-limit-tokens")
        tpm_remaining = _int("x-ratelimit-remaining-tokens")
        if None in (rpd_limit, rpd_remaining, tpm_limit, tpm_remaining):
            return None
        return {
            "rpd_limit": rpd_limit,
            "rpd_remaining": rpd_remaining,
            "tpm_limit": tpm_limit,
            "tpm_remaining": tpm_remaining,
            "model_id": model_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception:
        return None


def update_account_quota(account_name: str, model_id: str, quota: dict) -> None:
    """Store *quota* information for *model_id* under *account_name*.
    """
    data = load_accounts()
    for acc in data.get("accounts", []):
        if acc.get("name") == account_name:
            acc.setdefault("model_quota", {})[model_id] = quota
            break
    save_accounts(data)


def get_active_account_name() -> str | None:
    """Return the name of the account whose key matches the current .env key.
    """
    cur = get_current_key()
    if not cur:
        return None
    data = load_accounts()
    for acc in data.get("accounts", []):
        if acc.get("key") == cur:
            return acc.get("name")
    return None

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _update_dotenv(path: Path, key: str) -> None:
    """Rewrite the ``GROQ_API_KEY`` line inside a ``.env`` file.
    """
    lines: List[str] = []
    pattern = re.compile(r"^GROQ_API_KEY\s*=")
    if path.is_file():
        with path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
    updated = False
    for i, line in enumerate(lines):
        if pattern.match(line):
            lines[i] = f"GROQ_API_KEY={key}\n"
            updated = True
            break
    if not updated:
        lines.append(f"GROQ_API_KEY={key}\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.writelines(lines)


def _update_json_key(entry: dict[str, Any], key: str) -> None:
    """Navigate *entry[\"key_path\"]* inside the JSON file and set *key*.
    """
    json_path: Path = entry["path"]
    if not json_path.is_file():
        raise FileNotFoundError(json_path)
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    ptr = data
    for segment in entry["key_path"][:-1]:
        if segment not in ptr or not isinstance(ptr[segment], dict):
            raise KeyError(f"Missing path segment {segment} in {json_path}")
        ptr = ptr[segment]
    leaf = entry["key_path"][-1]
    ptr[leaf] = key
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

