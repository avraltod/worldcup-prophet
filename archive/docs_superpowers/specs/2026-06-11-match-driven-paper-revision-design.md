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
- The author's effort per match is **zero** — the GitHub Actions pipeline runs the full cycle
  hands-off, including the voice-matched interpretation; editing a note later is optional.

### Non-goals (YAGNI)
- No model change, no in-tournament learning, no touch to the locked picks or `prereg-2026`.
- The Learning track stays parked; this spec documents the frozen forecast only.
- The public markdown dossier diary (`Avraa_Prediction_WC2026.md`) and the README block are
  **secondary surfaces**, fed from the same source later; they are out of scope for v1.
- The v2 live-results recorder is **not modified** and stays zero-secret / stdlib-only; this
  paper-revision pipeline is a separate, isolated workflow that carries the API secret and the
  `anthropic` dependency, so the live-results path keeps its purity.

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
        ├─ build PDF (latexmk) → upload snapshot as CI artifact [Component 8: 104 versions]
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

### Component 3 — Interpretation draft (Claude in CI) + self-learning loop
`draft_interpretation(entry)` calls the Anthropic API from inside GitHub Actions, passing the
structured deltas (expected-vs-surprise via `info_bits`, the scoreline-vs-pick gap, any
failure-mode signal), the `avraa-voice` rules, and the accumulated `corrections.md` notes as
few-shot examples. It returns the voice-matched interpretation, published without a required human
step — so the pipeline is fully hands-off. If the API call fails, it falls back to a deterministic
templated sentence so the paper still updates, and flags the entry for an optional later voice
pass. The author may **optionally** edit any note later; an edit appends the `(draft, final)` pair
to `paper/match_book/corrections.md` and re-renders/re-snapshots that version. The corrections log
is therefore both the few-shot memory the CI draft conditions on and the self-learning signal:
with no edits it enforces voice consistency, and each optional edit sharpens later drafts. No model
is retrained.

### Component 3b — Manual parallel track (human backstop + learning signal)
The CI draft never blocks; alongside it the author can run a **parallel manual track** at any time:
write their own interpretation for any match via `update_after_match.py M --reopen`. This (a)
replaces that match's note with the human version, (b) records the `(CI draft → human)` pair in
`corrections.md` as the learning signal, and (c) re-renders so the edit flows into the current
paper's narrative. Interpretation prose affects only the rolling-narrative highlights, never
`live_stats`, so no number moves — it is purely wording and judgment. The track is parallel (does
not gate CI), asynchronous, and **selective**: the author backs up only the matches worth their
judgment (upsets, failure-mode fires). Contemporaneity is preserved by timestamp — a note written
promptly is the contemporaneous record; a much-later rewrite is stored as a timestamped **amendment**
beside the original, never silently overwriting it.

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

### Component 5 — The entry point (`update_after_match.py M`)
The same driver runs in two contexts. **In CI** (default, hands-off) it reads the POST record,
builds the entry, calls Claude for the interpretation, regenerates the blocks + macros, appends the
revision note, builds the PDF with latexmk, uploads the snapshot artifact, runs the guard, commits
the living `.tex`, and logs:
> Paper revised through Match 1 — 1 documented · cumulative 1 pt · mean Brier 0.166 ·
> +1 ledger row · 0 failure modes fired · snapshot M001 (artifact).

**Locally** the author runs `python3 scripts/update_after_match.py M --reopen` to edit an
interpretation and re-render that version — the only time a human is in the loop.

### Component 6 — Integrity guards
- **Allowlist.** The update may *commit* only: `paper/match_book/**`, `paper/REVISIONS.md`,
  `paper/live_stats.tex`, the marker-delimited regions of `paper/Avraa_WC2026_paper.tex`, and the
  trajectory figure asset. (Version snapshots are uploaded as CI artifacts, never committed.) Any
  staged write outside the allowlist aborts the run (mirrors the v2 commit-step guard). Never the
  model, the locked picks, the frozen `.tex` outside markers, or `prereg-2026`.
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

