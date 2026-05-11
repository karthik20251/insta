"""One-time migration: add a real-life `example` field to every day in quotes.json.

The example is a concrete modern situation showing how to apply the principle —
shown in the new 12-second segment of the daily Reel.
"""
import json
from pathlib import Path

QUOTES = Path(__file__).parent.parent / "quotes.json"

EXAMPLES = {
    # === 48 Laws of Power (Days 1-49) ===
    1:  "Watch how power moves through the next 48 days. The patterns you notice in others are the same ones you can recognize — and use — in yourself.",
    2:  "When your boss shares an idea, sharpen it — don't replace it. In meetings, attribute the spark to them, even when you did the work.",
    3:  "That coworker who challenged you publicly? Bring them onto your project. Their need to prove themselves will outwork any friend who's coasting.",
    4:  "Don't announce you're job-hunting. Keep building quietly, line up the offer, then make your move from a position of strength.",
    5:  "In a salary negotiation, name your number and stop talking. Silence pressures them to fill the gap — usually with a better offer.",
    6:  "Before a job interview, audit your LinkedIn, your old tweets, your public profiles. One forgotten post can cost you the role.",
    7:  "Show up to industry events with a strong opinion, not a neutral one. Bland is forgettable. The loudest principled voice gets remembered.",
    8:  "Hire a contractor for the boring part. Take the lead on the strategy. Your name goes on the result — and you go home at 6 PM.",
    9:  "Don't chase prospects. Publish content valuable enough that they DM you. Let them initiate; you set the terms from there.",
    10: "Don't debate your roommate about cleanliness. Just clean the kitchen for a week. They'll either match your energy or step up.",
    11: "Mute the friend who complains every text. Add the friend who shares wins. After three months, your trajectory changes without you trying.",
    12: "Be the one person on your team who knows the legacy code. Document just enough to be useful, never so much that you're replaceable.",
    13: "When asking a favor, lead with one genuine compliment — make sure it's true. The disarm effect lasts long after the request.",
    14: "Want help from a busy mentor? Don't ask for advice — offer to do their grunt work. Match what they need to what you need.",
    15: "At networking events, ask 'what's keeping you up at night?' Listen. You'll learn industry weaknesses that 90% of competitors miss.",
    16: "If you part ways with a business partner, settle it in one clean conversation. Don't leave loose ends — they become the lawsuit later.",
    17: "Disappear from social media for two weeks before launching something. The silence makes the announcement louder than weeks of teasing would.",
    18: "Don't always reply within five minutes. Sometimes five hours. Sometimes five days. People stop taking your responsiveness for granted.",
    19: "When you start a new role, schedule 1-on-1s with everyone — even people not on your team. Connections outside your function save you in a crisis.",
    20: "Before sending the angry email, ask: is this person someone who forgives, or someone who waits? Adjust the tone accordingly.",
    21: "When two factions ask you to side with them, propose a third option that benefits both. You become indispensable to neither, useful to all.",
    22: "In meetings, sometimes ask the 'dumb' question that opens the conversation. You learn what assumptions everyone is making.",
    23: "When called out publicly, agree first. 'You're right, I missed that.' Then quietly fix it. The agreement disarms; the fix preserves you.",
    24: "Don't apply to 50 jobs casually. Apply to 5 you genuinely want, with custom cover letters. The hit rate flips.",
    25: "When a senior person makes a weak suggestion, don't shoot it down. Build on it: 'Yes, and what if we...' Diplomacy preserves the room.",
    26: "Once a year, change one signature thing — your hair, your title, the way you introduce yourself. People recalibrate; you become a new variable.",
    27: "When delivering bad news, don't make it personal. Send it from the team account. The decision lands, but no single face takes the heat.",
    28: "Build a Discord or newsletter around something specific — not just 'mindset', but '90-second daily decisions for new founders.' Niche beats broad.",
    29: "When negotiating, ask for 20% more than you think they'll accept. Half the time they say yes — and you discover the floor was higher than you thought.",
    30: "Before launching the product, write the post-launch press release. If you can't write a compelling one yet, the product isn't ready.",
    31: "When you nail a hard task, don't share the struggle. Share the calm result. Mystery preserves the magic; complaint dilutes it.",
    32: "Don't ask 'do you want to meet?' — they'll say maybe. Ask 'Tuesday or Thursday?' Both lead to a meeting; the choice is illusion.",
    33: "Sell the vision before the spec. Tell the team what life looks like after we ship — not the JIRA tickets. Hope mobilizes; specs paralyze.",
    34: "If a teammate keeps blocking decisions, find out what they're protecting. Usually it's recognition or job security. Address that, the block clears.",
    35: "Walk into the meeting like you booked it. Sit before being asked. Speak first if you want the room. Composure is a strategy.",
    36: "Don't pitch your idea on Friday afternoon. Try Tuesday morning. Same idea, three times more likely to land.",
    37: "Someone got the promotion you wanted? Don't dissect it. Outwork them quietly next quarter. Public bitterness ages worse than missed opportunities.",
    38: "Don't write a normal birthday post for the company. Make a 30-second video, write a poem, do something visible. Symbols stick; sentences don't.",
    39: "Have unpopular views? Hold them. But pick your battles. Save them for moments when your stance changes outcomes, not just signals identity.",
    40: "Want the team to act? Send an email at 8 AM raising a small concern. By 10, everyone is talking. Decisions follow conversation, not silence.",
    41: "When someone offers something for nothing, ask what they'll want from you eventually. The obligation always comes due — usually at a bad time.",
    42: "Don't be the third founder of an 'X for Y' clone. Your name will always be third in search results. Find your own first-mover position.",
    43: "Bad team dynamics? Don't try to fix the whole team. Find the one person whose attitude is poisoning the rest. Move them — or move them out.",
    44: "Want adoption of a new process? Don't email a memo. Talk to the three most influential people 1-on-1. They convince the rest for you.",
    45: "When someone is rude in a meeting, repeat their words calmly. 'So you're saying X?' They hear themselves, and either soften or expose their own tone.",
    46: "Don't redesign the entire workflow on day one. Change one thing per week. After two months, everything is new — and no one noticed the upheaval.",
    47: "When asked about a recent win, mention what almost went wrong. Vulnerability invites trust; bulletproof invites envy.",
    48: "After winning a negotiation, get up and leave. Don't celebrate. Don't add 'one more thing.' Exit while you're ahead — the negotiation is over.",
    49: "Don't commit to one 5-year plan. Commit to skills and relationships. The specific career will reshape itself; you stay relevant by staying adaptable.",

    # === Atomic Habits (Days 50-79) ===
    50: "Tomorrow, do one small thing 1% better than today. The habit isn't the goal — the system that makes the habit easy is.",
    51: "Read 10 pages a day. That's one book a month, 12 a year, 120 in a decade. The math nobody believes until they try it.",
    52: "Don't say 'I want to write a book.' Say 'I write 200 words before coffee.' The system runs; the book emerges.",
    53: "If you've worked out for 30 days with no visible change, you're not failing — you're at the plateau. Day 60 is usually when the mirror shifts.",
    54: "Don't say 'I want to quit smoking.' Say 'I'm not a smoker.' One sentence changes, but the next decision flows from identity, not willpower.",
    55: "Notice the cue → craving → response → reward of one habit today. Once you name the loop, you can rewire it. Awareness is the first move.",
    56: "Put your gym shoes by the bed. Put the candy in the back of the cupboard. The visible thing wins; design accordingly.",
    57: "Write down your 10 most common daily actions. Mark each + / – / =. Your priorities are revealed by the marks, not your to-do list.",
    58: "'I will exercise at 7 AM in the living room' is a habit. 'I will exercise more' is a wish. Specify or surrender.",
    59: "After I pour my morning coffee, I'll do 10 push-ups. After 30 days, the coffee triggers the push-ups automatically. Anchor to what exists.",
    60: "Move your phone to the kitchen at 9 PM. Your bedroom becomes a place for sleep, not scrolling. Environment beats willpower.",
    61: "Pair your workout with your favorite podcast — only allow the podcast while exercising. The thing you want fuels the thing you need.",
    62: "Want to journal more? Do it while sipping the one drink you love. The pleasure carries the practice for the first 30 days.",
    63: "Join a Discord, gym, or community where what you want is the default. After six weeks, you stop trying and start fitting in.",
    64: "Instead of 'I have to wake up at 5,' say 'I get to start the day before anyone else.' Same alarm, different relationship with it.",
    65: "Lay out tomorrow's clothes tonight. Pre-cut the vegetables. Sign up for the gym before bedtime. Future-you can't refuse a path already cleared.",
    66: "Reading 'how to start a business' is motion. Sending the first invoice is action. Be honest about which one you're doing today.",
    67: "'I'll write a book' → 'I'll open the document and write one sentence.' Start so small you can't refuse. Momentum is built, not summoned.",
    68: "Log out of Instagram. Make it require a password every time. Sixty seconds of friction kills 80% of mindless opens.",
    69: "Pre-pay for the year of yoga. Donate to a cause you hate if you skip a workout. Money is the most reliable motivator.",
    70: "After every workout, mark an X on a paper calendar. The visual satisfaction is what your brain remembers, not the abstract goal.",
    71: "Reward yourself the moment you finish, not after a week. Coffee after the run. Brain learns: this hard thing has an immediate payoff.",
    72: "A simple paper habit tracker beats every app. You see the streak. You don't want to break it.",
    73: "Missed today? Fine. Just don't miss tomorrow. One missed day is human; two starts a pattern.",
    74: "Tell your friend the goal. Ask them to follow up every Sunday. Fear of disappointing them outperforms internal willpower.",
    75: "If you can do 50 push-ups easily, you're not training — you're maintaining. Push for the 51st. Growth lives 1% beyond capacity.",
    76: "Every Sunday, ask: what worked? what didn't? what changes for next week? 15 minutes of reflection beats five hours of unreviewed effort.",
    77: "Don't let your morning routine become automatic. Notice it. Stay present. Rituals stay rituals only when you pay attention.",
    78: "Make the cue obvious, the craving attractive, the response easy, the reward satisfying. Audit one habit today — change the broken step.",
    79: "Habits are the compound interest of self-improvement. Don't budget for the year — budget for the day, and let the year compound itself.",

    # === 12 Rules for Life (Days 80-92) ===
    80: "When life feels chaotic, fix one thing today. Make your bed. Wash a dish. Order, like meaning, starts very small.",
    81: "Before a hard conversation, stand. Pull your shoulders back. Take three deep breaths. Your posture changes your hormones in 90 seconds.",
    82: "Would you let a friend skip meals because they were 'too busy'? No. Then don't let yourself.",
    83: "List your five closest friends. Are three of them going somewhere? If not, choose your time accordingly. You become the average of these five.",
    84: "At the end of each day, ask: am I 1mm better than yesterday on the thing I care about? Comparison to others is a trap; comparison to yesterday is fuel.",
    85: "If your child does something that makes you secretly dislike them, say so calmly. Children prefer clear rules to vague resentment.",
    86: "Before posting your opinion on a global issue, ask: have I done dishes today? Did I keep my last promise to myself? Fix small first.",
    87: "When choosing between two paths, ask: which one will I be glad I chose in 10 years? The easier one usually loses to that question.",
    88: "When you almost lie, pause. The small lie costs nothing today and costs your reputation tomorrow. Truth, even awkward, is cheaper.",
    89: "In your next conversation, don't form your reply while they're talking. Just listen. Then pause two seconds before replying. You'll hear what you usually miss.",
    90: "Stop saying 'I'm stressed.' Say 'I'm anxious about the Tuesday meeting because I haven't prepared.' Naming the exact problem makes it solvable.",
    91: "Let people fail at small things. Stop rescuing. The 5-year-old who scrapes their knee learns balance. The 25-year-old you rescue learns nothing.",
    92: "When life is too heavy, find one small beautiful thing today — a cat, a song, a sunbeam through a window. Beauty isn't a luxury; it's how you survive.",
}


def main() -> int:
    data = json.loads(QUOTES.read_text(encoding="utf-8"))
    added = 0
    for d in data["days"]:
        ex = EXAMPLES.get(d["day"])
        if ex and d.get("example") != ex:
            d["example"] = ex
            added += 1
    QUOTES.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated {added}/{len(data['days'])} days with example.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
