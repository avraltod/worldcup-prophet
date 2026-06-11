# RUNBOOK — Finalize KO third-place conditioning (~27 June 2026)

**Do this when:** the group stage has concluded (all 72 group matches played) and
FIFA has announced the Round-of-32 bracket — **before the first R32 match (28 June).**
**Time:** ~10–15 minutes. **Risk:** low (baseline-neutral; one hardcoded table).

**Why this exists:** `scripts/condition.py` already ships a *deterministic* third-place
slotter, but with a placeholder `REALIZED_THIRDS = {}`. Until it's filled with FIFA's
actual slotting, a recorded **third-placed-team R32 result** won't reliably move the
live champion-probability trajectory (the paper's central metric). Full background:
`2026-06-10-ko-conditioning-issue.md` (same folder).

---

## The one edit

In `scripts/condition.py`, set `REALIZED_THIRDS` to map each of the 8 third-place R32
match numbers to the **group letter** whose third-placed team FIFA put in that slot:

```python
REALIZED_THIRDS = {74: "A", 77: "C", 79: "F", 80: "K", 81: "B", 82: "G", 85: "E", 87: "D"}
#                  ^^ EXAMPLE ONLY — replace every value with FIFA's actual assignment.
```

The 8 T-slot match numbers are fixed: **74, 77, 79, 80, 81, 82, 85, 87**. Each value is
one of the 8 groups (A–L) whose third-placed team qualified.

---

## Steps

1. **Confirm groups are complete.** All 72 group results recorded (the live automation
   should have them in `data/results_log_v2.json` under `"group"`).

2. **Read FIFA's official R32 bracket.** For each of the 8 third-place matches
   (74,77,79,80,81,82,85,87), note which group's 3rd-placed team is assigned to it.

3. **Cross-check against the engine's own guess** (the deterministic fallback — *not*
   authoritative, just a sanity check):
   ```bash
   python3 -c "import sys,json; sys.path.insert(0,'scripts'); import condition as C; \
   g=json.load(open('data/results_log_v2.json'))['group']; \
   slots,am=C.realized_bracket({'group':g}); print({m:am[m] for m in sorted(am)})"
   ```
   It prints `{matchno: group}`. If it matches FIFA's bracket, good. **If it differs, use
   FIFA's** — the official third-place combination table is authoritative; the fallback is
   only a deterministic placeholder.

4. **Edit `REALIZED_THIRDS`** in `scripts/condition.py` to FIFA's assignment (8 entries).

5. **Run the acceptance test — both must pass:**
   ```bash
   python3 -m pytest tests/test_ko_conditioning.py -q
   ```

6. **Commit + push** `scripts/condition.py` to `main` (keep the KO docs local, as before —
   stash the code, branch from `origin/main`, commit there, push, rebase the local doc
   commits back on top; see how the earlier KO-fix commit `b855bf2` was pushed).

7. **Verify live:** when the first third-place R32 match is played and recorded, confirm
   the conditioned forecast responds — the loser's `R16` prob → ~0, the winner's → ~1.

---

## Then: un-park the KO automation (optional, same window)

The KO automation is fully built on branch **`ko-automation-parked`** (6 commits), blocked
only by this conditioning issue. To ship it:
- Rebase the branch onto current `main`.
- Apply the **same deterministic `assign()`** (and `REALIZED_THIRDS`) to its `ko_bracket.py`
  resolver so it matches `condition.py`.
- Re-run its tests + `tests/test_ko_conditioning.py`.
- Enable its workflow (cron), mirroring the live group-stage v2 workflow.

---

## Acceptance criteria
- `tests/test_ko_conditioning.py` passes with `REALIZED_THIRDS` filled.
- `REALIZED_THIRDS` matches FIFA's announced bracket (verified in step 3).
- A recorded third-place R32 winner moves its `R16` probability to ~1.0 (was ~0.31 with the bug).
- Baseline unchanged: Spain champion ~27%, podium order Spain > Argentina > France.
