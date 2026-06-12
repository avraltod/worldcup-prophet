"""COUNTERFACTUAL Mongolia scenario — the honest version of the title-run
figure. Mongolia did NOT qualify; for fun they replace Bosnia and Herzegovina
in Group B at real-world Elo 1050. At that strength a TITLE world is
unfindable (~1-in-a-trillion; in 200,000 simulated tournaments Mongolia never
won two knockout games), so this figure replays their BEST world instead:
generator seed 22010 — beat hosts Canada 1-0 in the opener, advance third
while Canada finish last, knock out GERMANY in the R32, fall to France in the
R16 (Switzerland win that world's title). Tracks Mongolia's stage
probabilities, not champion. Writes archive/Mongolia_World_Cup_scenario.png."""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import condition as C
from poisson_model import fit_rates
from dryrun import generate_realization, kl_bits

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "archive"
CACHE = OUT / "Mongolia_best_trajectory.json"
GEN_SEED = 22010
N = 8000

# ---- the counterfactual patch: Mongolia in for Bosnia, Elo 1050 ------------
C.ELO["Mongolia"] = 1050


def synth(d):
    e = 1 / (1 + 10 ** (-d / 400))
    pD = 0.30 * math.exp(-abs(d) / 700)
    pH = max(0.01, e - pD / 2)
    pA = max(0.01, 1 - pH - pD)
    s = pH + pD + pA
    return pH / s, pD / s, pA / s


for row in (10, 12, 15):
    lh, la, h, a = C.RATES[row]
    h2 = "Mongolia" if h == "Bosnia and Herzegovina" else h
    a2 = "Mongolia" if a == "Bosnia and Herzegovina" else a
    pH, pD, pA = synth(C.rating(h2) - C.rating(a2))
    C.RATES[row] = (*fit_rates(pH, pD, pA), h2, a2)

g_res, ko_res, champ = generate_realization(GEN_SEED)
assert champ == "Switzerland", champ

group_order = sorted(g_res)
ko_order = list(C.R32) + list(C.R16) + list(C.QF) + list(C.SF) + [104]

if CACHE.exists():
    traj = json.loads(CACHE.read_text())
else:
    traj = []
    cum = {"group": {}, "ko": {}}

    def snap(n, label, kind, prev):
        probs = C.conditional_probs(cum, N=N, seed=2026)
        champ_now = {t: d["champion"] for t, d in probs.items() if d["champion"] > 0}
        bits = 0.0 if prev is None else kl_bits(champ_now, prev)
        mng = probs.get("Mongolia", {})
        traj.append({"label": label, "n": n, "info_bits": round(bits, 4),
                     "mongolia": {k: round(v, 4) for k, v in mng.items()},
                     "champion": {t: round(p, 4) for t, p in champ_now.items()},
                     "kind": kind})
        return champ_now

    prev = snap(0, "baseline", "baseline", None)
    steps = [("group", m) for m in group_order] + [("ko", m) for m in ko_order]
    for i, (kind, m) in enumerate(steps, 1):
        if kind == "group":
            cum["group"][str(m)] = g_res[m]
        else:
            cum["ko"][str(m)] = ko_res[m]
        prev = snap(i, f"{kind} match {m}", kind, prev)
        if i % 12 == 0 or traj[-1]["info_bits"] > 0.05:
            mg = traj[-1]["mongolia"]
            print(f"  [{i:3}/104] {traj[-1]['label']:<16} "
                  f"info={traj[-1]['info_bits']:5.3f} | "
                  f"MNG adv {mg.get('advance_KO',0)*100:5.1f}% "
                  f"R16 {mg.get('R16',0)*100:5.1f}% QF {mg.get('QF',0)*100:4.1f}%",
                  flush=True)
    CACHE.write_text(json.dumps(traj, ensure_ascii=False, indent=1))

# --------------- figure (Uzbekistan house style, stage metric) --------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

GROUP_END = 72
TEAL = "#11a0b8"

