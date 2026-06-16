# Paper editions

The paper is a living document: the pre-registered core is frozen, and a
*conditional edition* is issued after every graded match (104 in total by the
final). Each edition's title page self-describes its state ("Live edition —
after match N, FIXTURE SCORE (date)"); the ledger, scorecard, divergence table
(frozen vs conditional, frozen column pinned to `data/frozen_stage_probs.json`,
N=200k), and revealed group standings are conditioned through that match
(N=50k, seed 2026).

Editions are built by the `paper-revision` CI workflow and archived here, one
per match, named `WC2026_paper_Mnnn.pdf` where **nnn is the schedule match
number** (the fixed fixture slot). The working source is
`../../paper/WC2026_paper.tex`; the repo's `paper/WC2026_paper.pdf` remains the
locked pre-kickoff build (identical to M000).

## Update order matters

The model is recursive: it re-conditions after each result *as that result is
confirmed*. Results do not arrive in schedule-number order, so the **update
sequence (G###) differs from the match number (M###)**. For example, match 8
(Qatar v Switzerland) was confirmed before match 5 (Haiti v Scotland), so
edition M008 was issued before M005. The table below is therefore ordered by
the actual update sequence — the order the model saw the games — not by match
number. The grading order is recorded in `data/records_index_v2.json` and
matches the CI commit timestamps of the archived PDFs.

| Update | Match (file) | Fixture | Result | Pts | Cum pts | Brier |
|--------|--------------|---------|--------|-----|---------|-------|
| — | M000 | Locked pre-kickoff original (before any game) | — | — | 0 | — |
| G001 | M001 | Mexico v South Africa | 2–0 | 1 | 1 | 0.166 |
| G002 | M002 | South Korea v Czechia | 2–1 | 0 | 1 | 0.613 |
| G003 | M003 | Canada v Bosnia and Herzegovina | 1–1 | 0 | 1 | 0.888 |
| G004 | M004 | United States v Paraguay | 4–1 | 1 | 2 | 0.418 |
| G005 | M008 | Qatar v Switzerland | 1–1 | 0 | 2 | 1.220 |
| G006 | M007 | Brazil v Morocco | 1–1 | 0 | 2 | 0.965 |
| G007 | M005 | Haiti v Scotland | 0–1 | 2 | 4 | 0.194 |
| G008 | M006 | Australia v Turkey | 2–0 | 0 | 4 | 0.976 |
| G009 | M010 | Germany v Curaçao | 7–1 | 1 | 5 | 0.010 |
| G010 | M011 | Netherlands v Japan | 2–2 | 0 | 5 | 0.844 |
| G011 | M009 | Ivory Coast v Ecuador | 1–0 | 0 | 5 | 0.807 |
| G012 | M012 | Sweden v Tunisia | 5–1 | 1 | 6 | 0.399 |
| G013 | M014 | Spain v Cape Verde | 0–0 | 0 | 6 | 1.538 |
| G014 | M016 | Belgium v Egypt | 1–1 | 0 | 6 | 0.972 |
| G015 | M013 | Saudi Arabia v Uruguay | 1–1 | 0 | 6 | 0.992 |
| G016 | M015 | Iran v New Zealand | 2–2 | 0 | 6 | 0.847 |

The latest update is **G016 (edition M015, Iran 2–2 New Zealand)**; the
highest-numbered match graded so far is match 16 (Belgium 1–1 Egypt).
"Pts" is the per-match scorecard award and "Cum pts" the running total in
update order; "Brier" is the Brier score for that single match (from the live
ledger). Subsequent editions are issued automatically once each result is
confirmed by the CI workflow.
