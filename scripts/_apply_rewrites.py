"""One-shot script to apply the 14-item tactical-specificity rewrite to
quotes.json. Updates ONLY tease/body/comment_q for the named items —
everything else (headline, author, book, parent_law, variant_type, item
number) is preserved untouched.

Rewrite principle (the discipline this session adopted): every BODY must
end with a concrete Monday-morning move — the exact line, action, or
script the viewer would actually use. Diagnoses without prescriptions
are the failure mode we're fixing. Teases were already strong (specific
scenarios with payoffs) — only sharpened where needed.

Run once:
  .\.venv\Scripts\python.exe scripts\_apply_rewrites.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
QUOTES = ROOT / "quotes.json"

# (item_number, tease, body, comment_q) — None means keep current.
REWRITES = [
    (155,
     None,
     'Goals don\'t change your Tuesday at 6 PM — systems do. Block 30 minutes, same time, same trigger, every week. No exceptions.',
     'Goal or system — which one actually shows up Tuesday? 👇'),

    (86,
     None,
     'Three disclaimers and they spent the meeting on your doubts. Open with: "Here\'s where I land. Three reasons." Earn doubt later, not first.',
     None),

    (25,
     None,
     'Stop asking for the project. Ship one piece publicly — a Loom, a one-page memo, a working prototype. Make it the room\'s only obvious answer. They\'ll bring it to you.',
     'Pitch the work — or publish it and let them come? 👇'),

    (27,
     None,
     'Switched the default Slack reply from "sure" to "Let me check my priorities and get back to you." Within a month they brought the ones that mattered.',
     None),

    (163,
     None,
     'Motivation is unreliable. Tie the habit to a cue you can\'t avoid: standup ends, I open the doc. Calendar pings, I close Slack. The cue does the work.',
     None),

    (165,
     None,
     'He stapled the weekly update to one cue: closing the laptop Friday. Cue, then action, no willpower required. Twenty-three weeks unbroken.',
     None),

    (14,
     None,
     'Every hedge shrinks the idea before it lands. Cut "I might be wrong but," "just to clarify," "this might be silly." Open with: "Here\'s where I land." Take the position first.',
     None),

    (200,
     None,
     'Hour-a-day commits die on day three. Start with the two-minute version: one push-up, one page, one sentence. Scale only after 30 days unbroken.',
     'Big start or two-minute start — which lasts a year? 👇'),

    (244,
     None,
     'You\'d never let a junior skip growth, rest, or advocacy. Put yourself on the same calendar. One hour, Wednesday mornings, blocked for your own development. Non-negotiable.',
     None),

    (246,
     None,
     'Same time, same three questions she\'d ask a report: what blocked you, what\'s the win, what\'s next. In a year she was the one running the actual 1:1s.',
     None),

    (28,
     None,
     'Don\'t argue the plan — build the smallest working version. Demo Monday morning: "Here\'s how it\'d actually run." Working code ends debates that opinions can\'t.',
     None),

    (30,
     None,
     'Instead of a week defending the plan, you built the prototype over the weekend. Slack Monday: "Pushed a working version to the fork — see commit." The demo ended the argument.',
     None),

    (17,
     None,
     'Reputation isn\'t your average — it\'s your worst unmanaged moment. Slack your manager within the hour: "Missed it. Here\'s why, here\'s the new ETA, here\'s the prevention." Own it before they hear it.',
     None),

    (89,
     None,
     'Phase one died in phase two\'s politics. Before you ship: name the three stakeholders phase two depends on. Pre-sell each. "Heads up — here\'s what changes for your team next week." Never blindsided.',
     None),
]


def main() -> int:
    data = json.loads(QUOTES.read_text(encoding="utf-8"))
    items_by_n = {x["item"]: x for x in data["items"]}

    changed = 0
    for n, tease, body, comment_q in REWRITES:
        if n not in items_by_n:
            print(f"  SKIP item {n}: not found")
            continue
        it = items_by_n[n]
        if tease is not None:
            it["tease"] = tease
            changed += 1
        if body is not None:
            it["body"] = body
            changed += 1
        if comment_q is not None:
            it["comment_q"] = comment_q
            changed += 1

    QUOTES.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"applied {changed} field updates across {len(REWRITES)} items")
    # Verify by reading back a sample
    data2 = json.loads(QUOTES.read_text(encoding="utf-8"))
    sample = next(x for x in data2["items"] if x["item"] == 25)
    print()
    print("=== verification: item 25 (the worst one before) ===")
    print(f"  TEASE: {sample['tease']}")
    print(f"  BODY:  {sample['body']}")
    print(f"  Q:     {sample['comment_q']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
