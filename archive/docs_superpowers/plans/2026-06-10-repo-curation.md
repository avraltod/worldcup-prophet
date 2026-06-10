# Repo Curation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Curate the public `worldcup-prophet` repo so a visitor sees only the pre-registration essentials, moving all supporting/draft material into `/archive/` without rewriting history, and anchor the locked forecast with a `prereg-2026` git tag.

**Architecture:** Additive-only curation. One git tag on the existing locked commit `3ebbb8f`, then a single curation commit on `main` that `git mv`s clutter into `archive/`, adds 3 real untracked files, and rewrites `README.md`. No force-push, no `git filter-repo`.

**Tech Stack:** git, plain shell. No build step. Source spec: `docs/superpowers/specs/2026-06-10-repo-curation-design.md`.

**Verification model:** This is a repository-curation plan, not a code change. Each task's "verify" step is a `git`/`ls` assertion (TDD-style: assert the expected state before and after). Per the spec there is exactly **one** curation commit (Task 7); Tasks 2–6 only modify the working tree + index and verify with `git status`.

**Self-archiving note:** This plan file and the spec both live under `docs/superpowers/`, which Task 6 moves into `archive/`. That is intentional — the planning artifacts get archived alongside the rest of the internal docs. When run, the plan moves itself; that is expected, not a bug.

**Preconditions:**
- Working tree is clean except the 4 known untracked files. Confirm with `git status --porcelain` before starting (Task 0).
- Current branch is `main`, up to date with `origin/main` (the spec commit `94cc091` may be the tip; that is fine — the tag still points at `3ebbb8f`).
- All work completes before kickoff 2026-06-11.

---

### Task 0: Confirm clean starting state

**Files:** none (read-only checks)

- [ ] **Step 1: Confirm branch and cleanliness**

Run:
```bash
cd /Users/avraa/iDrive/GitHub/MGL/FIFA
git branch --show-current
git status --porcelain
```
Expected: branch is `main`. The only porcelain lines are the 4 untracked files:
```
?? data/group_predictions_v2_3to1backup.json
?? paper/figs/fig_bracket.pdf
?? paper/figs/fig_bracket.tex
?? scripts/make_bracket_tikz.py
```
If there are other modified/staged files, STOP and resolve before continuing.

- [ ] **Step 2: Confirm the locked commit exists**

Run:
```bash
git cat-file -t 3ebbb8f
git log --oneline -1 3ebbb8f
```
Expected: type `commit`, and the subject line is
`Pre-registered FIFA 2026 forecast: predictions locked before kickoff`.

---

### Task 1: Create and push the lock tag

**Files:** none (git ref only)

- [ ] **Step 1: Verify the tag does not already exist**

Run: `git tag -l prereg-2026`
Expected: empty output (no such tag yet).

- [ ] **Step 2: Create the annotated tag on the locked commit**

Run:
```bash
git tag -a prereg-2026 3ebbb8f -m "Locked WC2026 forecast, before kickoff"
```

- [ ] **Step 3: Verify the tag points at 3ebbb8f**

Run: `git rev-list -n 1 prereg-2026`
Expected: a full SHA beginning `3ebbb8f`.

- [ ] **Step 4: Push the tag**

Run: `git push origin prereg-2026`
Expected: `* [new tag]  prereg-2026 -> prereg-2026`.

- [ ] **Step 5: Verify the tag is on the remote**

Run: `git ls-remote --tags origin prereg-2026`
Expected: one line containing `refs/tags/prereg-2026`.

---

### Task 2: Create archive/ and move duplicate document formats + scratch files

**Files:**
- Create: `archive/` (directory, via first `git mv`)
- Move: `Avraa_Prediction_WC2026.docx`, `Avraa_Prediction_WC2026.html`, `HOW_THE_MODEL_WORKS.docx`, `HOW_THE_MODEL_WORKS.html`, `COMMIT_INSTRUCTIONS.txt`, `England_World_Cup_scenario.png` → `archive/`

- [ ] **Step 1: Create the archive directory**

Run:
```bash
cd /Users/avraa/iDrive/GitHub/MGL/FIFA
mkdir -p archive
```

- [ ] **Step 2: Move duplicate formats and scratch files (history preserved)**

Run:
```bash
git mv Avraa_Prediction_WC2026.docx archive/
git mv Avraa_Prediction_WC2026.html archive/
git mv HOW_THE_MODEL_WORKS.docx archive/
git mv HOW_THE_MODEL_WORKS.html archive/
git mv COMMIT_INSTRUCTIONS.txt archive/
git mv England_World_Cup_scenario.png archive/
```

- [ ] **Step 3: Verify the canonical docs remain at root**

Run: `ls Avraa_Prediction_WC2026.md HOW_THE_MODEL_WORKS.md HOW_THE_MODEL_WORKS.pdf`
Expected: all three listed (the `.md` picks and `.md`+`.pdf` method survive at root).

- [ ] **Step 4: Verify the moves are staged as renames**

