"""One-time migration: inject the 92 curated `tease` fields into quotes.json.

Pattern: 8-12 words, specific noun + outcome, one emoji as visual anchor,
watch-cue at end. Never reveals the law name — the reveal is the MAIN frame.
"""
import json
from pathlib import Path

QUOTES = Path(__file__).parent.parent / "quotes.json"

TEASES = {
    1:  "The 48 moves that explain why some people always win 🎯 stay for the game",
    2:  "The 1 way to make your boss love your ideas 🤝 wait for it",
    3:  "The coworker who fought you in public is your secret weapon ⚔️ wait for it",
    4:  "The job-hunt move that lands you a better offer 🤐 wait for it",
    5:  "The 1 silence that gets you a higher salary 💰 wait for it",
    6:  "The 1 tweet that can cost you the job 📱 watch before your next interview",
    7:  "Why bland people get forgotten at networking events 🎤 stay for the fix",
    8:  "How to leave work at 6 PM and still get the credit 🏆 wait for it",
    9:  "The 1 move that makes prospects come to you 🧲 wait for it",
    10: "The move that ends roommate fights without a single word 🧽 wait for it",
    11: "The 1 change to your contacts that shifts your trajectory in 3 months ⚡ wait for it",
    12: "The 1 thing to be on your team that makes you irreplaceable 🔑 wait for it",
    13: "The 1 sentence that gets you any favor you ask 🤝 wait for it",
    14: "The 1 move that gets a busy mentor to mentor you 🎯 wait for it",
    15: "The 1 networking question that beats 90% of competitors 🗣️ wait for it",
    16: "The 1 conversation that prevents a future lawsuit ⚖️ wait for it",
    17: "Why disappearing before a launch makes it 10x louder 🤐 wait for it",
    18: "The 1 reply habit that makes people respect your time ⏳ wait for it",
    19: "The 1 thing you do in week 1 that saves you in month 12 🤝 wait for it",
    20: "The 1 question to ask before sending an angry email 📧 wait for it",
    21: "The 1 move when both sides want you to pick one 🪜 wait for it",
    22: "Why the 'dumb' question wins meetings 💡 wait for it",
    23: "The 2 words that disarm anyone who calls you out 🛡️ wait for it",
    24: "Why applying to 5 jobs beats applying to 50 🎯 wait for it",
    25: "The 2 words that turn a bad idea into a team win 💬 wait for it",
    26: "The 1 yearly change that makes people see you differently 🔄 wait for it",
    27: "The 1 way to deliver bad news without taking the heat 🛡️ wait for it",
    28: "Why niche beats broad when building a following 🎯 wait for it",
    29: "The 1 number to ask for in any negotiation 💵 wait for it",
    30: "The 1 thing to write before launching that tells you if it's ready 📰 wait for it",
    31: "Why successful people never show the struggle 🌊 wait for it",
    32: "The 1 word swap that gets you the meeting every time 🗓️ wait for it",
    33: "What to sell first when launching anything 💫 wait for it",
    34: "The 1 question that unblocks any teammate 🔓 wait for it",
    35: "The 1 move that owns any meeting before you speak 👑 wait for it",
    36: "The exact day to pitch any idea for 3x the yes 📅 wait for it",
    37: "How to respond when someone gets the promotion you wanted 🤐 wait for it",
    38: "How to make a company birthday post unforgettable 🎉 wait for it",
    39: "When to share your unpopular views and when not to 🤐 wait for it",
    40: "The 1 morning email that gets the team moving 🌅 wait for it",
    41: "Why 'free' always costs more than the price tag 💸 wait for it",
    42: "Why being the third 'X for Y' clone kills you 🚫 wait for it",
    43: "The 1 person to remove to fix any bad team 🎯 wait for it",
    44: "How to roll out anything without writing a single memo 📣 wait for it",
    45: "The 1 sentence that disarms a rude person in any meeting 🔮 wait for it",
    46: "How to change everything without anyone noticing 🐾 wait for it",
    47: "The 1 sentence to add to every win that builds trust 💔 wait for it",
    48: "What to do the moment you win a negotiation 🏁 wait for it",
    49: "The 1 thing to commit to instead of a 5-year plan 🌊 wait for it",
    50: "The 1% rule that turns one year into a different person 📈 wait for it",
    51: "The math that turns 10 pages a day into 120 books 📚 wait for it",
    52: "The 1 sentence swap that makes goals actually happen ☕ wait for it",
    53: "What's actually happening on day 30 when nothing has changed yet 🧊 wait for it",
    54: "The 1 sentence that changes a habit faster than willpower 🦋 wait for it",
    55: "The 4-step loop running every habit you have 🔁 wait for it",
    56: "Why your gym shoes belong by your bed 👟 wait for it",
    57: "The 1 list that reveals your real priorities in 60 seconds 📋 wait for it",
    58: "Why most habits die before day 7 ⏰ wait for it",
    59: "The 1 trick that builds a new habit on top of an old one ☕ wait for it",
    60: "Why your phone shouldn't sleep in your bedroom 📵 wait for it",
    61: "The 1 pairing that makes a workout feel like a treat 🎧 wait for it",
    62: "How to make any habit feel like pleasure in 30 days 🍵 wait for it",
    63: "Why your environment shapes you faster than willpower 👥 wait for it",
    64: "The 1 word swap that changes how a 5 AM alarm feels 💪 wait for it",
    65: "Why future-you can't refuse a path that's already cleared 🚪 wait for it",
    66: "The honest test: motion or action? 🚶 wait for it",
    67: "The 2-minute rule that beats motivation every time ⏱️ wait for it",
    68: "The 60 seconds of friction that kills 80% of mindless scrolling 🪂 wait for it",
    69: "The 1 commitment device that beats willpower every time 🔒 wait for it",
    70: "Why a paper calendar beats every habit-tracking app 🎉 wait for it",
    71: "The 1 thing your brain needs right after a hard habit 🍎 wait for it",
    72: "The streak that never lets you skip a day ⛓️ wait for it",
    73: "The 1 rule when you miss a day of any habit 🔁 wait for it",
    74: "The 1 friend who can replace willpower 📢 wait for it",
    75: "Why your habit stopped working at 50 reps 🎯 wait for it",
    76: "The 15-minute weekly habit that beats 5 hours of effort 🔍 wait for it",
    77: "The 1 thing rituals need to stay rituals 🧠 wait for it",
    78: "The 4-step audit to fix any broken habit ✨ wait for it",
    79: "How to plan for a year you can actually execute 🌟 wait for it",
    80: "When life feels chaotic, fix this 1 thing first 🛏️ wait for it",
    81: "The 90-second move that rewires your hormones before a hard talk 💪 wait for it",
    82: "The 1 question that stops self-neglect 🤝 wait for it",
    83: "The 5-person test that predicts your next 3 years 🪜 wait for it",
    84: "The 1 question to ask every night that beats comparison 📈 wait for it",
    85: "What kids actually want when they push the limit 🛡️ wait for it",
    86: "The 1 question to ask before posting on a big issue 🏠 wait for it",
    87: "The 1 question that makes the hard choice obvious 🎯 wait for it",
    88: "What the small lie actually costs you 🗣️ wait for it",
    89: "The 2-second pause that changes every conversation 👂 wait for it",
    90: "The 1 sentence swap that makes any problem solvable 🎯 wait for it",
    91: "What kids learn when you stop rescuing them 🛹 wait for it",
    92: "When life feels too heavy, do this 1 small thing today 🐱 wait for it",
}


def main() -> int:
    data = json.loads(QUOTES.read_text(encoding="utf-8"))
    added = 0
    for d in data["days"]:
        tease = TEASES.get(d["day"])
        if tease and d.get("tease") != tease:
            d["tease"] = tease
            added += 1
    QUOTES.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated {added}/{len(data['days'])} days with tease.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
