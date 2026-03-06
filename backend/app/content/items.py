from __future__ import annotations

from typing import Dict, List

ARTIFACTS: List[str] = [
    "Amulet of the Dawn",
    "Gem of Whispering Shadows",
    "Codex of Nine Sigils",
    "Chalice of the Moon",
    "Blade-Fragment of the Oath",
    "Crown Shard of the Hollow King",
    "Lantern of the Last Watch",
    "Mirror of the Seventh Veil",
    "Reliquary of Saint Ash",
    "Sealed Reliquary of Ember",
    "Tome of the Broken Pact",
    "Vial of Starfire",
]

KEYS: List[str] = [
    "iron key",
    "bone key",
    "silver key",
    "rune key",
]

POTIONS: List[str] = [
    "healing potion",
    "greater healing potion",
    "superior healing potion",
    "potion of heroism",
    "potion of invisibility",
]

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
    "black phylactery": "A black vessel that drinks sound. It feels wrong to hold.",
}

SHOP_STOCK: Dict[str, int] = {
    "healing potion": 50,
    "greater healing potion": 150,
    "superior healing potion": 300,
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
    "smoke bomb": 50,
    "dagger": 2,
    "mace": 5,
    "shortbow": 25,
    "leather armor": 10,
    "shield": 10,
}
