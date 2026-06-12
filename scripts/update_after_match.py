"""Driver: turn a finalized match into a paper revision. In CI it runs hands-off;
locally `--reopen M` lets the author replace an interpretation (the only human
step). Writes only the living layer; a frozen-hash check guards the rest."""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import condition as cond
import match_book as mb
import live_stats as ls
import render_evolution as rev
import draft_interpretation as di
from ev321 import best_pick
from realism_backtest import score_321

DATA = ROOT / "data"
PAPER = ROOT / "paper"
TRAJ_PATH = DATA / "trajectory_v2.json"
EXP_PATH = DATA / "match_expectations.json"
INDEX = PAPER / "match_book" / "index.json"
CORRECTIONS = PAPER / "match_book" / "corrections.md"
REVISIONS = PAPER / "REVISIONS.md"
PAPER_TEX = PAPER / "Avraa_WC2026_paper.tex"
LIVE_STATS_TEX = PAPER / "live_stats.tex"
FROZEN_PATH = DATA / "frozen_stage_probs.json"
COND_N = 50000   # sims for the per-snapshot conditional forecast


def _load(p, default):
    return json.loads(Path(p).read_text()) if Path(p).exists() else default


def pending_matches(trajectory, index_path):
    posts = {r["match"] for r in trajectory if r["phase"] == "post"}
    done = set(mb.documented_matches(index_path))
    return sorted(posts - done)


def re_ev_delta_for(exp, result, realistic_points):
    """Running realistic-vs-EV pool-point delta for one match: realistic minus EV."""
    ev = best_pick(exp["lh"], exp["la"])
    ev_pts = score_321(list(ev), result[0], result[1])
    return realistic_points - ev_pts


def detect_failure_mode(entry, exp):
    """Coarse, documented first-pass; the human refines via --reopen.
    Flags systematic_rating_error when the model's modal outcome lost and it had
    assigned the realized outcome under 25%."""
    ph, pd, pa = entry["pre"]["probs_HDA"]
    modal = max(range(3), key=lambda i: (ph, pd, pa)[i])    # 0=H,1=D,2=A
    r = entry["result"]
    real = 0 if r[0] > r[1] else (1 if r[0] == r[1] else 2)
    if real != modal and (ph, pd, pa)[real] < 0.25:
        return "systematic_rating_error"
    return None


def build_full_entry(match, trajectory, expectations, forecast_commit,
                     documented_at, use_api):
    e = mb.build_entry(match, trajectory, expectations, forecast_commit, documented_at)
    exp = next(x for x in expectations if x["match"] == match)
    e["failure_mode"] = detect_failure_mode(e, exp)
    corrections = CORRECTIONS.read_text() if CORRECTIONS.exists() else ""
    text, source = di.draft(e, corrections, use_api)
    e["interpretation"], e["interpretation_source"] = text, source
    return e


def _entries_for_stats(index_path):
    """Load every documented entry back from disk for the aggregate pass."""
    out = []
    for m in mb.documented_matches(index_path):
        f = PAPER / "match_book" / f"M{m:03d}.md"
        out.append(mb.parse_markdown(f.read_text()))
    return out


def _latexmk():
    subprocess.run(["latexmk", "-xelatex", "-interaction=nonstopmode",
                    "Avraa_WC2026_paper.tex"], cwd=PAPER, check=True)


def results_through(trajectory, match):
    """Conditioning dict from POST records with match number <= match.
    Group matches carry [hg, ag]; knockout records are included only once they
    carry a winner name (the KO automation is not yet live)."""
    out = {"group": {}, "ko": {}}
    for r in trajectory:
        if r["phase"] != "post" or r["match"] > match:
            continue
        if r["match"] <= 72 and r.get("result"):
            out["group"][str(r["match"])] = r["result"]
        elif r["match"] > 72 and r.get("winner"):
            out["ko"][str(r["match"])] = r["winner"]
    return out


def group_state(results):
    """Standings rows for every group with at least one revealed result."""
    played_groups = {}
    for m_str in results["group"]:
        row = cond.MATCH_ROW[int(m_str)]
        grp = next(g for g, rows in cond.GROUPS.items() if row in rows)
        played_groups.setdefault(grp, 0)
        played_groups[grp] += 1
    state = []
    for grp in sorted(played_groups):
        teams = {}
        for row in cond.GROUPS[grp]:
            _, _, h, a = cond.RATES[row]
            teams.setdefault(h, [0, 0]); teams.setdefault(a, [0, 0])
            m = cond.ROW_MATCH[row]
            res = results["group"].get(str(m))
            if res:
                hg, ag = res
                teams[h][1] += hg - ag; teams[a][1] += ag - hg
                if hg > ag: teams[h][0] += 3
                elif hg < ag: teams[a][0] += 3
                else: teams[h][0] += 1; teams[a][0] += 1
        rows = sorted(((t, pts, gd) for t, (pts, gd) in teams.items()),
                      key=lambda x: (-x[1], -x[2]))
        state.append({"group": grp, "played": played_groups[grp],
                      "total": len(cond.GROUPS[grp]), "rows": rows})
    return state


