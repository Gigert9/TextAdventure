from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .game import Game, GameEngine


@dataclass
class StoredGame:
    game: Game
    last_access: float


class GameStore:
    def __init__(self, *, ttl_seconds: int = 60 * 60 * 2) -> None:
        self._ttl_seconds = ttl_seconds
        self._games: Dict[str, StoredGame] = {}
        self._engine = GameEngine()

    @property
    def engine(self) -> GameEngine:
        return self._engine

    def cleanup(self) -> None:
        now = time.time()
        stale = [gid for gid, sg in self._games.items() if (now - sg.last_access) > self._ttl_seconds]
        for gid in stale:
            self._games.pop(gid, None)

    def new_game(self) -> Game:
        self.cleanup()
        game = self._engine.new_game()
        self._games[game.id] = StoredGame(game=game, last_access=time.time())
        return game

    def get(self, game_id: str) -> Optional[Game]:
        self.cleanup()
        if not game_id:
            return None
        stored = self._games.get(game_id)
        if stored is None:
            return None
        stored.last_access = time.time()
        return stored.game

    def get_or_error(self, game_id: str) -> Tuple[Optional[Game], Optional[str]]:
        game = self.get(game_id)
        if game is None:
            return None, "Unknown or expired game. Start a new game."
        return game, None
