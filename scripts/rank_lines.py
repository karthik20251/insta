"""One-off audit: rank every curated line on Trending + Useful with reasoning."""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
queue = json.loads((ROOT / "output" / "queue.json").read_text(encoding="utf-8"))["queue"]
items_by_id = {it["item"]: it for it in json.loads(
    (ROOT / "quotes.json").read_text(encoding="utf-8"))["items"]}

# (Trending 1-5, Useful 1-5, one-line reasoning)
SCORES = {
    5:   (5, 5, "CORE - public correction = career suicide. Universal workplace fear."),
    6:   (5, 4, "CORE - credit-give-up wins. Counterintuitive, share-worthy."),
    11:  (5, 5, "CORE - info leak = idea theft. Strongest historical pattern (May 28 = 182v)."),
    12:  (4, 5, "STRONG - 5-year plan trap. Actionable: tighten the answer."),
    14:  (4, 4, "STRONG - over-clarifying signals junior. Hook is concrete."),
    15:  (4, 5, "STRONG - loaded question response. Useful: silence pressure."),
    20:  (4, 4, "STRONG - quiet builder loses. Hook resonates with most workers."),
    21:  (5, 5, "CORE - Friday recap tactic. Easy to apply Monday."),
    23:  (3, 4, "OK - martyrdom loses. Slightly preachy."),
    24:  (5, 5, "CORE - credit theft response. Crushed historically (May 30 = 106v)."),
    35:  (5, 5, "CORE - documented-out fear. Universal layoff anxiety."),
    36:  (4, 4, "STRONG - irreplaceable in reorgs. Specific layoff scenario."),
    41:  (3, 4, "OK - favor-asking is weak. Tactical: frame as their metric."),
    42:  (3, 4, "OK - frame asks as their metric."),
    44:  (4, 4, "STRONG - never tell what you can read. Specific betrayal arc."),
    45:  (3, 5, "Mid trending, HIGH useful - find the real decision-maker."),
    47:  (4, 4, "STRONG - humiliation creates lifelong opponents."),
    48:  (3, 4, "OK - let rival save face = loyalty. Counterintuitive."),
    50:  (4, 5, "STRONG - beach Slack reply. Relatable + specific tactic."),
    51:  (4, 4, "STRONG - real PTO shows your value."),
    53:  (4, 4, "STRONG - 100% predictable = replaceable."),
    54:  (3, 4, "OK - the one time he paused. Subtle."),
    62:  (4, 4, "STRONG - picking wrong boss = first cut."),
    63:  (3, 4, "OK - useful to both directors. Abstract."),
    77:  (4, 4, "STRONG - year-1 reputation sticks. Career fear."),
    78:  (3, 4, "OK - re-rated by showing up differently. Soft hook."),
    83:  (4, 4, "STRONG - CFO checked phone. Visceral scene."),
    84:  (3, 4, "OK - name outcome. Leadership-only audience."),
    101: (4, 4, "STRONG - same deck for finance + product. Specific."),
    102: (3, 5, "Mid trending, HIGH useful - lead with CFO's pain."),
    110: (4, 4, "STRONG - reply-all = drama tag. Relatable mistake."),
    111: (3, 4, "OK - let snipe die. Useful restraint."),
    116: (4, 4, "STRONG - pushback = uninvited."),
    117: (3, 4, "OK - 1:1 contrarian. Useful, soft hook."),
    137: (5, 5, "CORE - new VP rebuilds, out by month 3. Visceral."),
    138: (3, 4, "OK - prove one fix first. Sequencing."),
    140: (4, 4, "STRONG - perfection isolates. Vulnerability lesson."),
    143: (5, 5, "CORE - promotion greed = pause. Specific weekday."),
    144: (3, 4, "OK - don't renegotiate after promotion."),
    152: (4, 4, "STRONG - one skipped week = role shrank."),
    153: (3, 4, "OK - 20 min/day = own the tool."),
    158: (4, 4, "STRONG - replacement got the breakout. Survivorship."),
    159: (3, 4, "OK - 180 days flat. Patience narrative."),
    161: (3, 4, "OK - identity lock-in."),
    162: (3, 4, "OK - stop saying 'we'. Tactical language."),
    176: (4, 4, "STRONG - 30-min reading quit by week 2."),
    177: (3, 4, "OK - stack note on lunch."),
    179: (4, 4, "STRONG - willpower vs notifications."),
    180: (4, 4, "STRONG - Slack off first screen, output doubled."),
    200: (4, 4, "STRONG - gym card on mirror, 11 days past it."),
    201: (3, 4, "OK - open the editor = enough."),
    218: (4, 4, "STRONG - Monday miss = quit by Friday."),
    219: (3, 4, "OK - missed Monday, refused Tuesday."),
    224: (4, 4, "STRONG - same work 3 years, stopped growing."),
    225: (4, 4, "STRONG - volunteered for senior task, got title."),
    242: (3, 4, "OK - best work, sorry posture. Posture lesson."),
    243: (3, 4, "OK - stopped slumping. Posture tactic."),
    245: (3, 4, "OK - invested in everyone but self."),
    246: (4, 5, "STRONG useful - Tuesday 1:1 with self. Screenshotable."),
    251: (4, 4, "STRONG - comparison to top performer = quit."),
    252: (3, 4, "OK - track your own delta."),
    257: (3, 4, "OK - diagnose company, own work slips."),
    258: (3, 4, "OK - nail delivery before critiquing."),
    263: (4, 5, "STRONG - green-light lies = trust loss."),
    264: (3, 4, "OK - flag risk early. Trust-building."),
}

# Print full table grouped by tier
tier_a, tier_b, tier_c = [], [], []
for q in queue:
    iid = q["item"]
    if iid not in SCORES:
        continue
    t, u, note = SCORES[iid]
    item = items_by_id[iid]
    row = (t, u, iid, item["parent_law"], item["variant_type"], item["tease"], note)
    if t >= 5 and u >= 4:
        tier_a.append(row)
    elif t == 4 and u >= 4:
        tier_b.append(row)
    else:
        tier_c.append(row)

def print_tier(label, items):
    print(f"\n{'=' * 90}\n{label} ({len(items)} items)\n{'=' * 90}")
    for t, u, iid, parent, variant, tease, note in items:
        print(f"  T{t} U{u} | #{iid:3d} {parent:<18} {variant:<8} | {tease[:75]}")
        print(f"            -> {note}")

print_tier("TIER A - CORE viral candidates (T>=5, U>=4)", tier_a)
print_tier("TIER B - STRONG bench (T=4, U>=4)", tier_b)
print_tier("TIER C - Useful but lower-trending (T<=3)", tier_c)

print(f"\n{'=' * 90}")
print(f"Distribution: TIER A {len(tier_a)} | TIER B {len(tier_b)} | TIER C {len(tier_c)} | Total {len(tier_a)+len(tier_b)+len(tier_c)}")
