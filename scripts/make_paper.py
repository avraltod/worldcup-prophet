"""Generate 'Avraa's Prediction' — printable prediction paper (Markdown)."""
import json
from collections import defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from fixtures import GROUP_FIXTURES
from analysis_content import GROUP_ANALYSIS, KO_ANALYSIS, DIARY_INTRO, DIARY_DAYS
from group_dashboard import DASH
import json as _json
QUAL = _json.loads((Path(__file__).parent.parent / "data" / "group_qual.json").read_text())

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

# official match numbers per sheet row (column A of the template)
ROW_MATCH = dict(zip(range(4, 76), [
    1, 2, 25, 28, 53, 54,   3, 8, 26, 27, 51, 52,   7, 5, 30, 29, 49, 50,
    4, 6, 31, 32, 59, 60,  10, 9, 34, 33, 56, 55,  11, 12, 36, 35, 58, 57,
    16, 15, 40, 39, 64, 63, 14, 13, 37, 38, 66, 65, 17, 18, 41, 42, 61, 62,
    19, 20, 44, 43, 69, 70, 23, 24, 48, 47, 71, 72, 22, 21, 46, 45, 67, 68]))

preds = {p["row"]: p for p in json.loads((DATA / "group_predictions.json").read_text())}
sched = json.loads((DATA / "schedule_ub.json").read_text())
GS, KS = sched["group"], sched["ko"]
EV = {int(k): v for k, v in json.loads((DATA / "match_ev_all.json").read_text()).items()}  # expected pts per match
# realistic scorelines (single source of truth, scripts/realistic_scores.py)
REAL = {r["num"]: r for r in json.loads((DATA / "predictions_realistic.json").read_text())}

# ---- predicted group tables ----
tables = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0]))  # grp -> team -> [pts, gd, gf, ga]
for row, grp, h, a in GROUP_FIXTURES:
    hg, ag = preds[row]["hg"], preds[row]["ag"]
    for t, f, g in ((h, hg, ag), (a, ag, hg)):
        st = tables[grp][t]
        st[0] += 3 if f > g else (1 if f == g else 0)
        st[1] += f - g
        st[2] += f
        st[3] += g

KO = {
 "Round of 32 — June 28 to July 3": [
  (73, "South Korea", "Canada", "0-1", "Canada"),
  (74, "Germany", "Paraguay", "1-0", "Germany"),
  (75, "Netherlands", "Morocco", "1-0", "Netherlands"),
  (76, "Brazil", "Japan", "1-0", "Brazil"),
  (77, "France", "Sweden", "1-0", "France"),
  (78, "Ecuador", "Norway", "0-1", "Norway"),
  (79, "Mexico", "Ivory Coast", "1-0", "Mexico"),
  (80, "England", "Algeria", "1-0", "England"),
  (81, "United States", "Bosnia and Herzegovina", "1-0", "United States"),
  (82, "Belgium", "Czechia", "1-0", "Belgium"),
  (83, "Colombia", "Croatia", "0-1", "Croatia"),
  (84, "Spain", "Austria", "1-0", "Spain"),
  (85, "Switzerland", "Iran", "1-0", "Switzerland"),
  (86, "Argentina", "Uruguay", "1-0", "Argentina"),
  (87, "Portugal", "Senegal", "1-0", "Portugal"),
  (88, "Turkey", "Egypt", "1-0", "Turkey")],
 "Round of 16 — July 4 to 7": [
  (89, "Germany", "France", "0-1", "France"),
  (90, "Canada", "Netherlands", "0-1", "Netherlands"),
  (91, "Brazil", "Norway", "1-0", "Brazil"),
  (92, "Mexico", "England", "0-1", "England"),
  (93, "Croatia", "Spain", "0-1", "Spain"),
  (94, "United States", "Belgium", "0-1", "Belgium"),
  (95, "Argentina", "Turkey", "1-0", "Argentina"),
  (96, "Switzerland", "Portugal", "0-1", "Portugal")],
 "Quarter-finals — July 9 to 11": [
  (97, "France", "Netherlands", "1-0", "France"),
  (98, "Spain", "Belgium", "1-0", "Spain"),
  (99, "Brazil", "England", "0-1", "England"),
  (100, "Argentina", "Portugal", "1-0", "Argentina")],
 "Semi-finals — July 14 & 15": [
  (101, "France", "Spain", "0-1", "Spain"),
  (102, "England", "Argentina", "0-1", "Argentina")],
 "Third place — July 18": [(103, "France", "England", "1-0", "France")],
 "FINAL — July 19, MetLife Stadium": [(104, "Spain", "Argentina", "1-0", "SPAIN 🏆")],
}

