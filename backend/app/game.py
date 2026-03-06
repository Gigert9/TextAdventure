from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


DIRECTIONS: Dict[str, str] = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
}


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _roll(rng: random.Random, n: int, sides: int) -> int:
    return sum(rng.randint(1, sides) for _ in range(n))


def _pick(rng: random.Random, items: List[str]) -> str:
    return items[rng.randrange(0, len(items))]


@dataclass
class Monster:
    name: str
    hp: int
    ac: int
    attack_bonus: int
    damage_die: Tuple[int, int]  # (n, sides)
    flavor: str


@dataclass
class Room:
    id: str
    name: str
    desc: str
    exits: Dict[str, str] = field(default_factory=dict)  # dir -> room_id
    items: List[str] = field(default_factory=list)
    puzzle: Optional[str] = None
    puzzle_state: Dict[str, str] = field(default_factory=dict)
    monster: Optional[Monster] = None
    is_exit: bool = False


@dataclass
class Player:
    hp: int
    max_hp: int
    ac: int
    attack_bonus: int
    damage_die: Tuple[int, int]
    inventory: List[str] = field(default_factory=list)


@dataclass
class Game:
    id: str
    seed: int
    created_at: float
    rng_state: object

    rooms: Dict[str, Room]
    current_room_id: str
    player: Player

    boss_room_id: str
    artifact_item: str
    won: bool = False
    lost: bool = False

    log: List[str] = field(default_factory=list)


