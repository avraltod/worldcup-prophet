"""Record a forecast update after new results: the heart of the live experiment.

Adds new results to the cumulative log, re-conditions the forecast, then logs:
  - each team's new champion (and stage) probabilities
  - the change from the previous snapshot (which team moved most)
  - the INFORMATION CONTENT of the update: KL divergence between the champion
    distribution before and after, in bits. This quantifies how much each batch
    of results moved the forecast -- the paper's central metric.

Usage:
  python3 scripts/record_update.py '<json results>' "label"
  e.g. '{"group": {"1": [2,0], "8": [0,1]}}' "Matchday 1, June 11"
  Pass {} with a label to just snapshot the current baseline (t=0).
"""
import json
import math
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from condition import conditional_probs
from market_snapshot import fetch_market_champion

DATA = Path(__file__).parent.parent / "data"
LOG = DATA / "results_log.json"
TRAJ = DATA / "trajectory.json"
N = 50000


def kl_bits(p_after, p_before):
    """KL(after || before) over the champion distribution, in bits."""
    teams = set(p_after) | set(p_before)
    eps = 1e-6
    s = 0.0
    for t in teams:
        pa = p_after.get(t, 0) + eps
        pb = p_before.get(t, 0) + eps
        s += pa * math.log2(pa / pb)
    return s


def main():
    new = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    label = sys.argv[2] if len(sys.argv) > 2 else date.today().isoformat()

    log = json.loads(LOG.read_text()) if LOG.exists() else {"group": {}, "ko": {}}
    log.setdefault("group", {})
    log.setdefault("ko", {})
    for k, v in new.get("group", {}).items():
        log["group"][k] = v
    for k, v in new.get("ko", {}).items():
        log["ko"][k] = v
    LOG.write_text(json.dumps(log, ensure_ascii=False, indent=1))

    probs = conditional_probs(log, N=N)
    champ_after = {t: d["champion"] for t, d in probs.items() if d["champion"] > 0}

    traj = json.loads(TRAJ.read_text()) if TRAJ.exists() else []
    champ_before = traj[-1]["champion"] if traj else None
    n_played = len(log["group"]) + len(log["ko"])

    info_bits = kl_bits(champ_after, champ_before) if champ_before else 0.0
    # biggest movers
    movers = []
    if champ_before:
        for t in set(champ_after) | set(champ_before):
            d = champ_after.get(t, 0) - champ_before.get(t, 0)
            if abs(d) >= 0.005:
                movers.append((t, round(d * 100, 1)))
        movers.sort(key=lambda x: -abs(x[1]))

    market = fetch_market_champion()  # {} if offline/unavailable
    entry = {"label": label, "n_played": n_played,
             "info_bits": round(info_bits, 4),
             "champion": {t: round(p, 4) for t, p in champ_after.items()},
             "market_champion": market,
             "full": {t: probs[t] for t in champ_after},
             "top_movers": movers[:6]}
    traj.append(entry)
    TRAJ.write_text(json.dumps(traj, ensure_ascii=False, indent=1))

    print(f"=== {label} ===  ({n_played}/104 matches played)")
    if champ_before:
        print(f"information content of this update: {info_bits:.3f} bits")
        if movers:
            print("biggest probability moves (champion):")
            for t, d in movers[:6]:
                print(f"  {t:<16} {'+' if d >= 0 else ''}{d:.1f} pp")
    print("\nchampion probabilities now (model vs market):")
    print(f"  {'team':<16} {'model':>7} {'market':>7}  {'gap':>6}")
    for t, p in sorted(champ_after.items(), key=lambda x: -x[1])[:8]:
        mp = market.get(t)
        if mp is not None:
            print(f"  {t:<16} {p*100:6.1f}% {mp*100:6.1f}%  {(p-mp)*100:+5.1f}")
        else:
            print(f"  {t:<16} {p*100:6.1f}% {'  n/a':>7}")
    if market:
        # who does the model most over/under-rate vs the market?
        gaps = sorted(((t, champ_after.get(t, 0) - market.get(t, 0))
                       for t in set(champ_after) | set(market)),
                      key=lambda x: -abs(x[1]))
        print("  largest model-vs-market disagreements:")
        for t, g in gaps[:3]:
            verb = "over" if g > 0 else "under"
            print(f"    model {verb}-rates {t} by {abs(g)*100:.1f} pp")


if __name__ == "__main__":
    main()
