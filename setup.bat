@echo off
python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r requirements.txt

if not exist accounts.json (
    echo {"accounts": [], "active": null} > accounts.json
    echo Created accounts.json — add your Groq accounts via the TUI.
) else (
    echo accounts.json already exists, skipping.
)

echo.
echo Setup complete. Run "run.bat" to start the switcher.