md = []
md.append("# AVRAA'S PREDICTION")
md.append("## FIFA World Cup 2026 · June 11 – July 19")
md.append("")
md.append("> **Champion: 🇪🇸 SPAIN** — beats Argentina 2-1 in the Final.  ")
md.append("> Podium: 🥈 Argentina · 🥉 France · 4th England")
md.append("")
md.append("*Predictions locked before the June 11, 2026 kickoff (built June 7, Group K recalibrated to prediction-market prices, and a final pre-kickoff review of squad news that confirmed the entry). All kickoff times are Ulaanbaatar time (UTC+8). "
          "Write actual scores in the blank columns after each match.*")
md.append("")
md.append("### How these picks were made (short version)")
md.append("")
md.append("1. **Group matches** — live bookmaker odds (bet365, FanDuel, Betfair, collected June 5–7) "
          "converted to fair probabilities, then a Poisson goal model fits each match's expected goals and "
          "rounds them to a *realistic scoreline* (favourites win 2-1 or 2-0, even games end level). Tested on "
          "the 2018 and 2022 World Cups this predicts actual scores better than gaming the 3/2/1 rule — more "
          "exact scores, closer goal totals — at no cost in pool points.")
md.append("2. **Knockout rounds** — World Football Elo ratings adjusted for confirmed injuries "
          "(Brazil without Rodrygo, Netherlands without Xavi Simons…) and host advantage (Mexico/USA at home).")
md.append("3. **200,000 Monte Carlo simulations** of the whole tournament stress-tested every bracket call — "
          "four picks were changed because the simulations showed a likelier name in that bracket slot.")
md.append("")
md.append("**Simulated champion odds:** Spain 27% · Argentina 19% · France 14% · England 7% · "
          "Colombia 4% · Portugal 4% · Brazil 4% · others <3%")
md.append("")
md.append("*Reading the tables: **Exp.** is the model's expected points for that pick under the pool's 3/2/1 rule "
          "(3 exact, 2 result+goal-difference, 1 result) — higher means a more confident pick. Fill in **Actual** "
          "(the real 90-minute score) and **Pts** (what you scored) as the games are played.*")
md.append("")
md.append("* * *")
md.append("## Group Stage — Twelve Dashboards")
md.append("")
md.append("Each team's qualification odds come from 100,000 simulations. The bars "
          "show the chance of winning the group (dark blue), finishing second "
          "(light blue), advancing as a best third-placed team (orange), or going "
          "out (grey).")
md.append("")
md.append("![Qualification probability by team](paper/figs/fig_group_qual.png)")
md.append("")


def bar(pct):
    filled = round(pct / 10)
    return "█" * filled + "░" * (10 - filled)


MEDAL = {0: "🥇", 1: "🥈", 2: "🥉", 3: "▫️"}
for grp in "ABCDEFGHIJKL":
    d = DASH[grp]
    md.append(f"### Group {grp} — {d['tag']}")
    md.append("")
    md.append(f"*{d['fun']}*")
    md.append("")
    # qualification dashboard table
    md.append("| Team | Win grp | 2nd | 3rd→adv | **Qualify** | Outlook |")
    md.append("|------|:------:|:---:|:------:|:-----------:|---------|")
    qorder = sorted(QUAL[grp].items(), key=lambda x: -x[1]["qual"])
    for i, (t, q) in enumerate(qorder):
        md.append(f"| {MEDAL[i]} {t} | {q['p1']*100:.0f}% | {q['p2']*100:.0f}% | "
                  f"{q['p3adv']*100:.0f}% | **{q['qual']*100:.0f}%** | "
                  f"{bar(q['qual']*100)} |")
    md.append("")
    md.append(f"🔮 **Pick:** {GROUP_ANALYSIS[grp].replace('**Why:** ', '')}")
    md.append("")
    md.append(f"⭐ **Star:** {d['star']}  ")
    md.append(f"👀 **What to watch:** {d['watch']}  ")
    md.append(f"⚡ **Biggest risk:** {d['risk']}")
    md.append("")
    md.append("**Predicted scores:**")
    md.append("")
    md.append("| # | Date (UB) | Match | Pick | Exp. | Actual | Pts |")
    md.append("|---|-----------|-------|:----:|:---:|:------:|:---:|")
    rows = [r for r, g, h, a in GROUP_FIXTURES if g == grp]
    for r in sorted(rows, key=lambda x: ROW_MATCH[x]):
        p = preds[r]
        md.append(f"| {ROW_MATCH[r]} | {GS[str(r)]} | "
                  f"{p['home']} – {p['away']} | **{p['hg']}-{p['ag']}** | "
                  f"{EV.get(ROW_MATCH[r], 0):.2f} | ____ | __ |")
    md.append("")