class GameEngine:
    """Procedurally generated mini-adventure.

    Design constraints:
    - No DB/persistence.
    - Unique per new session.
    - Beat in one sitting (~10-30 commands).
    """

    ROOM_THEMES = [
        "mossy crypt",
        "collapsed library",
        "goblin den",
        "forgotten shrine",
        "arcane workshop",
        "fungal caverns",
        "blood-stained chapel",
        "abandoned guard post",
    ]

    MONSTERS = [
        ("Goblin", 7, 13, 4, (1, 6), "A wiry goblin hisses, clutching a jagged blade."),
        ("Skeleton", 10, 13, 4, (1, 6), "Bones clatter as a skeleton raises a rusted sword."),
        ("Kobold", 5, 12, 3, (1, 4), "A kobold yips and jabs with a spear."),
        ("Cultist", 9, 12, 3, (1, 6), "A hooded cultist murmurs a dark prayer."),
    ]

    BOSSES = [
        ("Hobgoblin Captain", 22, 15, 5, (1, 8), "A disciplined hobgoblin squares up, eyes cold."),
        ("Wight", 26, 14, 6, (1, 8), "A pallid wight glides forward, hunger in its gaze."),
        ("Owlbear", 30, 13, 6, (2, 6), "An owlbear bellows, feathers bristling."),
    ]

    ARTIFACTS = [
        "Amulet of the Dawn",
        "Gem of Whispering Shadows",
        "Codex of Nine Sigils",
        "Chalice of the Moon",
    ]

    KEYS = [
        "iron key",
        "bone key",
        "silver key",
        "rune key",
    ]

    POTIONS = [
        "healing potion",
        "greater healing potion",
    ]

    def new_game(self) -> Game:
        game_id = uuid.uuid4().hex
        seed = int(time.time() * 1000) ^ (uuid.uuid4().int & 0xFFFFFFFF)
        rng = random.Random(seed)

        dungeon_size = rng.randint(6, 9)
        rooms, start_id, boss_id = self._generate_dungeon(rng, dungeon_size)

        artifact = _pick(rng, self.ARTIFACTS)
        rooms[boss_id].items.append(artifact)

        player = Player(
            hp=18,
            max_hp=18,
            ac=14,
            attack_bonus=5,
            damage_die=(1, 8),
            inventory=[_pick(rng, self.POTIONS)],
        )

        game = Game(
            id=game_id,
            seed=seed,
            created_at=time.time(),
            rng_state=rng.getstate(),
            rooms=rooms,
            current_room_id=start_id,
            player=player,
            boss_room_id=boss_id,
            artifact_item=artifact,
            log=[],
        )

        self._log(game, "You awaken at the mouth of a forgotten dungeon, your pack light and your blade ready.")
        self._log(game, f"A rumor brought you here: recover the {artifact} and escape alive.")
        self._log(game, self._describe_room(game))
        return game

    def _generate_dungeon(self, rng: random.Random, size: int) -> Tuple[Dict[str, Room], str, str]:
        rooms: Dict[str, Room] = {}
        ids = [uuid.uuid4().hex[:8] for _ in range(size)]

        start_id = ids[0]
        boss_id = ids[-1]

        for idx, rid in enumerate(ids):
            theme = _pick(rng, self.ROOM_THEMES)
            name = theme.title()
            desc = f"You stand in a {theme}." \
                f" The air smells of damp stone and old secrets."

            room = Room(id=rid, name=name, desc=desc)
            rooms[rid] = room

            if rid == boss_id:
                boss = self._make_monster(rng, boss=True)
                room.monster = boss
                room.desc += " The presence here is oppressive—something powerful lairs within."

        # Create a guaranteed path start -> ... -> boss
        for i in range(size - 1):
            a, b = ids[i], ids[i + 1]
            direction = _pick(rng, list(DIRECTIONS.keys()))
            self._connect(rooms[a], rooms[b], direction)

        # Add extra connections for non-linearity
        extra_edges = rng.randint(2, 4)
        for _ in range(extra_edges):
            a, b = rng.sample(ids, 2)
            if a == b:
                continue
            direction = _pick(rng, list(DIRECTIONS.keys()))
            if direction in rooms[a].exits:
                continue
            self._connect(rooms[a], rooms[b], direction)

        # Place an exit room (different from boss room)
        exit_room_id = rng.choice(ids[:-1])
        rooms[exit_room_id].is_exit = True
        rooms[exit_room_id].desc += " A narrow stairway here leads back to the surface."

        # Add puzzles and loot.
        self._place_puzzles_and_loot(rng, rooms, start_id, boss_id)

        return rooms, start_id, boss_id

    def _connect(self, a: Room, b: Room, direction: str) -> None:
        a.exits[direction] = b.id
        b.exits[DIRECTIONS[direction]] = a.id

    def _make_monster(self, rng: random.Random, boss: bool) -> Monster:
        if boss:
            name, hp, ac, atk, dmg, flavor = _pick(rng, list(self.BOSSES))
        else:
            name, hp, ac, atk, dmg, flavor = _pick(rng, list(self.MONSTERS))
        return Monster(name=name, hp=hp, ac=ac, attack_bonus=atk, damage_die=dmg, flavor=flavor)

    def _place_puzzles_and_loot(self, rng: random.Random, rooms: Dict[str, Room], start_id: str, boss_id: str) -> None:
        room_ids = [rid for rid in rooms.keys() if rid not in (start_id, boss_id)]
        rng.shuffle(room_ids)

        key_item = _pick(rng, self.KEYS)
        locked_room_id = room_ids[0]
        key_room_id = room_ids[1] if len(room_ids) > 1 else start_id

        rooms[key_room_id].items.append(key_item)

        # Locked door puzzle blocks entry to the boss room from at least one direction
        # We pick a neighbor of boss (if any) and make that exit locked.
        boss_neighbors = list(rooms[boss_id].exits.values())
        if boss_neighbors:
            approach_id = rng.choice(boss_neighbors)
            # Find direction from approach -> boss
            dir_to_boss = None
            for d, target in rooms[approach_id].exits.items():
                if target == boss_id:
                    dir_to_boss = d
                    break
            if dir_to_boss:
                rooms[approach_id].puzzle = "locked_door"
                rooms[approach_id].puzzle_state = {
                    "dir": dir_to_boss,
                    "key": key_item,
                    "unlocked": "no",
                }
                rooms[approach_id].desc += " A heavy door nearby is engraved with warding runes."

        # Riddle puzzle grants a useful item
        riddle_room_id = locked_room_id
        rooms[riddle_room_id].puzzle = "riddle"
        answer = _pick(rng, ["torch", "silence", "time", "shadow", "stone"])
        rooms[riddle_room_id].puzzle_state = {
            "answer": answer,
            "solved": "no",
            "reward": _pick(rng, ["smoke bomb", "holy water", "antitoxin", _pick(rng, self.POTIONS)]),
        }
        rooms[riddle_room_id].desc += " A talking skull rests on a pedestal, waiting."

        # Sprinkle monsters and extra loot
        for rid, room in rooms.items():
            if rid in (start_id, boss_id):
                continue
            if rng.random() < 0.55 and room.monster is None:
                room.monster = self._make_monster(rng, boss=False)
            if rng.random() < 0.35:
                room.items.append(_pick(rng, ["rope", "chalk", "ration", "dagger", "lockpick", _pick(rng, self.POTIONS)]))

    def snapshot(self, game: Game) -> dict:
        room = game.rooms[game.current_room_id]
        return {
            "gameId": game.id,
            "seed": game.seed,
            "won": game.won,
            "lost": game.lost,
            "player": {
                "hp": game.player.hp,
                "maxHp": game.player.max_hp,
                "ac": game.player.ac,
                "inventory": list(game.player.inventory),
            },
            "room": {
                "id": room.id,
                "name": room.name,
                "desc": room.desc,
                "exits": sorted(list(room.exits.keys())),
                "items": list(room.items),
                "puzzle": room.puzzle,
                "monster": None
                if room.monster is None
                else {"name": room.monster.name, "hp": room.monster.hp, "ac": room.monster.ac},
                "isExit": room.is_exit,
            },
            "log": list(game.log[-200:]),
        }

    def handle_command(self, game: Game, command: str) -> dict:
        if game.won or game.lost:
            return {"text": "The adventure is over. Refresh the page to begin anew.", "state": self.snapshot(game)}

        command = (command or "").strip()
        if not command:
            return {"text": "Say what you do.", "state": self.snapshot(game)}

        rng = random.Random()
        rng.setstate(game.rng_state)

        verb, *rest = command.lower().split()
        arg = " ".join(rest).strip()

        response_lines: List[str] = []

        if verb in ("help", "?"):
            response_lines.append(self._help_text())
        elif verb in ("look", "l"):
            response_lines.append(self._describe_room(game))
        elif verb in ("leave", "exit", "escape"):
            msg = self.try_win(game)
            response_lines.append(msg or "You find no way out from here.")
        elif verb in ("go", "move", "walk"):
            response_lines.extend(self._cmd_go(game, rng, arg))
        elif verb in ("north", "south", "east", "west", "n", "s", "e", "w"):
            dir_map = {"n": "north", "s": "south", "e": "east", "w": "west"}
            response_lines.extend(self._cmd_go(game, rng, dir_map.get(verb, verb)))
        elif verb in ("take", "get", "grab"):
            response_lines.extend(self._cmd_take(game, arg))
        elif verb in ("inventory", "inv", "i"):
            response_lines.append(self._cmd_inventory(game))
        elif verb in ("use",):
            response_lines.extend(self._cmd_use(game, rng, arg))
        elif verb in ("attack", "hit", "fight"):
            response_lines.extend(self._cmd_attack(game, rng, arg))
        elif verb in ("rest",):
            response_lines.extend(self._cmd_rest(game, rng))
        else:
            response_lines.append("You hesitate, unsure how to do that. (Try `help`.)")

        # update RNG state
        game.rng_state = rng.getstate()

        for line in response_lines:
            self._log(game, line)

        return {"text": "\n".join(response_lines), "state": self.snapshot(game)}

    def _help_text(self) -> str:
        return (
            "Commands: look | go <north|south|east|west> | take <item> | use <item> | attack | inventory | rest | help\n"
            "Tips: Abbreviations n/s/e/w work. Some doors require keys. Some puzzles require answers."
        )

    def _describe_room(self, game: Game) -> str:
        room = game.rooms[game.current_room_id]
        lines = [f"== {room.name} ==", room.desc]
        if room.monster is not None and room.monster.hp > 0:
            lines.append(room.monster.flavor)
        if room.items:
            lines.append("You see: " + ", ".join(room.items) + ".")
        if room.exits:
            lines.append("Exits: " + ", ".join(sorted(room.exits.keys())) + ".")
        if room.is_exit:
            lines.append("You could leave from here if you have the artifact.")
        return "\n".join(lines)

    def _cmd_inventory(self, game: Game) -> str:
        if not game.player.inventory:
            return "Your inventory is empty."
        return "You carry: " + ", ".join(game.player.inventory) + "."

    def _cmd_take(self, game: Game, arg: str) -> List[str]:
        room = game.rooms[game.current_room_id]
        if room.monster is not None and room.monster.hp > 0:
            return ["Not while a hostile creature bars your way."]

        if not room.items:
            return ["There is nothing here to take."]

        if not arg:
            # take first item
            item = room.items.pop(0)
            game.player.inventory.append(item)
            return [f"You take the {item}."]

        # simple contains match
        for i, item in enumerate(room.items):
            if arg in item.lower():
                taken = room.items.pop(i)
                game.player.inventory.append(taken)
                return [f"You take the {taken}."]

        return ["You don't see that here."]

    def _cmd_go(self, game: Game, rng: random.Random, direction: str) -> List[str]:
        direction = (direction or "").strip().lower()
        if direction in ("n", "s", "e", "w"):
            direction = {"n": "north", "s": "south", "e": "east", "w": "west"}[direction]

        room = game.rooms[game.current_room_id]

        if room.monster is not None and room.monster.hp > 0:
            return ["The enemy blocks your escape! You'll need to fight or find another way."]

        if not direction:
            return ["Go where?"]

        if direction not in room.exits:
            return ["No passage that way."]

        # locked door puzzle on this room
        if room.puzzle == "locked_door":
            if room.puzzle_state.get("dir") == direction and room.puzzle_state.get("unlocked") != "yes":
                key_name = room.puzzle_state.get("key", "key")
                return [f"The rune-locked door resists you. You'll need the {key_name}."]

        game.current_room_id = room.exits[direction]
        new_room = game.rooms[game.current_room_id]

        lines = [self._describe_room(game)]

        # auto-trigger riddle hint
        if new_room.puzzle == "riddle" and new_room.puzzle_state.get("solved") != "yes":
            lines.append(
                "The skull's jaw chatters: 'I devour all; I bow to none. Name me, and I will grant you a gift.' "
                "(Try `use answer <word>`.)"
            )

        # If monster exists, it may ambush
        if new_room.monster is not None and new_room.monster.hp > 0 and rng.random() < 0.25:
            lines.append(f"{new_room.monster.name} lunges first!")
            lines.extend(self._monster_attack(game, rng, new_room.monster))

        return lines

    def _cmd_use(self, game: Game, rng: random.Random, arg: str) -> List[str]:
        room = game.rooms[game.current_room_id]
        arg = (arg or "").strip().lower()
        if not arg:
            return ["Use what?"]

        if arg.startswith("answer "):
            return self._cmd_answer_riddle(game, arg[len("answer ") :].strip())

        # Potion use
        if "potion" in arg:
            item_idx = next((i for i, it in enumerate(game.player.inventory) if "potion" in it.lower()), None)
            if item_idx is None:
                return ["You don't have a potion."]
            potion = game.player.inventory.pop(item_idx)
            heal = 0
            if potion == "healing potion":
                heal = _roll(rng, 2, 4) + 2
            else:
                heal = _roll(rng, 4, 4) + 4
            old = game.player.hp
            game.player.hp = _clamp(game.player.hp + heal, 0, game.player.max_hp)
            return [f"You drink the {potion} and recover {game.player.hp - old} HP."]

        # Key use for locked door
        if "key" in arg:
            if room.puzzle != "locked_door":
                return ["There's no lock here that fits."]
            key = room.puzzle_state.get("key")
            has_key = any(key and key in it.lower() for it in game.player.inventory)
            if not has_key:
                return [f"You need the {key}."]
            room.puzzle_state["unlocked"] = "yes"
            return ["The runes dim as the lock clicks open. The door is unlocked."]

        # Utility items
        if "holy water" in arg:
            if not any("holy water" in it.lower() for it in game.player.inventory):
                return ["You don't have holy water."]
            if room.monster is None or room.monster.hp <= 0:
                return ["You sprinkle holy water. Nothing happens."]
            dmg = _roll(rng, 2, 6)
            room.monster.hp = max(0, room.monster.hp - dmg)
            lines = [f"Holy water sizzles on {room.monster.name}! It takes {dmg} radiant damage."]
            if room.monster.hp <= 0:
                lines.append(self._on_monster_defeated(game, rng, room))
            return lines

        return ["You can't figure out how to use that here."]

    def _cmd_answer_riddle(self, game: Game, answer: str) -> List[str]:
        room = game.rooms[game.current_room_id]
        if room.puzzle != "riddle":
            return ["No one here asks you riddles."]
        if room.puzzle_state.get("solved") == "yes":
            return ["The skull is silent now."]
        expected = room.puzzle_state.get("answer", "")
        if answer.strip().lower() == expected.lower():
            room.puzzle_state["solved"] = "yes"
            reward = room.puzzle_state.get("reward", "trinket")
            room.items.append(reward)
            return [
                "The skull grins. 'Correct.'",
                f"A hidden compartment opens, revealing {reward}.",
            ]
        return ["The skull rattles: 'Wrong.'"]

    def _cmd_attack(self, game: Game, rng: random.Random, arg: str) -> List[str]:
        room = game.rooms[game.current_room_id]
        if room.monster is None or room.monster.hp <= 0:
            return ["There is nothing here to fight."]

        lines: List[str] = []

        # player attack
        d20 = rng.randint(1, 20)
        total = d20 + game.player.attack_bonus
        if d20 == 20 or total >= room.monster.ac:
            dmg_n, dmg_s = game.player.damage_die
            dmg = _roll(rng, dmg_n, dmg_s) + (2 if d20 == 20 else 0)
            room.monster.hp = max(0, room.monster.hp - dmg)
            lines.append(f"You strike {room.monster.name} (roll {d20}+{game.player.attack_bonus}={total}) for {dmg} damage.")
        else:
            lines.append(f"You miss {room.monster.name} (roll {d20}+{game.player.attack_bonus}={total}).")

        if room.monster.hp <= 0:
            lines.append(self._on_monster_defeated(game, rng, room))
            return lines

        # monster retaliates
        lines.extend(self._monster_attack(game, rng, room.monster))

        return lines

    def _monster_attack(self, game: Game, rng: random.Random, monster: Monster) -> List[str]:
        if monster.hp <= 0:
            return []
        d20 = rng.randint(1, 20)
        total = d20 + monster.attack_bonus
        if d20 == 20 or total >= game.player.ac:
            dmg_n, dmg_s = monster.damage_die
            dmg = _roll(rng, dmg_n, dmg_s) + (2 if d20 == 20 else 0)
            game.player.hp = max(0, game.player.hp - dmg)
            lines = [f"{monster.name} hits you (roll {d20}+{monster.attack_bonus}={total}) for {dmg} damage."]
        else:
            lines = [f"{monster.name} misses you (roll {d20}+{monster.attack_bonus}={total})."]

        if game.player.hp <= 0:
            game.lost = True
            lines.append("You collapse. Darkness takes you. (Refresh to start a new adventure.)")

        return lines

    def _on_monster_defeated(self, game: Game, rng: random.Random, room: Room) -> str:
        name = room.monster.name if room.monster else "the foe"
        # drop small loot sometimes
        if room.monster and rng.random() < 0.35:
            room.items.append("coin pouch")
        if room.monster and room.monster.name == "Owlbear" and "ration" not in room.items:
            room.items.append("ration")
        if room.monster and room.monster.name in ("Wight",):
            room.items.append("holy water")
        return f"{name} falls."

    def _cmd_rest(self, game: Game, rng: random.Random) -> List[str]:
        room = game.rooms[game.current_room_id]
        if room.monster is not None and room.monster.hp > 0:
            return ["Not with an enemy nearby."]
        heal = _roll(rng, 1, 8) + 2
        old = game.player.hp
        game.player.hp = _clamp(game.player.hp + heal, 0, game.player.max_hp)
        return [f"You rest for a moment, steadying your breath. (+{game.player.hp - old} HP)"]

    def try_win(self, game: Game) -> Optional[str]:
        room = game.rooms[game.current_room_id]
        if not room.is_exit:
            return None
        if room.monster is not None and room.monster.hp > 0:
            return "Something hostile guards the way out."
        if game.artifact_item not in game.player.inventory and game.artifact_item not in room.items:
            return "You can't leave yet. The artifact is still somewhere below."
        game.won = True
        return f"You ascend to the surface with the {game.artifact_item}. You've won!"

    def _log(self, game: Game, text: str) -> None:
        game.log.append(text)