### Component 8 — Versioning (104 versions, as CI artifacts)
Each successful update builds an immutable snapshot (`Avraa_WC2026_paper_M0XX.pdf` + the `.tex` it
was built from). To keep the public mirror small, snapshots are **not committed** — CI uploads each
as a retained **build artifact** (downloadable on demand), and only the small living `.tex`,
`live_stats.tex`, `REVISIONS.md`, and Match Book are committed. The accumulated artifact sequence is
the match-by-match revision reel; the author pulls any version locally when wanted.

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
3. It builds `match_book/M0XX.md` with PRE/RESULT/POST auto-filled, calls Claude for the
   voice-matched interpretation (with `corrections.md` as few-shot), and sets the failure-mode tag.
4. The note is published as-is (hands-off); an optional later author edit lands in `corrections.md`
   and re-renders that version.
5. `live_stats` is recomputed; `render_evolution.py` rewrites the marker blocks and `live_stats.tex`.
6. `REVISIONS.md` gets the response note; `match_book/index.json` marks M documented.
7. LaTeX builds; the PDF + `.tex` snapshot is uploaded as a CI artifact (not committed).
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
scripts/
  update_after_match.py         # the driver (runs in CI; locally for --reopen)
  render_evolution.py           # Match Book + trajectory → generated LaTeX blocks + macros
  draft_interpretation.py       # calls Anthropic API; deterministic templated fallback
.github/workflows/
  paper-revision.yml            # isolated CI: chains off live-update-v2; carries ANTHROPIC_API_KEY
# Version snapshots are NOT in the repo — built in CI, uploaded as retained build artifacts.
```

---

## 7. Error handling

- Missing POST record for M → abort with "match M not final / not recorded yet."
- Missing markers or `live_stats.tex` `\input` → abort before writing.
- LaTeX build failure → keep the previous latest version; report the build log; do not upload a
  snapshot or mark the match documented (the next run retries).
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

## 9. Resolved decisions

1. **Build:** `latexmk` — via a TeX Live GitHub Action in CI; local `latexmk` for `--reopen`.
2. **Full notes:** Match-Book-only; the paper prose highlights only the informative matches; no
   appendix.
3. **Tagged twins:** the abstract/conclusion gain a live twin for **cumulative points** and **mean
   Brier** only; every other pre-registered figure keeps its literal untouched.
4. **Snapshots:** kept out of the repo — generated in CI and retained as build artifacts
   (downloaded locally on demand), not committed to the public mirror.
5. **Interpretation:** drafted by Claude in CI via the Anthropic API (voice-matched, hands-off),
   with a deterministic templated fallback on API failure; an optional later human edit feeds the
   self-learning loop.

---

## 10. Automation: the GitHub Actions pipeline (`paper-revision.yml`)

A new workflow, **isolated** from `live-update-v2.yml` (which stays zero-secret / stdlib-only).

- **Trigger.** `workflow_run` after `live-update-v2` completes successfully (fires right after a
  POST lands), plus `workflow_dispatch`. It processes every match that has a POST record but is not
  yet in `match_book/index.json`, in ascending match order.
- **Steps.** checkout → TeX Live action (provides `latexmk`) → setup Python + `pip install
  anthropic` → for each undocumented finalized match, run `update_after_match.py M` → upload the
  PDF snapshot as a build artifact → allowlist-guarded commit of the living files.
- **Secret.** `ANTHROPIC_API_KEY` in repo Actions secrets. The repo is public, but Actions secrets
  are **not** exposed to fork-PR runs; this workflow triggers only via `workflow_run` /
  `workflow_dispatch` on the main repo, which have secret access. The key is never echoed; per-match
  cost is one short completion.
- **Isolation.** The v2 recorder is untouched and keeps its purity. This workflow alone carries the
  secret and the `anthropic` dependency.
- **Degradation.** API failure → deterministic templated note (paper still updates, flagged for a
  later voice pass). `latexmk` failure → keep the prior latest, surface the log, do not snapshot or
  mark the match documented (so the next run retries).
- **Idempotency.** The `index.json` documented-set makes re-runs and overlapping triggers safe.
