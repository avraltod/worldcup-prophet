# Avraa's Prophet — Living Recursive Forecaster (Design Spec)

**Date:** 2026-06-09 (pre-kickoff; tournament runs June 11 – July 19, 2026)
**Author:** Avralt-Od Purevjav
**Status:** Design approved in brainstorming; pending implementation plan.
**Hard constraint:** Free data sources only — nothing is ever purchased.

---

## 1. Purpose

Turn the paper's central thesis — *a forecast evolves as results arrive, and the
information is uneven* — from a one-time measurement into a living system.

Starting from a frozen pre-tournament baseline (**"Avraa's Prophet"**, the 104
predictions locked at the June 11 kickoff), run **two forecasters in parallel**
through the 2026 World Cup, record a **before/after** forecast snapshot for every
game, and at the end identify the handful of events that actually moved the
tournament — and how to model them next time (2030).

### Success criteria

1. A complete, timestamped trajectory of forecasts (~416 snapshots: 208 per track),
   produced by an **unattended daily loop**.
2. A defensible answer to the headline question: **did learning from performance
   beat conditioning on results alone, and when did it help vs. chase noise?**
3. An **attribution log** naming the most informative games (KL-divergence, bits).
4. A **living paper section** that subsumes roadmap item A1 (the promised
   confirmatory study) and becomes the centerpiece.
5. Runs **entirely on free data**; degrades gracefully when any free source fails.

---

## 2. Architecture — two tracks from one baseline

Both tracks start from the same frozen baseline forecast and diverge only in how
they react to each played game. The result of the study is the **gap between them**.

- **Track A — Frozen Prophet (control).** After each game, fix the played results
  and re-simulate the rest. Team strengths never change. *(Half-exists today:
  `condition.py` + `record_update.py`.)*
- **Track B — Learning Prophet (new).** Same conditioning on results, **plus** after
  each game it updates each team's strength from *how they played* (Section 6),
  then re-simulates. It learns as it goes.

Both emit a full champion/stage forecast at every step. Headline result: **A vs B.**

