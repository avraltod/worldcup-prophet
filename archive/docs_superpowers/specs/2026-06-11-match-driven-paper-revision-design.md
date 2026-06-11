# Match-driven paper revision — design

**Date:** 2026-06-11
**Status:** Design (approved in brainstorming; pending spec review)
**Author:** Avralt-Od Purevjav
**Related:** `scripts/live_update_v2.py` (the v2 before/after recorder), `data/trajectory_v2.json`,
`scripts/scoring.py`, `paper/Avraa_WC2026_paper.tex` (`sec:evolution`), the v2 automation memory.

---

## 1. Goal

Document every World Cup 2026 match as it is played, before and after, so that the formal
paper's live-study section (`sec:evolution`) becomes a faithful, contemporaneous record of how
the pre-registered forecast tracked reality. The model never changes; this is documentation only.

The chosen mental model: **a finished match is a peer-review comment** — *"why don't you include
this result?"* — and each update is the author's revision in response: integrate the new data
point, propagate every number it touches through the *living* layer of the paper, re-read, and
emit a new complete version. Running this 104 times produces 104 versioned papers — a match-by-match
revision history that is itself a research artifact.

### Success criteria
- After match M, one command produces an updated paper (PDF + `.tex` snapshot) that incorporates
  match M everywhere it matters in the living layer, with all living numbers internally consistent.
- The pre-registered (frozen) layer is **byte-identical across all 104 versions**.
- Each version carries a response-to-reviewer note recording what that match changed and why.
- The per-match interpretation is captured contemporaneously (before the next match is known).
- The author's effort per match is minutes: everything mechanical is auto-filled; only the
  1–3 sentence interpretation needs human judgment, and even that is auto-drafted first.

### Non-goals (YAGNI)
- No model change, no in-tournament learning, no touch to the locked picks or `prereg-2026`.
- The Learning track stays parked; this spec documents the frozen forecast only.
- The public markdown dossier diary (`Avraa_Prediction_WC2026.md`) and the README block are
  **secondary surfaces**, fed from the same source later; they are out of scope for v1.
- No attempt to automate the human interpretation away — it is drafted, never decided, by code.

---

## 2. Existing infrastructure this builds on

- **`data/trajectory_v2.json`** — the v2 recorder already writes one PRE and one POST record per
  match. PRE: `{champion, market_champion, info_bits, lineup, ...}`. POST: `{result, performance:
  {points, ev_points, p_outcome, brier}, champion, info_bits, ...}`. This is the structured spine;
  this project adds a documentation/revision layer on top of it and writes nothing back into it.
- **`scripts/scoring.py`** — the authoritative 3/2/1 + Brier scorer. Reused, not duplicated.
- **`paper/Avraa_WC2026_paper.tex`** — already reserves `\subsection{Forecast evolution: a
  pre-registered live study}\label{sec:evolution}` (L263) and the six failure modes (L541–546).
- **`archive/paper_versions/`** — an existing precedent for versioned `.tex`/PDF snapshots.
- **README `<!-- LIVE-RESULTS:START/END -->`** — the existing marker-block pattern this design
  reuses for generated LaTeX blocks.

---

## 3. The two strata (the integrity boundary)

The paper is explicitly divided. The revision touches only the living stratum.

| Stratum | Across the 104 versions | Contents |
|---|---|---|
| **Frozen** (pre-registered) | **Never changes** — byte-identical | original forecast, methodology, locked picks, the prereg sections, the abstract's pre-registered claims |
| **Living** (the live study) | Revised every match | `sec:evolution` generated blocks, the live results ledger table, the champion-trajectory figure, running aggregates, the failure-mode tally, and any *"as of match M"* line |

Mechanism that makes the boundary enforceable:

1. **Marker-delimited generated blocks.** All generated LaTeX lives between
   `% LIVE-EVOLUTION:START` / `% LIVE-EVOLUTION:END` markers inside `sec:evolution` (and a
   second pair for the ledger table). The generator only ever rewrites between markers; it errors
   if a marker is missing. Frozen prose lives outside markers and is never written.
2. **Living numbers as generated macros.** Numbers that must appear in otherwise-frozen-looking
   prose (e.g., an abstract "live scorecard" line, a conclusion running-performance sentence) are
   LaTeX macros in a generated file `paper/live_stats.tex` (`\def\liveCumPoints{44}`,
   `\def\liveMeanBrier{0.19}`, `\def\liveChampSpain{27.1}`, ...). The paper `\input`s it. Frozen
   prose references `\liveCumPoints`; the consistency pass regenerates only `live_stats.tex`, so
   one match changes one generated file and every reference updates together. The original
   pre-registered figure, where one is shown alongside, stays as a literal and gets a tagged twin.

The frozen forecast is therefore safe by construction: the revision can only write markers, macros,
the Match Book, `REVISIONS.md`, the trajectory figure, and version snapshots.

---

## 4. Architecture

