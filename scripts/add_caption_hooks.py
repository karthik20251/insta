"""One-time migration: add a `caption_hook` field to every day in quotes.json.

The hook is a punchy question-led line that goes above the fold of the IG caption
to drive engagement. For the 48 Laws of Power, hooks are taken verbatim from the
user's curated list. For Atomic Habits and 12 Rules, hooks are in the same style.
"""
from __future__ import annotations
import json
from pathlib import Path

QUOTES = Path(__file__).parent.parent / "quotes.json"

HOOKS = {
    # Day 1: Intro to 48 Laws
    1: "Power is a game 🎯 Who's playing — and who's being played?",

    # Days 2-49: 48 Laws of Power (verbatim from user)
    2:  "Know when to step back 🚀 How do you balance confidence and humility?",
    3:  "Loyal or liable? 🤔 Who's your go-to advisor?",
    4:  "Keep your plans close 👀 What's your biggest secret?",
    5:  "Silence is power 🔇 When was the last time you bit your tongue?",
    6:  "Reputation is everything 💼 How do you protect yours?",
    7:  "Be seen, be heard 🚀 What's your spotlight moment?",
    8:  "Work smarter, not harder 💡 How do you delegate effectively?",
    9:  "Draw them in 🧲 What's your irresistible offer?",
    10: "Actions speak louder 💪 What's your latest win?",
    11: "Energy is contagious ⚡️ Who uplifts you?",
    12: "Be the solution 🔑 How do you add value?",
    13: "Honesty can be strategic 🤝 When was a time it paid off?",
    14: "What's in it for them? 💰 How do you make requests effective?",
    15: "Listen more than you talk 🗣️ What's the hidden agenda?",
    16: "Finish strong 💥 How do you handle competition?",
    17: "Out of sight, in mind 👀 When did absence boost your value?",
    18: "Expect the unexpected 🔮 How do you keep them guessing?",
    19: "Connections are key 🌐 Who's in your network?",
    20: "Read the room 👀 Who's got your back?",
    21: "Keep your options open 🚪 What's your exit strategy?",
    22: "Sometimes less is more 🤑 When did playing dumb work?",
    23: "Surrender to win 🤝 When did you last yield?",
    24: "Focus is power 🔍 What's your target?",
    25: "Tact is key 🕺 How do you navigate tricky situations?",
    26: "Reinvention is power 🔄 What's your next chapter?",
    27: "Accountability is key 🚿 How do you stay above the fray?",
    28: "Belief is power ✨ What's your magic trick?",
    29: "Courage is contagious 💥 What's holding you back?",
    30: "Plan, execute, win 🎯 What's your endgame?",
    31: "Effortless mastery 🌊 How do you make it look easy?",
    32: "The house always wins 🃏 How do you set the game?",
    33: "Dreams are powerful 💫 What's yours?",
    34: "What's their weakness 🔓 How do you leverage it?",
    35: "Own it 👑 How do you embody confidence?",
    36: "Timing is everything ⏰ What's your cue?",
    37: "Let go to win 🙅‍♂️ What are you ignoring for peace?",
    38: "Make it memorable 🎉 What's your showstopper?",
    39: "Fit in to stand out 🐝 When did blending work?",
    40: "Create movement 🌊 How do you shake things up?",
    41: "Nothing's free 💸 What's the real cost?",
    42: "Carve your path 🛤️ Who's your role model?",
    43: "Target the source 🎯 How do you handle hierarchy?",
    44: "Emotions drive decisions ❤️ What's their motivation?",
    45: "Reflect their moves 🔮 How do you handle conflict?",
    46: "Baby steps 🐾 How do you implement change?",
    47: "Flaws are human 💔 How do you show vulnerability?",
    48: "Know when to stop 🏁 What's your limit?",
    49: "Adapt to win 🌊 How do you stay flexible?",

    # Days 50-79: Atomic Habits (same style)
    50: "Tiny changes, big results 🌱 What's your 1% today?",
    51: "1% every day 📈 What are you compounding?",
    52: "Goals fade, systems win 🎯 What's your daily process?",
    53: "Growth is silent before it explodes 🌋 What plateau are you pushing through?",
    54: "Who do you wish to become? 🦋 Vote for it daily.",
    55: "Cue → craving → response → reward 🔁 Which loop runs your life?",
    56: "You can't change what you don't see 👀 What habit do you need to notice?",
    57: "Track your habits 📋 What does yours reveal?",
    58: "I will [X] at [time] in [place] 📍 What's your plan?",
    59: "Stack the new on the old 🔗 What can you attach?",
    60: "Your space shapes you 🏠 What needs redesigning?",
    61: "Dopamine drives action ⚡ What makes your habit appealing?",
    62: "Pair pleasure with progress 🎧 What bundles for you?",
    63: "You become your tribe 👥 Who surrounds you?",
    64: "I get to, not I have to 💪 What feels like a chore?",
    65: "Lower the barrier 🚪 What's stopping you?",
    66: "Motion ≠ action 🚶 Which one are you doing?",
    67: "Start with 2 minutes ⏱️ What's the smallest version?",
    68: "Make it easy on future you 🪂 What can you pre-decide?",
    69: "Make bad habits hard 🔒 What's your commitment device?",
    70: "What's rewarded gets repeated 🎉 How do you celebrate?",
    71: "Reward now, not later 🍎 What's your immediate win?",
    72: "Don't break the chain ⛓️ What streak are you building?",
    73: "One slip is human, two starts a pattern 🔁 How do you recover?",
    74: "Tell someone 📢 Who's your accountability partner?",
    75: "Just right difficulty 🎯 Are you bored or overwhelmed?",
    76: "Review, refine, repeat 🔍 What's working?",
    77: "Habits + thinking = mastery 🧠 What needs your attention?",
    78: "Small habits, remarkable results ✨ What's compounding?",
    79: "You are what you do, repeatedly 🌟 Make today's vote count.",

    # Days 80-92: 12 Rules for Life (same style)
    80: "Order or chaos — where do you live? ⚖️",
    81: "Posture is a stance toward life 🦅 How do you carry yourself?",
    82: "Would you give this to a friend? 🤝 Why not yourself?",
    83: "Who pulls you up? Who drags you down? 🪜",
    84: "Better than yesterday 📈 What's your win today?",
    85: "Boundaries are love 🛡️ What rule keeps the peace?",
    86: "Fix your own first 🏠 What's calling for attention?",
    87: "Meaningful > expedient 🎯 What's worth the hard path?",
    88: "Truth is the foundation 🗣️ What needs saying?",
    89: "Listen to learn, not to reply 👂 Who taught you recently?",
    90: "Name the monster to defeat it 🎯 What needs articulating?",
    91: "Let them struggle, let them grow 🛹 Where are you over-protecting?",
    92: "Stop. Notice the beauty 🐱 What small wonder did you miss today?",
}


def main() -> int:
    data = json.loads(QUOTES.read_text(encoding="utf-8"))
    added = 0
    for d in data["days"]:
        hook = HOOKS.get(d["day"])
        if hook and d.get("caption_hook") != hook:
            d["caption_hook"] = hook
            added += 1
    QUOTES.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated {added}/{len(data['days'])} days with caption_hook.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
