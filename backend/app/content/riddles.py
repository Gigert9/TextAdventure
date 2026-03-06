from __future__ import annotations

from typing import Dict, List, TypedDict


class Riddle(TypedDict):
    prompt: str
    answer: str
    hints: List[str]


# Distinct skull riddles (prompt+answer), not one prompt with many answers.
# Keep the answers simple (single word) since the parser expects that.
SKULL_RIDDLES: List[Riddle] = [
    {
        "prompt": "I devour all; I bow to none. Name me, and I will grant you a gift.",
        "answer": "time",
        "hints": [
            "Clocks and calendars exist to measure it.",
            "It turns infants into elders and ruins into dust.",
        ],
    },
    {
        "prompt": "I speak without a mouth and answer without lungs. In empty halls I grow bold. What am I?",
        "answer": "echo",
        "hints": [
            "It is a sound that returns after bouncing off stone or wood.",
            "Try shouting into a cave, corridor, or well.",
        ],
    },
    {
        "prompt": "I follow you without feet, and flee you without running. What am I?",
        "answer": "shadow",
        "hints": [
            "It appears when your body blocks a light source.",
            "It shortens at noon and stretches at sunset.",
        ],
    },
    {
        "prompt": "Feed me and I live; give me drink and I die. What am I?",
        "answer": "fire",
        "hints": [
            "It needs fuel and air; smother it and it fades.",
            "Water can kill it, but it can also cook your meal.",
        ],
    },
    {
        "prompt": "I am the thing you carry until you speak. Once shared, I cannot be taken back. What am I?",
        "answer": "secret",
        "hints": [
            "It is hidden knowledge kept from others.",
            "A confession or gossip is how it escapes.",
        ],
    },
    {
        "prompt": "I bind without rope, yet I can break a heart. What am I?",
        "answer": "oath",
        "hints": [
            "A sworn promise can hold you tighter than chains.",
            "Knights, priests, and lovers all make them.",
        ],
    },
    {
        "prompt": "I am a wall with an opinion. I decide who becomes inside. What am I?",
        "answer": "door",
        "hints": [
            "It is a barrier on hinges with a handle or latch.",
            "A threshold you cross to enter a room.",
        ],
    },
    {
        "prompt": "I am small, but I move walls. I open without speaking. What am I?",
        "answer": "key",
        "hints": [
            "It fits into a lock and turns to release a bolt.",
            "Old ones have teeth; new ones can be carved runes.",
        ],
    },
    {
        "prompt": "I fall without mercy, and turn roads into guesses. What am I?",
        "answer": "night",
        "hints": [
            "It arrives when the sun is gone and lamps are needed.",
            "Stars are easiest to see during it.",
        ],
    },
    {
        "prompt": "I return even when no one invites me. I reveal what the dark tried to keep. What am I?",
        "answer": "sun",
        "hints": [
            "It brings dawn and casts the strongest shadows.",
            "Crops grow by its light, and vampires fear it.",
        ],
    },
    {
        "prompt": "I change my face, but not my loyalty. I follow you without feet. What am I?",
        "answer": "moon",
        "hints": [
            "Its phases wax and wane through a month.",
            "It pulls the tides and lights midnight roads.",
        ],
    },
    {
        "prompt": "I guide the lost with silent patience. A needle of light in the world's cloth. What am I?",
        "answer": "star",
        "hints": [
            "Sailors navigate by them; they form constellations.",
            "They are distant suns that glitter in the dark.",
        ],
    },
    {
        "prompt": "I am a book you cannot close. The past, still breathing. What am I?",
        "answer": "memory",
        "hints": [
            "It is what you recall after an event has ended.",
            "Songs and scars can both keep it alive.",
        ],
    },
    {
        "prompt": "I can be warmer than truth, and build castles from air. What am I?",
        "answer": "lie",
        "hints": [
            "It is a falsehood told to comfort, profit, or deceive.",
            "It collapses when tested against facts.",
        ],
    },
    {
        "prompt": "I cut clean. I weigh the same in light and dark. What am I?",
        "answer": "truth",
        "hints": [
            "It is what remains after all excuses are stripped away.",
            "It matches reality, even when it's unpleasant.",
        ],
    },
    {
        "prompt": "I am always with you until I am not. I fog glass and prove you're still here. What am I?",
        "answer": "breath",
        "hints": [
            "It is air moving in and out of your lungs.",
            "Hold it too long and your body will demand it.",
        ],
    },
    {
        "prompt": "I settle on forgotten names. I am the slow snowfall of ruined places. What am I?",
        "answer": "dust",
        "hints": [
            "It gathers on shelves and in tombs when nothing is disturbed.",
            "Wipe a finger across a table and you'll see it.",
        ],
    },
    {
        "prompt": "I am a river without a bed, and I write truth on steel. What am I?",
        "answer": "blood",
        "hints": [
            "It runs in veins and spills when you're wounded.",
            "It is red, and it clots when exposed to air.",
        ],
    },
    {
        "prompt": "I am the last architecture of the living. I rattle, but never lie. What am I?",
        "answer": "bone",
        "hints": [
            "It forms a skeleton and stays after flesh is gone.",
            "Break one and it will mend, but never quickly.",
        ],
    },
    {
        "prompt": "I tell the truth backward. I show a face, but never a soul. What am I?",
        "answer": "mirror",
        "hints": [
            "It is polished glass that reflects light.",
            "Left and right swap when you look into it.",
        ],
    },
    {
        "prompt": "I hide the wearer and reveal the world. I can lie while smiling. What am I?",
        "answer": "mask",
        "hints": [
            "It is worn on the face to conceal identity.",
            "Actors, thieves, and doctors all have versions of it.",
        ],
    },
    {
        "prompt": "I am made by walking, and I am a promise drawn on earth. What am I?",
        "answer": "road",
        "hints": [
            "It is a path that connects places and guides travel.",
            "It can be paved stone, packed dirt, or a worn trail.",
        ],
    },
    {
        "prompt": "You feel me more than you see me. I carry whispers and turn pages without hands. What am I?",
        "answer": "wind",
        "hints": [
            "It is moving air — gentle as a breeze or fierce as a gale.",
            "It makes banners flap and trees sway.",
        ],
    },
    {
        "prompt": "I fall on crowns and graves alike, and turn dust into truth. What am I?",
        "answer": "rain",
        "hints": [
            "It is water from clouds; it patters on roofs and armor.",
            "It makes streets slick and fills rivers.",
        ],
    },
    {
        "prompt": "I silence footsteps and make every road look the same. What am I?",
        "answer": "snow",
        "hints": [
            "It is frozen water that falls in flakes.",
            "It blankets the world white and numbs your toes.",
        ],
    },
    {
        "prompt": "I can lift sorrow without touching it, and make strangers share a heartbeat. What am I?",
        "answer": "song",
        "hints": [
            "It is music made with voice or instruments.",
            "Bards wield it; taverns are built around it.",
        ],
    },
]