```
match finished (POST record in trajectory_v2.json)        [Component 1: trigger]
        │
        ▼
scripts/update_after_match.py M                            [Component 5: one command]
        │
        ├─ build Match Book entry  paper/match_book/M0XX.md [Component 2]
        │     PRE / RESULT+POST auto-filled; INTERPRETATION auto-drafted
        │
        ├─ draft_interpretation → author edits             [Component 3: self-learning]
        │     (draft → edit) diff appended to corrections.md
        │
        ├─ compute live_stats (single object)              [Component 7: consistency]
        │
        ├─ render generated blocks + live_stats.tex         [Component 4: paper integration]
        │     sec:evolution table/figure/highlights; macros
        │
        ├─ append response note  paper/REVISIONS.md         [Component 9]
        │
        ├─ build PDF → snapshot  paper/versions/..._M0XX.*  [Component 8: 104 versions]
        │
        └─ allowlist guard on every written path            [Component 6: integrity]
```

### Component 1 — Trigger
A match's POST record landing in `trajectory_v2.json` is the event. `update_after_match.py M`
detects *"POST exists for M, but the paper is not yet revised through M"* (tracked in a small
`paper/match_book/index.json`: `{"documented": [1, 2, ...]}`) and opens the cycle. Can be invoked
by hand or offered automatically when a POST commits. Same code path either way.

### Component 2 — Match Book entry
One file per match, `paper/match_book/M001.md`, fixed template:

```markdown
---
match: 1
stage: "Group A"
fixture: "Mexico v South Africa"
kickoff: 2026-06-11T19:00:00Z
documented_at: 2026-06-11T21:10:58Z    # contemporaneity stamp
forecast_commit: <git sha the forecast was graded against>
failure_mode: null                      # or one of the six enum keys
---

## PRE   (auto from the pre record)
- Pick: 2-1   P(H/D/A): 0.672 / 0.209 / 0.119
- Market (de-vigged) champion top: Spain 16.4%, France 15.5%, ...
- Pre-match champion top-5: Spain 27.1%, Argentina 17.7%, ...
- Watch line: a South Africa draw or win would be the surprise (model 67% home).

## RESULT
2-0 (home win)

## POST   (auto from the post record)
- Points: 1/3   Brier: 0.166   p(outcome): 0.672
- Info: 0.0011 bits
- Top movers: Argentina 17.68→18.15, England 6.98→6.88, ...

## INTERPRETATION   (auto-drafted, author-edited — the only human field)
A 67%-likely home win duly arrived, so the opener barely informs the title race
(0.001 bits); the realistic 2-1 read lost the exact-score points to a clean sheet.
```

The `failure_mode` enum is keyed to the paper's six (L541–546): `champion_call`, `bracket_decay`,
`group_upset_cascade`, `md3_rotation`, `systematic_rating_error`, `knockout_coinflip`.

### Component 3 — Auto-draft + self-learning loop
`draft_interpretation(entry)` produces the first-pass interpretation from the structured deltas
(expected-vs-surprise via `info_bits`, the scoreline-vs-pick gap, any failure-mode signal),
written in the author's voice (the `avraa-voice` skill rules apply). The author edits; the
`(draft, final)` pair is appended to `paper/match_book/corrections.md`. Each subsequent draft is
conditioned on the accumulated corrections, so drafts calibrate to the author's judgment over the
run. This is the concrete "self-learning": the loop is the corrections log, not a model retrain.

### Component 4 — Paper integration
A generator (`scripts/render_evolution.py`) consumes the Match Book and rewrites, between markers:
- **Results ledger table** — one row per documented match: `M, fixture, pick, result, pts, Brier,
  info_bits, failure-mode`. Carries **all** documented matches (all 104 by the end).
- **Champion-trajectory figure** — refreshed through match M from the trajectory data.
- **Running aggregates** — cumulative points, mean Brier, exact-rate, realistic-vs-EV running
  delta, failure-mode tally — emitted both as a small table and as `live_stats.tex` macros.
- **Rolling narrative** — the interpretation notes compiled; the prose **highlights only the
  informative matches** (high `info_bits`, a failure-mode fire, an upset). The table/figure carry
  the exhaustive record; the prose stays readable. Full per-match notes live in the Match Book,
  optionally surfaced as a paper appendix.

The paper then recompiles via its existing LaTeX build.

### Component 5 — The one command
```
python3 scripts/update_after_match.py 1
```
Scaffolds the entry (auto-fields filled), shows the drafted interpretation, takes the edit,
regenerates the blocks + macros, appends the revision note, builds the PDF, snapshots the version,
runs the guard, and reports:
> Paper revised through Match 1 — 1 documented · cumulative 1 pt · mean Brier 0.166 ·
> +1 ledger row · trajectory refreshed · 0 failure modes fired · snapshot M001.

### Component 6 — Integrity guards
- **Allowlist.** The update may write only: `paper/match_book/**`, `paper/REVISIONS.md`,
  `paper/live_stats.tex`, the marker-delimited regions of `paper/Avraa_WC2026_paper.tex`, the
  trajectory figure asset, and `paper/versions/**`. Any staged write outside the allowlist aborts
  the run (mirrors the v2 commit-step guard). Never the model, the locked picks, the frozen `.tex`
  outside markers, or `prereg-2026`.
