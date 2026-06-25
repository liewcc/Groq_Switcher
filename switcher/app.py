"""Textual TUI application for Groq account switching."""

from __future__ import annotations

import subprocess
import threading
from datetime import datetime
from typing import Any

import httpx
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
)

from switcher.config import (
    get_active_account_name,
    get_current_key,
    load_accounts,
    mask_key,
    ping_model_quota,
    save_accounts,
    switch_account,
    update_account_quota,
)

GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"

STT_META: dict[str, dict] = {
    "whisper-large-v3": {"language": "Multilingual", "cost": "$0.111/hr", "wer": "10.3%"},
    "whisper-large-v3-turbo": {"language": "Multilingual", "cost": "$0.04/hr", "wer": "12%"},
    "distil-whisper-large-v3-en": {"language": "English", "cost": "$0.02/hr", "wer": "13%"},
}

MODEL_TYPE_OPTIONS = [("LLM", "llm"), ("STT", "stt"), ("TTS", "tts")]


def _fetch_models(key: str) -> list[dict]:
    try:
        r = httpx.get(GROQ_MODELS_URL, headers={"Authorization": f"Bearer {key}"}, timeout=10)
        if r.status_code == 200:
            return r.json().get("data", [])
    except Exception:
        pass
    return []


def _filter_models(models: list[dict], model_type: str) -> list[dict]:
    if model_type == "stt":
        return [m for m in models if "whisper" in m["id"]]
    if model_type == "tts":
        return [m for m in models if any(x in m["id"] for x in ("tts", "playai", "orpheus"))]
    # LLM: everything else
    return [
        m for m in models
        if not any(x in m["id"] for x in ("whisper", "tts", "playai", "orpheus", "guard", "safeguard"))
    ]


def _fmt_context(n: int | None) -> str:
    if n is None:
        return "—"
    return f"{n // 1000}K" if n >= 1000 else str(n)