# Rune-dial riddles: slightly more arcane phrasing.
DIAL_RIDDLES: List[Riddle] = [
    {
        "prompt": "Set the dial to the word that binds without rope, breaks without sound.",
        "answer": "oath",
        "hints": [
            "A vow sworn aloud carries weight even in silence.",
            "Paladins and cultists both live by it.",
        ],
    },
    {
        "prompt": "Set the dial to what opens without speaking, small enough to hide in a palm.",
        "answer": "key",
        "hints": [
            "Turn it in the lock and the bolt slides free.",
            "If you have the right one, a door stops being a wall.",
        ],
    },
    {
        "prompt": "Set the dial to what settles on forgotten names and turns bright metal dull.",
        "answer": "dust",
        "hints": [
            "Neglected rooms grow a coat of it.",
            "Disturb it and it rises in a sneeze.",
        ],
    },
    {
        "prompt": "Set the dial to the thing that tells the truth backward.",
        "answer": "mirror",
        "hints": [
            "Polished glass shows what stands before it.",
            "Your sword arm looks swapped when you stare into one.",
        ],
    },
    {
        "prompt": "Set the dial to what falls on crowns and graves alike.",
        "answer": "rain",
        "hints": [
            "Stormclouds deliver it in sheets or gentle taps.",
            "It soaks cloaks and makes mud out of dirt.",
        ],
    },
    {
        "prompt": "Set the dial to the silent needle of light that guides the lost.",
        "answer": "star",
        "hints": [
            "Navigators chart their course by it.",
            "It's a tiny point of light in the night sky — not the moon.",
        ],
    },
    {
        "prompt": "Set the dial to what is always with you until it isn't.",
        "answer": "breath",
        "hints": [
            "Without it, your body has minutes, not hours.",
            "You can see it in cold air as a faint cloud.",
        ],
    },
    {
        "prompt": "Set the dial to what follows you without feet and changes its face.",
        "answer": "moon",
        "hints": [
            "It waxes and wanes; wolves are said to heed it.",
            "It rules the tides and haunts the midnight sky.",
        ],
    },
    {
        "prompt": "Set the dial to what returns even when no one invites it.",
        "answer": "sun",
        "hints": [
            "It rises at dawn whether you wish it or not.",
            "Its light ends night and starts the day.",
        ],
    },
]


def riddle_index(riddles: List[Riddle]) -> Dict[str, List[str]]:
    """Convenience index: answer -> hints.

    Used only as a fallback for older saves/states.
    """

    out: Dict[str, List[str]] = {}
    for r in riddles:
        out[str(r["answer"]).lower()] = list(r.get("hints") or [])
    return out