ns = [s["n"] for s in traj]
adv = [100 * s["mongolia"].get("advance_KO", 0.0) for s in traj]
r16 = [100 * s["mongolia"].get("R16", 0.0) for s in traj]
qf = [100 * s["mongolia"].get("QF", 0.0) for s in traj]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12.2, 9.5),
                               gridspec_kw={"height_ratios": [2.0, 1.0]})

ax1.plot(ns, adv, color=TEAL, lw=2.0, ls="--", label="advance from group")
ax1.plot(ns, r16, color=TEAL, lw=4.5, label="reach the R16",
         solid_capstyle="round", zorder=5)
ax1.plot(ns, qf, color="#1f2440", lw=2.0, label="reach the QF")

ax1.axvspan(0, GROUP_END, color="0.96", zorder=0)
ax1.text(GROUP_END * 0.55, 95, "group stage", ha="center", color="0.6", fontsize=15)
ax1.text((GROUP_END + 104) / 2, 95, "knockouts", ha="center", color="0.6", fontsize=15)
ax1.set_ylabel("P(Mongolia reach stage), %", fontsize=15)
ax1.set_xlim(0, 105)
ax1.set_ylim(0, 100)
ax1.tick_params(labelsize=14)
ax1.set_title("The best MONGOLIA world in 200,000 simulations "
              f"(counterfactual, seed {GEN_SEED})",
              fontsize=18, fontweight="bold", color=TEAL, loc="left", pad=12)
ax1.legend(frameon=False, loc="lower right", fontsize=14,
           bbox_to_anchor=(0.99, 0.04))
for s in ("top", "right"):
    ax1.spines[s].set_visible(False)

m3 = group_order.index(3) + 1
ax1.annotate("Jun 13: MONGOLIA 1-0 CANADA\n— the host, beaten in game one",
             xy=(m3, adv[m3]), xytext=(10, 78),
             fontsize=14, fontweight="bold", color=TEAL, ha="left",
             arrowprops=dict(arrowstyle="->", color=TEAL, lw=1.8))
ax1.annotate("through as a third-placer\n(Canada finish LAST)",
             xy=(72, r16[72]), xytext=(48, 40),
             fontsize=13.5, color=TEAL, ha="left",
             arrowprops=dict(arrowstyle="->", color=TEAL, lw=1.6))
n74 = 72 + ko_order.index(74) + 1
ax1.annotate("R32: BEAT GERMANY",
             xy=(n74, r16[n74]), xytext=(76, 72),
             fontsize=14, fontweight="bold", color=TEAL, ha="left",
             arrowprops=dict(arrowstyle="->", color=TEAL, lw=1.8))
n89 = 72 + ko_order.index(89) + 1
ax1.annotate("R16: France\nend the dream",
             xy=(n89, qf[n89] + 2), xytext=(88, 45),
             fontsize=13.5, color="#1f2440", ha="left",
             arrowprops=dict(arrowstyle="->", color="#1f2440", lw=1.6))

bx = [s["n"] for s in traj if s["n"] >= 1]
by = [s["info_bits"] for s in traj if s["n"] >= 1]
ax2.bar(bx, by, width=0.9, color="#1f77b4", linewidth=0)
ax2.axvspan(0, GROUP_END, color="0.96", zorder=0)
ax2.set_xlabel("Matches played", fontsize=15)
ax2.set_ylabel("Info gained\n(bits)", fontsize=15)
ax2.set_xlim(0, 105)
ax2.tick_params(labelsize=14)
for s in ("top", "right"):
    ax2.spines[s].set_visible(False)

fig.text(0.045, 0.030,
         "Counterfactual for fun — Mongolia did NOT qualify. They take Bosnia and "
         "Herzegovina's Group B slot at real-world Elo 1050; everything else is the "
         "locked model.",
         fontsize=10, color="0.45")
fig.text(0.045, 0.008,
         "A Mongolia TITLE world is ~1-in-a-trillion — in 200,000 simulated "
         "tournaments they never won two knockout games. This is the best one.  "
         "Avraa's prediction model",
         fontsize=10, color="0.45")
fig.tight_layout(rect=(0, 0.035, 1, 1))
fig.savefig(OUT / "Mongolia_World_Cup_scenario.png", dpi=150)
print("wrote archive/Mongolia_World_Cup_scenario.png")