- **Marker integrity.** Missing or unbalanced `LIVE-EVOLUTION` markers abort before any write.
- **Frozen-hash check.** A pre-run hash of the frozen regions is compared post-run; any change
  aborts and reverts.
- **Contemporaneity.** `documented_at` is stamped at first write and never rewritten; later edits
  to an entry are recorded as amendments, so a note can be shown to predate later matches.
- **Idempotent.** Re-running for an already-documented match is a no-op unless `--reopen M`.

### Component 7 — Consistency pass
All living numbers derive from one computed `live_stats` object (built from `trajectory_v2.json`
+ the Match Book index). It is rendered once to `live_stats.tex`; every in-prose living number is
a macro reference, so a single match cannot leave two places disagreeing.

### Component 8 — Versioning (104 versions)
Each successful update writes an immutable snapshot `paper/versions/Avraa_WC2026_paper_M0XX.pdf`
and the `.tex` it was built from, and updates a `LATEST` pointer. The accumulated sequence is the
match-by-match revision reel.

### Component 9 — Reviewer-revision response log
Each update appends one paragraph to `paper/REVISIONS.md`, formatted as a response-to-reviewers
note:
> **Rev M031 (Match 31, Germany 1-0 Ivory Coast).** Added ledger row; champion Spain 27.0→27.1%;
> cumulative 44 pts, mean Brier 0.19; failure-mode "MD3 rotation" not triggered. Updated the
> evolution table, trajectory figure, and abstract scorecard line. No frozen content changed.

---

## 5. Data flow (end to end)

1. v2 recorder commits a POST record for match M to `trajectory_v2.json` (existing).
2. `update_after_match.py M` reads the PRE+POST records and `scoring.py` outputs.
3. It scaffolds `match_book/M0XX.md` with PRE/RESULT/POST auto-filled and a drafted interpretation.
4. Author edits the interpretation (and the failure-mode tag if any); the diff lands in
   `corrections.md`.
5. `live_stats` is recomputed; `render_evolution.py` rewrites the marker blocks and `live_stats.tex`.
6. `REVISIONS.md` gets the response note; `match_book/index.json` marks M documented.
7. LaTeX builds; the PDF + `.tex` are snapshotted to `paper/versions/`.
8. The allowlist + frozen-hash guards verify nothing outside the living layer changed.

---

## 6. File / artifact layout

```
paper/
  Avraa_WC2026_paper.tex        # frozen prose + LIVE-EVOLUTION marker blocks + \input{live_stats}
  live_stats.tex                # GENERATED — living-number macros
  REVISIONS.md                  # GENERATED — response-to-reviewer log, one note per match
  match_book/
    index.json                  # {"documented": [...]}
    corrections.md              # (draft → edit) pairs, the self-learning log
    M001.md ... M104.md         # one contemporaneous entry per match
  versions/
    Avraa_WC2026_paper_M001.pdf # immutable snapshots (+ .tex)
    LATEST -> ...
scripts/
  update_after_match.py         # the one command (driver)
  render_evolution.py           # Match Book + trajectory → generated LaTeX blocks + macros
  draft_interpretation.py       # auto-draft note from structured deltas, in avraa-voice
```

---

## 7. Error handling

- Missing POST record for M → abort with "match M not final / not recorded yet."
- Missing markers or `live_stats.tex` `\input` → abort before writing.
- LaTeX build failure → keep the previous `LATEST`; report the build log; do not snapshot.
- Guard or frozen-hash violation → revert all writes from the run, report the offending path.
- Re-run on a documented match → no-op unless `--reopen`.

---

## 8. Testing

- **Auto-fill unit test:** a sample POST record yields the correct Match Book fields; the
  scorecard numbers equal `scoring.py` for the same input.
- **Golden test:** a fixture match → expected `match_book/M0XX.md` and expected `sec:evolution`
  block + `live_stats.tex`.
- **Consistency test:** every living number in the rendered `.tex` resolves to a `live_stats`
  macro (no stray literals in living regions).
- **Frozen-invariance test:** run the updater for several matches; assert the frozen regions'
  hash is unchanged and `prereg-2026` is untouched.
- **Idempotency test:** running M twice changes nothing the second time.
- **Allowlist test:** an injected write outside the allowlist aborts the run.

---

## 9. Open questions for review

1. **Build command.** Confirm the exact LaTeX build invocation for `Avraa_WC2026_paper.tex` so
   the driver can call it (latexmk? a Makefile? a script?).
2. **Appendix of full notes.** Do the full per-match interpretations get a paper appendix, or stay
   Match-Book-only with the prose highlighting the informative ones? (Current spec: Match-Book-only,
   appendix optional.)
3. **Abstract scorecard line.** Confirm which one or two living numbers earn a tagged twin in the
   abstract/conclusion (e.g., cumulative points and mean Brier), so the pre-registered figures keep
   their original literals alongside.
4. **Snapshot storage.** 104 PDFs in-repo, or snapshots kept local / in `archive/`? (Affects repo
   size on the public mirror.)