Run: `git status --porcelain | grep '^R' | grep archive/`
Expected: 6 lines, each `R  <old> -> archive/<file>` (rename detection confirms history is preserved).

---

### Task 3: Archive paper drafts and paper-process notes

**Files:**
- Move: `paper/versions/` (44 files) → `archive/paper_versions/`
- Move: `paper/REVISION_ROADMAP.md`, `paper/revision_numbers.md` → `archive/`

- [ ] **Step 1: Confirm the canonical paper stays at paper/ root**

Run: `ls paper/Avraa_WC2026_paper.pdf paper/Avraa_WC2026_paper.tex paper/avtables.sty`
Expected: all three listed — these stay; only drafts move.

- [ ] **Step 2: Move the 44 draft versions**

Run:
```bash
git mv paper/versions archive/paper_versions
```
(Moving the directory in one operation moves all 44 tracked files.)

- [ ] **Step 3: Move the paper-process notes**

Run:
```bash
git mv paper/REVISION_ROADMAP.md archive/
git mv paper/revision_numbers.md archive/
```

- [ ] **Step 4: Verify**

Run:
```bash
test ! -d paper/versions && echo "versions moved OK"
ls archive/paper_versions/ | wc -l
git ls-files paper/Avraa_WC2026_paper.tex
```
Expected: `versions moved OK`; count `44`; the canonical `.tex` still tracked at `paper/`.

---

### Task 4: Archive experiment/ and internal dev docs

**Files:**
- Move: `experiment/` (6 files) → `archive/experiment/`
- Move: `docs/superpowers/` (plans + specs, incl. this plan and the spec) → `archive/docs_superpowers/`

