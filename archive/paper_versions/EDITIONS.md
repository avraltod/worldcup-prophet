# Paper editions

The paper is a living document: the pre-registered core is frozen, and a
*conditional edition* is issued after every graded match (104 in total by the
final). Each edition's title page self-describes its state ("Live edition —
after match N, FIXTURE SCORE (date)"); the ledger, scorecard, divergence table
(frozen vs conditional, frozen column pinned to `data/frozen_stage_probs.json`,
N=200k), and revealed group standings are conditioned through that match
(N=50k, seed 2026).

| Edition | State | Scorecard |
|---------|-------|-----------|
| M000 | Locked pre-kickoff original (June 11, 2026, before match 1) | — |
| M001 | after M1, Mexico 2-0 South Africa (June 11) | 1 pt / 1 graded / Brier 0.166 |
| M002 | after M2, South Korea 2-1 Czechia (June 12) | 1 pt / 2 graded / Brier 0.389 |
| M003 | after M3, Canada 1-1 Bosnia and Herzegovina (June 12) | 1 pt / 3 graded / Brier 0.556 |
| M004 | after M4, United States 4-1 Paraguay (June 13) | 2 pts / 4 graded / Brier 0.521 |
| M007 | after M7, Brazil 1-1 Morocco (June 13) | 2 pts / 5 graded / Brier 0.610 |
| M008 | after M8, Qatar 1-1 Switzerland (June 13) | 2 pts / 6 graded / Brier 0.712 |

M005 and M006 (Haiti v Scotland and Australia v Turkey, June 14) are pending;
editions will be issued automatically once results are confirmed by the CI workflow.

Editions M001+ are built by the `paper-revision` CI workflow and archived here,
one per match, named `WC2026_paper_Mnnn.pdf`. The working source is
`../../paper/WC2026_paper.tex`; the repo's `paper/WC2026_paper.pdf` remains
the locked pre-kickoff build (identical to M000).
