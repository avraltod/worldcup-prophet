"""Dress rehearsal: treat ONE simulated tournament as 'reality' and run the full
live-update pipeline through all 104 matches. Proves the skeleton end-to-end and
produces an example forecast-evolution trajectory. Writes ONLY dryrun_* files;
the real results_log.json / trajectory.json (the June 11 baseline) are untouched.
"""
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import condition as C

DATA = Path(__file__).parent.parent / "data"
N = 12000               # sims per conditioning step (speed vs noise)
GEN_SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 41


def generate_realization(seed):
    """Play one full tournament. Return (group_results, ko_results, champion).
    group_results: {official_match_no: [hg, ag]}; ko_results: {ko_match_no: winner}."""
    random.seed(seed)
    pos, thirds, g_res = {}, {}, {}
    for grp in "ABCDEFGHIJKL":
        st = defaultdict(lambda: [0, 0, 0])
        for row in C.GROUPS[grp]:
            lh, la, home, away = C.RATES[row]
            hg, ag = C.sample(lh), C.sample(la)
            g_res[C.ROW_MATCH[row]] = [hg, ag]
            for t, f, gg in ((home, hg, ag), (away, ag, hg)):
                st[t][1] += f - gg
                st[t][2] += f
                st[t][0] += 3 if f > gg else (1 if f == gg else 0)
        o = sorted(st, key=lambda t: (*st[t], random.random()), reverse=True)
        pos[f"{grp}1"], pos[f"{grp}2"] = o[0], o[1]
        thirds[grp] = (o[2], tuple(st[o[2]]))
    rk = sorted(thirds, key=lambda g: (*thirds[g][1], random.random()), reverse=True)
    am = C.assign(rk[:8]) or C.assign(rk[:7] + [rk[8]])
    slots = dict(pos)
    for m_, g_ in am.items():
        slots[f"T{m_}"] = thirds[g_][0]
    W, ko = {}, {}
    for m, (s1, s2) in C.R32.items():
        W[m] = C.kw(slots[s1], slots[s2]); ko[m] = W[m]
    for tab, late in C.KO_TABLES:
        for m, (m1, m2) in tab.items():
            W[m] = C.kw(W[m1], W[m2], late); ko[m] = W[m]
    champ = C.kw(W[101], W[102], True); ko[104] = champ
    return g_res, ko, champ


def kl_bits(q, p):
    teams = set(q) | set(p)
    eps = 1e-6
    return sum((q.get(t, 0) + eps) * math.log2((q.get(t, 0) + eps) / (p.get(t, 0) + eps))
               for t in teams)


def main():
    g_res, ko_res, champ = generate_realization(GEN_SEED)
    print(f"=== synthetic tournament (seed {GEN_SEED}) -> CHAMPION: {champ} ===")

    # chronological feed order: group matches 1..72, then KO rounds in order
    group_order = sorted(g_res)                      # official match numbers 1..72
    ko_order = (list(C.R32) + list(C.R16) + list(C.QF) + list(C.SF) + [104])

    traj = []
    cum = {"group": {}, "ko": {}}
    # baseline
    base = C.conditional_probs(cum, N=N, seed=2026)
    champ0 = {t: d["champion"] for t, d in base.items() if d["champion"] > 0}
    traj.append({"label": "baseline", "n": 0, "info_bits": 0.0,
                 "champion": {t: round(p, 4) for t, p in champ0.items()},
                 "kind": "baseline"})
    prev = champ0

    steps = [("group", m) for m in group_order] + [("ko", m) for m in ko_order]
    for i, (kind, m) in enumerate(steps, 1):
        if kind == "group":
            cum["group"][str(m)] = g_res[m]
            label = f"group match {m}"
        else:
            cum["ko"][str(m)] = ko_res[m]
            label = f"KO match {m}"
        probs = C.conditional_probs(cum, N=N, seed=2026)
        champ_now = {t: d["champion"] for t, d in probs.items() if d["champion"] > 0}
        bits = kl_bits(champ_now, prev)
        traj.append({"label": label, "n": i, "info_bits": round(bits, 4),
                     "champion": {t: round(p, 4) for t, p in champ_now.items()},
                     "kind": kind})
        prev = champ_now
        if i % 12 == 0 or bits > 0.05:
            top = max(champ_now, key=champ_now.get)
            print(f"  [{i:3}/104] {label:<16} info={bits:5.3f} bits | "
                  f"leader {top} {champ_now[top]*100:.0f}%")

    (DATA / "dryrun_trajectory.json").write_text(json.dumps(traj, ensure_ascii=False, indent=1))
    (DATA / "dryrun_truth.json").write_text(json.dumps(
        {"champion": champ, "group": g_res, "ko": ko_res}, ensure_ascii=False, indent=1))

    # hypothesis checks
    infos = [(e["n"], e["info_bits"], e["label"], e["kind"]) for e in traj[1:]]
    total = sum(b for _, b, _, _ in infos)
    infos_sorted = sorted(infos, key=lambda x: -x[1])
    top10 = sum(b for _, b, _, _ in infos_sorted[:10])
    group_info = sum(b for _, b, _, k in infos if k == "group")
    ko_info = sum(b for _, b, _, k in infos if k == "ko")
    print(f"\n=== HYPOTHESIS CHECKS (synthetic) ===")
    print(f"total information over the tournament: {total:.2f} bits")
    print(f"H1 concentration: top 10 matches carry {100*top10/total:.0f}% of all information")
    print(f"H3 late arrival: group stage {100*group_info/total:.0f}% vs knockouts {100*ko_info/total:.0f}%")
    print(f"H2 biggest spikes:")
    for n, b, lab, k in infos_sorted[:5]:
        print(f"   match {n:3} ({lab}): {b:.3f} bits")


if __name__ == "__main__":
    main()
