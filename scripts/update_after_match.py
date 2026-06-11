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


def _git(*args):
    subprocess.run(["git", *args], cwd=ROOT, check=True)


def _latexmk():
    subprocess.run(["latexmk", "-xelatex", "-interaction=nonstopmode",
                    "Avraa_WC2026_paper.tex"], cwd=PAPER, check=True)


def revise(match, use_api=True, reopen_text=None):
    trajectory = _load(TRAJ_PATH, [])
    expectations = _load(EXP_PATH, [])
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    entry_path = PAPER / "match_book" / f"M{match:03d}.md"
    if reopen_text is not None and entry_path.exists():
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
    latest_champ = next(r["champion"] for r in reversed(trajectory)
                        if r["phase"] == "post")
    stats = ls.compute(entries, latest_champ)
    stats["re_ev_delta"] = sum(
        re_ev_delta_for(next(x for x in expectations if x["match"] == en["match"]),
                        en["result"], en["post"]["points"]) for en in entries)
    LIVE_STATS_TEX.write_text(ls.render_macros(stats))

    tex = PAPER_TEX.read_text()
    before = rev.frozen_hash(tex)
    tex = rev.render_paper(tex, entries)
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
    ap.add_argument("match", type=int)
    ap.add_argument("--reopen", metavar="TEXT", default=None,
                    help="replace the interpretation with TEXT (human track)")
    ap.add_argument("--no-api", action="store_true", help="force templated draft")
    ap.add_argument("--build", action="store_true", help="run latexmk after writing")
    a = ap.parse_args(argv)
    revise(a.match, use_api=not a.no_api, reopen_text=a.reopen)
    if a.build:
        _latexmk()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