md.append("* * *")
md.append("## Knockout Bracket")
md.append("")
for rnd, matches in KO.items():
    md.append(f"### {rnd}")
    md.append("")
    md.append("| M# | Date (UB) | Match | Prediction | Advances | Exp. | Actual | Pts |")
    md.append("|----|-----------|-------|:---------:|----------|:---:|:------:|:---:|")
    for num, a, b, _score, adv in matches:
        rr = REAL[num]                       # realistic scoreline from the canonical source
        score = f"{rr['hg']}-{rr['ag']}" + (" (pens)" if rr["pen"] else "")
        md.append(f"| {num} | {KS[str(num)]} | {a} – {b} | **{score}** | {adv} | "
                  f"{EV.get(num, 0):.2f} | ____ | __ |")
    md.append("")
    md.append(KO_ANALYSIS[rnd])
    md.append("")
md.append("* * *")
md.append(DIARY_INTRO.rstrip())
for d in DIARY_DAYS:
    md.append(f"| {d} |  |  |  |  |")
md.append("")
md.append("* * *")
md.append("### Methodology (for the curious)")
md.append("")
md.append("- **Odds → probabilities**: bookmaker margins stripped by normalising implied probabilities. "
          "Matchday-3 fixtures without published odds use Elo-based estimates.")
md.append("- **Poisson scorelines**: for each match, goal rates (λ-home, λ-away) are fitted to reproduce "
          "the market's win/draw/loss probabilities; the predicted score is the rounded expected goals, with "
          "the predicted result preserved (the winner takes the higher score, even games stay level). This "
          "realistic readout out-predicts the points-optimal pick on the 2018/2022 backtest.")
md.append("- **Knockout model**: Elo win expectancy 1/(1+10^(−ΔElo/400)); injury adjustments "
          "Brazil −20, Netherlands −15, Japan −10, Croatia −10, Spain −5; hosts +40 (fading to +20 late).")
md.append("- **Slot-emergence optimisation**: knockout picks maximise P(team actually occupies and wins "
          "that bracket slot) across 200,000 simulated tournaments — not just head-to-head strength. "
          "This is why Croatia (27.5%) is picked over Portugal (25.1%) in M83: Portugal too often wins "
          "his group and never plays that match at all.")
md.append("- **Machine-learning risk check**: a Random Forest *and* XGBoost (gradient boosting) trained on "
          "40,000 simulated tournaments agree (rank correlation 0.83) that getting **Group H right (Spain) "
          "is the single highest-leverage call** — SHAP says naming Spain as Group H winner is worth "
          "**+0.79 knockout points**, ~3× the weakest group call — because Spain's path runs 6 matches deep. "
          "Both models also agree that group results explain only **~50% of the bracket score**; the rest is "
          "knockout luck. The call to protect above all: Spain topping Group H.")
md.append("- Model: odds research + Poisson fitting + Elo Monte Carlo, built June 7 and locked at the June 11 kickoff. "
          "Good luck to everyone — Авраа.")
md.append("")

text = "\n".join(md)
(ROOT / "Avraa_Prediction_WC2026.md").write_text(text, encoding="utf-8")
print(f"written: Avraa_Prediction_WC2026.md ({len(text.splitlines())} lines)")
