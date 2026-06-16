# Paper editions

The paper is a living document: the pre-registered core is frozen, and a
*conditional edition* is issued after every graded match (104 in total by the
final). Each edition's title page self-describes its state ("Live edition —
after match N, FIXTURE SCORE (date)"); the ledger, scorecard, divergence table
(frozen vs conditional, frozen column pinned to `data/frozen_stage_probs.json`,
N=200k), and revealed group standings are conditioned through that match
(N=50k, seed 2026).

Editions M001+ are built by the `paper-revision` CI workflow and archived here,
one per match, named `WC2026_paper_Mnnn.pdf`. The working source is
`../../paper/WC2026_paper.tex`; the repo's `paper/WC2026_paper.pdf` remains the
locked pre-kickoff build (identical to M000). The per-edition fixture, result,
points, and Brier figures below are drawn from `data/edition_vintages.json`
(the same source as the paper's vintages table).

| Edition | Match | Fixture | Result | Pts | Cum pts | Mean Brier |
|---------|-------|---------|--------|-----|---------|------------|
| M000 | — | Locked pre-kickoff original (before match 1) | — | — | 0 | — |
| M001 | 1 | Mexico v South Africa | 2–0 | 1 | 1 | 0.166 |
| M002 | 2 | South Korea v Czechia | 2–1 | 0 | 1 | 0.389 |
| M003 | 3 | Canada v Bosnia and Herzegovina | 1–1 | 0 | 1 | 0.556 |
| M004 | 4 | United States v Paraguay | 4–1 | 1 | 2 | 0.521 |
| M005 | 5 | Haiti v Scotland | 0–1 | 2 | 4 | 0.456 |
| M006 | 6 | Australia v Turkey | 2–0 | 0 | 4 | 0.543 |
| M007 | 7 | Brazil v Morocco | 1–1 | 0 | 2 | 0.610 |
| M008 | 8 | Qatar v Switzerland | 1–1 | 0 | 4 | 0.680 |
| M009 | 9 | Ivory Coast v Ecuador | 1–0 | 0 | 4 | 0.694 |
| M010 | 10 | Germany v Curaçao | 7–1 | 1 | 5 | 0.606 |
| M011 | 11 | Netherlands v Japan | 2–2 | 0 | 5 | 0.646 |
| M012 | 12 | Sweden v Tunisia | 5–1 | 1 | 6 | 0.625 |
| M013 | 13 | Saudi Arabia v Uruguay | 1–1 | 0 | 6 | 0.653 |
| M014 | 14 | Spain v Cape Verde | 0–0 | 0 | 6 | 0.695 |
| M015 | 15 | Iran v New Zealand | 2–2 | 0 | 6 | 0.725 |
| M016 | 16 | Belgium v Egypt | 1–1 | 0 | 6 | 0.741 |

The latest archived edition is **M016** (after match 16, Belgium 1–1 Egypt,
15 June 2026). Subsequent editions are issued automatically once each result is
confirmed by the CI workflow. "Pts" is the per-match scorecard award; "Cum pts"
is the running total; "Mean Brier" is the cumulative mean Brier score through
that edition.
