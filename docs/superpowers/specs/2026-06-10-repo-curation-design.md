# Repo Curation Design — worldcup-prophet

**Date:** 2026-06-10
**Author:** Avralt-Od Purevjav (Avraa)
**Status:** Approved, pending execution
**Scope:** Project A of two. Project B (live auto-update automation) is brainstormed separately after this.

## Purpose

The public GitHub repo `worldcup-prophet` (https://github.com/avraltod/worldcup-prophet)
exists as a **pre-registration proof**: a timestamped public record that the World Cup 2026
forecast was locked before the first match (kickoff 2026-06-11), and not altered afterward.

A single commit `3ebbb8f` ("Pre-registered FIFA 2026 forecast: predictions locked before
kickoff") already swept all 262 files into the public repo. That commit's pre-kickoff
timestamp is the asset. This design curates the repo so a visitor lands on the essential
pre-registration artifacts instead of 262 mixed files — **without** weakening the lock.

## Constraints / decisions

- **Additive curation only. No history rewrite.** `git mv` preserves each file's history.
  No force-push, no `git filter-repo`. Rewriting history would undermine the "locked before
  kickoff, untouched" guarantee.
- **Nothing genuinely sensitive is public.** A read-only scan found no secrets, API keys,
  `.env`/credential files, or private keys. Only minor flags: local home paths
  (`/Users/avraa/...`) in two soon-to-be-archived files, and transcribed public bookmaker
  odds values (bet365/Betfair/FanDuel) used as provenance labels — low risk, and they
  support the pre-registration provenance story.
- **All curation happens before kickoff** (2026-06-11), so the reorganization itself also
  predates the tournament.
- The `.xlsx` ScoreCharts are gitignored and stay private — unchanged.

## Target structure

### Root / prominent — the pre-registration essentials (stay public, stay at top)

| Item | Why essential |
|---|---|
| `README.md` (rewritten) | Frames the repo as a locked pre-registration; links everything |
| `Avraa_Prediction_WC2026.md` | The locked picks — the core artifact |
| `HOW_THE_MODEL_WORKS.md` + `.pdf` | The method, so the forecast is credible/verifiable |
| `paper/Avraa_WC2026_paper.pdf` + `.tex` + `paper/avtables.sty` | The canonical paper |
| `data/` | Locked input + prediction data (verifiability) — **kept public** |
| `scripts/` | Model code that generated the forecast (reproducibility) — **kept public** |
| `tests/`, `pytest.ini` | Demonstrates the code is tested — bolsters credibility |
| `paper/figs/` | Figures the paper references |

### Move into `/archive/` (stays in repo + full history, out of the front view)

| Item | What it is |
|---|---|
| `paper/versions/` (44 files, v1–v21 × pdf+tex) | Every draft of the paper; canonical stays at `paper/` |
| `Avraa_Prediction_WC2026.docx` + `.html` | Duplicate formats of the picks (keep `.md`) |
| `HOW_THE_MODEL_WORKS.docx` + `.html` | Duplicate formats (keep `.md` + `.pdf`) |
| `COMMIT_INSTRUCTIONS.txt` | Internal scratch note; also leaks home path |
| `experiment/` (6) | Pilot / stress-test / peer-review process docs |
| `docs/superpowers/` (6) | Internal dev plans & specs (one leaks home path) |
| `paper/REVISION_ROADMAP.md`, `paper/revision_numbers.md` | Paper-editing process notes |
| `England_World_Cup_scenario.png` | Illustrative one-off |

Note: this spec lives under `docs/superpowers/specs/`, which is itself being archived.
That is intentional — the spec records the curation; it does not need to sit at the front.

## README content (rewritten front door)

1. **One-line claim** — pre-registered WC2026 forecast; all predictions committed to this
   public repo on 2026-06-10, before the first match (2026-06-11); forecast unaltered since.
2. **The lock** — link to commit `3ebbb8f` and the `prereg-2026` tag as the immutable anchor.
3. **What's predicted** — link to `Avraa_Prediction_WC2026.md`; champion call (Spain).
4. **How it works** — link to `HOW_THE_MODEL_WORKS.md` + the paper PDF.
5. **Verify it yourself** — data in `data/`, code in `scripts/`, run `pytest`.
6. **Repo map** — `data/`, `scripts/`, `paper/`, `tests/`, `archive/` (archive = supporting
   material, not part of the locked forecast).
7. **Results tracking** — placeholder section: "Live results will be appended here during
   the tournament." (Filled by Project B.)

## The lock tag

A branch tip can move; a tag on a commit is a stable pointer. Tag the **original** locked
commit, not the curated one — the lock should be the raw moment; curation is openly a later
tidy-up that sits on top.

```
git tag -a prereg-2026 3ebbb8f -m "Locked WC2026 forecast, before kickoff"
git push origin prereg-2026
```

## Loose ends

- **Home-path leak:** `COMMIT_INSTRUCTIONS.txt` and one plan doc contain `/Users/avraa/...`.
  Both move to `/archive/`. Default: leave the strings as-is (no history rewrite; only the
  mac username is exposed). Optional cosmetic scrub to `<repo-root>` in the curation commit.
- **4 untracked files** added in the curation commit:
  - `data/group_predictions_v2_3to1backup.json` → `/archive/` (it's a backup)
  - `paper/figs/fig_bracket.pdf` / `.tex` → keep in `paper/figs/` (real figures)
  - `scripts/make_bracket_tikz.py` → keep in `scripts/` (real code)

## Execution plan

1. Create + push tag `prereg-2026` on `3ebbb8f`.
2. `mkdir archive/`; `git mv` all archive items into it (history preserved).
3. Add the 3 real untracked files to their proper homes; archive the backup json.
4. Rewrite `README.md` per the outline above.
5. Single commit on `main`:
   `Curate repo: archive supporting material, add pre-registration README`
6. Push `main` + tag. All before 2026-06-11 kickoff.

## Explicitly NOT doing

No force-push. No `git filter-repo`. No deletion of locked forecast files. No touching
`3ebbb8f`. No unrelated refactoring of `scripts/` or `data/`.

## Out of scope (→ Project B)

Live results tracking during the tournament (the README "Results tracking" placeholder),
and whether to drive it with `/loop`, a dedicated program, or a scheduled cloud agent.
