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
| M001 | after M1, Mexico 2-0 South Africa | 1 pt / 1 graded / Brier 0.17 |
| M002 | after M2, South Korea 2-1 Czechia | 1 pt / 2 graded / Brier 0.39 |

Editions M001+ are built by the `paper-revision` CI workflow and fetched here,
one per match, named `WC2026_paper_Mnnn.pdf`. The working source is
`../../paper/WC2026_paper.tex`; the repo's `paper/WC2026_paper.pdf` remains
the locked pre-kickoff build (identical to M000).