def _fmt_dt(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso


# ---------------------------------------------------------------------------
# Modal screens
# ---------------------------------------------------------------------------

class AddEditModal(ModalScreen):
    """Modal for adding or editing an account."""

    DEFAULT_CSS = """
    AddEditModal > Vertical {
        width: 60;
        height: auto;
        border: round $primary;
        padding: 1 2;
        background: $surface;
    }
    AddEditModal Label { margin-bottom: 1; }
    AddEditModal Input { margin-bottom: 1; }
    AddEditModal #validate-msg { margin-bottom: 1; color: $text-muted; }
    AddEditModal Horizontal { height: auto; }
    AddEditModal Button { margin-right: 1; }
    """

    def __init__(self, name: str = "", key: str = "", edit_mode: bool = False) -> None:
        super().__init__()
        self._init_name = name
        self._init_key = key
        self._edit_mode = edit_mode
        self._valid: bool | None = None

    def compose(self) -> ComposeResult:
        title = "Edit Account" if self._edit_mode else "Add Account"
        with Vertical():
            yield Label(title)
            yield Label("Name")
            yield Input(value=self._init_name, placeholder="Account name", id="inp-name")
            yield Label("API Key")
            yield Input(value=self._init_key, placeholder="gsk_...", id="inp-key")
            yield Static("", id="validate-msg")
            with Horizontal():
                yield Button("Validate", id="btn-validate", variant="default")
                yield Button("OK", id="btn-ok", variant="primary")
                yield Button("Cancel", id="btn-cancel", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-validate":
            key = self.query_one("#inp-key", Input).value.strip()
            msg = self.query_one("#validate-msg", Static)
            msg.update("Validating...")
            result = ping_model_quota(key, "llama-3.1-8b-instant")
            if result:
                msg.update("✓ Valid")
                self._valid = True
            else:
                msg.update("✗ Invalid key or network error")
                self._valid = False
        elif event.button.id == "btn-ok":
            name = self.query_one("#inp-name", Input).value.strip()
            key = self.query_one("#inp-key", Input).value.strip()
            if name and key:
                self.dismiss({"name": name, "key": key})
            else:
                self.query_one("#validate-msg", Static).update("Name and key are required.")


class DeleteModal(ModalScreen):
    """Confirmation modal for account deletion."""

    DEFAULT_CSS = """
    DeleteModal > Vertical {
        width: 50;
        height: auto;
        border: round $error;
        padding: 1 2;
        background: $surface;
    }
    DeleteModal Horizontal { height: auto; margin-top: 1; }
    DeleteModal Button { margin-right: 1; }
    """

    def __init__(self, account_name: str) -> None:
        super().__init__()
        self._account_name = account_name

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"Delete '{self._account_name}'? This cannot be undone.")
            with Horizontal():
                yield Button("Confirm", id="btn-confirm", variant="error")
                yield Button("Cancel", id="btn-cancel", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-confirm")


class RenameModal(ModalScreen):
    """Modal for renaming an account."""

    DEFAULT_CSS = """
    RenameModal > Vertical {
        width: 50;
        height: auto;
        border: round $primary;
        padding: 1 2;
        background: $surface;
    }
    RenameModal Input { margin: 1 0; }
    RenameModal Horizontal { height: auto; }
    RenameModal Button { margin-right: 1; }
    """

    def __init__(self, current_name: str) -> None:
        super().__init__()
        self._current = current_name

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Rename Account")
            yield Input(value=self._current, id="inp-name")
            with Horizontal():
                yield Button("OK", id="btn-ok", variant="primary")
                yield Button("Cancel", id="btn-cancel", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-ok":
            name = self.query_one("#inp-name", Input).value.strip()
            self.dismiss(name if name else None)
        else:
            self.dismiss(None)


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

class GroqSwitcherApp(App):
    """Groq Account Switcher TUI."""

    TITLE = "Groq Account Switcher"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("ctrl+c", "copy", "Copy", priority=True),
        Binding("tab", "focus_next", "Next"),
    ]

    DEFAULT_CSS = """
    Screen { layout: vertical; align: left top; }

    #toolbar {
        height: 3;
        padding: 0 1;
        background: $panel;
        layout: horizontal;
        align: left middle;
    }
    #toolbar Button { margin-right: 1; min-width: 8; }
    #toolbar Select { width: 14; margin-right: 1; }
    #toolbar .spacer { width: 1fr; }

    #models-label, #accounts-label {
        height: 1;
        padding: 0 1;
        background: $boost;
        color: $text-muted;
    }

    #tbl-models { height: 9; }
    #tbl-accounts { height: auto; max-height: 12; }
    #spacer { height: 1fr; }

    #status {
        height: 1;
        padding: 0 1;
        background: $panel;
        color: $text-muted;
    }
    #copy-bar { height: 1; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._all_models: list[dict] = []
        self._model_type: str = "llm"
        self._selected_model_row: int = 0
        self._selected_account_row: int = 0
        self._copy_value: str = ""

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="toolbar"):
            yield Button("Add", id="btn-add")
            yield Button("Edit", id="btn-edit")
            yield Button("Delete", id="btn-delete")
            yield Button("Rename", id="btn-rename")
            yield Select(
                options=MODEL_TYPE_OPTIONS,
                value="llm",
                id="sel-model-type",
                prompt="Model Type",
            )
            yield Static("", classes="spacer")
            yield Button("Refresh", id="btn-refresh")
            yield Button("Refresh All", id="btn-refresh-all")
        yield Static("Models", id="models-label")
        yield DataTable(id="tbl-models", cursor_type="cell", zebra_stripes=False)
        yield Static("Accounts", id="accounts-label")
        yield DataTable(id="tbl-accounts", cursor_type="row", zebra_stripes=False)
        yield Static("", id="spacer")
        yield Input(id="copy-bar", compact=True)
        yield Static("Ready.", id="status")
        yield Footer()

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self._build_models_table()
        self._build_accounts_table()
        self._populate_accounts_table()
        self._load_models_async()

    def _load_models_async(self) -> None:
        key = get_current_key()
        if not key:
            self._set_status("No active key found — add an account first.")
            return

        def _fetch():
            models = _fetch_models(key)
            self.call_from_thread(self._on_models_loaded, models)

        threading.Thread(target=_fetch, daemon=True).start()

    def _on_models_loaded(self, models: list[dict]) -> None:
        self._all_models = models
        self._populate_models_table()

    # ------------------------------------------------------------------
    # Models table
    # ------------------------------------------------------------------

    def _build_models_table(self) -> None:
        tbl: DataTable = self.query_one("#tbl-models", DataTable)
        tbl.clear(columns=True)
        if self._model_type == "llm":
            tbl.add_columns(" ", "Model", "Owner", "Context", "RPD left", "TPM left")
        elif self._model_type == "stt":
            tbl.add_columns(" ", "Model", "Language", "Cost/hr", "WER")
        else:
            tbl.add_columns(" ", "Voice", "Language")

    def _populate_models_table(self) -> None:
        tbl: DataTable = self.query_one("#tbl-models", DataTable)
        tbl.clear()
        filtered = _filter_models(self._all_models, self._model_type)
        active_name = get_active_account_name()
        data = load_accounts()
        quota_cache: dict[str, dict] = {}
        if active_name:
            for acc in data.get("accounts", []):
                if acc.get("name") == active_name:
                    quota_cache = acc.get("model_quota", {})
                    break

        for i, m in enumerate(filtered):
            sel = "●" if i == self._selected_model_row else "○"
            mid = m["id"]
            q = quota_cache.get(mid, {})
            rpd = str(q.get("rpd_remaining", "—")) if q else "—"
            tpm = str(q.get("tpm_remaining", "—")) if q else "—"

            if self._model_type == "llm":
                tbl.add_row(sel, mid, m.get("owned_by", "—"), _fmt_context(m.get("context_window")), rpd, tpm)
            elif self._model_type == "stt":
                meta = STT_META.get(mid, {})
                tbl.add_row(sel, mid, meta.get("language", "—"), meta.get("cost", "—"), meta.get("wer", "—"))
            else:
                lang = "AR" if "arabic" in mid else "EN"
                tbl.add_row(sel, mid, lang)

    def _get_selected_model_id(self) -> str | None:
        tbl: DataTable = self.query_one("#tbl-models", DataTable)
        if tbl.row_count == 0:
            return None
        try:
            row = tbl.get_row_at(self._selected_model_row)
            return str(row[1])  # Model column is index 1
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Accounts table
    # ------------------------------------------------------------------

    def _build_accounts_table(self) -> None:
        tbl: DataTable = self.query_one("#tbl-accounts", DataTable)
        tbl.clear(columns=True)
        tbl.add_columns(" ", "Name", "Key (masked)", "Last used", "Status")

    def _populate_accounts_table(self) -> None:
        tbl: DataTable = self.query_one("#tbl-accounts", DataTable)
        tbl.clear()
        data = load_accounts()
        # Derive active account from current .env key, not just the stored "active" field,
        # so accounts added before any switch() call still show correctly.
        active = get_active_account_name() or data.get("active")
        for acc in data.get("accounts", []):
            name = acc.get("name", "")
            is_active = name == active
            sel = "●" if is_active else "○"
            masked = mask_key(acc.get("key", ""))
            last = _fmt_dt(acc.get("last_used"))
            status = "active" if is_active else ""
            tbl.add_row(sel, name, masked, last, status)

    def _get_selected_account(self) -> dict | None:
        tbl: DataTable = self.query_one("#tbl-accounts", DataTable)
        if tbl.row_count == 0:
            return None
        try:
            row = tbl.get_row_at(self._selected_account_row)
            name = str(row[1])
        except Exception:
            return None
        data = load_accounts()
        for acc in data.get("accounts", []):
            if acc.get("name") == name:
                return acc
        return None

    # ------------------------------------------------------------------
    # Table events
    # ------------------------------------------------------------------

    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted) -> None:
        if event.data_table.id == "tbl-models":
            self._copy_value = str(event.value) if event.value is not None else ""
            self._set_status(f"Selected: {self._copy_value}")
            self.query_one("#copy-bar", Input).value = self._copy_value

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        tbl = event.data_table
        if tbl.id == "tbl-models":
            self._selected_model_row = event.cursor_row
            self._refresh_model_sel_column()
        elif tbl.id == "tbl-accounts":
            self._selected_account_row = event.cursor_row
            self.action_switch_selected()

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        tbl = event.data_table
        if tbl.id == "tbl-models":
            self._selected_model_row = event.coordinate.row
            self._refresh_model_sel_column()

    def _refresh_model_sel_column(self) -> None:
        tbl: DataTable = self.query_one("#tbl-models", DataTable)
        for i in range(tbl.row_count):
            sym = "●" if i == self._selected_model_row else "○"
            tbl.update_cell_at((i, 0), sym)

    # ------------------------------------------------------------------
    # Button events
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "btn-refresh":
            self.action_refresh()
        elif bid == "btn-refresh-all":
            self._refresh_all()
        elif bid == "btn-add":
            self._do_add()
        elif bid == "btn-edit":
            self._do_edit()
        elif bid == "btn-delete":
            self._do_delete()
        elif bid == "btn-rename":
            self._do_rename()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "sel-model-type":
            self._model_type = str(event.value)
            self._build_models_table()
            self._populate_models_table()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "copy-bar":
            self._copy_value = event.value

    # ------------------------------------------------------------------
    # Key bindings
    # ------------------------------------------------------------------

    def action_copy(self) -> None:
        text = self._copy_value
        if not text:
            self._set_status("Nothing to copy.")
            return
        try:
            subprocess.run(["clip"], input=text.encode("utf-8"), check=False)
            self._set_status(f"Copied: {text}")
        except Exception as e:
            self._set_status(f"Copy failed: {e}")

    def action_refresh(self) -> None:
        key = get_current_key()
        model_id = self._get_selected_model_id()
        if not key or not model_id:
            self._set_status("No active key or model selected.")
            return
        self._set_status(f"Pinging {model_id}...")

        def _ping():
            result = ping_model_quota(key, model_id)
            self.call_from_thread(self._on_single_refresh, model_id, result)

        threading.Thread(target=_ping, daemon=True).start()

    def _on_single_refresh(self, model_id: str, result: dict | None) -> None:
        if result:
            active_name = get_active_account_name()
            if active_name:
                update_account_quota(active_name, model_id, result)
            self._populate_models_table()
            self._set_status(f"✓ Quota updated for {model_id}")
        else:
            self._set_status(f"✗ Failed to fetch quota for {model_id}")

    def _refresh_all(self) -> None:
        key = get_current_key()
        if not key:
            self._set_status("No active key.")
            return
        filtered = _filter_models(self._all_models, self._model_type)
        if not filtered:
            self._set_status("No models to refresh.")
            return
        total = len(filtered)
        self._set_status(f"Scanning 0/{total}...")

        def _scan():
            active_name = get_active_account_name()
            for i, m in enumerate(filtered, 1):
                mid = m["id"]
                self.call_from_thread(self._set_status, f"Scanning {i}/{total}...")
                result = ping_model_quota(key, mid)
                if result and active_name:
                    update_account_quota(active_name, mid, result)
            self.call_from_thread(self._populate_models_table)
            self.call_from_thread(self._set_status, f"✓ Refreshed {total} models.")

        threading.Thread(target=_scan, daemon=True).start()

    # ------------------------------------------------------------------
    # Account actions (Enter key on accounts table = switch)
    # ------------------------------------------------------------------

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id == "tbl-accounts":
            self._selected_account_row = event.cursor_row
            try:
                row = event.data_table.get_row_at(event.cursor_row)
                self._copy_value = str(row[1]) if len(row) > 1 else ""
                self._set_status(f"Selected: {self._copy_value}")
                self.query_one("#copy-bar", Input).value = self._copy_value
            except Exception:
                pass

    def action_switch_selected(self) -> None:
        acc = self._get_selected_account()
        if not acc:
            return
        skipped = switch_account(acc["name"], acc["key"])
        # Clear model quota display
        self._clear_models_quota()
        self._populate_accounts_table()
        # Re-fetch models with new key
        self._load_models_async()
        msg = f"✓ Switched to {acc['name']} — restart Claude Desktop + agy CLI"
        if skipped:
            short = [p.split("\\")[-1] for p in skipped]
            msg += f" | skipped: {', '.join(short)}"
        self._set_status(msg)

    def _clear_models_quota(self) -> None:
        tbl: DataTable = self.query_one("#tbl-models", DataTable)
        if self._model_type == "llm":
            for i in range(tbl.row_count):
                tbl.update_cell_at((i, 4), "—")
                tbl.update_cell_at((i, 5), "—")

    # ------------------------------------------------------------------
    # CRUD modals
    # ------------------------------------------------------------------

    def _do_add(self) -> None:
        def _on_result(result: dict | None) -> None:
            if result:
                data = load_accounts()
                data.setdefault("accounts", []).append({
                    "name": result["name"],
                    "key": result["key"],
                    "last_used": None,
                    "model_quota": {},
                })
                save_accounts(data)
                self._populate_accounts_table()
                self._set_status(f"Account '{result['name']}' added.")

        self.push_screen(AddEditModal(), _on_result)

    def _do_edit(self) -> None:
        acc = self._get_selected_account()
        if not acc:
            self._set_status("Select an account to edit.")
            return

        def _on_result(result: dict | None) -> None:
            if result:
                data = load_accounts()
                for a in data.get("accounts", []):
                    if a.get("name") == acc["name"]:
                        a["name"] = result["name"]
                        a["key"] = result["key"]
                        break
                if data.get("active") == acc["name"]:
                    data["active"] = result["name"]
                save_accounts(data)
                self._populate_accounts_table()
                self._set_status(f"Account updated.")

        self.push_screen(AddEditModal(acc.get("name", ""), acc.get("key", ""), edit_mode=True), _on_result)

    def _do_delete(self) -> None:
        acc = self._get_selected_account()
        if not acc:
            self._set_status("Select an account to delete.")
            return

        def _on_result(confirmed: bool) -> None:
            if confirmed:
                data = load_accounts()
                data["accounts"] = [a for a in data.get("accounts", []) if a.get("name") != acc["name"]]
                if data.get("active") == acc["name"]:
                    data["active"] = None
                save_accounts(data)
                self._selected_account_row = 0
                self._populate_accounts_table()
                self._set_status(f"Account '{acc['name']}' deleted.")

        self.push_screen(DeleteModal(acc.get("name", "")), _on_result)

    def _do_rename(self) -> None:
        acc = self._get_selected_account()
        if not acc:
            self._set_status("Select an account to rename.")
            return

        def _on_result(new_name: str | None) -> None:
            if new_name:
                data = load_accounts()
                for a in data.get("accounts", []):
                    if a.get("name") == acc["name"]:
                        a["name"] = new_name
                        break
                if data.get("active") == acc["name"]:
                    data["active"] = new_name
                save_accounts(data)
                self._populate_accounts_table()
                self._set_status(f"Renamed to '{new_name}'.")

        self.push_screen(RenameModal(acc.get("name", "")), _on_result)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_status(self, msg: str) -> None:
        self.query_one("#status", Static).update(msg)

    def _populate_all(self) -> None:
        self._populate_models_table()
        self._populate_accounts_table()
