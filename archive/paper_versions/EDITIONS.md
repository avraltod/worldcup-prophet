# Paper editions

The paper is a living document: the pre-registered core is frozen, and a
*conditional edition* is issued after every graded match (104 in total by the
final). Each edition's title page self-describes its state ("Live edition —
after match N, FIXTURE SCORE (date)"); the ledger, scorecard, divergence table
(frozen vs conditional, frozen column pinned to `data/frozen_stage_probs.json`,
N=200k), and revealed group standings are conditioned through that match
(N=50k, seed 2026).

Editions are built by the `paper-revision` CI workflow and archived here, one
per match, named `WC2026_paper_Gggg_Mmmm.pdf`, where **ggg is the issue order**
(the order the model actually saw the results and re-conditioned) and **mmm is
the schedule match number** (the fixed fixture slot). The working source is
`../../paper/WC2026_paper.tex`; the repo's `paper/WC2026_paper.pdf` remains the
locked pre-kickoff build (identical to G000/M000).

## Issue order ≠ match order

The model re-conditions as each result is confirmed, and results do **not**
arrive in schedule-number order. The true issue order is recovered from each
edition's own conditioning set: e.g. match 7 (Brazil v Morocco) was confirmed
**before** match 8 (Qatar) — edition M007 conditioned on {1,2,3,4,7} and M008
then added 8 — and both were issued before matches 5–6 (Haiti, Australia).
Likewise match 9 (Ivory Coast) landed after 10 and 11, and match 16 (Belgium)
was the very last. The table is ordered by issue order (Gggg); each edition
conditions only on the results available at that point, never on later matches.

| Issue | Match (file) | Fixture | Result | Pts | Brier |
|-------|--------------|---------|--------|-----|-------|
| — | M000 | Locked pre-kickoff original (before any game) | — | — | — |
| G001 | M001 | Mexico v South Africa | 2–0 | 1 | 0.166 |
| G002 | M002 | South Korea v Czechia | 2–1 | 0 | 0.613 |
| G003 | M003 | Canada v Bosnia and Herzegovina | 1–1 | 0 | 0.888 |
| G004 | M004 | United States v Paraguay | 4–1 | 1 | 0.418 |
| G005 | M007 | Brazil v Morocco | 1–1 | 0 | 0.965 |
| G006 | M008 | Qatar v Switzerland | 1–1 | 0 | 1.220 |
| G007 | M005 | Haiti v Scotland | 0–1 | 2 | 0.194 |
| G008 | M006 | Australia v Turkey | 2–0 | 0 | 0.976 |
| G009 | M010 | Germany v Curaçao | 7–1 | 1 | 0.010 |
| G010 | M011 | Netherlands v Japan | 2–2 | 0 | 0.844 |
| G011 | M009 | Ivory Coast v Ecuador | 1–0 | 0 | 0.807 |
| G012 | M012 | Sweden v Tunisia | 5–1 | 1 | 0.399 |
| G013 | M014 | Spain v Cape Verde | 0–0 | 0 | 1.538 |
| G014 | M013 | Saudi Arabia v Uruguay | 1–1 | 0 | 0.992 |
| G015 | M015 | Iran v New Zealand | 2–2 | 0 | 0.847 |
| G016 | M016 | Belgium v Egypt | 1–1 | 0 | 0.972 |

The latest edition is **G016 (M016, Belgium 1–1 Egypt)**. "Pts" is the
scorecard award for that single match (running total: 6 points through G016);
"Brier" is the Brier score for that match alone (from the live ledger). Each
edition's *cumulative* mean Brier and points are reported on its own title page
and scorecard; because conditioning sets are not strictly nested in issue order
(a later-issued edition can condition on fewer high-numbered matches), those
cumulative figures are best read per edition rather than down this column.
Subsequent editions are issued automatically once each result is confirmed by
the CI workflow.
