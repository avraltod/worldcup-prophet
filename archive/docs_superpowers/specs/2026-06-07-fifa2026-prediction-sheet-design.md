# FIFA 2026 Prediction Sheet — Design

**Date:** 2026-06-07
**Goal:** Fill `FIFA_WORLDCUP_2026_ScoreChart_R3.2.xlsx` (excel4soccer template, real 48-team draw) with predictions that maximize expected points in a friends' betting pool scored per match with **exact score > correct result**.

## Decisions (confirmed with user)

- Scoring: points per match; exact scoreline worth more than correct outcome.
- Strategy: **max expected points** — for every match pick the modal exact score whose outcome matches the most likely result. No contrarian picks.
- Work on a copy `FIFA_WORLDCUP_2026_ScoreChart_Avraa.xlsx`; original untouched.
- User Name = `Avraa`; Time Zone = closest UTC+8 option to Ulaanbaatar (sheet dropdown).

## 1. Research (live data)

- Web research, parallel: (a) current bookmaker odds for all 72 group matches + outright winner odds; (b) tournament-eve news (injuries, suspensions, June friendlies) for bracket-relevant teams.
- Bookmaker consensus odds are the probability source; news only adjusts edge cases.

## 2. Prediction model

- Implied probabilities from odds, margin-stripped.
- Poisson goal model: pick expected-goals pair consistent with W/D/L probabilities and World Cup scoring rates; output the modal exact score conditional on the most likely outcome.
  - Heavy favorite → 2-0 / 3-0; moderate favorite → 2-1 / 1-0; true coin-flip with draw modal → 1-1.
- Knockouts: same model. If modal score is a draw, keep FT draw and set the winner via the OT/PK score column.

## 3. Filling the workbook

- Drive the real Microsoft Excel via AppleScript (osascript) so all formulas, conditional formatting, and the 3rd-place allocation logic stay intact and recalculate live.
- Input cells only (never overwrite formulas):
  - Header: `U1` (time zone), `X1` (user name), `Z1` (date)
  - Group stage: `O4:O75`, `Q4:Q75` (72 matches, sheet `FIFA2026`)
  - R32: `BM`/`BN` pairs; R16: `BX`/`BY`; QF: `CI`/`CJ`; SF: `CT`/`CU`; Final + 3rd place: `DE`/`DF`
- Sequence: enter group scores → Excel recalcs → read computed R32 team names (`BK`/`BL` columns) → enter R32 scores → read R16 → … → Final. Save.

## 4. Verification

- Re-read filled sheet: all 72 group + 32 knockout score-cell pairs populated; champion cell `CY6` equals intended winner; no error values (`#REF!`, `#VALUE!`, `#N/A`) in the bracket; file opens cleanly.
- Deliverable to user: the filled copy + a short bracket summary (group winners, R16/QF/SF picks, final, champion).

## Out of scope

- No macro/VBA changes, no formatting changes, no edits to the `3rd Place Group` / `Tie Break` / `Ranking` sheets.
