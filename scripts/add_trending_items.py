"""Add 8 brand-new market-trending items to quotes.json — 2026 zeitgeist hooks.

Themes researched June 2026 (HR Executive, Tech Otlist, Workers Rights, SocialBee):
  - Quiet firing / quiet cutting (workload up, support down)
  - Stealth layoff warning signs (5 red flags, 3 things your boss does)
  - AI-driven layoffs (44% of managers expect AI cuts)
  - PIP / sudden 1:1 spike
  - Selective RTO as exit pressure
  - Workplace anxiety confessional ("looked unbothered, rage-applying every weekend")

Each item has strong narrative tease, divisive comment_q, body with payoff.
Item IDs 277-284 (extends the existing 1-276 range).
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
QUOTES = ROOT / "quotes.json"

NEW_ITEMS = [
    {
        "item": 277,
        "parent_law": "Law 11",
        "book": "The 48 Laws of Power",
        "title": "Law 11",
        "headline": "Spot the Quiet Push",
        "author": "Robert Greene",
        "variant_type": "MISTAKE",
        "series_label": "QUIET FIRING",
        "tease": "Three things your boss does the week before quietly pushing you out.",
        "comment_q": "Have you spotted these signs at your current job? 👇",
        "body": "Workload up, support down, decisions made without you. It's not in your head — it's the playbook."
    },
    {
        "item": 278,
        "parent_law": "Law 11",
        "book": "The 48 Laws of Power",
        "title": "Law 11",
        "headline": "Read the Room Before They Read You Out",
        "author": "Robert Greene",
        "variant_type": "SCENARIO",
        "series_label": "LAYOFF SIGNAL",
        "tease": "Her director stopped including her in decisions. Six weeks later, role eliminated.",
        "comment_q": "Act on the early signal or wait for HR to call? 👇",
        "body": "Exclusion from key meetings, vague feedback, project reassignment — the corporate version of slow-fade."
    },
    {
        "item": 279,
        "parent_law": "Law 17",
        "book": "The 48 Laws of Power",
        "title": "Law 17",
        "headline": "The Calendar Tells the Truth",
        "author": "Robert Greene",
        "variant_type": "MISTAKE",
        "series_label": "PIP WARNING",
        "tease": "He missed one deadline. By Friday his calendar was full of 'check-ins'.",
        "comment_q": "Sudden spike in 'check-ins' — red flag or your imagination? 👇",
        "body": "When 1:1s become daily and 'just touching base' shows up unannounced, the documentation is being built."
    },
    {
        "item": 280,
        "parent_law": "Law 25",
        "book": "The 48 Laws of Power",
        "title": "Law 25",
        "headline": "Re-skill Before the Restructure",
        "author": "Robert Greene",
        "variant_type": "MISTAKE",
        "series_label": "AI LAYOFF",
        "tease": "Her job got 'optimized with AI' in three months. Severance was the only positive part.",
        "comment_q": "Is AI a tool that helps you, or the one your boss uses to cut you? 👇",
        "body": "If your daily work can be templated, prompted, or scripted, someone at finance has already done the math."
    },
    {
        "item": 281,
        "parent_law": "Law 14",
        "book": "The 48 Laws of Power",
        "title": "Law 14",
        "headline": "The Reassignment Tell",
        "author": "Robert Greene",
        "variant_type": "MISTAKE",
        "series_label": "STEALTH FIRING",
        "tease": "His projects started getting reassigned 'temporarily'. Two months later, severance.",
        "comment_q": "Have you ever caught the 'temporary' reassignment in time? 👇",
        "body": "Temporary becomes permanent. Coverage becomes ownership. The org restructures around your absence before HR calls."
    },
    {
        "item": 282,
        "parent_law": "Rule 2",
        "book": "12 Rules for Life",
        "title": "Rule 2",
        "headline": "What the All-Hands Doesn't Show",
        "author": "Jordan Peterson",
        "variant_type": "MISTAKE",
        "series_label": "WORKPLACE ANXIETY",
        "tease": "He looked unbothered in every all-hands. He was rage-applying every weekend for six months.",
        "comment_q": "How long would you stay in a role you'd already quit mentally? 👇",
        "body": "Performing confidence while doing the hidden work of leaving. The polish is the cost of waiting for the right exit."
    },
    {
        "item": 283,
        "parent_law": "Law 11",
        "book": "The 48 Laws of Power",
        "title": "Law 11",
        "headline": "The 'Return to Office' That Wasn't About the Office",
        "author": "Robert Greene",
        "variant_type": "MISTAKE",
        "series_label": "RTO POLITICS",
        "tease": "She was the only one called back to the office full-time. They wanted her to quit.",
        "comment_q": "Is selective RTO a layoff in disguise? 👇",
        "body": "Mandates target specific roles, specific people. Office attendance becomes the metric no one admits is the metric."
    },
    {
        "item": 284,
        "parent_law": "Law 11",
        "book": "The 48 Laws of Power",
        "title": "Law 11",
        "headline": "The Last One Standing",
        "author": "Robert Greene",
        "variant_type": "SCENARIO",
        "series_label": "LAYOFF SURVIVOR",
        "tease": "Tech layoffs hit her team. She was the one who'd documented the system nobody else understood.",
        "comment_q": "Knowledge hoarding or knowledge protection? 👇",
        "body": "Two roles, one budget. The org keeps the person whose departure breaks three things by Monday — every time."
    },
]


def main() -> int:
    data = json.loads(QUOTES.read_text(encoding="utf-8"))
    existing_ids = {it["item"] for it in data["items"]}
    added = 0
    for it in NEW_ITEMS:
        if it["item"] in existing_ids:
            print(f"  skip #{it['item']} (already exists)")
            continue
        data["items"].append(it)
        added += 1
        print(f"  added #{it['item']} - {it['tease'][:60]}")
    QUOTES.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote {added} new items. Total items now: {len(data['items'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
