from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .content import bestiary as content_bestiary
from .content import features as content_features
from .content import items as content_items
from .content import lore as content_lore
from .content import riddles as content_riddles


DIRECTIONS: Dict[str, str] = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
}

ABILITY_KEYS: Tuple[str, ...] = ("str", "dex", "con", "int", "wis", "cha")

MAX_CHAPTERS: int = 20


def _ability_mod(score: int) -> int:
    return (score - 10) // 2


def _roll_4d6_drop_lowest(rng: random.Random) -> int:
    rolls = sorted([rng.randint(1, 6) for _ in range(4)])
    return sum(rolls[1:])


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
    x: int = 0
    y: int = 0
    feature: str = ""
    exits: Dict[str, str] = field(default_factory=dict)  # dir -> room_id
    items: List[str] = field(default_factory=list)
    puzzle: Optional[str] = None
    puzzle_state: Dict[str, str] = field(default_factory=dict)
    room_state: Dict[str, str] = field(default_factory=dict)
    scenery: Dict[str, str] = field(default_factory=dict)
    combat_state: Dict[str, str] = field(default_factory=dict)
    monster: Optional[Monster] = None
    is_exit: bool = False


@dataclass
class Player:
    name: str
    species: str
    char_class: str
    level: int
    ability_scores: Dict[str, int]

    hp: int
    max_hp: int
    ac: int
    proficiency_bonus: int

    inventory: List[str] = field(default_factory=list)
    equipped_melee: Optional[str] = None
    equipped_ranged: Optional[str] = None
    equipped_armor: Optional[str] = None
    equipped_shield: bool = False

    known_spells: List[str] = field(default_factory=list)
    spell_slots: int = 0
    max_spell_slots: int = 0

    # Class feature resources (simplified SRD-inspired)
    is_raging: bool = False
    rages: int = 0
    max_rages: int = 0
    rage_damage_bonus: int = 0
    reckless_next: bool = False

    bardic_inspiration: int = 0
    max_bardic_inspiration: int = 0
    bardic_inspiration_die: int = 0  # sides: 6/8/10/12
    inspired_die: int = 0  # sides granted to next attack roll

    rogue_hidden: bool = False

    rogue_sneak_dice: int = 0  # number of d6

    warlock_pact_slot_level: int = 1
    warlock_invocations_known: int = 0
    warlock_has_agonizing_blast: bool = False

    xp: int = 0
    gold: int = 0


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
    chapter: int = 1
    objective: Dict[str, Any] = field(default_factory=dict)
    phase: str = "character_creation"  # character_creation | adventure
    creation_state: Dict[str, str] = field(default_factory=dict)
    story: Dict[str, str] = field(default_factory=dict)
    won: bool = False
    lost: bool = False
    campaign_complete: bool = False

    visited_rooms: set[str] = field(default_factory=set)

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

    SENSORY_LINES = [
        "The air is cool and heavy on your tongue.",
        "A wet draft curls along the floor.",
        "Your footsteps echo, swallowed by distance.",
        "Dust stirs at the edges of your torchlight.",
        "Somewhere deeper, something drips in a slow, patient rhythm.",
        "The place smells of mineral damp and stale smoke.",
        "You taste old ash and stone.",
        "Silence presses close—broken only by your breathing.",
    ]

    THEME_DETAILS: Dict[str, List[str]] = {
        "mossy crypt": [
            "Green-black moss quilts the joints between ancient stones.",
            "Carved names line the walls, half-erased by time.",
            "A cracked sarcophagus lid lies askew.",
        ],
        "collapsed library": [
            "Shelves lie broken, their books spilled like bones.",
            "Loose pages cling to puddles, ink bleeding into gray swirls.",
            "A toppled lectern points accusingly toward the dark.",
        ],
        "goblin den": [
            "Crude fetishes hang from cord and sinew.",
            "Scraps of stolen gear glitter among the filth.",
            "A soot-stained firepit squats in the center.",
        ],
        "forgotten shrine": [
            "A defaced altar bears the scars of old iconoclasm.",
            "Crumbling offerings cups sit in a neat, unsettling row.",
            "Faded murals watch you with blank, flaking eyes.",
        ],
        "arcane workshop": [
            "Scorched circles mark the floor where rituals went wrong.",
            "Glassware glints from shattered benches.",
            "A copper smell lingers, sharp as a struck bell.",
        ],
        "fungal caverns": [
            "Pale mushrooms glow with a faint, cold light.",
            "Spongy growths soften the rock underfoot.",
            "A haze of spores drifts like lazy snow.",
        ],
        "blood-stained chapel": [
            "Dark stains mar the flagstones in long-dried streaks.",
            "Bent candlesticks crowd a ruined pew.",
            "A broken bell-rope dangles from the rafters.",
        ],
        "abandoned guard post": [
            "A splintered table sits beside a rack of dulled weapons.",
            "Old bootprints are preserved in dust like fossils.",
            "A watchman's stool lies on its side, hurriedly discarded.",
        ],
    }

    def _make_room_desc(self, rng: random.Random, theme: str) -> str:
        base_templates = [
            "You stand in a {theme}.",
            "You step into a {theme}.",
            "This is a {theme}.",
            "You find yourself in a {theme}.",
        ]
        base = _pick(rng, [t.format(theme=theme) for t in base_templates])
        sensory = _pick(rng, self.SENSORY_LINES)
        details = self.THEME_DETAILS.get(theme, [])
        detail = _pick(rng, details) if details else ""
        parts = [base, sensory]
        if detail:
            parts.append(detail)
        return " ".join(parts)

    MONSTERS = content_bestiary.MONSTERS
    BOSSES = content_bestiary.BOSSES

    ARTIFACTS = content_items.ARTIFACTS
    KEYS = content_items.KEYS
    POTIONS = content_items.POTIONS

    SPECIES = ["Human", "Halfling", "Elf", "Tiefling"]
    CLASSES = ["Barbarian", "Bard", "Rogue", "Warlock"]

    SPECIES_BONUSES: Dict[str, Dict[str, int]] = {
        # 5e (classic) style bonuses, kept intentionally simple.
        "Human": {"str": 1, "dex": 1, "con": 1, "int": 1, "wis": 1, "cha": 1},
        "Halfling": {"dex": 2},
        "Elf": {"dex": 2},
        "Tiefling": {"cha": 2, "int": 1},
    }

    CLASS_HIT_DIE: Dict[str, int] = {
        "Barbarian": 12,
        "Bard": 8,
        "Rogue": 8,
        "Warlock": 8,
    }

    CLASS_PRIMARY: Dict[str, str] = {
        "Barbarian": "str",
        "Bard": "cha",
        "Rogue": "dex",
        "Warlock": "cha",
    }

    # SRD-style XP thresholds (level 1..20). Indexed by level.
    XP_BY_LEVEL: Tuple[int, ...] = (
        0,  # unused 0-index
        0,
        300,
        900,
        2700,
        6500,
        14000,
        23000,
        34000,
        48000,
        64000,
        85000,
        100000,
        120000,
        140000,
        165000,
        195000,
        225000,
        265000,
        305000,
        355000,
    )

    BARBARIAN_RAGES_BY_LEVEL: Tuple[int, ...] = (
        0,
        2,
        2,
        3,
        3,
        3,
        4,
        4,
        4,
        4,
        4,
        4,
        5,
        5,
        5,
        5,
        5,
        6,
        6,
        6,
        6,
    )

    ROGUE_SNEAK_DICE_BY_LEVEL: Tuple[int, ...] = (
        0,
        1,
        1,
        2,
        2,
        3,
        3,
        4,
        4,
        5,
        5,
        6,
        6,
        7,
        7,
        8,
        8,
        9,
        9,
        10,
        10,
    )

    BARD_INSP_DIE_BY_LEVEL: Tuple[int, ...] = (
        0,
        6,
        6,
        6,
        6,
        8,
        8,
        8,
        8,
        8,
        10,
        10,
        10,
        10,
        10,
        12,
        12,
        12,
        12,
        12,
        12,
    )

    # UI keeps a single "spell slots" number; we map that to 1st-level slots for Bards.
    BARD_FIRST_LEVEL_SLOTS_BY_LEVEL: Tuple[int, ...] = (
        0,
        2,
        3,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
    )

    WARLOCK_SLOTS_BY_LEVEL: Tuple[int, ...] = (
        0,
        1,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        3,
        3,
        3,
        3,
        3,
        3,
        4,
        4,
        4,
        4,
    )

    WARLOCK_SLOT_LEVEL_BY_LEVEL: Tuple[int, ...] = (
        0,
        1,
        1,
        2,
        2,
        3,
        3,
        4,
        4,
        5,
        5,
        5,
        5,
        5,
        5,
        5,
        5,
        5,
        5,
        5,
        5,
    )

    WARLOCK_INVOCATIONS_BY_LEVEL: Tuple[int, ...] = (
        0,
        0,
        2,
        2,
        2,
        3,
        3,
        4,
        4,
        5,
        5,
        5,
        6,
        6,
        6,
        7,
        7,
        7,
        8,
        8,
        8,
    )

    WEAPONS: Dict[str, Dict[str, object]] = {
        "greataxe": {"kind": "melee", "damage": (1, 12), "properties": {"heavy"}},
        "rapier": {"kind": "melee", "damage": (1, 8), "properties": {"finesse"}},
        "dagger": {"kind": "melee", "damage": (1, 4), "properties": {"finesse", "light", "thrown"}},
        "shortsword": {"kind": "melee", "damage": (1, 6), "properties": {"finesse", "light"}},
        "mace": {"kind": "melee", "damage": (1, 6), "properties": set()},
        "shortbow": {"kind": "ranged", "damage": (1, 6), "properties": {"ammunition"}},
        "light crossbow": {"kind": "ranged", "damage": (1, 8), "properties": {"ammunition", "loading"}},
    }

    ARMOR: Dict[str, Dict[str, Optional[int]]] = {
        "leather armor": {"base": 11, "dex_cap": None},
        "chain shirt": {"base": 13, "dex_cap": 2},
        "chain mail": {"base": 16, "dex_cap": 0},
    }

    SHIELDS: Dict[str, int] = {
        "shield": 2,
    }

    SPELLS: Dict[str, Dict[str, object]] = {
        "eldritch blast": {"level": 0, "mode": "attack", "dice": (1, 10), "school": "evocation"},
        "fire bolt": {"level": 0, "mode": "attack", "dice": (1, 10), "school": "evocation"},
        "chill touch": {"level": 0, "mode": "attack", "dice": (1, 8), "school": "necromancy"},
        "vicious mockery": {"level": 0, "mode": "attack", "dice": (1, 4), "school": "enchantment"},
        "healing word": {"level": 1, "mode": "heal", "dice": (1, 4), "school": "evocation"},
        "dissonant whispers": {"level": 1, "mode": "attack", "dice": (3, 6), "school": "enchantment"},
    }

    ITEM_DESCRIPTIONS: Dict[str, str] = {
        "rope": "A sturdy coil of hemp rope. In a pinch, it can bind, climb, or secure.",
        "journal page": (
            "A torn journal page, written in a cramped hand. 'The warded door listens for iron and intent. "
            "If you find the relic, don't linger—follow the stair-mark and breathe the cold air like it's home.'"
        ),
        "chalk": "A stub of chalk—useful for marks, warnings, or quick symbols.",
        "ration": "Travel rations, dry but filling.",
        "lockpick": "A slim set of picks and tension tools, kept oiled and ready.",
        "healing potion": "A small vial that glows faintly. It smells of sharp herbs.",
        "greater healing potion": "A richer red draught—warm to the touch.",
        "superior healing potion": "A thick crimson draught that tastes like iron and thunder.",
        "potion of heroism": "A golden tincture that leaves your chest warm and your hands steady.",
        "potion of invisibility": "A clear liquid that refuses to catch the light. The vial looks empty until it moves.",
        "greataxe": "A heavy axe with a broad, hungry edge.",
        "rapier": "A slender blade made for precision and timing.",
        "dagger": "A simple knife balanced for quick strikes (and throwing).",
        "shortsword": "A short blade, quick in close quarters.",
        "mace": "A solid-headed mace, good for cracked bone and dented mail.",
        "shortbow": "A compact bow with a smooth draw.",
        "light crossbow": "A simple crossbow, slow to load but hard-hitting.",
        "holy water": "Blessed water in a stoppered flask. It stings the unclean.",
        "smoke bomb": "A fragile orb that bursts into thick, eye-watering smoke.",
        "antitoxin": "A bitter draught that fights venom in the blood.",
        "silver dust": "A pinch of glittering dust in a wax-paper twist. It clings to your fingertips.",
        "warding chalk": "Chalk mixed with salt and ash—meant for circles, sigils, and wards.",
        "coin pouch": "A small pouch with a few clinking coins.",
        "iron key": "A plain iron key, its teeth worn smooth by use. It feels heavier than it should.",
        "bone key": "A key carved from bone—polished, old, and unsettlingly warm.",
        "silver key": "A bright silver key that seems reluctant to tarnish.",
        "rune key": "A key etched with tiny sigils. It hums faintly when you hold it close to stone.",
        "leather armor": "Sturdy boiled leather armor—scuffed, but serviceable.",
        "chain shirt": "Interlocking rings sewn under leather. It whispers when you breathe.",
        "chain mail": "Heavy iron links and weighty certainty. Loud, but protective.",
        "shield": "A plain shield with dents that tell old stories.",
    }

    def _recompute_player_ac(self, p: Player) -> int:
        dex_mod = _ability_mod(p.ability_scores.get("dex", 10))
        con_mod = _ability_mod(p.ability_scores.get("con", 10))

        if p.equipped_armor:
            a = self.ARMOR.get(p.equipped_armor.lower())
            if a:
                base = int(a.get("base") or 10)
                cap = a.get("dex_cap")
                if cap is None:
                    ac = base + dex_mod
                else:
                    ac = base + min(dex_mod, int(cap))
            else:
                ac = 10 + dex_mod
        else:
            # Default class-based AC
            if p.char_class == "Barbarian":
                ac = 10 + dex_mod + con_mod
            else:
                ac = 11 + dex_mod

        if p.equipped_shield:
            ac += int(self.SHIELDS.get("shield", 2))
        return ac

    def _xp_for_level(self, level: int) -> int:
        level = _clamp(int(level), 1, 20)
        return int(self.XP_BY_LEVEL[level])

    def _level_for_xp(self, xp: int) -> int:
        xp = int(xp)
        for lvl in range(20, 0, -1):
            if xp >= self._xp_for_level(lvl):
                return lvl
        return 1

    def _proficiency_bonus_for_level(self, level: int) -> int:
        # +2 (1-4), +3 (5-8), +4 (9-12), +5 (13-16), +6 (17-20)
        return _clamp(2 + ((int(level) - 1) // 4), 2, 6)

    def _cantrip_scale(self, level: int) -> int:
        level = int(level)
        if level >= 17:
            return 4
        if level >= 11:
            return 3
        if level >= 5:
            return 2
        return 1

    def _apply_class_progression(self, p: Player) -> None:
        lvl = _clamp(int(p.level), 1, 20)
        p.proficiency_bonus = self._proficiency_bonus_for_level(lvl)

        if p.char_class == "Barbarian":
            p.max_rages = int(self.BARBARIAN_RAGES_BY_LEVEL[lvl])
            if lvl >= 16:
                p.rage_damage_bonus = 4
            elif lvl >= 9:
                p.rage_damage_bonus = 3
            else:
                p.rage_damage_bonus = 2
            p.rages = _clamp(p.rages, 0, p.max_rages)
        elif p.char_class == "Rogue":
            p.rogue_sneak_dice = int(self.ROGUE_SNEAK_DICE_BY_LEVEL[lvl])
        elif p.char_class == "Bard":
            p.bardic_inspiration_die = int(self.BARD_INSP_DIE_BY_LEVEL[lvl])
            cha_mod = _ability_mod(p.ability_scores.get("cha", 10))
            p.max_bardic_inspiration = max(1, cha_mod)
            p.bardic_inspiration = _clamp(p.bardic_inspiration, 0, p.max_bardic_inspiration)
            p.max_spell_slots = int(self.BARD_FIRST_LEVEL_SLOTS_BY_LEVEL[lvl])
            p.spell_slots = _clamp(p.spell_slots, 0, p.max_spell_slots)
        elif p.char_class == "Warlock":
            p.max_spell_slots = int(self.WARLOCK_SLOTS_BY_LEVEL[lvl])
            p.spell_slots = _clamp(p.spell_slots, 0, p.max_spell_slots)
            p.warlock_pact_slot_level = int(self.WARLOCK_SLOT_LEVEL_BY_LEVEL[lvl])
            p.warlock_invocations_known = int(self.WARLOCK_INVOCATIONS_BY_LEVEL[lvl])
            if lvl >= 2:
                p.warlock_has_agonizing_blast = True

    def _apply_asi(self, p: Player) -> Optional[str]:
        lvl = int(p.level)
        class_asi = {
            "Barbarian": {4, 8, 12, 16, 19},
            "Bard": {4, 8, 12, 16, 19},
            "Rogue": {4, 8, 10, 12, 16, 19},
            "Warlock": {4, 8, 12, 16, 19},
        }.get(p.char_class, set())
        if lvl not in class_asi:
            return None

        primary = self.CLASS_PRIMARY.get(p.char_class, "cha")
        secondary = "con" if primary != "con" else "dex"

        def bump(stat: str, amount: int, *, cap: int = 20) -> int:
            before = int(p.ability_scores.get(stat, 10))
            after = _clamp(before + amount, 1, cap)
            p.ability_scores[stat] = after
            return after - before

        gained = bump(primary, 2)
        if gained < 2:
            bump(secondary, 2 - gained)

        # Primal Champion (SRD): Barbarian 20
        if p.char_class == "Barbarian" and lvl >= 20:
            bump("str", 4, cap=24)
            bump("con", 4, cap=24)

        return "Ability Score Improvement applied."

    def _level_up_once(self, p: Player, rng: random.Random) -> Tuple[int, Optional[str]]:
        con_mod = _ability_mod(p.ability_scores.get("con", 10))
        hit_die = self.CLASS_HIT_DIE.get(p.char_class, 8)

        p.level += 1
        hp_gain = max(1, rng.randint(1, hit_die) + con_mod)
        p.max_hp += hp_gain
        p.hp += hp_gain

        asi_note = self._apply_asi(p)
        self._apply_class_progression(p)
        p.ac = self._recompute_player_ac(p)
        return hp_gain, asi_note

    def _award_xp_and_apply_levelups(self, game: Game, rng: random.Random, *, boss: bool) -> List[str]:
        p = game.player
        if p.level >= 20:
            return []

        # Chapter pacing: you can't out-level the current chapter.
        level_cap = _clamp(int(game.chapter), 1, 20)

        cur_floor = self._xp_for_level(p.level)
        next_floor = self._xp_for_level(min(20, p.level + 1))
        span = max(1, next_floor - cur_floor)

        gain = int(span * (0.35 if boss else 0.14))
        gain = max(25 if boss else 10, gain)
        p.xp += gain

        # Prevent banking enough XP to skip multiple levels when the chapter cap increases.
        if level_cap < 20:
            p.xp = min(p.xp, self._xp_for_level(level_cap + 1) - 1)
        lines = [f"You gain {gain} XP."]

        old_level = p.level
        new_level = min(self._level_for_xp(p.xp), level_cap)
        if new_level <= old_level:
            return lines

        gained_hp_total = 0
        for _ in range(new_level - old_level):
            hp_gain, asi_note = self._level_up_once(p, rng)
            gained_hp_total += hp_gain
            if asi_note:
                lines.append(asi_note)

        lines.append(f"You advance to level {p.level}. (+{gained_hp_total} max HP)")
        return lines

    FEATURE_DESCRIPTIONS: Dict[str, str] = content_features.FEATURE_DESCRIPTIONS

    SKULL_RIDDLES: List[Dict[str, object]] = list(content_riddles.SKULL_RIDDLES)
    DIAL_RIDDLES: List[Dict[str, object]] = list(content_riddles.DIAL_RIDDLES)

    # Indexes used for hint lookup (answer -> hints)
    SKULL_RIDDLE_HINTS: Dict[str, List[str]] = content_riddles.riddle_index(content_riddles.SKULL_RIDDLES)
    DIAL_RIDDLE_HINTS: Dict[str, List[str]] = content_riddles.riddle_index(content_riddles.DIAL_RIDDLES)

    PRESET_BUILDS: List[Dict[str, str]] = [
        {"name": "Human Barbarian", "species": "Human", "class": "Barbarian"},
        {"name": "Halfling Bard", "species": "Halfling", "class": "Bard"},
        {"name": "Elf Rogue", "species": "Elf", "class": "Rogue"},
        {"name": "Tiefling Warlock", "species": "Tiefling", "class": "Warlock"},
    ]

    def _chapter_dungeon_size(self, rng: random.Random, *, chapter: int) -> int:
        ch = _clamp(int(chapter), 1, MAX_CHAPTERS)
        # Start small and grow steadily; keep maps readable.
        growth = ((ch - 1) // 2) + ((ch - 1) // 3)  # 0..15 across chapters 1..20
        min_size = 8 + growth
        max_size = 12 + growth
        return int(rng.randint(min_size, max_size))

    def _chapter_tier(self, chapter: int) -> int:
        # 0..4 across chapters 1..20
        return _clamp((int(chapter) - 1) // 4, 0, 4)

    def new_game(self) -> Game:
        game_id = uuid.uuid4().hex
        seed = int(time.time() * 1000) ^ (uuid.uuid4().int & 0xFFFFFFFF)
        rng = random.Random(seed)

        dungeon_size = self._chapter_dungeon_size(rng, chapter=1)
        rooms, start_id, boss_id = self._generate_dungeon(rng, dungeon_size, chapter=1)

        objective = self._roll_objective(rng, chapter=1, previous_type=None)
        artifact = self._apply_objective_setup(rng, rooms, start_id=start_id, boss_id=boss_id, objective=objective)

        patron = _pick(rng, content_lore.PATRONS)
        place = _pick(rng, content_lore.PLACES)

        # Player is created during the character creation phase.
        placeholder_scores = {k: 10 for k in ABILITY_KEYS}
        player = Player(
            name="Adventurer",
            species="Human",
            char_class="Barbarian",
            level=1,
            ability_scores=placeholder_scores,
            hp=1,
            max_hp=1,
            ac=10,
            proficiency_bonus=2,
            inventory=[],
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
            chapter=1,
            objective=objective,
            phase="character_creation",
            story={"patron": patron, "place": place},
            log=[],
        )

        self._log(game, "Welcome to Text Adventure.")
        self._log(game, f"In {place}, you were hired by {patron}.")
        self._log(game, "Before you descend, choose who you are.")
        self._log(game, self._character_creation_prompt())
        return game

    def _roll_objective(self, rng: random.Random, *, chapter: int, previous_type: Optional[str]) -> Dict[str, Any]:
        ch = _clamp(int(chapter), 1, MAX_CHAPTERS)

        # Objective variety increases as the campaign goes deeper.
        types = [
            "recover_artifact",
            "slay_boss",
            "collect_sigils",
            "light_beacons",
            "rescue_prisoner",
            "cleanse_shrine",
        ]
        if ch >= 5:
            types.append("seal_portal")
        if ch >= 9:
            types.append("destroy_phylactery")

        if previous_type in types and len(types) > 1:
            types = [t for t in types if t != previous_type]
        t = _pick(rng, types)

        obj: Dict[str, Any] = {"type": t, "chapter": int(ch)}
        if t == "recover_artifact":
            obj["artifact"] = _pick(rng, self.ARTIFACTS)
            return obj
        if t == "slay_boss":
            return obj
        if t == "collect_sigils":
            sigil_pool = [
                "rune sigil (ember)",
                "rune sigil (tide)",
                "rune sigil (stone)",
                "rune sigil (gale)",
                "rune sigil (grave)",
                "rune sigil (dawn)",
                "rune sigil (night)",
            ]
            rng.shuffle(sigil_pool)
            obj["sigils"] = sigil_pool[:3]
            return obj
        if t == "light_beacons":
            obj["count"] = 3
            obj["lit"] = 0
            return obj
        if t == "rescue_prisoner":
            prisoner = _pick(rng, content_lore.PRISONERS)
            obj["prisoner"] = prisoner
            obj["rescued"] = "no"
            obj["key"] = _pick(rng, self.KEYS)
            return obj
        if t == "cleanse_shrine":
            obj["cleansed"] = "no"
            return obj
        if t == "seal_portal":
            obj["sealed"] = "no"
            obj["components"] = ["warding chalk", "silver dust"]
            return obj
        if t == "destroy_phylactery":
            obj["destroyed"] = "no"
            obj["phylactery"] = "black phylactery"
            return obj
        return obj

    def _apply_objective_setup(
        self,
        rng: random.Random,
        rooms: Dict[str, Room],
        *,
        start_id: str,
        boss_id: str,
        objective: Dict[str, Any],
    ) -> str:
        t = str(objective.get("type") or "recover_artifact")

        # A helper to pick a non-start, non-boss, non-exit room.
        def candidates() -> List[Room]:
            return [r for r in rooms.values() if r.id not in (start_id, boss_id) and (not r.is_exit)]

        if t == "recover_artifact":
            artifact = str(objective.get("artifact") or "")
            if artifact:
                rooms[boss_id].items.append(artifact)
            return artifact

        if t == "collect_sigils":
            sigils = list(objective.get("sigils") or [])
            self._place_objective_items(rng, rooms, start_id=start_id, boss_id=boss_id, items=sigils)
            return ""

        if t == "light_beacons":
            spots = candidates()
            rng.shuffle(spots)
            chosen = spots[:3]
            for r in chosen:
                r.scenery.setdefault(
                    "brazier",
                    "A soot-black brazier sits cold. It looks like it wants fire more than comfort.",
                )
                r.room_state.setdefault("brazier_lit", "no")
                r.desc += " A cold brazier squats here, waiting."
            return ""

        if t == "rescue_prisoner":
            spots = candidates()
            if spots:
                cage_room = rng.choice(spots)
                cage_room.scenery.setdefault(
                    "cage",
                    "An iron-bar cage is bolted to the floor. Someone watches you through the gaps with exhausted hope.",
                )
                cage_room.room_state.setdefault("cage_open", "no")
                cage_room.desc += " An iron cage has been wedged into a corner."

            # Place the needed key elsewhere so it's solvable without relying on the shop.
            key_item = str(objective.get("key") or "iron key")
            key_spots = [r for r in spots if ("cage" not in r.scenery)]
            if not key_spots:
                key_spots = spots
            if key_spots:
                rng.choice(key_spots).items.append(key_item)
            return ""

        if t == "cleanse_shrine":
            spots = candidates()
            shrine = next((r for r in spots if r.feature == "altar" or "chapel" in r.name.lower()), None)
            if shrine is None and spots:
                shrine = rng.choice(spots)
                shrine.feature = "altar"
            if shrine is not None:
                shrine.scenery.setdefault(
                    "defiled altar",
                    "An altar has been fouled with ash and old blood. The air tastes wrong around it.",
                )
                shrine.room_state.setdefault("altar_cleansed", "no")
                shrine.desc += " An altar here has been defaced, as if to dare the faithful."

            # Guarantee at least one holy water somewhere.
            if not any(any(it.lower() == "holy water" for it in r.items) for r in rooms.values()):
                pool = spots or list(rooms.values())
                if pool:
                    rng.choice(pool).items.append("holy water")
            return ""

        if t == "seal_portal":
            spots = candidates()
            if spots:
                portal = rng.choice(spots)
                portal.scenery.setdefault(
                    "rift",
                    "A hairline crack in the world hangs in the air like a wound. Cold wind breathes from it.",
                )
                portal.room_state.setdefault("rift_sealed", "no")
                portal.desc += " The air shivers here, as if reality is thin."

            comps = [str(c) for c in (objective.get("components") or [])]
            if comps:
                self._place_objective_items(rng, rooms, start_id=start_id, boss_id=boss_id, items=comps)
            return ""

        if t == "destroy_phylactery":
            name = str(objective.get("phylactery") or "black phylactery")
            rooms[boss_id].items.append(name)
            return ""

        return ""

    def _place_objective_items(
        self,
        rng: random.Random,
        rooms: Dict[str, Room],
        *,
        start_id: str,
        boss_id: str,
        items: List[str],
    ) -> None:
        candidates = [r for r in rooms.values() if r.id not in (start_id, boss_id) and (not r.is_exit)]
        if not candidates:
            return
        for it in items:
            rng.choice(candidates).items.append(it)

    def _objective_brief(self, game: Game) -> str:
        t = str((game.objective or {}).get("type") or "recover_artifact")
        if t == "slay_boss":
            return "Slay the dungeon's boss, then escape."
        if t == "collect_sigils":
            return "Collect the three rune sigils, then escape."
        if t == "light_beacons":
            need = int((game.objective or {}).get("count") or 3)
            return f"Light {need} ancient braziers, then escape."
        if t == "rescue_prisoner":
            who = str((game.objective or {}).get("prisoner") or "the prisoner")
            return f"Rescue {who}, then escape."
        if t == "cleanse_shrine":
            return "Cleanse the defiled altar, then escape."
        if t == "seal_portal":
            return "Seal the planar rift, then escape."
        if t == "destroy_phylactery":
            return "Destroy the black phylactery, then escape."
        art = str((game.objective or {}).get("artifact") or game.artifact_item or "artifact")
        return f"Recover the {art}, then escape."

    def _objective_leave_hint(self, game: Game) -> str:
        t = str((game.objective or {}).get("type") or "recover_artifact")
        if t == "slay_boss":
            return "A narrow stairway leads up… but you haven't slain the dungeon's master yet."
        if t == "collect_sigils":
            return "A narrow stairway leads up… but the sigils you need are still below."
        if t == "light_beacons":
            lit = int((game.objective or {}).get("lit") or 0)
            need = int((game.objective or {}).get("count") or 3)
            return f"A narrow stairway leads up… but only {lit}/{need} braziers burn with ancient flame."
        if t == "rescue_prisoner":
            who = str((game.objective or {}).get("prisoner") or "the prisoner")
            return f"A narrow stairway leads up… but {who} is still trapped below."
        if t == "cleanse_shrine":
            return "A narrow stairway leads up… but the shrine below is still defiled."
        if t == "seal_portal":
            return "A narrow stairway leads up… but the rift still breathes cold wind from beyond."
        if t == "destroy_phylactery":
            return "A narrow stairway leads up… but the phylactery remains intact."
        art = str((game.objective or {}).get("artifact") or game.artifact_item or "artifact")
        return f"A narrow stairway leads up… but you came for something. You need the {art}."

    def _objective_pickup_lines(self, game: Game, item: str) -> List[str]:
        t = str((game.objective or {}).get("type") or "recover_artifact")
        if t == "recover_artifact":
            art = str((game.objective or {}).get("artifact") or game.artifact_item or "")
            if art and item == art:
                return [
                    "For a heartbeat, everything goes quiet—like the dungeon is listening.",
                    "Whatever this is, it matters. Now you just have to get out with it.",
                ]
        if t == "collect_sigils":
            sigils = set([str(s).lower() for s in (game.objective or {}).get("sigils") or []])
            if item.lower() in sigils:
                return ["The sigil thrums faintly, as if it recognizes you."]
        if t == "destroy_phylactery":
            name = str((game.objective or {}).get("phylactery") or "black phylactery")
            if item.lower() == name.lower():
                return [
                    "The air chills as you lift it. Something on the far side of the world notices.",
                    "You should destroy it—now."
                ]
        return []

    def _objective_completed(self, game: Game) -> bool:
        t = str((game.objective or {}).get("type") or "recover_artifact")
        if t == "slay_boss":
            boss_room = game.rooms.get(game.boss_room_id)
            return bool(boss_room and (boss_room.monster is None or boss_room.monster.hp <= 0))
        if t == "collect_sigils":
            need = [str(s).lower() for s in (game.objective or {}).get("sigils") or []]
            have = set([it.lower() for it in game.player.inventory])
            return all(n in have for n in need)
        if t == "light_beacons":
            lit = int((game.objective or {}).get("lit") or 0)
            need = int((game.objective or {}).get("count") or 3)
            return lit >= need
        if t == "rescue_prisoner":
            return str((game.objective or {}).get("rescued") or "no") == "yes"
        if t == "cleanse_shrine":
            return str((game.objective or {}).get("cleansed") or "no") == "yes"
        if t == "seal_portal":
            return str((game.objective or {}).get("sealed") or "no") == "yes"
        if t == "destroy_phylactery":
            return str((game.objective or {}).get("destroyed") or "no") == "yes"
        art = str((game.objective or {}).get("artifact") or game.artifact_item or "")
        return bool(art and (art in game.player.inventory))

    def _character_creation_prompt(self) -> str:
        lines = ["Choose an existing build or create your own:"]
        for i, b in enumerate(self.PRESET_BUILDS, start=1):
            lines.append(f"  {i}) {b['name']}")
        lines.append("Commands: builds | choose <1-4> | custom | help")
        return "\n".join(lines)

    def _species_blurb(self) -> str:
        return (
            "Species (traits):\n"
            "  Human: +1 to all abilities (versatile, adaptable).\n"
            "  Halfling: +2 DEX (nimble, lucky-footed).\n"
            "  Elf: +2 DEX (keen senses, graceful).\n"
            "  Tiefling: +2 CHA, +1 INT (infernal presence, clever)."
        )

    def _class_blurb(self) -> str:
        return (
            "Classes (playstyle):\n"
            "  Barbarian: front-line bruiser; hits hard; tough (STR/CON).\n"
            "  Bard: support + tricks; heals and insults foes (CHA).\n"
            "  Rogue: mobile striker; excels at finesse and bows (DEX).\n"
            "  Warlock: pact-mage; powerful cantrip blasts (CHA)."
        )

    def _creation_help_text(self) -> str:
        return (
            "Character creation commands:\n"
            "  builds                 (list preset characters)\n"
            "  choose <1-4>           (pick a preset)\n"
            "  custom                 (start custom creation)\n"
            "  species <human|halfling|elf|tiefling>\n"
            "  class <barbarian|bard|rogue|warlock>\n"
            "  roll                   (roll stats: 4d6 drop lowest, six times)\n"
            "  species                (show species traits)\n"
            "  classes                (show class playstyles)\n"
            "\nAfter choosing a preset, or after 'roll' for custom, the adventure begins."
        )

    def _apply_species_bonuses(self, scores: Dict[str, int], species: str) -> Dict[str, int]:
        out = dict(scores)
        bonuses = self.SPECIES_BONUSES.get(species, {})
        for k, v in bonuses.items():
            out[k] = out.get(k, 10) + int(v)
        return out

    def _standard_array_for_class(self, char_class: str) -> Dict[str, int]:
        if char_class == "Barbarian":
            return {"str": 15, "con": 14, "dex": 13, "wis": 12, "int": 10, "cha": 8}
        if char_class == "Bard":
            return {"cha": 15, "dex": 14, "con": 13, "int": 12, "wis": 10, "str": 8}
        if char_class == "Rogue":
            return {"dex": 15, "int": 14, "con": 13, "wis": 12, "cha": 10, "str": 8}
        return {"cha": 15, "con": 14, "dex": 13, "int": 12, "wis": 10, "str": 8}

    def _starting_loadout(
        self, rng: random.Random, *, char_class: str, deterministic: bool = False
    ) -> Tuple[List[str], Optional[str], Optional[str], List[str], int]:
        inventory: List[str] = []
        equipped_melee: Optional[str] = None
        equipped_ranged: Optional[str] = None
        known_spells: List[str] = []
        max_slots = 0

        if deterministic:
            inventory.append("healing potion")
            inventory.append("rope")
        else:
            inventory.append(_pick(rng, self.POTIONS))
            inventory.append(_pick(rng, ["rope", "chalk", "ration"]))

        if char_class == "Barbarian":
            inventory.append("greataxe")
            equipped_melee = "greataxe"
        elif char_class == "Bard":
            inventory.extend(["rapier", "dagger"])
            equipped_melee = "rapier"
            known_spells = ["vicious mockery", "healing word"]
            max_slots = 2
        elif char_class == "Rogue":
            inventory.extend(["shortsword", "dagger", "shortbow"])
            equipped_melee = "shortsword"
            equipped_ranged = "shortbow"
        elif char_class == "Warlock":
            inventory.extend(["dagger"])
            equipped_melee = "dagger"
            known_spells = ["eldritch blast"]
            max_slots = 1

        return inventory, equipped_melee, equipped_ranged, known_spells, max_slots

    def _compute_ac(self, *, char_class: str, scores: Dict[str, int]) -> int:
        dex = _ability_mod(scores.get("dex", 10))
        con = _ability_mod(scores.get("con", 10))
        if char_class == "Barbarian":
            return 10 + dex + con
        return 11 + dex

    def _build_player(
        self,
        rng: random.Random,
        *,
        name: str,
        species: str,
        char_class: str,
        scores: Dict[str, int],
        deterministic: bool = False,
    ) -> Player:
        scores = self._apply_species_bonuses(scores, species)
        prof = self._proficiency_bonus_for_level(1)
        con_mod = _ability_mod(scores.get("con", 10))
        hit_die = self.CLASS_HIT_DIE.get(char_class, 8)
        max_hp = max(1, hit_die + con_mod)
        ac = self._compute_ac(char_class=char_class, scores=scores)  # Compute AC based on class and scores
        inventory, eq_melee, eq_ranged, spells, max_slots = self._starting_loadout(
            rng, char_class=char_class, deterministic=deterministic
        )
        p = Player(name=name,
                      species=species,
                      char_class=char_class,
                      level=1,
                      ability_scores={k: int(scores.get(k, 10)) for k in ABILITY_KEYS},
                      hp=max_hp,
                      max_hp=max_hp,
                      ac=ac,
                      proficiency_bonus=prof,
                      inventory=inventory,
                      equipped_melee=eq_melee,
                      equipped_ranged=eq_ranged,
                      known_spells=spells,
                      spell_slots=max_slots,
                      max_spell_slots=max_slots,
                      xp=0,
                      )

        self._apply_class_progression(p)
        if p.char_class == "Barbarian":
            p.rages = p.max_rages
        if p.char_class == "Bard":
            p.bardic_inspiration = p.max_bardic_inspiration

        return p

    def _generate_dungeon(self, rng: random.Random, size: int, *, chapter: int) -> Tuple[Dict[str, Room], str, str]:
        rooms: Dict[str, Room] = {}
        ids = [uuid.uuid4().hex[:8] for _ in range(size)]

        start_id = ids[0]
        boss_id = ids[-1]

        feature_by_theme = {
            "mossy crypt": "sarcophagus",
            "collapsed library": "shelves",
            "goblin den": "firepit",
            "forgotten shrine": "altar",
            "arcane workshop": "workbench",
            "fungal caverns": "mushrooms",
            "blood-stained chapel": "pews",
            "abandoned guard post": "weapons rack",
        }

        # Place rooms on a small grid so we can draw an ASCII map.
        offsets = {
            "north": (0, -1),
            "south": (0, 1),
            "east": (1, 0),
            "west": (-1, 0),
        }
        coord_to_id: Dict[Tuple[int, int], str] = {}
        id_to_coord: Dict[str, Tuple[int, int]] = {}

        def open_neighbors(x: int, y: int) -> List[Tuple[str, int, int]]:
            out: List[Tuple[str, int, int]] = []
            for d, (dx, dy) in offsets.items():
                nx, ny = x + dx, y + dy
                if (nx, ny) in coord_to_id:
                    continue
                out.append((d, nx, ny))
            return out

        # Start at origin.
        coord_to_id[(0, 0)] = start_id
        id_to_coord[start_id] = (0, 0)
        cursor_id = start_id

        for rid in ids[1:]:
            placed = False
            for _ in range(200):
                cx, cy = id_to_coord[cursor_id]
                choices = open_neighbors(cx, cy)
                if not choices:
                    cursor_id = rng.choice(list(id_to_coord.keys()))
                    continue
                d, nx, ny = rng.choice(choices)
                coord_to_id[(nx, ny)] = rid
                id_to_coord[rid] = (nx, ny)
                cursor_id = rid
                placed = True
                break
            if not placed:
                # Fallback: find any open spot adjacent to any placed room.
                for pid, (px, py) in list(id_to_coord.items()):
                    choices = open_neighbors(px, py)
                    if choices:
                        _, nx, ny = rng.choice(choices)
                        coord_to_id[(nx, ny)] = rid
                        id_to_coord[rid] = (nx, ny)
                        cursor_id = rid
                        placed = True
                        break
            if not placed:
                raise RuntimeError("Failed to place dungeon rooms on grid")

        # Create Room objects
        for rid in ids:
            theme = _pick(rng, self.ROOM_THEMES)
            name = theme.title()
            desc = self._make_room_desc(rng, theme)
            x, y = id_to_coord[rid]
            room = Room(id=rid, name=name, desc=desc, x=x, y=y, feature=feature_by_theme.get(theme, ""))
            rooms[rid] = room

        # Add ambient scenery to increase "look" targets and story texture.
        ch = _clamp(int(chapter), 1, MAX_CHAPTERS)
        scenery_chance = _clamp(0.25 + (ch * 0.01), 0.25, 0.50)
        scenery_pool: List[Tuple[str, str]] = [
            (
                "statue",
                "A cracked stone statue watches the room with a face worn smooth by time. Something about it feels deliberate.",
            ),
            (
                "fountain",
                "A dry fountain bowl is stained dark. A few drops still gather in the deepest crack, impossibly cold.",
            ),
            (
                "inscription",
                "An inscription curls along the stone in old script. Some letters have been gouged out, as if someone feared the words.",
            ),
            (
                "bones",
                "Old bones lie in a careless scatter, gnawed clean. The dungeon has eaten here before.",
            ),
            (
                "tapestry",
                "A moth-eaten tapestry hangs in tatters. A battle scene is stitched in faded thread—victory, then smoke.",
            ),
            (
                "mural",
                "A flaking mural depicts a door beneath three symbols: sun, moon, and star.",
            ),
            (
                "chains",
                "Rusty chains hang from iron rings set into the wall. They sway when you breathe.",
            ),
        ]
        placed_any = False
        for rid, r in rooms.items():
            if rid in (start_id, boss_id):
                continue
            if rng.random() > scenery_chance:
                continue
            key, text = _pick(rng, scenery_pool)
            if key in r.scenery:
                continue
            r.scenery[key] = text
            placed_any = True
            # Keep room descriptions short; mention only occasionally.
            if rng.random() < 0.20:
                r.desc += f" You notice a {key}."

        if not placed_any:
            candidates = [rid for rid in ids if rid not in (start_id, boss_id)]
            if candidates:
                rid = _pick(rng, candidates)
                key, text = _pick(rng, scenery_pool)
                rooms[rid].scenery[key] = text

        # Boss room gets a boss.
        boss_room = rooms[boss_id]
        boss_room.monster = self._make_monster(rng, boss=True, chapter=chapter)
        boss_room.desc += " The presence here is oppressive—something powerful lairs within."

        # Guaranteed path: connect in id order (placement is adjacent by construction).
        for i in range(size - 1):
            a, b = ids[i], ids[i + 1]
            ax, ay = id_to_coord[a]
            bx, by = id_to_coord[b]
            dx, dy = bx - ax, by - ay
            if dx == 1 and dy == 0:
                direction = "east"
            elif dx == -1 and dy == 0:
                direction = "west"
            elif dx == 0 and dy == 1:
                direction = "south"
            elif dx == 0 and dy == -1:
                direction = "north"
            else:
                # Shouldn't happen, but keep generation robust.
                direction = _pick(rng, list(DIRECTIONS.keys()))
            self._connect(rooms[a], rooms[b], direction)

        # Add extra connections for non-linearity (only between adjacent grid cells).
        extra_edges = rng.randint(3, max(4, (size // 2) + 1))
        for _ in range(extra_edges * 4):
            a = rng.choice(ids)
            ax, ay = id_to_coord[a]
            d, (dx, dy) = rng.choice(list(offsets.items()))
            bx, by = ax + dx, ay + dy
            b = coord_to_id.get((bx, by))
            if not b:
                continue
            if d in rooms[a].exits:
                continue
            self._connect(rooms[a], rooms[b], d)
            extra_edges -= 1
            if extra_edges <= 0:
                break

        # Place an exit room (different from boss room)
        exit_room_id = rng.choice(ids[:-1])
        rooms[exit_room_id].is_exit = True
        rooms[exit_room_id].desc += " A narrow stairway here leads back to the surface."

        self._place_puzzles_and_loot(rng, rooms, start_id, boss_id, chapter=chapter)
        return rooms, start_id, boss_id

    def _connect(self, a: Room, b: Room, direction: str) -> None:
        a.exits[direction] = b.id
        b.exits[DIRECTIONS[direction]] = a.id

    def _make_monster(self, rng: random.Random, boss: bool, *, chapter: int) -> Monster:
        if boss:
            name, hp, ac, atk, dmg, flavor = _pick(rng, list(self.BOSSES))
        else:
            name, hp, ac, atk, dmg, flavor = _pick(rng, list(self.MONSTERS))

        tier = self._chapter_tier(int(chapter))
        # Gentle scaling to keep later chapters tense without becoming unfair.
        hp = int(hp + (tier * (6 if boss else 3)) + rng.randint(0, tier * (4 if boss else 2)))
        ac = int(ac + (1 if (boss and tier >= 2) else 0) + (1 if (not boss and tier >= 3) else 0))
        atk = int(atk + (tier // 2))
        dmg_n, dmg_s = dmg
        if boss and tier >= 4:
            dmg_n = int(dmg_n + 1)
        elif (not boss) and tier >= 4 and dmg_s <= 6:
            dmg_s = 8

        return Monster(name=name, hp=hp, ac=ac, attack_bonus=atk, damage_die=(int(dmg_n), int(dmg_s)), flavor=flavor)

    def _place_puzzles_and_loot(self, rng: random.Random, rooms: Dict[str, Room], start_id: str, boss_id: str, *, chapter: int) -> None:
        room_ids = [rid for rid in rooms.keys() if rid not in (start_id, boss_id)]
        rng.shuffle(room_ids)

        locked_room_id = room_ids[0]
        key_room_id = room_ids[1] if len(room_ids) > 1 else start_id

        # Boss gate puzzle blocks entry to the boss room from at least one direction.
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
                if rng.random() < 0.65:
                    key_item = _pick(rng, self.KEYS)
                    rooms[key_room_id].items.append(key_item)
                    rooms[approach_id].puzzle = "locked_door"
                    rooms[approach_id].puzzle_state = {
                        "dir": dir_to_boss,
                        "key": key_item,
                        "unlocked": "no",
                    }
                    rooms[approach_id].desc += " A heavy door nearby is engraved with warding runes."
                else:
                    lever = _pick(rng, ["sun", "moon", "star"])
                    rooms[approach_id].puzzle = "lever_door"
                    rooms[approach_id].puzzle_state = {
                        "dir": dir_to_boss,
                        "lever": lever,
                        "unlocked": "no",
                    }
                    rooms[approach_id].scenery.setdefault(
                        "lever console",
                        "A waist-high console holds three iron levers marked with faded glyphs: sun, moon, and star.",
                    )
                    rooms[approach_id].desc += " A lever console stands before a sealed door."

                    # Place a clue elsewhere.
                    clue_candidates = [rid for rid in room_ids if rid not in (approach_id, boss_id) and rooms[rid].puzzle is None]
                    if clue_candidates:
                        clue_room = rooms[rng.choice(clue_candidates)]
                        clue_room.scenery.setdefault(
                            "graffiti",
                            f"Someone scratched a warning into the stone: 'The {lever} opens the way. The others bite.'",
                        )
                        clue_room.desc += " Scratched graffiti mars the stone, half-hidden under grime."

        # Riddle puzzle grants a useful item
        riddle_room_id = locked_room_id
        rooms[riddle_room_id].puzzle = "riddle"
        r1 = rng.choice(self.SKULL_RIDDLES)
        answer = str(r1.get("answer") or "time")
        prompt = str(r1.get("prompt") or "Name me, and I will grant you a gift.")
        rooms[riddle_room_id].puzzle_state = {
            "answer": answer,
            "prompt": prompt,
            "solved": "no",
            "reward": _pick(rng, ["smoke bomb", "holy water", "antitoxin", _pick(rng, self.POTIONS)]),
        }
        rooms[riddle_room_id].desc += " A talking skull rests on a pedestal, waiting."

        # A second riddle, if we have room for it.
        riddle2_id = next(
            (
                rid
                for rid in room_ids
                if rid not in (riddle_room_id, key_room_id) and rooms[rid].puzzle is None
            ),
            None,
        )
        if riddle2_id:
            rooms[riddle2_id].puzzle = "riddle"
            # Ensure the second riddle is a different prompt/answer.
            for _ in range(10):
                r2 = rng.choice(self.SKULL_RIDDLES)
                answer2 = str(r2.get("answer") or "shadow")
                if answer2.lower() != answer.lower():
                    break
            else:
                r2 = rng.choice(self.SKULL_RIDDLES)
                answer2 = str(r2.get("answer") or "shadow")
            prompt2 = str(r2.get("prompt") or "Speak, and be rewarded.")
            rooms[riddle2_id].puzzle_state = {
                "answer": answer2,
                "prompt": prompt2,
                "solved": "no",
                "reward": _pick(rng, ["smoke bomb", "holy water", "antitoxin", _pick(rng, self.POTIONS)]),
            }
            rooms[riddle2_id].desc += " A second skull has been set here, as if to mock the first."

        # Add a few optional puzzles for variety (scaled by chapter tier).
        tier = self._chapter_tier(int(chapter))
        extra_puzzles = 1 + tier
        puzzle_spots = [rid for rid in room_ids if rooms[rid].puzzle is None and (not rooms[rid].is_exit)]
        rng.shuffle(puzzle_spots)
        for rid in puzzle_spots[:extra_puzzles]:
            kind = _pick(rng, ["rune_dial", "trapped_chest"])
            if kind == "rune_dial":
                rooms[rid].puzzle = "rune_dial"
                r = rng.choice(self.DIAL_RIDDLES)
                ans = str(r.get("answer") or "key")
                prompt = str(r.get("prompt") or "Set the dial with intention.")
                rooms[rid].puzzle_state = {
                    "answer": ans,
                    "prompt": prompt,
                    "solved": "no",
                    "reward": _pick(rng, ["holy water", "antitoxin", _pick(rng, self.POTIONS)]),
                }
                rooms[rid].desc += " A stone dial set with runes is mounted in the wall."
            else:
                rooms[rid].puzzle = "trapped_chest"
                dc = 11 + tier
                rooms[rid].puzzle_state = {
                    "dc": str(dc),
                    "disarmed": "no",
                    "solved": "no",
                    "reward": _pick(rng, ["coin pouch", _pick(rng, self.POTIONS), "holy water", "antitoxin"]),
                }
                rooms[rid].desc += " A heavy chest sits here, its lock surrounded by suspicious scratches."

        # Sprinkle monsters and extra loot
        ch = _clamp(int(chapter), 1, MAX_CHAPTERS)
        monster_chance = _clamp(0.40 + (ch * 0.005), 0.40, 0.60)
        loot_chance = _clamp(0.30 + (ch * 0.003), 0.30, 0.45)
        for rid, room in rooms.items():
            if rid in (start_id, boss_id):
                continue
            if rng.random() < monster_chance and room.monster is None:
                room.monster = self._make_monster(rng, boss=False, chapter=chapter)
            if rng.random() < loot_chance:
                room.items.append(
                    _pick(
                        rng,
                        [
                            "rope",
                            "chalk",
                            "warding chalk",
                            "silver dust",
                            "ration",
                            "lockpick",
                            "dagger",
                            "shortsword",
                            "mace",
                            "shortbow",
                            "light crossbow",
                            "leather armor",
                            "shield",
                            _pick(rng, self.POTIONS),
                        ],
                    )
                )

        # Guarantee at least one quiet, lore-forward room (no combat).
        candidates = [
            r
            for r in rooms.values()
            if (r.id not in (start_id, boss_id)) and (not r.is_exit) and (r.puzzle is None)
        ]
        if not candidates:
            candidates = [r for r in rooms.values() if r.id not in (start_id, boss_id)]
        if candidates:
            lore_room = rng.choice(candidates)
            lore_room.monster = None
            lore_room.feature = "camp"
            if "journal page" not in lore_room.items:
                lore_room.items.append("journal page")
            lore_room.desc += (
                " A makeshift camp has been wedged into an alcove—old ash, a torn blanket, and a few careful stones."
                " A travelling merchant lingers here, eyes sharp and voice low."
                " A torn journal page lies in the dust, weighted by a small stone."
            )

    def snapshot(self, game: Game) -> dict:
        room = game.rooms[game.current_room_id]
        next_xp = None
        if game.player.level < 20:
            next_xp = self._xp_for_level(game.player.level + 1)
        return {
            "gameId": game.id,
            "seed": game.seed,
            "won": game.won,
            "lost": game.lost,
            "campaignComplete": game.campaign_complete,
            "phase": game.phase,
            "chapter": game.chapter,
            "maxChapters": MAX_CHAPTERS,
            "player": {
                "name": game.player.name,
                "species": game.player.species,
                "class": game.player.char_class,
                "level": game.player.level,
                "hp": game.player.hp,
                "maxHp": game.player.max_hp,
                "ac": game.player.ac,
                "proficiencyBonus": game.player.proficiency_bonus,
                "abilityScores": dict(game.player.ability_scores),
                "equipped": {
                    "melee": game.player.equipped_melee,
                    "ranged": game.player.equipped_ranged,
                    "armor": game.player.equipped_armor,
                    "shield": "shield" if game.player.equipped_shield else None,
                },
                "spells": list(game.player.known_spells),
                "spellSlots": game.player.spell_slots,
                "maxSpellSlots": game.player.max_spell_slots,
                "inventory": list(game.player.inventory),
                "xp": game.player.xp,
                "nextLevelXp": next_xp,
                "gold": game.player.gold,
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
            "dungeonMap": self._render_dungeon_minimap(game),
            "roomMap": self._render_room_view(game),
            # Back-compat string for any older UI code.
            "map": self._render_dungeon_minimap(game) + "\n\n" + self._render_room_view(game),
            "log": list(game.log[-200:]),
        }

    def _render_dungeon_minimap(self, game: Game) -> str:
        rooms = list(game.rooms.values())
        min_x = min(r.x for r in rooms)
        max_x = max(r.x for r in rooms)
        min_y = min(r.y for r in rooms)
        max_y = max(r.y for r in rooms)

        w = (max_x - min_x) + 1
        h = (max_y - min_y) + 1
        grid_w = max(1, (w * 2) - 1)
        grid_h = max(1, (h * 2) - 1)
        canvas = [[" " for _ in range(grid_w)] for _ in range(grid_h)]

        current = game.rooms[game.current_room_id]

        def symbol_for(r: Room) -> str:
            if r.id == current.id:
                return "P"
            if r.monster is not None and r.monster.hp > 0:
                return "M"
            if r.is_exit:
                return "E"
            if r.id == game.boss_room_id:
                return "B"
            if r.puzzle is not None and (r.puzzle_state.get("solved") != "yes") and (r.puzzle_state.get("unlocked") != "yes"):
                return "?"
            if r.items:
                return "*"
            return "."

        for r in rooms:
            ix = r.x - min_x
            iy = r.y - min_y
            cx = ix * 2
            cy = iy * 2
            if 0 <= cy < grid_h and 0 <= cx < grid_w:
                canvas[cy][cx] = symbol_for(r)

        for r in rooms:
            ix = (r.x - min_x) * 2
            iy = (r.y - min_y) * 2
            for _, target_id in r.exits.items():
                t = game.rooms.get(target_id)
                if t is None:
                    continue
                dx = t.x - r.x
                dy = t.y - r.y
                if dx == 1 and dy == 0 and (ix + 1) < grid_w:
                    canvas[iy][ix + 1] = "-"
                elif dx == -1 and dy == 0 and (ix - 1) >= 0:
                    canvas[iy][ix - 1] = "-"
                elif dx == 0 and dy == 1 and (iy + 1) < grid_h:
                    canvas[iy + 1][ix] = "|"
                elif dx == 0 and dy == -1 and (iy - 1) >= 0:
                    canvas[iy - 1][ix] = "|"

        return "\n".join("".join(row).rstrip() for row in canvas).rstrip()

    def _render_room_view(self, game: Game) -> str:
        room = game.rooms[game.current_room_id]
        # Wider, clearer top-down view. (Kept short vertically to stay readable.)
        w, h = 41, 13
        canvas = [[" " for _ in range(w)] for _ in range(h)]
        for x in range(w):
            canvas[0][x] = "-"
            canvas[h - 1][x] = "-"
        for y in range(h):
            canvas[y][0] = "|"
            canvas[y][w - 1] = "|"
        canvas[0][0] = "+"
        canvas[0][w - 1] = "+"
        canvas[h - 1][0] = "+"
        canvas[h - 1][w - 1] = "+"

        # Doors are explicitly marked with 'D' to reduce confusion.
        if "north" in room.exits:
            canvas[0][w // 2] = "D"
        if "south" in room.exits:
            canvas[h - 1][w // 2] = "D"
        if "west" in room.exits:
            canvas[h // 2][0] = "D"
        if "east" in room.exits:
            canvas[h // 2][w - 1] = "D"

        # Player near center.
        canvas[h // 2][w // 2] = "@"

        feature_symbol = self._feature_symbol(room.feature)
        if feature_symbol:
            canvas[2][3] = feature_symbol

        if room.monster is not None and room.monster.hp > 0:
            canvas[2][w // 2] = "m"
        if room.items:
            canvas[h - 3][w - 4] = "*"
        if room.puzzle is not None and (room.puzzle_state.get("solved") != "yes") and (room.puzzle_state.get("unlocked") != "yes"):
            canvas[2][w - 4] = "?"

        return "\n".join("".join(row).rstrip() for row in canvas)

    def _feature_symbol(self, feature: str) -> str:
        f = (feature or "").lower()
        if not f:
            return ""
        return {
            "sarcophagus": "S",
            "shelves": "H",
            "altar": "A",
            "workbench": "W",
            "mushrooms": "F",
            "pews": "P",
            "weapons rack": "R",
            "firepit": "T",
            "camp": "C",
        }.get(f, "#")

    def handle_command(self, game: Game, command: str) -> dict:
        if game.lost:
            return {"text": "The adventure is over. Refresh the page to begin anew.", "state": self.snapshot(game)}

        command = (command or "").strip()
        if not command:
            return {"text": "Say what you do.", "state": self.snapshot(game)}

        rng = random.Random()
        rng.setstate(game.rng_state)

        if game.phase == "character_creation":
            response_lines = self._handle_character_creation(game, rng, command)
            game.rng_state = rng.getstate()
            for line in response_lines:
                self._log(game, line)
            return {"text": "\n".join(response_lines), "state": self.snapshot(game)}

        verb, *rest = command.lower().split()
        arg = " ".join(rest).strip()

        if game.won:
            if game.campaign_complete or int(game.chapter) >= MAX_CHAPTERS:
                game.campaign_complete = True
                return {
                    "text": "You've completed the 20-level campaign. Refresh the page to begin a new run.",
                    "state": self.snapshot(game),
                }
            if verb in ("continue", "descend", "next"):
                response_lines = self._cmd_continue(game, rng)
                game.rng_state = rng.getstate()
                for line in response_lines:
                    self._log(game, line)
                return {"text": "\n".join(response_lines), "state": self.snapshot(game)}
            return {
                "text": "You've won this chapter. Type `continue` to descend again, or refresh to start over.",
                "state": self.snapshot(game),
            }

        response_lines: List[str] = []

        if verb in ("help", "?"):
            response_lines.append(self._help_text())
        elif verb in ("look", "l", "examine", "x"):
            response_lines.extend(self._cmd_look(game, rng, arg))
        elif verb in ("leave", "exit", "escape"):
            msg = self.try_win(game)
            response_lines.append(msg or "You find no way out from here.")
        elif verb in ("continue", "descend", "next"):
            response_lines.append("You can't continue until you've escaped this chapter.")
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
        elif verb in ("shop", "store", "merchant"):
            response_lines.extend(self._cmd_shop(game))
        elif verb in ("buy",):
            response_lines.extend(self._cmd_buy(game, arg))
        elif verb in ("sell",):
            response_lines.extend(self._cmd_sell(game, arg))
        elif verb in ("gold", "coins", "coin"):
            response_lines.append(f"You have {game.player.gold} gp.")
        elif verb in ("attack", "hit", "fight"):
            response_lines.extend(self._cmd_attack(game, rng, arg))
        elif verb in ("shoot", "fire"):
            response_lines.extend(self._cmd_shoot(game, rng, arg))
        elif verb in ("cast", "spell"):
            response_lines.extend(self._cmd_cast(game, rng, arg))
        elif verb in ("rage",):
            response_lines.extend(self._cmd_rage(game))
        elif verb in ("reckless",):
            response_lines.extend(self._cmd_reckless(game))
        elif verb in ("inspire", "inspiration"):
            response_lines.extend(self._cmd_inspire(game, rng))
        elif verb in ("hide", "stealth"):
            response_lines.extend(self._cmd_hide(game, rng))
        elif verb in ("hex",):
            response_lines.extend(self._cmd_hex(game, rng))
        elif verb in ("equip", "wield"):
            response_lines.extend(self._cmd_equip(game, arg))
        elif verb in ("spells",):
            response_lines.append(self._cmd_spells(game))
        elif verb in ("stats", "sheet"):
            response_lines.append(self._cmd_stats(game))
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
            "Commands: look | go <north|south|east|west> | take <item> | use <item> | equip <item> | "
            "attack | shoot | cast <spell> | spells | stats | inventory | rest | shop | buy <item> | sell <item> | gold | help\n"
            "Class features: rage | reckless | inspire | hide | hex\n"
            "Tips: Abbreviations n/s/e/w work. If you pick up a weapon/armor, `equip <name>` (or `use <name>`) to ready it. "
            "Some doors require keys. Some puzzles require answers."
        )

    def _handle_character_creation(self, game: Game, rng: random.Random, command: str) -> List[str]:
        cmd = (command or "").strip()
        if not cmd:
            return ["Choose a build (try `builds`)."]

        verb, *rest = cmd.lower().split()
        arg = " ".join(rest).strip()

        if verb in ("help", "?"):
            return [self._creation_help_text()]

        if verb in ("builds", "build", "list"):
            return [self._character_creation_prompt()]

        if verb in ("choose", "pick"):
            if not arg:
                return ["Choose which? (Example: `choose 2`)"]
            chosen = None
            if arg.isdigit():
                idx = int(arg)
                if 1 <= idx <= len(self.PRESET_BUILDS):
                    chosen = self.PRESET_BUILDS[idx - 1]
            else:
                for b in self.PRESET_BUILDS:
                    if arg in b["name"].lower() or arg == b["class"].lower():
                        chosen = b
                        break
            if chosen is None:
                return ["Unknown build. Try `builds`."]

            scores = self._standard_array_for_class(chosen["class"])
            game.player = self._build_player(
                rng,
                name=chosen["name"],
                species=chosen["species"],
                char_class=chosen["class"],
                scores=scores,
                deterministic=True,
            )
            game.phase = "adventure"
            patron = game.story.get("patron", "your patron")
            place = game.story.get("place", "your hometown")
            return [
                f"You are {game.player.name}.",
                f"Class: {game.player.char_class}  Species: {game.player.species}",
                self._cmd_stats(game),
                "",
                f"In {place}, {patron} promised you coin and favor for one thing:",
                self._objective_brief(game),
                "Find the stairway back up, and leave alive.",
                "",
                "You descend into the dungeon...",
                self._describe_room(game),
            ]

        if verb == "custom":
            game.creation_state = {"mode": "custom"}
            return [
                "Custom character creation:",
                "Step 1: Choose a species.",
                "Step 2: Choose a class.",
                "Step 3: Roll your stats.",
                "Commands: species <...> | class <...> | roll",
                f"Species: {', '.join(self.SPECIES)}",
                f"Classes: {', '.join(self.CLASSES)}",
                "Tip: type `species` or `classes` for more info.",
            ]

        if verb in ("species", "race"):
            if not arg:
                return [self._species_blurb()]
            species = arg.title()
            if species not in self.SPECIES:
                return ["Unknown species. Choose: " + ", ".join(self.SPECIES)]
            game.creation_state["species"] = species
            return [f"Species set to {species}. Now choose a class with `class <...>`."]

        if verb in ("classes", "classinfo") and not arg:
            return [self._class_blurb()]

        if verb == "class":
            if not arg:
                return ["Pick a class (barbarian/bard/rogue/warlock)."]
            cls = arg.title()
            if cls not in self.CLASSES:
                return ["Unknown class. Choose: " + ", ".join(self.CLASSES)]
            game.creation_state["class"] = cls
            return [f"Class set to {cls}. Now roll stats with `roll`."]

        if verb == "roll":
            species = game.creation_state.get("species")
            cls = game.creation_state.get("class")
            if not species or not cls:
                return ["Choose both `species <...>` and `class <...>` first."]
            rolled = {k: _roll_4d6_drop_lowest(rng) for k in ABILITY_KEYS}
            game.player = self._build_player(rng, name="Custom Hero", species=species, char_class=cls, scores=rolled)
            game.phase = "adventure"
            patron = game.story.get("patron", "your patron")
            place = game.story.get("place", "your hometown")
            return [
                "You roll your ability scores...",
                " ".join([f"{k.upper()} {game.player.ability_scores[k]}" for k in ABILITY_KEYS]),
                self._cmd_stats(game),
                "",
                f"In {place}, {patron} gave you a name and a warning.",
                self._objective_brief(game),
                "Find the stairway back up, and leave alive.",
                "",
                "You descend into the dungeon...",
                self._describe_room(game),
            ]

        return ["You haven't chosen a character yet. Try `builds`, `choose 1`, or `custom`."]

    def _cmd_stats(self, game: Game) -> str:
        p = game.player
        mods = {k: _ability_mod(p.ability_scores.get(k, 10)) for k in ABILITY_KEYS}
        mod_text = " ".join([f"{k.upper()} {p.ability_scores.get(k, 10)}({mods[k]:+d})" for k in ABILITY_KEYS])
        eq = []
        if p.equipped_melee:
            eq.append(f"melee={p.equipped_melee}")
        if p.equipped_ranged:
            eq.append(f"ranged={p.equipped_ranged}")
        if p.equipped_armor:
            eq.append(f"armor={p.equipped_armor}")
        if p.equipped_shield:
            eq.append("shield")
        eq_text = ", ".join(eq) if eq else "none"
        slots = f"{p.spell_slots}/{p.max_spell_slots}" if p.max_spell_slots else "-"
        return (
            f"{p.name} — Level {p.level} {p.species} {p.char_class}\n"
            f"HP {p.hp}/{p.max_hp}  AC {p.ac}  Proficiency +{p.proficiency_bonus}  Spell Slots {slots}  Gold {p.gold}gp\n"
            f"Abilities: {mod_text}\n"
            f"Equipped: {eq_text}"
        )

    def _cmd_spells(self, game: Game) -> str:
        p = game.player
        if not p.known_spells:
            return "You don't know any spells."
        lines = ["Known spells:"]
        for s in p.known_spells:
            info = self.SPELLS.get(s.lower())
            if info:
                lvl = int(info.get("level", 0))
                mode = str(info.get("mode", ""))
                lines.append(f"- {s} (level {lvl if lvl else 'cantrip'}, {mode})")
            else:
                lines.append(f"- {s}")
        if p.max_spell_slots:
            lines.append(f"Spell slots: {p.spell_slots}/{p.max_spell_slots}")
        return "\n".join(lines)

    def _cmd_equip(self, game: Game, arg: str) -> List[str]:
        p = game.player
        arg = (arg or "").strip().lower()
        if not arg:
            return ["Equip what?"]

        inv_item = next((it for it in p.inventory if arg in it.lower()), None)
        if inv_item is None:
            return ["You don't have that."]

        item_name = inv_item.lower()

        # Shield
        if item_name in self.SHIELDS:
            p.equipped_shield = True
            p.ac = self._recompute_player_ac(p)
            return [f"You strap on your {inv_item}. (AC {p.ac})"]

        # Armor
        if item_name in self.ARMOR:
            p.equipped_armor = item_name
            p.ac = self._recompute_player_ac(p)
            return [f"You don your {inv_item}. (AC {p.ac})"]

        # Weapons
        w = self.WEAPONS.get(item_name)
        if not w:
            return ["You can't equip that."]
        kind = str(w.get("kind"))
        if kind == "melee":
            p.equipped_melee = item_name
            return [f"You ready your {inv_item}."]
        p.equipped_ranged = item_name
        return [f"You ready your {inv_item}."]

    def _shop_available(self, game: Game) -> bool:
        room = game.rooms[game.current_room_id]
        return room.feature == "camp"

    SHOP_STOCK: Dict[str, int] = {
        "healing potion": 50,
        "greater healing potion": 150,
        "potion of heroism": 125,
        "potion of invisibility": 250,
        "rope": 5,
        "ration": 5,
        "chalk": 1,
        "warding chalk": 10,
        "silver dust": 25,
        "lockpick": 25,
        "holy water": 25,
        "antitoxin": 50,
        "dagger": 2,
        "mace": 5,
        "shortbow": 25,
        "leather armor": 10,
        "shield": 10,
    }

    def _cmd_shop(self, game: Game) -> List[str]:
        if not self._shop_available(game):
            return ["There's no merchant here."]
        lines = ["A travelling merchant has set out a small, careful display.", f"Gold: {game.player.gold} gp", "", "For sale:"]
        for name, price in sorted(self.SHOP_STOCK.items(), key=lambda kv: kv[0]):
            lines.append(f"  - {name} ({price} gp)")
        lines.append("")
        lines.append("Commands: buy <item> | sell <item>")
        return lines

    def _cmd_buy(self, game: Game, arg: str) -> List[str]:
        if not self._shop_available(game):
            return ["There's no merchant here."]
        target = (arg or "").strip().lower()
        if not target:
            return ["Buy what?"]
        match = next((name for name in self.SHOP_STOCK.keys() if target in name), None)
        if not match:
            return ["The merchant doesn't have that."]
        price = int(self.SHOP_STOCK[match])
        if game.player.gold < price:
            return [f"You don't have enough gold. ({game.player.gold}/{price} gp)"]
        game.player.gold -= price
        game.player.inventory.append(match)
        return [f"You buy {match} for {price} gp."]

    def _cmd_sell(self, game: Game, arg: str) -> List[str]:
        if not self._shop_available(game):
            return ["There's no merchant here."]
        target = (arg or "").strip().lower()
        if not target:
            return ["Sell what?"]
        idx = next((i for i, it in enumerate(game.player.inventory) if target in it.lower()), None)
        if idx is None:
            return ["You don't have that."]
        item = game.player.inventory[idx].lower()
        if item == "coin pouch":
            return ["The merchant eyes your coin pouch. 'That's already money.'"]
        base = int(self.SHOP_STOCK.get(item, 2))
        value = max(1, base // 2)
        game.player.inventory.pop(idx)
        game.player.gold += value
        # If you sold what you were wearing, update AC.
        if game.player.equipped_armor == item:
            game.player.equipped_armor = None
            game.player.ac = self._recompute_player_ac(game.player)
        if item == "shield" and game.player.equipped_shield:
            game.player.equipped_shield = False
            game.player.ac = self._recompute_player_ac(game.player)
        if game.player.equipped_melee == item:
            game.player.equipped_melee = None
        if game.player.equipped_ranged == item:
            game.player.equipped_ranged = None
        return [f"You sell {item} for {value} gp."]

    def _weapon_to_hit_bonus(self, player: Player, weapon_name: str) -> int:
        w = self.WEAPONS.get(weapon_name.lower())
        if not w:
            return player.proficiency_bonus
        props = set(w.get("properties", set()))
        if str(w.get("kind")) == "ranged":
            ability = "dex"
        elif "finesse" in props:
            ability = "dex" if _ability_mod(player.ability_scores.get("dex", 10)) >= _ability_mod(player.ability_scores.get("str", 10)) else "str"
        else:
            ability = "str"
        return player.proficiency_bonus + _ability_mod(player.ability_scores.get(ability, 10))

    def _spell_attack_bonus(self, player: Player) -> int:
        ability = self.CLASS_PRIMARY.get(player.char_class, "cha")
        return player.proficiency_bonus + _ability_mod(player.ability_scores.get(ability, 10))

    def _roll_damage(self, rng: random.Random, die: Tuple[int, int], *, crit: bool) -> int:
        n, sides = die
        total_n = n * (2 if crit else 1)
        return _roll(rng, total_n, sides)

    def _cmd_shoot(self, game: Game, rng: random.Random, arg: str) -> List[str]:
        room = game.rooms[game.current_room_id]
        if room.monster is None or room.monster.hp <= 0:
            return ["There is nothing here to shoot."]
        weapon = game.player.equipped_ranged
        if not weapon:
            return ["You don't have a ranged weapon equipped. (Try `equip shortbow`.)"]
        w = self.WEAPONS.get(weapon.lower())
        if not w or str(w.get("kind")) != "ranged":
            return ["That isn't a ranged weapon."]
        die = w.get("damage", (1, 6))  # type: ignore[assignment]
        to_hit = self._weapon_to_hit_bonus(game.player, weapon)

        advantage = False
        if room.combat_state.get("player_hidden") == "yes":
            advantage = True
            room.combat_state["player_hidden"] = "no"

        roll1 = rng.randint(1, 20)
        roll2 = rng.randint(1, 20) if advantage else None
        d20 = max(roll1, roll2) if roll2 is not None else roll1
        inspiration = 0
        if game.player.inspired_die:
            inspiration = rng.randint(1, game.player.inspired_die)
            game.player.inspired_die = 0
        total = d20 + to_hit + inspiration
        crit = d20 == 20
        dmg_mod = _ability_mod(game.player.ability_scores.get("dex", 10))
        if crit or total >= room.monster.ac:
            dmg = self._roll_damage(rng, die, crit=crit) + dmg_mod

            # Rogue Sneak Attack (simplified: once per fight)
            if (
                game.player.char_class == "Rogue"
                and room.combat_state.get("sneak_used") != "yes"
                and game.player.rogue_sneak_dice > 0
            ):
                extra_dice = game.player.rogue_sneak_dice * (2 if crit else 1)
                dmg += _roll(rng, extra_dice, 6)
                room.combat_state["sneak_used"] = "yes"

            # Warlock Hex: +1d6 necrotic per hit (doubled on crit)
            if game.player.char_class == "Warlock" and room.combat_state.get("hex") == "yes":
                dmg += _roll(rng, 2 if crit else 1, 6)

            dmg = max(0, dmg)
            room.monster.hp = max(0, room.monster.hp - dmg)
            adv_txt = " (adv)" if advantage else ""
            insp_txt = f"+{inspiration}" if inspiration else ""
            lines = [f"You fire your {weapon}{adv_txt} (roll {d20}+{to_hit}{insp_txt}={total}) for {dmg} damage."]
        else:
            adv_txt = " (adv)" if advantage else ""
            insp_txt = f"+{inspiration}" if inspiration else ""
            lines = [f"Your shot misses{adv_txt} (roll {d20}+{to_hit}{insp_txt}={total})."]
        if room.monster.hp <= 0:
            lines.append(self._on_monster_defeated(game, rng, room))
            return lines
        lines.extend(self._monster_attack(game, rng, room, room.monster))
        return lines

    def _cmd_cast(self, game: Game, rng: random.Random, arg: str) -> List[str]:
        p = game.player
        room = game.rooms[game.current_room_id]
        spell = (arg or "").strip().lower()
        if not spell:
            return ["Cast what? (Try `spells`.)"]

        known = {s.lower() for s in p.known_spells}
        if spell not in known:
            return ["You don't know that spell. (Try `spells`.)"]

        info = self.SPELLS.get(spell)
        if not info:
            return ["That spell feels fuzzy in your mind."]

        level = int(info.get("level", 0))
        mode = str(info.get("mode", ""))
        die = info.get("dice", (1, 4))  # type: ignore[assignment]

        # Cantrip scaling (SRD-style)
        if level == 0:
            scale = self._cantrip_scale(p.level)
            n, sides = die
            if spell == "eldritch blast":
                die = (scale, sides)
            else:
                die = (n * scale, sides)

        if level > 0:
            if p.spell_slots <= 0:
                return ["You're out of spell slots."]
            p.spell_slots -= 1

        if mode == "heal":
            ability = self.CLASS_PRIMARY.get(p.char_class, "cha")
            amount = self._roll_damage(rng, die, crit=False) + _ability_mod(p.ability_scores.get(ability, 10))
            amount = max(1, amount)
            before = p.hp
            p.hp = _clamp(p.hp + amount, 0, p.max_hp)
            return [f"You cast {spell}. (+{p.hp - before} HP)"]

        if room.monster is None or room.monster.hp <= 0:
            return ["There's nothing here to target."]
        to_hit = self._spell_attack_bonus(p)

        advantage = False
        if room.combat_state.get("player_hidden") == "yes":
            advantage = True
            room.combat_state["player_hidden"] = "no"

        roll1 = rng.randint(1, 20)
        roll2 = rng.randint(1, 20) if advantage else None
        d20 = max(roll1, roll2) if roll2 is not None else roll1
        inspiration = 0
        if p.inspired_die:
            inspiration = rng.randint(1, p.inspired_die)
            p.inspired_die = 0
        total = d20 + to_hit + inspiration
        crit = d20 == 20
        if crit or total >= room.monster.ac:
            dmg = self._roll_damage(rng, die, crit=crit)

            # Agonizing Blast (simplified): add CHA mod to each beam
            if spell == "eldritch blast" and p.char_class == "Warlock" and p.warlock_has_agonizing_blast:
                beams = int(die[0])
                dmg += beams * _ability_mod(p.ability_scores.get("cha", 10))

            if p.char_class == "Warlock" and room.combat_state.get("hex") == "yes":
                dmg += _roll(rng, 2 if crit else 1, 6)

            room.monster.hp = max(0, room.monster.hp - dmg)
            insp_txt = f"+{inspiration}" if inspiration else ""
            adv_txt = " (adv)" if advantage else ""
            lines = [f"You cast {spell}{adv_txt} (roll {d20}+{to_hit}{insp_txt}={total}) for {dmg} damage."]
        else:
            insp_txt = f"+{inspiration}" if inspiration else ""
            adv_txt = " (adv)" if advantage else ""
            lines = [f"Your spell misses{adv_txt} (roll {d20}+{to_hit}{insp_txt}={total})."]
        if room.monster.hp <= 0:
            lines.append(self._on_monster_defeated(game, rng, room))
            return lines
        lines.extend(self._monster_attack(game, rng, room, room.monster))
        return lines

    def _describe_room(self, game: Game) -> str:
        room = game.rooms[game.current_room_id]
        lines = [f"== {room.name} ==", room.desc]
        if room.monster is not None and room.monster.hp > 0:
            lines.append(room.monster.flavor)
        if room.items:
            lines.append("You see: " + ", ".join(room.items) + ".")
        if room.exits:
            lines.append("Exits: " + ", ".join(sorted(room.exits.keys())) + ".")
        if room.scenery:
            notable = sorted(list(room.scenery.keys()))
            if len(notable) > 5:
                notable = notable[:5] + ["..."]
            lines.append("Notable: " + ", ".join(notable) + ".")
        if room.is_exit:
            lines.append("A stairway leads up. (Try `leave`.)")
        if room.feature == "camp":
            lines.append("A merchant camp is here. (Try `shop`, `buy <item>`, `sell <item>`.)")
        if room.puzzle == "locked_door":
            key_name = room.puzzle_state.get("key", "key")
            lines.append(f"A rune-locked door is here. (Try `look door` / `look runes` / `use {key_name}`.)")
        if room.puzzle == "lever_door" and room.puzzle_state.get("unlocked") != "yes":
            lines.append("A sealed door is here. (Try `look lever console` / `look graffiti` / `use lever <sun|moon|star>`.)")
        if room.puzzle == "riddle" and room.puzzle_state.get("solved") != "yes":
            lines.append("A talking skull watches you. (Try `look skull`.)")
        if room.puzzle == "rune_dial" and room.puzzle_state.get("solved") != "yes":
            lines.append("A rune dial is set into the wall. (Try `look dial` / `use dial <word>`.)")
        if room.puzzle == "trapped_chest" and room.puzzle_state.get("solved") != "yes":
            lines.append("A suspicious chest waits here. (Try `look chest` / `use chest` / `use lockpick`.)")
        return "\n".join(lines)

    def _ability_check(self, rng: random.Random, player: Player, ability: str, dc: int) -> Tuple[int, int, bool]:
        roll = rng.randint(1, 20)
        mod = _ability_mod(player.ability_scores.get(ability, 10))
        total = roll + mod
        return roll, total, total >= dc

    def _cmd_look(self, game: Game, rng: random.Random, arg: str) -> List[str]:
        room = game.rooms[game.current_room_id]
        target = (arg or "").strip().lower()
        if not target:
            return [self._describe_room(game)]

        # Common synonyms
        if target in ("around", "room", "here"):
            return [self._describe_room(game)]

        # Merchant / shop
        if target in ("merchant", "shop", "shopkeeper", "trader", "vendor"):
            if room.feature != "camp":
                return ["You listen for the jingle of trade, but hear only dungeon silence."]
            return [
                "The merchant keeps their pack close and their smile cautious.",
                "'Gold spends the same in the dark,' they murmur. (Try `shop`, then `buy <item>`.)",
            ]

        # Door / runes (door puzzles)
        if target in ("door", "rune", "runes", "lock", "ward", "wards", "warding", "warding runes"):
            if room.puzzle not in ("locked_door", "lever_door"):
                return ["You search the stonework for a door worth noting, but find nothing unusual."]
            dir_to = room.puzzle_state.get("dir", "somewhere")
            unlocked = room.puzzle_state.get("unlocked") == "yes"
            lines = [
                "The door is iron-banded and set into the rock like a tomb seal.",
                f"It blocks the way {dir_to}.",
            ]
            if unlocked:
                lines.append("The runes are dim and cold. The lock has been broken.")
            else:
                if room.puzzle == "locked_door":
                    key_name = room.puzzle_state.get("key", "key")
                    lines.append("Warding runes crawl over the frame like faint embers.")
                    roll, total, ok = self._ability_check(rng, game.player, "int", 12)
                    if ok:
                        lines.append(f"You study them (INT check {roll} -> {total}). They name a key: the {key_name}.")
                        lines.append("A skilled hand might also pick the lock. (Try `use lockpick`.)")
                    else:
                        lines.append(f"You try to decipher them (INT check {roll} -> {total}), but the meaning slips away.")
                else:
                    lines.append("A ward seals the seam. The door doesn't want keys—it wants the right choice.")
                    lines.append("A lever console sits nearby. (Try `look lever console` / `use lever <sun|moon|star>`.)")
            return lines

        # Riddle skull
        if target in ("skull", "talking skull", "pedestal"):
            if room.puzzle != "riddle":
                return ["No skull addresses you here—only dust and stone."]
            solved = room.puzzle_state.get("solved") == "yes"
            expected = str(room.puzzle_state.get("answer", "")).lower()
            prompt = str(room.puzzle_state.get("prompt") or "")
            if solved:
                return [
                    "The skull sits slack-jawed now.",
                    "Whatever animus stirred within it has gone quiet.",
                ]
            hints = self.SKULL_RIDDLE_HINTS.get(expected, [])
            lines = [
                "The skull's teeth click softly as if counting your heartbeats.",
                (f"It rasps: '{prompt}'" if prompt else "It waits for a single word—spoken with certainty."),
                "(Try `use answer <word>`.)",
            ]
            if hints:
                roll, total, ok = self._ability_check(rng, game.player, "wis", 12)
                if ok:
                    hint = rng.choice(hints)
                    lines.append(f"A sudden intuition hits (WIS check {roll} -> {total}): {hint}")
                else:
                    lines.append(f"You search your memory (WIS check {roll} -> {total}), but grasp only fragments.")
            return lines

        # Rune dial puzzle
        if target in ("dial", "rune dial", "runes dial"):
            if room.puzzle != "rune_dial":
                return ["You look for a dial or mechanism, but see none."]
            if room.puzzle_state.get("solved") == "yes":
                return ["The dial sits inert now, its runes dulled as if ashamed."]
            expected = str(room.puzzle_state.get("answer", "")).lower()
            prompt = str(room.puzzle_state.get("prompt") or "")
            hints = self.DIAL_RIDDLE_HINTS.get(expected, [])
            lines = [
                "A ring of runes surrounds a stone dial that can be turned with a firm grip.",
                (prompt if prompt else "It feels like it wants a single word—set with intention."),
                "(Try `use dial <word>`.)",
            ]
            if hints:
                roll, total, ok = self._ability_check(rng, game.player, "int", 12)
                if ok:
                    hint = rng.choice(hints)
                    lines.append(f"You note etched wear-marks (INT check {roll} -> {total}): {hint}")
                else:
                    lines.append(f"You study the runes (INT check {roll} -> {total}) but learn little.")
            return lines

        # Trapped chest puzzle
        if target in ("chest", "lock", "trap"):
            if room.puzzle != "trapped_chest":
                return ["You don't see any chest worth worrying about."]
            if room.puzzle_state.get("solved") == "yes":
                return ["The chest lies open and empty now."]
            dc = int(room.puzzle_state.get("dc") or 12)
            disarmed = room.puzzle_state.get("disarmed") == "yes"
            if disarmed:
                return [
                    "The chest's trap has been disarmed. The lock is still stubborn, but harmless.",
                    "(Try `use chest`.)",
                ]
            return [
                "The chest is heavy and old. Fine scratches radiate from the keyhole like a spiderweb.",
                f"Your instincts say: trap. (DC ~{dc})",
                "(Try `use chest` or `use lockpick`.)",
            ]

        # Shrine dressing: offerings cups
        if target in ("cups", "offerings", "offering", "offerings cups", "offering cups"):
            if "shrine" not in room.name.lower() and room.feature != "altar":
                return ["You look for offerings, but there are none here."]
            roll, total, ok = self._ability_check(rng, game.player, "wis", 11)
            lines = [
                "Small offering cups sit in a careful row, each stained by old wax and older wine.",
                "Some are engraved with faded symbols—names of saints, or devils, or both.",
            ]
            if ok:
                lines.append(f"You notice a pattern (WIS check {roll} -> {total}): the cups align toward the deepest dark.")
                lines.append("It feels like an instruction: descend, retrieve, return." )
            else:
                lines.append(f"You search for meaning (WIS check {roll} -> {total}) and find only cold metal.")
            return lines

        # Feature objects
        for feature, desc in self.FEATURE_DESCRIPTIONS.items():
            if target == feature or target in feature:
                if room.feature != feature:
                    continue
                return [desc]

        # Scenery objects (dynamic per-room interactables)
        if room.scenery:
            matched = next(
                (
                    k
                    for k in sorted(room.scenery.keys(), key=len, reverse=True)
                    if target == k or target in k or k in target
                ),
                None,
            )
            if matched:
                lines = [str(room.scenery.get(matched) or "")]
                if matched == "brazier":
                    lit = room.room_state.get("brazier_lit") == "yes"
                    lines.append("It is burning." if lit else "It is unlit.")
                    if str((game.objective or {}).get("type")) == "light_beacons":
                        cur = int((game.objective or {}).get("lit") or 0)
                        need = int((game.objective or {}).get("count") or 3)
                        lines.append(f"Objective: {cur}/{need} braziers lit.")
                    lines.append("(Try `use brazier`.)")
                if matched == "cage":
                    opened = room.room_state.get("cage_open") == "yes"
                    lines.append("The cage door hangs open." if opened else "The cage door is locked.")
                    lines.append("(Try `use cage`.)")
                if matched == "defiled altar":
                    cleansed = room.room_state.get("altar_cleansed") == "yes"
                    lines.append("The altar is cleansed." if cleansed else "It is still defiled.")
                    lines.append("(Try `use defiled altar`.)")
                if matched == "rift":
                    sealed = room.room_state.get("rift_sealed") == "yes"
                    lines.append("The rift is sealed." if sealed else "The rift is open.")
                    lines.append("(Try `use rift`.)")
                return [ln for ln in lines if ln]

        # Exit / stairs
        if target in ("stairs", "stair", "surface", "exit"):
            if not room.is_exit:
                return ["You see no clear way up from here—only more dungeon."]
            if self._objective_completed(game):
                return ["The stairway leads to the surface. You've done what you came to do—now you can leave (`leave`)."]
            return [self._objective_leave_hint(game)]

        # Monster
        if room.monster is not None and room.monster.hp > 0:
            if target in room.monster.name.lower() or target in ("monster", "enemy", "foe"):
                return [room.monster.flavor]

        # Items (room or inventory)
        all_items = [it.lower() for it in room.items] + [it.lower() for it in game.player.inventory]
        matched = next((it for it in all_items if target in it), None)
        if matched:
            base = self.ITEM_DESCRIPTIONS.get(matched)
            if base:
                return [base]
            if matched in self.WEAPONS:
                w = self.WEAPONS[matched]
                dmg = w.get("damage", (1, 4))
                kind = w.get("kind", "")
                return [f"{matched.title()} ({kind}, {dmg[0]}d{dmg[1]})."]
            return ["You look it over, but it's hard to say more from here."]

        return ["You don't notice anything like that."]

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
            if item.lower() == "coin pouch":
                game.player.gold += 10
                return ["You take the coin pouch and count out 10 gp.", f"Gold: {game.player.gold} gp"]
            game.player.inventory.append(item)
            lines = [f"You take the {item}."]
            lines.extend(self._objective_pickup_lines(game, item))
            return lines

        # simple contains match
        for i, item in enumerate(room.items):
            if arg in item.lower():
                taken = room.items.pop(i)
                if taken.lower() == "coin pouch":
                    game.player.gold += 10
                    return ["You take the coin pouch and count out 10 gp.", f"Gold: {game.player.gold} gp"]
                game.player.inventory.append(taken)
                lines = [f"You take the {taken}."]
                lines.extend(self._objective_pickup_lines(game, taken))
                return lines

        return ["You don't see that here."]

    def _cmd_go(self, game: Game, rng: random.Random, direction: str) -> List[str]:
        direction = (direction or "").strip().lower()
        if direction in ("n", "s", "e", "w"):
            direction = {"n": "north", "s": "south", "e": "east", "w": "west"}[direction]

        room = game.rooms[game.current_room_id]

        escaped_line = None
        if room.monster is not None and room.monster.hp > 0:
            if room.combat_state.get("escape_ok") == "yes":
                room.combat_state["escape_ok"] = "no"
                escaped_line = "Using the distraction, you slip past your foe."
            else:
                return ["The enemy blocks your escape! You'll need to fight or find another way."]

        if not direction:
            return ["Go where?"]

        if direction not in room.exits:
            return ["No passage that way."]

        # door puzzles on this room
        if room.puzzle in ("locked_door", "lever_door"):
            if room.puzzle_state.get("dir") == direction and room.puzzle_state.get("unlocked") != "yes":
                if room.puzzle == "locked_door":
                    key_name = room.puzzle_state.get("key", "key")
                    return [f"The rune-locked door resists you. You'll need the {key_name} (or tools to pick it)."]
                return ["The sealed door refuses to budge. The console must be solved first."]

        game.current_room_id = room.exits[direction]
        new_room = game.rooms[game.current_room_id]

        # New room = new fight context.
        new_room.combat_state.clear()

        lines: List[str] = []
        if escaped_line:
            lines.append(escaped_line)
        lines.append(self._describe_room(game))

        # auto-trigger riddle hint
        if new_room.puzzle == "riddle" and new_room.puzzle_state.get("solved") != "yes":
            prompt = str(new_room.puzzle_state.get("prompt") or "")
            if prompt:
                lines.append(f"The skull's jaw chatters: '{prompt}' (Try `use answer <word>`.)")
            else:
                lines.append("A talking skull watches you. (Try `look skull` / `use answer <word>`.)")

        # If monster exists, it may ambush
        if new_room.monster is not None and new_room.monster.hp > 0 and rng.random() < 0.25:
            lines.append(f"{new_room.monster.name} lunges first!")
            lines.extend(self._monster_attack(game, rng, new_room, new_room.monster))

        return lines

    def _cmd_use(self, game: Game, rng: random.Random, arg: str) -> List[str]:
        room = game.rooms[game.current_room_id]
        arg = (arg or "").strip().lower()
        if not arg:
            return ["Use what?"]

        if arg.startswith("answer "):
            return self._cmd_answer_riddle(game, arg[len("answer ") :].strip())

        # Gear shortcut: allow `use <weapon/armor/shield>` as alias for equip.
        if arg in self.WEAPONS or arg in self.ARMOR or arg in self.SHIELDS:
            return self._cmd_equip(game, arg)

        # Smoke bomb: create an opening to escape one move.
        if "smoke bomb" in arg:
            idx = next((i for i, it in enumerate(game.player.inventory) if "smoke bomb" in it.lower()), None)
            if idx is None:
                return ["You don't have a smoke bomb."]
            if room.monster is None or room.monster.hp <= 0:
                return ["You crack the orb. Smoke blooms, then drifts away. (No threat here.)"]
            game.player.inventory.pop(idx)
            room.combat_state["escape_ok"] = "yes"
            return ["You smash the smoke bomb. Thick smoke floods the room.", "You can escape this room once. (Try `go <direction>`.)"]

        # Lockpick: pick locks on doors/chests/cages.
        if "lockpick" in arg:
            if not any("lockpick" in it.lower() for it in game.player.inventory):
                return ["You don't have lockpicks."]

            # Door lockpicking.
            if room.puzzle == "locked_door" and room.puzzle_state.get("unlocked") != "yes":
                roll, total, ok = self._ability_check(rng, game.player, "dex", 14)
                if ok:
                    room.puzzle_state["unlocked"] = "yes"
                    return [f"You work the warded lock (DEX check {roll} -> {total}). The runes gutter out."]
                return [f"Your picks scrape uselessly (DEX check {roll} -> {total}). The ward holds."]

            # Chest lockpicking.
            if room.puzzle == "trapped_chest" and room.puzzle_state.get("solved") != "yes":
                dc = int(room.puzzle_state.get("dc") or 12)
                roll, total, ok = self._ability_check(rng, game.player, "dex", dc)
                if ok:
                    room.puzzle_state["disarmed"] = "yes"
                    return [f"You find the trap's trigger (DEX check {roll} -> {total}) and disable it.", "Now you can open the chest. (Try `use chest`.)"]
                # small trap sting
                dmg = _roll(rng, 1, 6)
                game.player.hp = max(0, game.player.hp - dmg)
                if game.player.hp <= 0:
                    game.lost = True
                    return [f"Your pick slips. A needle snaps out—{dmg} damage.", "You collapse. Darkness takes you. (Refresh to start a new adventure.)"]
                return [f"You fumble the mechanism (DEX check {roll} -> {total}). A needle bites you for {dmg} damage."]

            # Cage lockpicking.
            if "cage" in room.scenery and room.room_state.get("cage_open") != "yes":
                roll, total, ok = self._ability_check(rng, game.player, "dex", 13)
                if ok:
                    room.room_state["cage_open"] = "yes"
                    if str((game.objective or {}).get("type")) == "rescue_prisoner":
                        game.objective["rescued"] = "yes"
                    return [f"You pick the cage lock (DEX check {roll} -> {total}).", "The captive staggers free, whispering thanks."]
                return [f"You can't find purchase in the lock (DEX check {roll} -> {total})."]

            return ["You don't see a lock here that your picks can help with."]

        # Unlock rune-locked door with the named key.
        if room.puzzle == "locked_door" and room.puzzle_state.get("unlocked") != "yes":
            required_key = str(room.puzzle_state.get("key", "")).lower()
            if required_key and (required_key in arg):
                if any(required_key == it.lower() for it in game.player.inventory):
                    room.puzzle_state["unlocked"] = "yes"
                    return [f"You turn the {required_key}. The warding runes gutter out."]
                return [f"You don't have the {required_key}."]

        # Lever-gated boss door.
        if room.puzzle == "lever_door" and room.puzzle_state.get("unlocked") != "yes":
            if arg.startswith("lever") or "lever console" in arg:
                parts = arg.split()
                if len(parts) < 2 or parts[-1].strip().lower() in ("lever", "console"):
                    return ["Choose a lever: `use lever sun` or `use lever moon` or `use lever star`."]
                chosen = parts[-1].strip().lower()
                expected = str(room.puzzle_state.get("lever") or "").lower()
                if chosen == expected:
                    room.puzzle_state["unlocked"] = "yes"
                    return ["The console clicks. Somewhere deep in the door, a lock gives way.", "The sealed door is unlocked."]
                # wrong lever: small punishment
                dmg = _roll(rng, 1, 6) + 1
                game.player.hp = max(0, game.player.hp - dmg)
                if game.player.hp <= 0:
                    game.lost = True
                    return [f"You pull the wrong lever. A jolt of force slams you—{dmg} damage.", "You collapse. Darkness takes you. (Refresh to start a new adventure.)"]
                return [f"You pull the {chosen} lever. The ward bites back—{dmg} damage.", "The door remains sealed."]

        # Convert any coin pouch in inventory into usable gold.
        if "coin" in arg and "pouch" in arg:
            idx = next((i for i, it in enumerate(game.player.inventory) if it.lower() == "coin pouch"), None)
            if idx is None:
                return ["You don't have a coin pouch."]
            game.player.inventory.pop(idx)
            game.player.gold += 10
            return ["You loosen the strings and count out 10 gp.", f"Gold: {game.player.gold} gp"]

        # Potion use
        if "potion" in arg:
            inv = [it.lower() for it in game.player.inventory]
            item_idx = next((i for i, it in enumerate(inv) if (arg in it and "potion" in it)), None)
            if item_idx is None:
                item_idx = next((i for i, it in enumerate(inv) if "potion" in it), None)
            if item_idx is None:
                return ["You don't have a potion."]
            potion = game.player.inventory.pop(item_idx).lower()

            if potion in ("healing potion", "greater healing potion", "superior healing potion"):
                if potion == "healing potion":
                    heal = _roll(rng, 2, 4) + 2
                elif potion == "greater healing potion":
                    heal = _roll(rng, 4, 4) + 4
                else:
                    heal = _roll(rng, 8, 4) + 8
                old = game.player.hp
                game.player.hp = _clamp(game.player.hp + heal, 0, game.player.max_hp)
                return [f"You drink the {potion} and recover {game.player.hp - old} HP."]

            if potion == "potion of heroism":
                game.player.inspired_die = max(game.player.inspired_die, 8)
                return ["You drink the potion of heroism. Your courage sharpens.", "(+1d8 to your next attack roll)"]

            if potion == "potion of invisibility":
                if room.monster is None or room.monster.hp <= 0:
                    return ["You drink it. For a moment, your hands fade—then return. (No immediate threat.)"]
                room.combat_state["player_hidden"] = "yes"
                room.combat_state["escape_ok"] = "yes"
                return ["You drink the potion and vanish from your foe's sight.", "Your next attack has advantage, and you can escape once. (Try `go <direction>`.)"]

            return ["You drink it, but nothing obvious happens."]

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
            idx = next((i for i, it in enumerate(game.player.inventory) if "holy water" in it.lower()), None)
            if idx is None:
                return ["You don't have holy water."]

            # Objective: cleanse a shrine.
            if "defiled altar" in room.scenery and str((game.objective or {}).get("type")) == "cleanse_shrine":
                if room.room_state.get("altar_cleansed") == "yes":
                    return ["The altar is already cleansed."]
                if room.monster is not None and room.monster.hp > 0:
                    return ["Not while something hostile watches your every move."]
                game.player.inventory.pop(idx)
                room.room_state["altar_cleansed"] = "yes"
                game.objective["cleansed"] = "yes"
                return ["You sprinkle holy water over the altar.", "The foulness recoils and breaks like a wave on stone.", "Objective complete."]

            if room.monster is None or room.monster.hp <= 0:
                return ["You sprinkle holy water. Nothing happens."]
            game.player.inventory.pop(idx)
            dmg = _roll(rng, 2, 6)
            room.monster.hp = max(0, room.monster.hp - dmg)
            lines = [f"Holy water sizzles on {room.monster.name}! It takes {dmg} radiant damage."]
            if room.monster.hp <= 0:
                lines.append(self._on_monster_defeated(game, rng, room))
            return lines

        if "antitoxin" in arg:
            idx = next((i for i, it in enumerate(game.player.inventory) if "antitoxin" in it.lower()), None)
            if idx is None:
                return ["You don't have antitoxin."]
            game.player.inventory.pop(idx)
            old = game.player.hp
            game.player.hp = _clamp(game.player.hp + (_roll(rng, 1, 4) + 1), 0, game.player.max_hp)
            return [f"You swallow the antitoxin. (+{game.player.hp - old} HP)"]

        # Rune dial puzzle interaction.
        if room.puzzle == "rune_dial" and room.puzzle_state.get("solved") != "yes":
            if arg.startswith("dial"):
                parts = arg.split(maxsplit=1)
                if len(parts) < 2:
                    return ["Set the dial to what word? (Example: `use dial shadow`)"]
                word = parts[1].strip().lower()
                expected = str(room.puzzle_state.get("answer") or "").lower()
                if word == expected:
                    room.puzzle_state["solved"] = "yes"
                    reward = str(room.puzzle_state.get("reward") or "trinket")
                    room.items.append(reward)
                    return ["The dial turns with a grinding sigh.", "The runes flare once, then fade.", f"A compartment opens, revealing {reward}."]
                return ["The dial shudders, then snaps back. Wrong."]

        # Trapped chest puzzle interaction.
        if room.puzzle == "trapped_chest" and room.puzzle_state.get("solved") != "yes":
            if "chest" in arg:
                if room.monster is not None and room.monster.hp > 0:
                    return ["Not while an enemy threatens you."]
                dc = int(room.puzzle_state.get("dc") or 12)
                if room.puzzle_state.get("disarmed") != "yes":
                    roll, total, ok = self._ability_check(rng, game.player, "dex", dc)
                    if ok:
                        room.puzzle_state["disarmed"] = "yes"
                        return [f"You find the mechanism (DEX check {roll} -> {total}) and disable it.", "Now you can open the chest safely. (Try `use chest` again.)"]
                    dmg = _roll(rng, 1, 6) + 1
                    game.player.hp = max(0, game.player.hp - dmg)
                    if game.player.hp <= 0:
                        game.lost = True
                        return [f"A spring snaps. A needle strikes—{dmg} damage.", "You collapse. Darkness takes you. (Refresh to start a new adventure.)"]
                    return [f"You trigger the trap (DEX check {roll} -> {total}). A needle strikes—{dmg} damage."]

                reward = str(room.puzzle_state.get("reward") or "coin pouch")
                room.puzzle_state["solved"] = "yes"
                room.items.append(reward)
                return ["You open the chest.", f"Inside, you find {reward}."]

        # Objective interactables
        if arg in ("brazier", "light brazier") and "brazier" in room.scenery:
            if room.monster is not None and room.monster.hp > 0:
                return ["Not while something hostile prowls nearby."]
            if room.room_state.get("brazier_lit") == "yes":
                return ["The brazier is already burning."]
            room.room_state["brazier_lit"] = "yes"
            if str((game.objective or {}).get("type")) == "light_beacons":
                game.objective["lit"] = int((game.objective or {}).get("lit") or 0) + 1
                cur = int((game.objective or {}).get("lit") or 0)
                need = int((game.objective or {}).get("count") or 3)
                return ["You coax a flame from the old coals. The brazier catches.", f"Objective: {cur}/{need} braziers lit."]
            return ["You light the brazier. The flame throws long shadows."]

        if "cage" in arg and "cage" in room.scenery:
            if room.monster is not None and room.monster.hp > 0:
                return ["Not while an enemy threatens you."]
            if room.room_state.get("cage_open") == "yes":
                return ["The cage is already open."]
            needed = str((game.objective or {}).get("key") or "").lower()
            if needed and any(needed == it.lower() for it in game.player.inventory):
                room.room_state["cage_open"] = "yes"
                if str((game.objective or {}).get("type")) == "rescue_prisoner":
                    game.objective["rescued"] = "yes"
                return [f"You unlock the cage with the {needed}.", "The captive steps out, trembling but alive.", "Objective complete."]
            if any("lockpick" in it.lower() for it in game.player.inventory):
                roll, total, ok = self._ability_check(rng, game.player, "dex", 13)
                if ok:
                    room.room_state["cage_open"] = "yes"
                    if str((game.objective or {}).get("type")) == "rescue_prisoner":
                        game.objective["rescued"] = "yes"
                    return [f"You pick the cage lock (DEX check {roll} -> {total}).", "The captive stumbles free.", "Objective complete."]
                return [f"You can't get the lock to give (DEX check {roll} -> {total})."]
            if needed:
                return [f"The cage is locked. You'll need the {needed} (or lockpicks)."]
            return ["The cage is locked tight."]

        if ("altar" in arg) and ("defiled altar" in room.scenery):
            if str((game.objective or {}).get("type")) != "cleanse_shrine":
                return ["You steady your breath at the altar, but your current task lies elsewhere."]
            if room.room_state.get("altar_cleansed") == "yes":
                return ["The altar is already cleansed."]
            if not any("holy water" in it.lower() for it in game.player.inventory):
                return ["You need holy water to cleanse it."]
            return ["To cleanse the altar, try `use holy water`."]

        if arg in ("rift", "portal") and "rift" in room.scenery:
            if str((game.objective or {}).get("type")) != "seal_portal":
                return ["You stare into the rift and feel it stare back. This isn't your task—yet."]
            if room.room_state.get("rift_sealed") == "yes":
                return ["The rift is already sealed."]
            if room.monster is not None and room.monster.hp > 0:
                return ["Not while an enemy threatens you."]
            comps = [str(c).lower() for c in (game.objective or {}).get("components") or []]
            inv = [it.lower() for it in game.player.inventory]
            missing = [c for c in comps if c not in inv]
            if missing:
                return ["You lack the components to seal it.", "Missing: " + ", ".join(missing) + "."]
            # consume components
            for c in comps:
                idx = next((i for i, it in enumerate(game.player.inventory) if it.lower() == c), None)
                if idx is not None:
                    game.player.inventory.pop(idx)
            room.room_state["rift_sealed"] = "yes"
            game.objective["sealed"] = "yes"
            return ["You draw a warding circle and cast silver dust into the wound.", "The rift shrinks, then snaps shut like a held breath released.", "Objective complete."]

        if "phylactery" in arg:
            name = str((game.objective or {}).get("phylactery") or "black phylactery").lower()
            if any(name == it.lower() for it in game.player.inventory) and str((game.objective or {}).get("type")) == "destroy_phylactery":
                if str((game.objective or {}).get("destroyed") or "no") == "yes":
                    return ["It's already destroyed."]
                if room.monster is not None and room.monster.hp > 0:
                    return ["Not while an enemy threatens you."]
                roll, total, ok = self._ability_check(rng, game.player, "wis", 12)
                # remove from inventory
                idx = next((i for i, it in enumerate(game.player.inventory) if it.lower() == name), None)
                if idx is not None:
                    game.player.inventory.pop(idx)
                if not ok:
                    dmg = _roll(rng, 1, 6)
                    game.player.hp = max(0, game.player.hp - dmg)
                    if game.player.hp <= 0:
                        game.lost = True
                        return [f"You crack it open, and the backlash hits you—{dmg} damage.", "You collapse. Darkness takes you. (Refresh to start a new adventure.)"]
                    game.objective["destroyed"] = "yes"
                    return [f"You smash the phylactery (WIS check {roll} -> {total}).", f"A cold scream rips through you for {dmg} damage—then fades.", "Objective complete."]
                game.objective["destroyed"] = "yes"
                return [f"You smash the phylactery (WIS check {roll} -> {total}).", "Whatever held it together unravels into harmless ash.", "Objective complete."]

        # Ambient interactions
        if ("statue" in arg) and ("statue" in room.scenery):
            if room.monster is not None and room.monster.hp > 0:
                return ["Not while an enemy threatens you."]
            if room.room_state.get("statue_touched") == "yes":
                return ["You've already searched the statue." ]
            room.room_state["statue_touched"] = "yes"
            roll, total, ok = self._ability_check(rng, game.player, "wis", 12)
            if ok:
                game.player.inspired_die = max(game.player.inspired_die, 6)
                return [f"You place a hand on the stone (WIS check {roll} -> {total}).", "For a moment, your doubts quiet. (+1d6 to your next attack roll)"]
            # small consolation loot
            if rng.random() < 0.50:
                room.items.append("coin pouch")
                return [f"You search the statue (WIS check {roll} -> {total}).", "Your fingers find a hidden niche with a coin pouch."]
            return [f"You search the statue (WIS check {roll} -> {total}), but find only cold stone."]

        if ("fountain" in arg) and ("fountain" in room.scenery):
            if room.monster is not None and room.monster.hp > 0:
                return ["Not while an enemy threatens you."]
            if room.room_state.get("fountain_used") == "yes":
                return ["The fountain offers nothing more."]
            room.room_state["fountain_used"] = "yes"
            roll, total, ok = self._ability_check(rng, game.player, "con", 11)
            if ok:
                old = game.player.hp
                game.player.hp = _clamp(game.player.hp + (_roll(rng, 1, 6) + 2), 0, game.player.max_hp)
                return [f"You drink a few cold drops (CON check {roll} -> {total}). (+{game.player.hp - old} HP)"]
            dmg = _roll(rng, 1, 4)
            game.player.hp = max(0, game.player.hp - dmg)
            if game.player.hp <= 0:
                game.lost = True
                return [f"The water burns like frost (CON check {roll} -> {total}). {dmg} damage.", "You collapse. Darkness takes you. (Refresh to start a new adventure.)"]
            return [f"The water burns like frost (CON check {roll} -> {total}). You take {dmg} damage."]

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

        weapon = game.player.equipped_melee or "fists"
        die: Tuple[int, int] = (1, 4)
        props: set = set()
        kind = "melee"
        if weapon != "fists":
            w = self.WEAPONS.get(weapon.lower())
            if w:
                die = w.get("damage", (1, 4))  # type: ignore[assignment]
                props = set(w.get("properties", set()))
                kind = str(w.get("kind", "melee"))

        if kind == "ranged":
            ability = "dex"
        elif "finesse" in props:
            ability = (
                "dex"
                if _ability_mod(game.player.ability_scores.get("dex", 10))
                >= _ability_mod(game.player.ability_scores.get("str", 10))
                else "str"
            )
        else:
            ability = "str"

        to_hit = self._weapon_to_hit_bonus(game.player, weapon)
        dmg_mod = _ability_mod(game.player.ability_scores.get(ability, 10))

        attacks = 2 if (game.player.char_class == "Barbarian" and game.player.level >= 5) else 1
        monster_adv = False
        for swing in range(attacks):
            if room.monster is None or room.monster.hp <= 0:
                break

            advantage = False
            if game.player.char_class == "Barbarian" and game.player.reckless_next and kind != "ranged":
                advantage = True
                monster_adv = True
                game.player.reckless_next = False

            if room.combat_state.get("player_hidden") == "yes":
                advantage = True
                room.combat_state["player_hidden"] = "no"

            roll1 = rng.randint(1, 20)
            roll2 = rng.randint(1, 20) if advantage else None
            d20 = max(roll1, roll2) if roll2 is not None else roll1

            inspiration = 0
            if game.player.inspired_die:
                inspiration = rng.randint(1, game.player.inspired_die)
                game.player.inspired_die = 0

            total = d20 + to_hit + inspiration
            crit = d20 == 20
            if crit or total >= room.monster.ac:
                dmg = self._roll_damage(rng, die, crit=crit) + dmg_mod

                # Barbarian Rage damage (simplified: STR-based attacks)
                if game.player.char_class == "Barbarian" and game.player.is_raging and ability == "str":
                    dmg += game.player.rage_damage_bonus

                # Barbarian Brutal Critical (SRD): extra weapon die on crit (9/13/17)
                if game.player.char_class == "Barbarian" and crit and weapon != "fists":
                    extra = 0
                    if game.player.level >= 17:
                        extra = 3
                    elif game.player.level >= 13:
                        extra = 2
                    elif game.player.level >= 9:
                        extra = 1
                    if extra:
                        dmg += _roll(rng, extra, die[1])

                # Rogue Sneak Attack (simplified: once per fight if using finesse/ranged)
                if (
                    game.player.char_class == "Rogue"
                    and room.combat_state.get("sneak_used") != "yes"
                    and game.player.rogue_sneak_dice > 0
                    and (kind == "ranged" or "finesse" in props)
                ):
                    extra_dice = game.player.rogue_sneak_dice * (2 if crit else 1)
                    dmg += _roll(rng, extra_dice, 6)
                    room.combat_state["sneak_used"] = "yes"

                # Warlock Hex: +1d6 necrotic per hit (doubled on crit)
                if game.player.char_class == "Warlock" and room.combat_state.get("hex") == "yes":
                    dmg += _roll(rng, 2 if crit else 1, 6)

                dmg = max(0, dmg)
                room.monster.hp = max(0, room.monster.hp - dmg)
                adv_txt = " (adv)" if advantage else ""
                insp_txt = f"+{inspiration}" if inspiration else ""
                prefix = "You attack" if swing == 0 else "You strike again"
                lines.append(f"{prefix} with {weapon}{adv_txt} (roll {d20}+{to_hit}{insp_txt}={total}) for {dmg} damage.")
            else:
                adv_txt = " (adv)" if advantage else ""
                insp_txt = f"+{inspiration}" if inspiration else ""
                prefix = "You miss" if swing == 0 else "You miss again"
                lines.append(f"{prefix} {room.monster.name}{adv_txt} (roll {d20}+{to_hit}{insp_txt}={total}).")

        if room.monster.hp <= 0:
            lines.append(self._on_monster_defeated(game, rng, room))
            return lines

        # monster retaliates
        lines.extend(self._monster_attack(game, rng, room, room.monster, advantage=monster_adv))

        return lines

    def _monster_attack(self, game: Game, rng: random.Random, room: Room, monster: Monster, *, advantage: bool = False) -> List[str]:
        if monster.hp <= 0:
            return []
        roll1 = rng.randint(1, 20)
        roll2 = rng.randint(1, 20) if advantage else None
        d20 = max(roll1, roll2) if roll2 is not None else roll1
        total = d20 + monster.attack_bonus
        crit = d20 == 20
        if crit or total >= game.player.ac:
            dmg_n, dmg_s = monster.damage_die
            dmg = _roll(rng, dmg_n * (2 if crit else 1), dmg_s)

            # Rogue Uncanny Dodge (SRD): halve one hit per fight (simplified)
            if game.player.char_class == "Rogue" and game.player.level >= 5 and room.combat_state.get("uncanny_used") != "yes":
                dmg = max(0, dmg // 2)
                room.combat_state["uncanny_used"] = "yes"

            game.player.hp = max(0, game.player.hp - dmg)
            adv_txt = " (adv)" if advantage else ""
            lines = [f"{monster.name} hits you{adv_txt} (roll {d20}+{monster.attack_bonus}={total}) for {dmg} damage."]
        else:
            adv_txt = " (adv)" if advantage else ""
            lines = [f"{monster.name} misses you{adv_txt} (roll {d20}+{monster.attack_bonus}={total})."]

        if game.player.hp <= 0:
            game.lost = True
            lines.append("You collapse. Darkness takes you. (Refresh to start a new adventure.)")

        return lines

    def _on_monster_defeated(self, game: Game, rng: random.Random, room: Room) -> str:
        name = room.monster.name if room.monster else "the foe"

        lines: List[str] = [f"{name} falls."]

        boss = room.id == game.boss_room_id
        lines.extend(self._award_xp_and_apply_levelups(game, rng, boss=boss))

        # Combat flags reset when a fight ends.
        room.combat_state.clear()

        # Rage ends after a fight in this simplified loop.
        if game.player.char_class == "Barbarian" and game.player.is_raging:
            game.player.is_raging = False
            lines.append("Your rage ebbs as the danger passes.")

        # drop small loot sometimes
        if room.monster and rng.random() < 0.35:
            room.items.append("coin pouch")
        if room.monster and room.monster.name == "Owlbear" and "ration" not in room.items:
            room.items.append("ration")
        if room.monster and room.monster.name in ("Wight",):
            room.items.append("holy water")
        return "\n".join(lines)

    def _apply_chapter_transition(self, game: Game, rng: random.Random) -> List[str]:
        p = game.player
        lines: List[str] = []

        target_level = _clamp(int(game.chapter), 1, 20)
        if p.level < target_level:
            # Guarantee one-at-a-time progression through levels 1..20 (chapter == level).
            p.xp = max(p.xp, self._xp_for_level(target_level))
            gained_hp_total = 0
            while p.level < target_level:
                hp_gain, asi_note = self._level_up_once(p, rng)
                gained_hp_total += hp_gain
                if asi_note:
                    lines.append(asi_note)
            lines.append(f"You advance to level {p.level}. (+{gained_hp_total} max HP)")

        # Between chapters, you get a full reset (a long rest in spirit).
        p.hp = p.max_hp
        if p.max_spell_slots:
            p.spell_slots = p.max_spell_slots
        if p.char_class == "Barbarian":
            p.rages = p.max_rages
            p.is_raging = False
            p.reckless_next = False
        if p.char_class == "Bard":
            p.bardic_inspiration = p.max_bardic_inspiration
            p.inspired_die = 0

        return lines

    def _cmd_continue(self, game: Game, rng: random.Random) -> List[str]:
        if int(game.chapter) >= MAX_CHAPTERS:
            game.campaign_complete = True
            return ["You've already conquered the deepest chapter. Your story is complete."]

        prev_type = str((game.objective or {}).get("type") or "")
        game.chapter = int(game.chapter) + 1

        transition_lines = self._apply_chapter_transition(game, rng)

        dungeon_size = self._chapter_dungeon_size(rng, chapter=int(game.chapter))
        rooms, start_id, boss_id = self._generate_dungeon(rng, dungeon_size, chapter=int(game.chapter))

        objective = self._roll_objective(rng, chapter=game.chapter, previous_type=prev_type)
        artifact = self._apply_objective_setup(rng, rooms, start_id=start_id, boss_id=boss_id, objective=objective)

        game.rooms = rooms
        game.current_room_id = start_id
        game.boss_room_id = boss_id
        game.objective = objective
        game.artifact_item = artifact
        game.won = False
        game.visited_rooms.clear()
        game.visited_rooms.add(start_id)

        patron = game.story.get("patron", "your patron")
        place = game.story.get("place", "your home")
        lines = [
            f"Chapter {game.chapter}: a new descent.",
            f"Back in {place}, {patron} sends word:",
            self._objective_brief(game),
        ]
        if transition_lines:
            lines.append("")
            lines.extend(transition_lines)
        lines.extend([
            "",
            "You steel yourself and head down again…",
            self._describe_room(game),
        ])
        return lines

    def _cmd_rage(self, game: Game) -> List[str]:
        p = game.player
        if p.char_class != "Barbarian":
            return ["You have no such fury to call upon."]
        if p.is_raging:
            p.is_raging = False
            return ["You let your rage gutter out."]
        if p.rages <= 0:
            return ["You're spent. No rages remain until you rest."]
        p.rages -= 1
        p.is_raging = True
        return [f"You fly into a rage. (Rages left: {p.rages}/{p.max_rages})"]

    def _cmd_reckless(self, game: Game) -> List[str]:
        p = game.player
        if p.char_class != "Barbarian":
            return ["You don't know how to fight recklessly like that."]
        p.reckless_next = not p.reckless_next
        return ["Reckless Attack primed for your next melee attack." if p.reckless_next else "You fight with caution again."]

    def _cmd_inspire(self, game: Game, rng: random.Random) -> List[str]:
        p = game.player
        if p.char_class != "Bard":
            return ["You lack that kind of practiced inspiration."]
        if p.bardic_inspiration <= 0 or p.bardic_inspiration_die <= 0:
            return ["You have no Bardic Inspiration left. (Rest to recover it.)"]
        p.bardic_inspiration -= 1
        p.inspired_die = p.bardic_inspiration_die
        return [
            f"You whisper a quick verse and steel your nerves. (+1d{p.inspired_die} to your next attack roll)",
            f"Bardic Inspiration: {p.bardic_inspiration}/{p.max_bardic_inspiration}",
        ]

    def _cmd_hide(self, game: Game, rng: random.Random) -> List[str]:
        p = game.player
        room = game.rooms[game.current_room_id]
        if p.char_class != "Rogue":
            return ["You don't have the instincts for that kind of vanishing act."]
        if room.monster is None or room.monster.hp <= 0:
            return ["You melt into the shadows for practice. (There's no immediate threat.)"]
        if room.combat_state.get("hide_used") == "yes":
            return ["You've already tried to hide in this fight."]

        # Simple stealth check. This is a text-adventure abstraction, not full 5e rules.
        roll, total, ok = self._ability_check(rng, p, "dex", 12)
        room.combat_state["hide_used"] = "yes"
        if not ok:
            return [f"You try to vanish (DEX check {roll} -> {total}), but your movement gives you away."]

        room.combat_state["player_hidden"] = "yes"
        return [
            f"You slip out of sight (DEX check {roll} -> {total}).",
            "Your next attack will have advantage.",
        ]

    def _cmd_hex(self, game: Game, rng: random.Random) -> List[str]:
        p = game.player
        room = game.rooms[game.current_room_id]
        if p.char_class != "Warlock":
            return ["You speak the word, but no pact answers."]
        if room.monster is None or room.monster.hp <= 0:
            return ["There's nothing here to curse."]
        if room.combat_state.get("hex") == "yes":
            return ["Your hex is already clinging to your foe."]
        if p.spell_slots <= 0:
            return ["You're out of spell slots."]

        p.spell_slots -= 1
        room.combat_state["hex"] = "yes"
        room.combat_state["hex_target"] = room.monster.name
        return [
            f"You whisper a cruel syllable and lay a hex upon {room.monster.name}.",
            "Your hits against it deal +1d6 necrotic damage (this fight).",
        ]

    def _cmd_rest(self, game: Game, rng: random.Random) -> List[str]:
        room = game.rooms[game.current_room_id]
        if room.monster is not None and room.monster.hp > 0:
            return ["Not with an enemy nearby."]
        heal = _roll(rng, 1, 8) + 2
        old = game.player.hp
        game.player.hp = _clamp(game.player.hp + heal, 0, game.player.max_hp)
        lines = [f"You rest for a moment, steadying your breath. (+{game.player.hp - old} HP)"]
        if game.player.max_spell_slots > 0:
            game.player.spell_slots = game.player.max_spell_slots
            lines.append("You focus and regain your spell slots.")
        if game.player.char_class == "Barbarian":
            game.player.rages = game.player.max_rages
            game.player.is_raging = False
            lines.append("Your fury settles. You feel your rage returning.")
        if game.player.char_class == "Bard":
            game.player.bardic_inspiration = game.player.max_bardic_inspiration
            game.player.inspired_die = 0
            lines.append("You steady your voice and feel inspiration return.")
        return lines

    def try_win(self, game: Game) -> Optional[str]:
        room = game.rooms[game.current_room_id]
        if not room.is_exit:
            return None
        if room.monster is not None and room.monster.hp > 0:
            return "Something hostile guards the way out."
        if not self._objective_completed(game):
            return "You can't leave yet. Your objective is still unfinished."
        game.won = True
        if int(game.chapter) >= MAX_CHAPTERS:
            game.campaign_complete = True
            return "You climb into daylight after the final descent. You've won the campaign."
        t = str((game.objective or {}).get("type") or "recover_artifact")
        header = f"Chapter {game.chapter} complete."
        if t == "slay_boss":
            body = "With the dungeon's master slain, you climb to the surface." 
        elif t == "collect_sigils":
            body = "The sigils hum in your pack as you climb into daylight." 
        elif t == "light_beacons":
            body = "Behind you, three ancient flames burn again—small lights pushing back a very old dark." 
        elif t == "rescue_prisoner":
            who = str((game.objective or {}).get("prisoner") or "the prisoner")
            body = f"You lead {who} up into clean air." 
        elif t == "cleanse_shrine":
            body = "You leave the altar cleansed, and the dungeon feels a fraction less hungry." 
        elif t == "seal_portal":
            body = "The rift is sealed. The cold wind is gone." 
        elif t == "destroy_phylactery":
            body = "The phylactery is broken. Whatever it bound can no longer cling so easily to this world." 
        else:
            art = str((game.objective or {}).get("artifact") or game.artifact_item or "artifact")
            body = f"You ascend to the surface with the {art}." 

        footer = "You can stop here for a complete chapter, or type `continue` to descend again."
        return "\n".join([header, body + " You've won!", footer])

    def _log(self, game: Game, text: str) -> None:
        game.log.append(text)
