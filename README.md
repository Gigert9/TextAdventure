# TextAdventure (D&D-flavored, procedural)

A small web-based, D&D-inspired text adventure with procedural dungeons and ASCII maps.

- Frontend: vanilla HTML/CSS/JS
- Backend: FastAPI (Python)
- State: in-memory only (no DB)

## Features

- Procedural dungeon crawl with two ASCII maps:
	- **Dungeon map** (minimap of rooms + connections)
	- **Room map** (top-down view of the current room)
- Character creation:
	- Presets: Human Barbarian, Halfling Bard, Elf Rogue, Tiefling Warlock
	- Or go custom: pick species/class and roll stats (4d6 drop lowest)
- Combat + gear:
	- Weapons/armor/shield affect AC and attack options
	- Loot and gold; coin pouches convert to gp
- Puzzles:
	- Rune-locked doors that require keys
	- Riddle skulls (answer with a single word)
- Merchant camp:
	- `shop`, `buy <item>`, `sell <item>` when you find a camp room
- Progression:
	- XP + leveling from 1–20 (SRD-style thresholds)
	- Class scaling (rage, sneak attack dice, bardic inspiration die, warlock pact slots, cantrip scaling)
- Chapters:
	- After you win, you can `continue` to descend again into a new dungeon with a new objective.

## Objectives (per chapter)

Each chapter rolls one of these objectives:

- **Recover an artifact**, then escape.
- **Slay the boss**, then escape.
- **Collect three rune sigils**, then escape.

Once the objective is complete, find the exit stairway and `leave`.

## Commands

Character creation:

- `builds` (list presets)
- `choose <1-4>`
- `custom`
- `species <human|halfling|elf|tiefling>`
- `class <barbarian|bard|rogue|warlock>`
- `roll` (roll stats)
- `help`

Adventure:

- `look` (or `l`)
- `go <north|south|east|west>` (or `n/s/e/w`)
- `take <item>`
- `use <item>` (includes puzzle interactions)
- `equip <item>`
- `attack` / `shoot`
- `cast <spell>` / `spells`
- `inventory`
- `stats`
- `rest`
- `shop` / `buy <item>` / `sell <item>`
- `gold`
- `leave` (escape if you’re on the exit and your objective is done)
- `continue` (only after you’ve escaped a chapter)

Class feature commands:

- Barbarian: `rage`, `reckless`
- Bard: `inspire`

Tip: most item commands accept partial matches (e.g. `equip leather`).

## Map legends

Dungeon map:

- `P` = you
- `M` = monster
- `B` = boss room
- `E` = exit stairway
- `*` = items/loot
- `?` = unsolved puzzle
- `.` = empty/cleared room
- `-` and `|` = connections

Room map:

- Border `+ - |` = room walls
- `D` = doorway
- `@` = you
- `m` = monster
- `*` = items/loot
- `?` = puzzle

Room feature symbols:

- `F` = mushrooms
- `A` = altar
- `R` = weapons rack
- `S` = sarcophagus
- `H` = shelves
- `W` = workbench
- `P` = pews
- `T` = firepit
- `C` = camp / merchant

## Run locally

### 1) Create a venv + install deps

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
\.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2) Start the server

```powershell
uvicorn app.main:app --reload --port 8000
```

### 3) Play

Open http://127.0.0.1:8000

## State / persistence notes

- The server stores games in memory (no DB). Games expire after a TTL (default: 2 hours).
- The frontend starts a fresh game on each page load (and when you click “New Game”).
- To keep the same run going, keep the tab open.
