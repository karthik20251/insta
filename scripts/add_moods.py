"""One-time migration: tag every day in quotes.json with a mood.

Moods: regal | dark | tense | contemplative | energetic | mysterious

The pick_music() picker prefers tracks matching the day's mood, falling back
to the book-wide pool if no mood-matched track exists.
"""
import json
from pathlib import Path

QUOTES = Path(__file__).parent.parent / "quotes.json"

MOODS = {
    # === 48 Laws of Power (Days 1-49) ===
    1:  "regal",          # Introduction
    2:  "regal",          # Law 1 — Never Outshine the Master
    3:  "tense",          # Law 2 — Use enemies
    4:  "mysterious",     # Law 3 — Conceal Intentions
    5:  "contemplative",  # Law 4 — Say Less
    6:  "regal",          # Law 5 — Reputation
    7:  "energetic",      # Law 6 — Court Attention
    8:  "regal",          # Law 7 — Get others to work
    9:  "tense",          # Law 8 — Bait
    10: "energetic",      # Law 9 — Win through actions
    11: "contemplative",  # Law 10 — Avoid unhappy
    12: "tense",          # Law 11 — Dependence
    13: "mysterious",     # Law 12 — Selective honesty
    14: "tense",          # Law 13 — Self-interest
    15: "mysterious",     # Law 14 — Pose as friend, spy
    16: "dark",           # Law 15 — Crush enemy
    17: "contemplative",  # Law 16 — Absence
    18: "tense",          # Law 17 — Unpredictability
    19: "tense",          # Law 18 — Don't isolate
    20: "tense",          # Law 19 — Know the person
    21: "tense",          # Law 20 — Don't commit
    22: "mysterious",     # Law 21 — Play sucker
    23: "contemplative",  # Law 22 — Surrender
    24: "regal",          # Law 23 — Concentrate forces
    25: "regal",          # Law 24 — Courtier
    26: "energetic",      # Law 25 — Re-create yourself
    27: "mysterious",     # Law 26 — Hands clean
    28: "mysterious",     # Law 27 — Cult following
    29: "energetic",      # Law 28 — Boldness
    30: "regal",          # Law 29 — Plan to end
    31: "regal",          # Law 30 — Effortless
    32: "tense",          # Law 31 — Control options
    33: "mysterious",     # Law 32 — Fantasies
    34: "dark",           # Law 33 — Thumbscrew
    35: "regal",          # Law 34 — Be royal
    36: "contemplative",  # Law 35 — Timing
    37: "contemplative",  # Law 36 — Disdain
    38: "regal",          # Law 37 — Spectacles
    39: "tense",          # Law 38 — Think like, behave
    40: "tense",          # Law 39 — Stir waters
    41: "tense",          # Law 40 — Free lunch
    42: "contemplative",  # Law 41 — Great man's shoes
    43: "dark",           # Law 42 — Strike shepherd
    44: "regal",          # Law 43 — Hearts and minds
    45: "mysterious",     # Law 44 — Mirror
    46: "contemplative",  # Law 45 — Gradual change
    47: "contemplative",  # Law 46 — Not too perfect
    48: "regal",          # Law 47 — When to stop
    49: "mysterious",     # Law 48 — Formlessness

    # === Atomic Habits (Days 50-79) ===
    50: "energetic",      # Intro
    51: "energetic",      # Compound effect
    52: "regal",          # Systems
    53: "contemplative",  # Plateau
    54: "contemplative",  # Identity
    55: "regal",          # Habit loop
    56: "regal",          # 1st Law: Make it obvious
    57: "contemplative",  # Scorecard
    58: "regal",          # Intentions
    59: "regal",          # Habit stacking
    60: "contemplative",  # Environment
    61: "energetic",      # 2nd Law: Make it attractive
    62: "energetic",      # Temptation bundling
    63: "regal",          # Culture
    64: "energetic",      # Reframe
    65: "energetic",      # 3rd Law: Make it easy
    66: "energetic",      # Motion vs Action
    67: "regal",          # Two-minute rule
    68: "energetic",      # Friction
    69: "regal",          # Commitment
    70: "regal",          # 4th Law: Make it satisfying
    71: "energetic",      # Cardinal rule
    72: "regal",          # Tracking
    73: "contemplative",  # Never miss twice
    74: "energetic",      # Accountability
    75: "regal",          # Goldilocks
    76: "contemplative",  # Reflection
    77: "contemplative",  # Mindfulness
    78: "regal",          # Synthesis
    79: "regal",          # Closing

    # === 12 Rules for Life (Days 80-92) ===
    80: "mysterious",     # An Antidote to Chaos
    81: "regal",          # Rule 1 — Stand up straight
    82: "contemplative",  # Rule 2 — Treat yourself as someone you help
    83: "contemplative",  # Rule 3 — Friends who want best for you
    84: "regal",          # Rule 4 — Compare to yesterday
    85: "regal",          # Rule 5 — Children & discipline
    86: "contemplative",  # Rule 6 — Set house in order
    87: "regal",          # Rule 7 — Pursue meaningful
    88: "regal",          # Rule 8 — Tell truth
    89: "contemplative",  # Rule 9 — Listen
    90: "regal",          # Rule 10 — Be precise
    91: "energetic",      # Rule 11 — Skateboarding
    92: "contemplative",  # Rule 12 — Pet a cat
}


def main() -> int:
    data = json.loads(QUOTES.read_text(encoding="utf-8"))
    added = 0
    for d in data["days"]:
        mood = MOODS.get(d["day"])
        if mood and d.get("mood") != mood:
            d["mood"] = mood
            added += 1
    QUOTES.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated {added}/{len(data['days'])} days with mood.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
