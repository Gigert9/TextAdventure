from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .store import GameStore


ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"
ASSETS_DIR = FRONTEND_DIR / "assets"

PREFIX = "/easter-egg"

app = FastAPI(title="TextAdventure")
store = GameStore()


class NewGameResponse(BaseModel):
    text: str
    state: dict


class CommandRequest(BaseModel):
    gameId: str = Field(min_length=1)
    command: str = Field(default="")


class CommandResponse(BaseModel):
    text: str
    state: dict


@app.get(PREFIX)
def easter_egg_redirect() -> RedirectResponse:
    return RedirectResponse(url=f"{PREFIX}/")


@app.get(f"{PREFIX}/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.post(f"{PREFIX}/api/new_game", response_model=NewGameResponse)
def api_new_game() -> dict:
    game = store.new_game()
    return {"text": "\n".join(game.log[-5:]), "state": store.engine.snapshot(game)}


@app.post(f"{PREFIX}/api/command", response_model=CommandResponse)
def api_command(req: CommandRequest) -> dict:
    game, err = store.get_or_error(req.gameId)
    if err:
        return {"text": err, "state": {"lost": True, "won": False}}

    return store.engine.handle_command(game, req.command)


# Static assets under the same prefix
app.mount(f"{PREFIX}/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount(f"{PREFIX}/assets", StaticFiles(directory=ASSETS_DIR), name="assets")