- [ ] **Step 1: Move experiment/**

Run:
```bash
cd /Users/avraa/iDrive/GitHub/MGL/FIFA
git mv experiment archive/experiment
```

- [ ] **Step 2: Move docs/superpowers/ (self-archiving — see header note)**

Run:
```bash
git mv docs/superpowers archive/docs_superpowers
```
Note: this moves THIS plan file and the design spec into `archive/docs_superpowers/`.
That is intentional per the spec. After this step the plan lives at
`archive/docs_superpowers/plans/2026-06-10-repo-curation.md`; continue from memory /
the open editor copy — the remaining tasks need no further reads of the plan file.

- [ ] **Step 3: Verify**

Run:
```bash
test ! -d experiment && echo "experiment moved OK"
test ! -d docs/superpowers && echo "docs/superpowers moved OK"
ls archive/docs_superpowers/specs/2026-06-10-repo-curation-design.md
```
Expected: both "moved OK" lines; the spec is now under `archive/docs_superpowers/specs/`.

---

### Task 5: Place the 4 untracked files

**Files:**
- Move into repo: `scripts/make_bracket_tikz.py`, `paper/figs/fig_bracket.pdf`, `paper/figs/fig_bracket.tex` (keep — real code/figures)
- Archive: `data/group_predictions_v2_3to1backup.json` → `archive/`

- [ ] **Step 1: Stage the 3 real files in their proper homes**

Run:
```bash
git add scripts/make_bracket_tikz.py paper/figs/fig_bracket.pdf paper/figs/fig_bracket.tex
```

- [ ] **Step 2: Move the backup json into archive/**

Run:
```bash
git mv data/group_predictions_v2_3to1backup.json archive/group_predictions_v2_3to1backup.json 2>/dev/null \
  || { mv data/group_predictions_v2_3to1backup.json archive/ && git add archive/group_predictions_v2_3to1backup.json; }
```
(The fallback handles the untracked case: `git mv` only works on tracked files, so for an
untracked file we plain-`mv` then `git add`.)

- [ ] **Step 3: Verify no stray untracked files remain**

Run: `git status --porcelain | grep '^??'`
Expected: empty output — every previously-untracked file is now either staged in place or archived.

---

### Task 6: Rewrite README.md

**Files:**
- Modify (full rewrite): `README.md`

- [ ] **Step 1: Write the new README**

Replace the entire contents of `README.md` with:

```markdown
# worldcup-prophet — Pre-Registered World Cup 2026 Forecast

**A timestamped, public, pre-registered forecast of the 2026 FIFA World Cup.**
Every prediction in this repository was committed publicly on **2026-06-10**, before the
first match (**2026-06-11**). The forecast has not been altered since the lock.

## The lock (proof)

- Locked commit: [`3ebbb8f`](../../commit/3ebbb8f) — *"Pre-registered FIFA 2026 forecast:
  predictions locked before kickoff."*
- Immutable tag: [`prereg-2026`](../../releases/tag/prereg-2026) points at that commit.
  Check it out to see the exact locked state and its date:
  ```bash
  git checkout prereg-2026
  ```

## What's predicted

- **The picks:** [`Avraa_Prediction_WC2026.md`](Avraa_Prediction_WC2026.md) — full match-by-match
  and tournament predictions.
- **Champion call:** Spain.

## How it works

- **Method writeup:** [`HOW_THE_MODEL_WORKS.md`](HOW_THE_MODEL_WORKS.md)
- **Full paper:** [`paper/Avraa_WC2026_paper.pdf`](paper/Avraa_WC2026_paper.pdf)

The forecast starts from public bookmaker odds (converted to fair probabilities), applies a
Poisson goal model, and optimizes picks under the pool's 3/2/1 scoring rule.

## Verify it yourself

- Input + prediction data: [`data/`](data/)
- Model code: [`scripts/`](scripts/)
- Tests: `pytest`

## Repository map

| Path | Contents |
|------|----------|
| `Avraa_Prediction_WC2026.md` | The locked predictions |
| `HOW_THE_MODEL_WORKS.md` | Plain-language method |
| `paper/` | The formal paper (`Avraa_WC2026_paper.pdf` + LaTeX source + figures) |
| `data/` | Locked input odds and generated predictions |
| `scripts/` | Model, simulation, and analysis code |
| `tests/` | Test suite |
| `archive/` | Supporting material — drafts, alternate formats, dev notes. **Not part of the locked forecast.** |

## Results tracking

*Live results will be appended here during the tournament (2026-06-11 – 2026-07-19), compared
against the locked predictions above.*
```

- [ ] **Step 2: Verify the README references resolve**

Run:
```bash
cd /Users/avraa/iDrive/GitHub/MGL/FIFA
for f in Avraa_Prediction_WC2026.md HOW_THE_MODEL_WORKS.md paper/Avraa_WC2026_paper.pdf data scripts tests; do
  test -e "$f" && echo "OK $f" || echo "MISSING $f"; done
```
Expected: every line begins `OK` — all paths the README links to exist post-curation.

- [ ] **Step 3: Stage the README**

Run: `git add README.md`

---

### Task 7: Single curation commit and push

**Files:** none new — commits everything staged in Tasks 2–6.

- [ ] **Step 1: Review the full staged change set**

Run:
```bash
git status
git diff --cached --stat | tail -5
```
Expected: renames into `archive/` (≈58 files: 6 + 46 + 6 docs + others), 3 added real files,
1 archived json, `README.md` modified. No deletions of locked forecast files
(`Avraa_Prediction_WC2026.md`, `HOW_THE_MODEL_WORKS.md/.pdf`, `paper/Avraa_WC2026_paper.*`,
`data/`, `scripts/` all still present at their canonical paths).

- [ ] **Step 2: Sanity-check the essentials survived at HEAD-to-be**

Run:
```bash
for f in README.md Avraa_Prediction_WC2026.md HOW_THE_MODEL_WORKS.md HOW_THE_MODEL_WORKS.pdf \
         paper/Avraa_WC2026_paper.pdf paper/avtables.sty; do
  git ls-files --error-unmatch "$f" >/dev/null 2>&1 && echo "tracked $f" || echo "LOST $f"; done
```
Expected: every line begins `tracked`.

- [ ] **Step 3: Commit**

Run:
```bash
git commit -m "Curate repo: archive supporting material, add pre-registration README"
```

- [ ] **Step 4: Push main**

Run: `git push origin main`
Expected: push succeeds; `main` advances by one commit.

- [ ] **Step 5: Final verification**

Run:
```bash
git ls-remote --tags origin prereg-2026   # tag present on remote
git log --oneline -3                        # curation commit on top, 3ebbb8f still in history
ls                                          # root shows essentials + archive/, no clutter
```
Expected: tag present; top commit is the curation commit, `3ebbb8f` still reachable in history;
root listing shows the essential files plus `archive/`, with duplicate formats /
`COMMIT_INSTRUCTIONS.txt` / `paper/versions` no longer at their old locations.

---

## Self-review (completed by plan author)

- **Spec coverage:** tag on `3ebbb8f` (Task 1) ✓; keep/archive split (Tasks 2–4) ✓;
  data/ & scripts/ kept public (never moved) ✓; experiment/ archived (Task 4) ✓;
  4 untracked files handled (Task 5) ✓; README rewrite per outline incl. results-tracking
  placeholder (Task 6) ✓; single curation commit + push + tag push (Tasks 1, 7) ✓;
  no history rewrite / no force-push (none present) ✓; home-path leak left as-is in archive
  (default — no scrub step, consistent with spec) ✓.
- **Placeholder scan:** no TBD/TODO; README "Results tracking" is an intentional placeholder
  owned by Project B, explicitly noted in the spec's out-of-scope section.
- **Path consistency:** archive subpaths used consistently —
  `archive/paper_versions/`, `archive/experiment/`, `archive/docs_superpowers/`,
  and flat `archive/` for individual files. Canonical paths referenced by the README
  (`Avraa_Prediction_WC2026.md`, `HOW_THE_MODEL_WORKS.md`, `paper/Avraa_WC2026_paper.pdf`,
  `data/`, `scripts/`, `tests/`) are never moved by any task.