Two recorded outputs wrap the tracks:
- the **before/after snapshot trajectory** (every forecast, timestamped), and
- an **attribution log** — the KL-divergence of each update ("this game told us
  *X* bits"), surfacing the few events that moved the tournament.

---

## 3. The snapshot — the unit of record

Everything is built from one object, recorded **twice per game, for each track**
(2 phases × 104 games = **208 snapshots per track; 416 across both tracks**):

```
snapshot = {
  timestamp,
  game,                       # match id / fixture
  phase: before | after,
  track: frozen | learning,
  champion_probs[48],
  stage_probs[48],            # reach R32/R16/QF/SF/final/champion
  team_strengths[48],         # ratings used for this snapshot
  market_odds,                # de-vigged Polymarket champion odds (when free-available)
  KL_from_previous,           # info content of this update, in bits
  info_source                 # what moved it: lineup | result | performance | news
}
```

- **before** (at kickoff): confirmed lineups + late injury/news + strengths-so-far.
- **after** (at full-time): result + performance (proxy-xG, real-xG-when-free).
- `info_source` lets the final paper decompose total forecast change by source
  ("pre-match team news drove X%; on-pitch evidence drove the rest").

Each game therefore yields a **four-cell story** — frozen-before, frozen-after,
learning-before, learning-after — and the differences between those cells *are*
the experiment.

---

## 4. Data layer (free sources only)

### Available automatically (free), every match

| Category | Fields | Source |
|---|---|---|
| Result | scoreline, winner | data tool (`get_event_summary`) |
| Team stats | possession, **shots, shots on target**, corners, fouls, offsides, passes | `get_event_statistics` |
| Timeline | goals, **yellow/red cards**, substitutions (w/ minute) | `get_event_timeline` |
| Pre-match | confirmed lineups, referee, venue | `get_event_lineups` / schedule |
| Market | Polymarket champion + match odds (de-vigged) | `market_snapshot.py` (wired) |
| Strength | Elo ratings | existing model |

### The xG gap and the policy

xG is **not** free-available for the World Cup via the primary data tool
(`"xG data not available for world-cup"` — Understat covers top-5 leagues only).
Policy:

- **Proxy (reliable backbone):** estimate λ_obs from shots + shots-on-target counts
  (a calibrated "poor man's xG"). Built only from the free data tool; **always works.**
- **Real xG (free enrichment):** scrape from **FBref** or **FotMob** (free to view,
  Opta-powered). Used **when present**, with **graceful fallback to the proxy**.
- **Honest caveat:** free ≠ guaranteed — scraping is gray-area on their terms,
  fragile to page changes, and lands after the match, not live. The system never
  depends on it. We additionally log proxy-vs-real-xG agreement as a diagnostic.

### Not on a free feed

- **In-tournament injuries/news**: no free auto-feed for the WC (`get_missing_players`
  is Premier-League-only). This input is **best-effort** — a free news source or a
  quick manual line. The system runs fine without it (the `before` snapshot simply
  carries no `news` component that game).

---

## 5. Cadence — before and after each game

Two full snapshots per game, both tracks:

- **before** (≈1h pre-kickoff): incorporates confirmed **lineups** + late
  **injury/news** + strengths learned so far. Separates *"team news moved the
  forecast"* from *"the game moved it."*
- **after** (full-time): incorporates **result** + **performance**.

~208 snapshots × 2 tracks over the tournament.

---

## 6. Learning engine — regularized Elo (Approach #3)

The central modeling challenge: each team plays only **3 group games** (+1–4
knockouts), so naive learning overreacts to one match. The fix is shrinkage toward
the frozen baseline, and **the shrinkage strength is the swept knob** — sweeping it
is itself a paper result (learning helps up to a point, then chases noise).

Per team, after each game:

1. **Expected** λ_exp — the expected goals the team's pre-match rating implied
   (already fit from ratings via the Poisson model).
2. **Observed** λ_obs — the team's xG signal this game: real xG if free-available,
   else the shots-based proxy.
3. **Surprise** δ = λ_obs − λ_exp (attack), mirror for defense. *Out-xG expectation
   and the rating rises even in a loss; get dominated and it falls even in a win* —
   the reason performance ≠ result.
4. **Update, shrunk to baseline:**
   `new_rating = baseline + (1−w)·drift_so_far + w·K·δ`,
   bounded so a single game can move a rating at most ±X. **w** (and K) is the swept
   knob: at 0 it *is* the frozen track; higher learns harder. Report the curve over
   a small grid.
5. **Re-simulate** updated ratings through the existing Monte Carlo (≈50k runs live).

Three consistent dominant games move a team meaningfully; one fluke barely does.

---

## 7. Components — new vs. reused

**Reused (exists):** `condition.py` (re-sim from fixed results), `record_update.py`
(logging + KL), `market_snapshot.py`, `ev321.py`, `poisson_model.py`, `simulate.py`.

**New (small, focused modules):**

| Module | Responsibility |
|---|---|
| `collect_match.py` | Pull a finished game's stats/timeline/lineups → clean record |
| `fetch_xg.py` | Try FBref/FotMob real xG; fall back to proxy; flag source |
| `performance.py` | Stats → λ_obs (proxy + real-xG blend) |
| `learn.py` | The regularized Elo update (Section 6); owns Track B ratings |
| `snapshot.py` | Assemble + record a snapshot (both tracks, before/after) |
| `run_matchday.py` | Daily orchestrator (the loop) |
| `plot_attribution.py` | "What moved the forecast" figure; extend `plot_trajectory.py` for A-vs-B |

Design for isolation: each module has one purpose and a narrow interface
(`collect → performance → learn → snapshot`), so each can be tested alone.

---

## 8. Testing / validation — replay the 2022 World Cup

The entire **2022 World Cup is free in the data source** (64 games, full stats).
Before a 2026 ball is kicked, **replay 2022 end-to-end**:

- baseline from 2022 pre-tournament ratings,
- run both tracks game-by-game,
- verify (a) the pipeline runs unattended, (b) learning behaves sanely (does it
  catch Argentina's rise / Germany's group exit?), (c) the proxy tracks reality.

This is **both the test harness and a second backtest for the paper**, and it
de-risks the system while two days remain before June 11.

**Daily loop:** `run_matchday.py` → collect finished games → before/after snapshots
(both tracks) → update learning ratings → re-simulate → log + refresh figures + dossier.

---

## 9. Outputs & the living paper

New centerpiece section, *"Learning as the Tournament Speaks,"* growing with results:

- **A-vs-B trajectory** — did learning help, and by how much?
- **Attribution chart** — which games carried the information (KL, bits).
- **Swept-knob curve** — how much learning is too much.
- **"What to model next time"** — the events that mattered, as 2030 design notes.

Subsumes roadmap item A1; converts the promised confirmatory study into the
paper's actual centerpiece.

---

## 10. Robustness & operating constraints

- **Free only (hard):** no paid data, ever. Every external pull (xG scrape, market)
  is wrapped; on failure it logs the gap and falls back (proxy for xG, last value
  for market). The run never breaks and never requires anything paid.
- **The lock:** the frozen baseline ("Avraa's Prophet") and the submitted pool entry
  are immutable after the June 11 kickoff. Only the *evaluation* and the *learning
  track* evolve. Both tracks and all snapshots are timestamped for the out-of-sample
  record.
- **Reproducibility:** fixed seeds; every snapshot retained; the 2022 replay is a
  permanent regression test.

---

## 11. Out of scope (for now)

- Paid/premium xG or data feeds (violates the free constraint).
- Live in-game (minute-by-minute) updating — snapshots are pre-kickoff and full-time.
- Automated injury/news ingestion beyond free best-effort.
- Re-fitting the group-stage market-calibrated Poisson layer mid-tournament (the
  learning track updates *Elo strengths*, not the locked group-odds calibration).

---

## 12. Open questions to settle in the implementation plan

- Exact proxy-xG calibration (shots/SoT → goals) — fit on 2018+2022 WC data.
- Bound ±X and grid for the shrinkage knob **w** — pin during the 2022 replay.
- Live Monte Carlo size (speed vs. noise) — likely 50k; confirm on timing.
- FBref vs FotMob as the primary free xG scrape — pick by reliability in the replay.
