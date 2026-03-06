from __future__ import annotations

from typing import List, Tuple

MonsterRow = Tuple[str, int, int, int, Tuple[int, int], str]

MONSTERS: List[MonsterRow] = [
    ("Giant Rat", 5, 12, 3, (1, 4), "A giant rat bares yellow teeth, eyes bright with hunger."),
    ("Kobold", 5, 12, 3, (1, 4), "A kobold yips and jabs with a spear."),
    ("Goblin", 7, 13, 4, (1, 6), "A wiry goblin hisses, clutching a jagged blade."),
    ("Bandit", 11, 12, 3, (1, 6), "A cutpurse with a cruel grin weighs you with practiced eyes."),
    ("Skeleton", 10, 13, 4, (1, 6), "Bones clatter as a skeleton raises a rusted sword."),
    ("Zombie", 13, 8, 3, (1, 6), "A corpse shambles closer, mouthing words it can no longer speak."),
    ("Cultist", 9, 12, 3, (1, 6), "A hooded cultist murmurs a dark prayer."),
    ("Orc", 15, 13, 5, (1, 8), "An orc snarls, muscles tense beneath scarred hide."),
    ("Giant Spider", 16, 14, 5, (1, 8), "A giant spider clicks its mandibles and creeps forward."),
    ("Ghoul", 18, 12, 4, (2, 4), "A ghoul's nails scrape stone. It smells of graves."),
    ("Bugbear", 20, 14, 5, (2, 4), "A hulking bugbear hefts a spiked club, eager to smash."),
    ("Shadow", 16, 12, 5, (2, 4), "A living shadow peels off the wall, colder than fear."),
    ("Gargoyle", 22, 15, 5, (2, 4), "Stone cracks; a gargoyle unfolds, eyes like coals."),
    ("Ogre", 28, 11, 6, (2, 6), "An ogre lumbers in, drool and menace in equal measure."),
    ("Wraith", 24, 13, 6, (2, 6), "A wraith glides near, a hush following in its wake."),
    ("Helmed Horror", 30, 17, 6, (2, 4), "A floating suit of armor turns toward you with empty malice."),
]

BOSSES: List[MonsterRow] = [
    ("Hobgoblin Captain", 22, 15, 5, (1, 8), "A disciplined hobgoblin squares up, eyes cold."),
    ("Wight", 26, 14, 6, (1, 8), "A pallid wight glides forward, hunger in its gaze."),
    ("Owlbear", 30, 13, 6, (2, 6), "An owlbear bellows, feathers bristling."),
    ("Bugbear Chief", 34, 15, 6, (2, 6), "A bugbear chief looms, trophies clacking against its fur."),
    ("Necromancer Adept", 32, 13, 6, (2, 4), "A necromancer's eyes shine with borrowed life."),
    ("Troll", 42, 13, 7, (2, 6), "A troll grins, too many teeth in a mouth too wide."),
    ("Minotaur", 46, 14, 7, (2, 6), "A minotaur stamps the stone, snorting like a forge-bellows."),
    ("Vampire Spawn", 44, 15, 7, (2, 6), "A pale predator smiles without warmth, fangs catching the light."),
    ("Bone Naga", 48, 15, 7, (2, 6), "A serpent of bone coils, runes glowing in its ribs."),
    ("Young Dragon", 60, 16, 8, (2, 8), "Scaled wings stir stale air. A young dragon watches, amused."),
]
