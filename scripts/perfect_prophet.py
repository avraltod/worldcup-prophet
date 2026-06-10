"""Perfect Prophet: feed Avraa's OWN predictions in as 'reality' and trace how
the forecast would evolve if every pick came true. Pure fun, with one real
lesson: results that match expectations carry little information, so the
trajectory is smooth and the per-match bits stay low -- the mirror image of the
upset-driven random dry run. Writes only prophet_* files."""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import condition as C

DATA = Path(__file__).parent.parent / "data"
N = 12000

# Avraa's submitted knockout picks (winner of each bracket slot)
PICK = {74: "Germany", 77: "France", 73: "Canada", 75: "Netherlands",
        76: "Brazil", 78: "Norway", 79: "Mexico", 80: "England",
        83: "Croatia", 84: "Spain", 81: "United States", 82: "Belgium",
        86: "Argentina", 88: "Turkey", 85: "Switzerland", 87: "Portugal",
        89: "France", 90: "Netherlands", 91: "Brazil", 92: "England",
        93: "Spain", 94: "Belgium", 95: "Argentina", 96: "Portugal",
        97: "France", 98: "Spain", 99: "England", 100: "Argentina",
        101: "Spain", 102: "Argentina", 104: "Spain"}


def kl_bits(q, p):
    teams = set(q) | set(p)
    eps = 1e-6
    return sum((q.get(t, 0) + eps) * math.log2((q.get(t, 0) + eps) / (p.get(t, 0) + eps))
               for t in teams)


def main():
    preds = json.loads((DATA / "group_predictions.json").read_text())
    g_res = {C.ROW_MATCH[p["row"]]: [p["hg"], p["ag"]] for p in preds}
    ko_res = dict(PICK)
    print("=== PERFECT PROPHET: every Avraa prediction comes true -> Spain ===")

    group_order = sorted(g_res)
    ko_order = list(C.R32) + list(C.R16) + list(C.QF) + list(C.SF) + [104]
    traj = []
    cum = {"group": {}, "ko": {}}
    base = C.conditional_probs(cum, N=N, seed=2026)
    champ0 = {t: d["champion"] for t, d in base.items() if d["champion"] > 0}
    traj.append({"label": "baseline", "n": 0, "info_bits": 0.0,
                 "champion": {t: round(p, 4) for t, p in champ0.items()}, "kind": "baseline"})
    prev = champ0
    steps = [("group", m) for m in group_order] + [("ko", m) for m in ko_order]
    for i, (kind, m) in enumerate(steps, 1):
        if kind == "group":
            cum["group"][str(m)] = g_res[m]
            lab = f"group match {m}"
        else:
            cum["ko"][str(m)] = ko_res[m]
            lab = f"KO match {m}"
        probs = C.conditional_probs(cum, N=N, seed=2026)
        champ_now = {t: d["champion"] for t, d in probs.items() if d["champion"] > 0}
        bits = kl_bits(champ_now, prev)
        traj.append({"label": lab, "n": i, "info_bits": round(bits, 4),
                     "champion": {t: round(p, 4) for t, p in champ_now.items()}, "kind": kind})
        prev = champ_now
    (DATA / "prophet_trajectory.json").write_text(json.dumps(traj, ensure_ascii=False, indent=1))

    infos = [(e["n"], e["info_bits"], e["kind"]) for e in traj[1:]]
    total = sum(b for _, b, _ in infos)
    g_info = sum(b for _, b, k in infos if k == "group")
    spain = [e["champion"].get("Spain", 0) for e in traj]
    print(f"Spain's champion probability: baseline {spain[0]*100:.0f}% -> end {spain[-1]*100:.0f}%")
    print(f"total information to resolution: {total:.2f} bits "
          f"(theoretical minimum to confirm a {spain[0]*100:.0f}% favorite: {-math.log2(spain[0]):.2f} bits)")
    print(f"group stage carried {100*g_info/total:.0f}% of it; biggest single jump:")
    big = max(infos, key=lambda x: x[1])
    print(f"   match {big[0]} ({[e['label'] for e in traj if e['n']==big[0]][0]}): {big[1]:.3f} bits")
    print(f"Compare: the RANDOM dry run needed 2.48 bits with upset spikes up to 0.52;")
    print(f"the prophet path is smoother because nothing is a surprise.")


if __name__ == "__main__":
    main()
