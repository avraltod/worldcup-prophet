"""Pivotality: how much one match is EXPECTED to move the champion forecast,
before it is played. For each match along the predicted path, condition on the
results so far, then fork the match across its possible outcomes and measure the
expected KL divergence of the champion distribution. This quantifies the leverage
of a single small event -- the case that one result can change everything.

Group match: 3 outcomes (H/D/A) weighted by the model's odds; knockout match:
2 outcomes (each team advances) weighted by Elo win expectancy.
"""
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import condition as C

DATA = Path(__file__).parent.parent / "data"
N = 5000

preds = json.loads((DATA / "group_predictions.json").read_text())
G_RES = {C.ROW_MATCH[p["row"]]: [p["hg"], p["ag"]] for p in preds}
G_PROB = {C.ROW_MATCH[p["row"]]: p["p"] for p in preds}  # [pH,pD,pA]
PICK = {74: "Germany", 77: "France", 73: "Canada", 75: "Netherlands",
        76: "Brazil", 78: "Norway", 79: "Mexico", 80: "England",
        83: "Croatia", 84: "Spain", 81: "United States", 82: "Belgium",
        86: "Argentina", 88: "Turkey", 85: "Switzerland", 87: "Portugal",
        89: "France", 90: "Netherlands", 91: "Brazil", 92: "England",
        93: "Spain", 94: "Belgium", 95: "Argentina", 96: "Portugal",
        97: "France", 98: "Spain", 99: "England", 100: "Argentina",
        101: "Spain", 102: "Argentina", 104: "Spain"}


def kl(q, p):
    eps = 1e-6
    return sum((q.get(t, 0) + eps) * math.log2((q.get(t, 0) + eps) / (p.get(t, 0) + eps))
               for t in set(q) | set(p))


def champ_dist(cum):
    pr = C.conditional_probs(cum, N=N, seed=2026)
    return {t: d["champion"] for t, d in pr.items() if d["champion"] > 0}


def elo_winprob(a, b, late=False):
    ra = C.rating(a, late)
    rb = C.rating(b, late)
    return 1 / (1 + 10 ** (-(ra - rb) / 400))


def main():
    group_order = sorted(G_RES)
    ko_order = list(C.R32) + list(C.R16) + list(C.QF) + list(C.SF) + [104]
    cum = {"group": {}, "ko": {}}
    rows = []
    # we need the predicted advancers at each KO slot to know the two teams;
    # recompute the bracket from the predicted group results once groups are set.
    for stage, order in (("group", group_order), ("ko", ko_order)):
        for m in order:
            pre = champ_dist(cum)
            if stage == "group":
                pH, pD, pA = G_PROB[m]
                s = pH + pD + pA
                pH, pD, pA = pH / s, pD / s, pA / s
                outs = [("H", (1, 0), pH), ("D", (1, 1), pD), ("A", (0, 1), pA)]
                piv = 0.0
                for _, score, w in outs:
                    cum["group"][str(m)] = score
                    post = champ_dist(cum)
                    piv += w * kl(post, pre)
                cum["group"][str(m)] = G_RES[m]  # restore actual predicted result
            else:
                # the two teams contesting slot m, from the current (post-group) bracket
                snap = C.conditional_probs(cum, N=1, seed=1)  # not used for teams
                teams = ko_teams(m, cum)
                if teams is None:
                    rows.append({"match": m, "stage": stage, "pivotality": 0.0})
                    cum["ko"][str(m)] = PICK[m]
                    continue
                a, b = teams
                late = m in C.QF or m in C.SF or m == 104
                pw = elo_winprob(a, b, late)
                piv = 0.0
                for team, w in ((a, pw), (b, 1 - pw)):
                    cum["ko"][str(m)] = team
                    post = champ_dist(cum)
                    piv += w * kl(post, pre)
                cum["ko"][str(m)] = PICK[m]
            rows.append({"match": m, "stage": stage, "pivotality": round(piv, 4)})
            if stage == "group":
                cum["group"][str(m)] = G_RES[m]
            else:
                cum["ko"][str(m)] = PICK[m]
    (DATA / "pivotality.json").write_text(json.dumps(rows, indent=1))
    rows.sort(key=lambda r: -r["pivotality"])
    print("Most pivotal matches (expected forecast swing, bits):")
    for r in rows[:8]:
        print(f"  match {r['match']} ({r['stage']}): {r['pivotality']:.3f} bits")
    gp = [r["pivotality"] for r in rows if r["stage"] == "group"]
    kp = [r["pivotality"] for r in rows if r["stage"] == "ko"]
    print(f"\n  group matches: mean {sum(gp)/len(gp):.4f} bits, max {max(gp):.3f}")
    print(f"  knockout matches: mean {sum(kp)/len(kp):.3f} bits, max {max(kp):.3f}")
    print(f"  a knockout match is ~{(sum(kp)/len(kp))/(sum(gp)/len(gp)):.0f}x as pivotal as a group match")


# resolve the two teams in a knockout slot given results so far (predicted bracket)
def ko_teams(m, cum):
    # build winners from PICK for already-decided feeder matches
    if m in C.R32:
        s1, s2 = C.R32[m]
        # need the slot occupants; reuse a single deterministic sim conditioned on all groups
        slots = resolve_slots(cum)
        return (slots.get(s1), slots.get(s2)) if slots.get(s1) and slots.get(s2) else None
    feed = {**C.R16, **C.QF, **C.SF, 104: (101, 102)}
    if m in feed:
        m1, m2 = feed[m]
        return (PICK.get(m1), PICK.get(m2)) if PICK.get(m1) and PICK.get(m2) else None
    return None


def resolve_slots(cum):
    # deterministic group resolution from predicted scores -> bracket slot occupants
    if str(72) not in cum["group"] and len(cum["group"]) < 72:
        return {}
    random.seed(0)
    pos, thirds = {}, {}
    for grp in "ABCDEFGHIJKL":
        st = defaultdict(lambda: [0, 0, 0])
        for row in C.GROUPS[grp]:
            mm = C.ROW_MATCH[row]
            home, away = C.RATES[row][2], C.RATES[row][3]
            hg, ag = G_RES[mm]
            for t, f, x in ((home, hg, ag), (away, ag, hg)):
                st[t][1] += f - x
                st[t][2] += f
                st[t][0] += 3 if f > x else (1 if f == x else 0)
        o = sorted(st, key=lambda t: tuple(st[t]), reverse=True)
        pos[f"{grp}1"], pos[f"{grp}2"] = o[0], o[1]
        thirds[grp] = (o[2], tuple(st[o[2]]))
    rk = sorted(thirds, key=lambda g: thirds[g][1], reverse=True)
    am = C.assign(rk[:8]) or C.assign(rk[:7] + [rk[8]])
    slots = dict(pos)
    if am:
        for mm, g_ in am.items():
            slots[f"T{mm}"] = thirds[g_][0]
    return slots


if __name__ == "__main__":
    main()