def rerender(match=None):
    """Regenerate stats + living tex regions from already-documented entries,
    without creating a new match-book entry. `match` defaults to the latest
    documented; conditioning runs through that match."""
    trajectory = _load(TRAJ_PATH, [])
    entries = _entries_for_stats(INDEX)
    if not entries:
        raise SystemExit("nothing documented yet")
    if match is None:
        match = max(e["match"] for e in entries)
    latest_champ = next((r["champion"] for r in reversed(trajectory)
                         if r["phase"] == "post"), None)
    stats = ls.compute(entries, latest_champ)
    expectations = _load(EXP_PATH, [])
    stats["re_ev_delta"] = sum(
        re_ev_delta_for(next(x for x in expectations if x["match"] == en["match"]),
                        en["result"], en["post"]["points"]) for en in entries)
    LIVE_STATS_TEX.write_text(ls.render_macros(stats))

    frozen = _load(FROZEN_PATH, {}).get("stages")
    now_probs = group_st = None
    if frozen:
        res = results_through(trajectory, match)
        now_probs = cond.conditional_probs(res, N=COND_N, seed=2026)
        group_st = group_state(res)
    tex = PAPER_TEX.read_text()
    before = rev.frozen_hash(tex)
    tex = rev.render_paper(tex, entries, frozen=frozen, now=now_probs,
                           group_state=group_st)
    if rev.frozen_hash(tex) != before:
        raise SystemExit("ABORT: frozen region changed — refusing to write paper")
    PAPER_TEX.write_text(tex)
    print(f"Living layer re-rendered through Match {match} "
          f"({stats['documented']} documented)")
    return stats


def revise(match, use_api=True, reopen_text=None):
    trajectory = _load(TRAJ_PATH, [])
    expectations = _load(EXP_PATH, [])
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    entry_path = PAPER / "match_book" / f"M{match:03d}.md"
    if reopen_text is not None:
        if not entry_path.exists():
            raise SystemExit(f"--reopen: M{match:03d}.md not found — run without --reopen first")
        e = mb.parse_markdown(entry_path.read_text())
        old = e["interpretation"]
        e["interpretation"], e["interpretation_source"] = reopen_text, "human"
        with CORRECTIONS.open("a") as fh:
            fh.write(f"\n## M{match} (reopened {now})\nDRAFT: {old}\nHUMAN: {reopen_text}\n")
    else:
        e = build_full_entry(match, trajectory, expectations, commit, now, use_api)
    entry_path.parent.mkdir(parents=True, exist_ok=True)
    entry_path.write_text(mb.to_markdown(e))
    mb.mark_documented(INDEX, match)

    entries = _entries_for_stats(INDEX)
    latest_champ = next((r["champion"] for r in reversed(trajectory)
                         if r["phase"] == "post"), None)
    if latest_champ is None:
        raise SystemExit("no post record in trajectory — cannot compute stats")
    stats = ls.compute(entries, latest_champ)
    stats["re_ev_delta"] = sum(
        re_ev_delta_for(next(x for x in expectations if x["match"] == en["match"]),
                        en["result"], en["post"]["points"]) for en in entries)
    LIVE_STATS_TEX.write_text(ls.render_macros(stats))

    frozen = _load(FROZEN_PATH, {}).get("stages")
    now_probs = group_st = None
    if frozen:
        res = results_through(trajectory, match)
        now_probs = cond.conditional_probs(res, N=COND_N, seed=2026)
        group_st = group_state(res)

    tex = PAPER_TEX.read_text()
    before = rev.frozen_hash(tex)
    tex = rev.render_paper(tex, entries, frozen=frozen, now=now_probs,
                           group_state=group_st)
    after = rev.frozen_hash(tex)
    if before != after:
        raise SystemExit("ABORT: frozen region changed — refusing to write paper")
    PAPER_TEX.write_text(tex)

    with REVISIONS.open("a") as fh:
        fh.write(f"\n**Rev M{match:03d} ({e['fixture']} {e['result'][0]}-{e['result'][1]}).** "
                 f"Cumulative {stats['cum_points']} pts, mean Brier {stats['mean_brier']:.2f}; "
                 f"failure-mode {e['failure_mode'] or 'none'}. "
                 f"Updated evolution table + narrative; no frozen content changed.\n")
    print(f"Paper revised through Match {match} — {stats['documented']} documented · "
          f"{stats['cum_points']} pts · mean Brier {stats['mean_brier']:.3f} · "
          f"failure {e['failure_mode'] or 'none'}")
    return stats


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("match", type=int, nargs="?", default=None)
    ap.add_argument("--reopen", metavar="TEXT", default=None,
                    help="replace the interpretation with TEXT (human track)")
    ap.add_argument("--no-api", action="store_true", help="force templated draft")
    ap.add_argument("--build", action="store_true", help="run latexmk after writing")
    ap.add_argument("--rerender", action="store_true",
                    help="regenerate the living layer from documented entries only")
    a = ap.parse_args(argv)
    if a.rerender:
        rerender(a.match)
    elif a.match is None:
        ap.error("match number required unless --rerender")
    else:
        revise(a.match, use_api=not a.no_api, reopen_text=a.reopen)
    if a.build:
        _latexmk()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
