# TextAdventure (DnD-flavored, procedural)

A small web-based text adventure inspired by DnD.

- Frontend: vanilla HTML/CSS/JS (served as static files)
- Backend: FastAPI (Python)
- No database / no persistence across sessions
- Each new visit gets a newly generated adventure

## Run locally

### 1) Create a venv + install deps

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2) Start the server

```powershell
uvicorn app.main:app --reload --port 8000
```

### 3) Play

Open http://127.0.0.1:8000

## Notes

- Game state is stored in memory on the server (per-session cookie). Closing the tab / starting a new browser session starts a new game.
