# Paper version history

The working file is `../Avraa_WC2026_paper.tex` (always the latest). Dated
snapshots (.tex + compiled .pdf) are kept here so older states are never lost.

| Version | Date | Paper size | Notes |
|---------|------|-----------|-------|
| v1-a4 | 2026-06-10 | A4 | Bilingual: English + Mongolian (Хураангуй) abstract. No first-page update-log stamp. |
| v2-letter | 2026-06-10 | US Letter | Mongolian abstract commented out; update-log stamp on page 1. Table 6 = 16 teams of interest (30 pp). |
| v3-letter | 2026-06-10 | US Letter | Table 6 expanded to all 48 teams (sorted by champion prob); fixed a stage-probability double-count in `condition.py`. 31 pp. |
| v4-letter | 2026-06-10 | US Letter | Added a predicted-standings table (W-D-L, GF, GA, points from the locked scorelines) after each of the 12 group-rationale paragraphs in Appendix~A. Table 6 sorted by champion then qualification. 33 pp. |
| v5-letter | 2026-06-10 | US Letter | Added per-pick expected-points figure (Fig. of all 104 games' EV). Dossier gained an "Exp." points column on every match table. 33 pp. |
| v6-letter | 2026-06-10 | US Letter | After each group rationale: a **Predicted results** table (all six fixtures, score + expected points) above the standings table. Fixed inline-table paragraph spacing. 35 pp. |
| v7-letter | 2026-06-10 | US Letter | Replaced the two per-group tables with a single **cross-table** (results matrix + W, L, G=goal-diff, P=points). Per-match Exp. pts now lives only in the pick-value figure. 33 pp. |
| v8-letter | 2026-06-10 | US Letter | Added **flags** to every group cross-table: vector flags (worldflags, alpha-2 codes) for 46 teams + custom TikZ flags for England (St George) and Scotland (St Andrew). Flags head the result columns and sit beside team names. 34 pp. |
| v9-letter | 2026-06-10 | US Letter | Flag sizing fix: one uniform width (4mm) for all flags in headers and rows (was 4.2 vs 3.6mm). Note: flags still vary slightly in height because national flag proportions differ (Switzerland square, Qatar wide) and worldflags boxes can't be height-scaled cleanly. 34 pp. |
| v10-letter | 2026-06-10 | US Letter | Expected points added back, under the score in every cross-table cell (small type). Fixed a pre-existing overflow in the ablation table (small->footnotesize). 34 pp. |
| v11-letter | 2026-06-10 | US Letter | **Flag size FIXED** — true uniform height via resizebox. Root cause: Curacao's worldflags box was 0x0 (broke every scaler); replaced with a custom TikZ flag, so all flags now scale to one height with correct proportions. 34 pp. |
| v12-letter | 2026-06-10 | US Letter | Flags forced to an identical fixed box (4x2.7mm) — fully consistent size (square/wide flags slightly stretched to fit). Expected points moved after the score in parentheses, e.g. "1-0 (0.95)" (Option 1). 34 pp. |
| v13-letter | 2026-06-09 | US Letter | Date fix: title now "Pre-kickoff version, \\today" (auto-tracks the actual date, no longer the premature June 10); update log says squad news monitored through 9 June, entry unchanged so far, locks at 11 June kickoff. 34 pp. |
| v14-letter | 2026-06-10 | US Letter | Added §4.9 "Learning as the tournament speaks" + Fig 11: the 2022 group-stage two-track replay (frozen vs learning). Real demonstration of the Prophet living-forecaster — learning raised both eventual finalists, lowered the unconvincing group winners; info concentrated at Japan's upsets. 35 pp. |
| v15-letter | 2026-06-10 | US Letter | Added Fig 11: a TikZ flowchart of the two-track living-forecast algorithm — step-by-step, with the information gathered/fed BEFORE each game (lineups, injury news, learned strengths) vs AFTER (result, shots/possession/cards -> lambda_obs). 36 pp. |
| v16-letter | 2026-06-10 | US Letter | Widened the Fig 11 algorithm flowchart to full page width with two-column bullets — now fits on one page AND lists far more detail (every pre-tournament input; before-feed: lineups, injuries, rotation, tactics, venue/weather/referee, rest/travel, learned strengths, market snapshot; after-feed: result, timeline, full shot/possession/passing/card stats, xG proxy-or-real -> lambda_obs; the surprise formula; all outputs). 36 pp. |
| v17-letter | 2026-06-10 | US Letter | Fig 11 flowchart: all full-width boxes set to one uniform width (144mm) so edges align. 36 pp. **Current working version.** |

Both share identical content (3/2/1 model, June 11 lock, peer-review revisions,
penalty-grit audit, etc.); v1→v2 differs only in formatting (paper size, the
update-log stamp, and the commented Mongolian abstract).

To make a new version: copy the working .tex to `versions/..._vN-<label>_<date>.tex`,
compile, and add a row above.

## Post-kickoff: per-match CI snapshots (`_Mnnn`)

A second lineage, separate from the drafting versions above: once the
tournament started, the paper-revision CI recompiles the paper after each
graded match (live scorecard macros + match-book entry) and uploads the PDF as
a workflow artifact. Fetched copies are kept here, one per match, named
`Avraa_WC2026_paper_Mnnn.pdf`. The repo's `paper/Avraa_WC2026_paper.pdf`
remains the locked pre-kickoff build.

| Snapshot | State | Scorecard | CI artifact |
|----------|-------|-----------|-------------|
| M001 | after M1, Mexico 2-0 South Africa | 1 pt / 1 graded / Brier 0.17 | `build-check`, 2026-06-12T00:28Z |
| M002 | after M2, South Korea 2-1 Czechia | 1 pt / 2 graded / Brier 0.39 | `paper-versions`, run 27418484887 (re-rendered 2026-06-12 as the first full conditional edition: divergence table + group state) |

M002 onward are *conditional editions*: alongside the scorecard and ledger they
carry the frozen-vs-conditional divergence table (champion + advance, with the
frozen column pinned to `data/frozen_stage_probs.json`, N=200k) and the
revealed standings of every group in play, conditioned through that match
(N=50k, seed 2026). M001 predates the divergence region.
