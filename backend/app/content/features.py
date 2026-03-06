from __future__ import annotations

from typing import Dict, List, Tuple

FEATURE_DESCRIPTIONS: Dict[str, str] = {
    "sarcophagus": "A stone sarcophagus lies cracked and half-open. The lid is etched with worn prayers.",
    "shelves": "Broken shelves sag under the memory of books. Loose pages whisper when your breath hits them.",
    "altar": "A defaced altar stands at the far end. Dried wax and old offerings cling to its surface.",
    "workbench": "A scorched workbench is scattered with snapped tools and cloudy vials.",
    "mushrooms": "Clusters of pale mushrooms glow softly. Spores drift like lazy snow.",
    "pews": "Bent pews crowd the room in crooked rows. Someone once prayed here—long ago.",
    "weapons rack": "A weapon rack holds dulled steel and cracked wood. The guards never came back for it.",
    "firepit": "A soot-black firepit squats in the center, ringed with gnawed bones and ash.",
    "camp": "A makeshift camp—old ash, a torn blanket, and a few careful stones. A travelling merchant keeps watch here, quiet as a mouse.",
    # Extra features for variety
    "cistern": "A stone cistern gathers slow drips from the ceiling. The water is too still to trust.",
    "banners": "Torn banners hang like dead skin. The heraldry has been scraped away with spite.",
    "runestone": "A waist-high runestone stands here, etched with lines that look like writing until you stare too long.",
    "armory": "Crates and racks lie smashed. A few weapon-hooks remain, still waiting for hands that will never return.",
    "cells": "Iron cell doors line the wall. Most hang open. One is shut, as if by choice.",
    "library desk": "A heavy desk has been dragged into the corner. Wax drips on old ledgers like sealed secrets.",
}

# Ambient scenery objects randomly sprinkled into rooms.
# Each is (key, description).
AMBIENT_SCENERY_POOL: List[Tuple[str, str]] = [
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
    (
        "basin",
        "A shallow stone basin holds dried residue and a single dark stain. Something was mixed here—carefully.",
    ),
    (
        "rubble",
        "Rubble has been piled with intent, not collapse. Someone made a barricade, then decided it wouldn't hold.",
    ),
]
