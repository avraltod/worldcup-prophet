"""Driver: turn a finalized match into a paper revision. In CI it runs hands-off;
locally `--reopen M` lets the author replace an interpretation (the only human
step). Renders every living unit to paper/live/*.tex; the skeleton
WC2026_paper.tex is never written and a sha256 check proves it byte-identical."""
import argparse
import json
import os
import subprocess
import sys

os.environ.setdefault("SOURCE_DATE_EPOCH", "1749686400")  # byte-stable figure PDFs across reruns
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import condition as cond
import match_book as mb
import live_stats as ls
import draft_interpretation as di
import fetch_stats_espn as fse
import live_state as lst
import render_live as rl
import vintages as vin
from ev321 import best_pick
from realism_backtest import score_321

DATA = ROOT / "data"
PAPER = ROOT / "paper"
TRAJ_PATH = DATA / "trajectory_v2.json"
EXP_PATH = DATA / "match_expectations.json"
INDEX = PAPER / "match_book" / "index.json"
CORRECTIONS = PAPER / "match_book" / "corrections.md"
REVISIONS = PAPER / "REVISIONS.md"
PAPER_TEX = PAPER / "WC2026_paper.tex"
FROZEN_PATH = DATA / "frozen_stage_probs.json"
GROUP_QUAL_PATH = DATA / "group_qual.json"   # frozen 1st/2nd/3rd*/qual (locked Table 13)
COND_N = 50000   # sims for the per-snapshot conditional forecast
LIVE_DIR = PAPER / "live"
SKELETON_SHA = DATA / "skeleton_sha256.txt"
TWO_TRACK_N = 20000   # per-track sims for the live A-vs-B


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
    # Track B pre-match H/D/A: learn_ratings at this moment are pre-match
    # (lst.sync runs later in _write_living_layer, after stats are collected)
    try:
        from learn import lambda_expected
        _state = lst.load_state()
        _lr = lst.ratings(_state)
        if exp["home"] in _lr and exp["away"] in _lr:
            _lh, _la = lambda_expected(_lr[exp["home"]], _lr[exp["away"]])
            e["pre"]["probs_HDA_b"] = list(rl.outcome_probs(_lh, _la))
    except Exception:
        pass  # best-effort; column shows "--" if unavailable
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


def _latexmk(out_path=None):
    """Compile live edition PDF.

    Outputs to WC2026_paper_live.pdf (via -jobname) so that
    paper/WC2026_paper.pdf — the locked pre-kickoff submission — is NEVER
    overwritten.  If out_path is given, copies the built PDF there.
    Returns the path of the built PDF.
    """
    import shutil as _sh
    job = "WC2026_paper_live"
    subprocess.run(
        ["latexmk", "-xelatex", "-bibtex", "-interaction=nonstopmode",
         "-f", "-e", "$max_repeat=8",
         f"-jobname={job}", "WC2026_paper.tex"],
        cwd=PAPER)
    built = PAPER / f"{job}.pdf"
    if not built.exists():
        raise RuntimeError(f"latexmk did not produce {built}")
    if out_path:
        _sh.copy(built, out_path)
    return built


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
    """Full standings for ALL 12 groups (played or not): rows carry
    P/W/D/L/GF/GA/Pts dicts sorted by (Pts, GD, GF)."""
    state = []
    for grp in sorted(cond.GROUPS):
        teams = {}
        played = 0
        for row in cond.GROUPS[grp]:
            _, _, h, a = cond.RATES[row]
            for t in (h, a):
                teams.setdefault(t, {"team": t, "P": 0, "W": 0, "D": 0, "L": 0,
                                     "GF": 0, "GA": 0, "Pts": 0})
            res = results["group"].get(str(cond.ROW_MATCH[row]))
            if not res:
                continue
            played += 1
            hg, ag = res
            for t, f, g in ((h, hg, ag), (a, ag, hg)):
                r = teams[t]
                r["P"] += 1; r["GF"] += f; r["GA"] += g
                if f > g: r["W"] += 1; r["Pts"] += 3
                elif f == g: r["D"] += 1; r["Pts"] += 1
                else: r["L"] += 1
        rows = sorted(teams.values(),
                      key=lambda r: (-r["Pts"], -(r["GF"] - r["GA"]), -r["GF"]))
        state.append({"group": grp, "played": played,
                      "total": len(cond.GROUPS[grp]), "rows": rows})
    return state


def _assert_skeleton():
    if not SKELETON_SHA.exists():
        raise SystemExit("ABORT: data/skeleton_sha256.txt missing — run the migration first")
    import hashlib
    actual = hashlib.sha256(PAPER_TEX.read_bytes()).hexdigest()
    if actual != SKELETON_SHA.read_text().strip():
        raise SystemExit("ABORT: skeleton WC2026_paper.tex changed — refusing to render")


def _stats_lookup(trajectory):
    """match -> box-score stats (cache-first ESPN fetch), or None."""
    def lookup(m):
        post = next((r for r in trajectory
                     if r["phase"] == "post" and r["match"] == m), None)
        if post is None:
            return None
        return fse.get_stats(m, post["kickoff"])
    return lookup


def _bracket_eliminated(ko_results):
    """Teams the live bracket figure should grey out: submitted R32 participants
    whose match is decided and who did not win it. ko_results maps official KO
    match numbers (as str or int) to the winning team. Empty during the group
    stage; deeper-round shading follows the same rule as those rounds resolve."""
    if not ko_results:
        return set()
    from render_live import _R32_PAIRS
    decided = {str(m): w for m, w in ko_results.items()}
    elim = set()
    for home, away, mn in _R32_PAIRS:
        w = decided.get(str(mn))
        if w is not None:
            elim.update(t for t in (home, away) if t != w)
    return elim


def _track_b_fixture_map(expectations, results, learn_ratings):
    """For every unplayed group fixture, Track~B's predicted scoreline and H/D/A
    probabilities from the live (learning-track) ratings: {match: {'pick':[h,a],
    'hda':[h,d,a]}}. Empty when the learning track has no ratings yet."""
    out = {}
    if not learn_ratings:
        return out
    from learn import lambda_expected
    played = set(results.get("group", {}).keys())
    for e in expectations:
        if str(e["match"]) in played:
            continue
        h, a = e["home"], e["away"]
        if h not in learn_ratings or a not in learn_ratings:
            continue
        lh, la = lambda_expected(learn_ratings[h], learn_ratings[a])
        out[e["match"]] = {"pick": [round(lh), round(la)],
                           "hda": list(rl.outcome_probs(lh, la))}
    return out


def _upcoming_picks(expectations, results, learn_ratings, limit=8):
    """Next-matchday unplayed group fixtures with each track's predicted scoreline.
    Frozen and Track~A reuse the submitted pick (both ride the June-10 ratings, so
    they are identical by construction); Track~B rounds the live-rating expected
    goals, so it can diverge once the learning track has moved a rating."""
    played = set(results.get("group", {}).keys())
    out = []
    for e in sorted(expectations, key=lambda x: x["match"]):
        if str(e["match"]) in played:
            continue
        fa = list(e["pick"])
        if learn_ratings and e["home"] in learn_ratings and e["away"] in learn_ratings:
            from learn import lambda_expected
            lh, la = lambda_expected(learn_ratings[e["home"]], learn_ratings[e["away"]])
            fb = [round(lh), round(la)]
        else:
            fb = list(fa)
        out.append({"match": e["match"], "fixture": f"{e['home']} v {e['away']}",
                    "frozen_pick": fa, "track_a_pick": list(fa), "track_b_pick": fb})
        if len(out) >= limit:
            break
    return out


def _implications(latest_entry, expectations, results, learn_ratings):
    """Remaining fixtures of the just-played group: lock odds + learning odds."""
    from learn import lambda_expected
    grp = next((e.get("group") for e in expectations
                if e["match"] == latest_entry["match"]), None)
    out = []
    if grp is None or learn_ratings is None:
        return out
    for e in expectations:
        if e.get("group") != grp or str(e["match"]) in results["group"]:
            continue
        lh, la = lambda_expected(learn_ratings[e["home"]], learn_ratings[e["away"]])
        out.append({"match": e["match"], "fixture": f"{e['home']} v {e['away']}",
                    "lock_HDA": e["probs_HDA"],
                    "learn_HDA": list(rl.outcome_probs(lh, la))})
    return out


def _write_living_layer(trajectory, entries, match, expectations, use_api=False):
    """Build one context and render every living unit to paper/live/."""
    _assert_skeleton()
    latest_champ = next((r["champion"] for r in reversed(trajectory)
                         if r["phase"] == "post" and r["match"] <= match), None)
    if latest_champ is None:
        raise SystemExit("no post record in trajectory — cannot compute stats")
    stats = ls.compute(entries, latest_champ)
    stats["real_vs_ev_delta"] = sum(
        re_ev_delta_for(next(x for x in expectations if x["match"] == en["match"]),
                        en["result"], en["post"]["points"]) for en in entries)
    stats["entries"] = entries
    latest = max(entries, key=lambda e: e["match"])
    if latest["match"] != match:
        raise SystemExit(f"ABORT: edition M{match:03d} requested but the latest "
                         f"documented match is M{latest['match']:03d} — refusing "
                         f"an out-of-order render")

    frozen = _load(FROZEN_PATH, {}).get("stages")
    if not frozen:
        raise SystemExit("frozen_stage_probs.json missing — cannot render")
    res = results_through(trajectory, match)
    now_probs = cond.conditional_probs(res, N=COND_N, seed=2026)
    prev_res = results_through(trajectory, latest["match"] - 1)
    prev_now = (cond.conditional_probs(prev_res, N=COND_N, seed=2026)
                if prev_res["group"] or prev_res["ko"] else frozen)
    group_st = group_state(res)
    stats["champ_now_top"] = sorted(
        ((t, d["champion"]) for t, d in now_probs.items()),
        key=lambda kv: -kv[1])[:3]

    # learning state: drain the queue, then the two-track re-simulation
    state = lst.load_state()
    state = lst.sync(state, entries, _stats_lookup(trajectory))
    two_track = None
    learn_ratings = None
    if state["processed"]:
        learn_ratings = lst.ratings(state)
        froz_probs_full = cond.conditional_probs(
            res, N=TWO_TRACK_N, seed=2026, ratings=state["baseline"])
        learn_probs_full = cond.conditional_probs(
            res, N=TWO_TRACK_N, seed=2026, ratings=learn_ratings)
        froz_dist = {t: d["champion"] for t, d in froz_probs_full.items()}
        learn_dist = {t: d["champion"] for t, d in learn_probs_full.items()}
        two_track = {"frozen": froz_dist, "learning": learn_dist,
                     "learn_probs": learn_probs_full}
        top8 = sorted(froz_dist, key=lambda t: -froz_dist[t])[:8]
        from live_state import load_live_inputs
        _live_snap = load_live_inputs()
        _snap_summary = _live_snap.get("deltas", {}).get("summary", {})
        hist_row = {"match": match,
                    "frozen_top": {t: round(froz_dist[t], 4) for t in top8},
                    "learning_top": {t: round(learn_dist.get(t, 0.0), 4) for t in top8},
                    "info_snapshot": {
                        "fetched_at": _live_snap.get("fetched_at"),
                        **_live_snap.get("source_freshness", {}),
                        **_snap_summary,
                    } if _live_snap else {}}
        hist_last = state["history"][-1]["match"] if state["history"] else 0
        if match > hist_last:    # monotonic: re-issues never zigzag the path
            state["history"].append(hist_row)
    lst.save_state(state)

    # vintages
    if not vin.load():
        vin.upsert(vin.m000_row(frozen))
    top5 = [(t, d["champion"]) for t, d in sorted(
        now_probs.items(), key=lambda kv: -kv[1]["champion"])[:5]]
    rows = vin.upsert(vin.row_for_edition(match, entries, stats, top5))

    # revision narrative (grounded pack -> Claude or template)
    rec = next((r for r in state["processed"] if r["match"] == latest["match"]), None)
    pack = {"edition": match, "fixture": latest["fixture"],
            "result": latest["result"], "points": latest["post"]["points"],
            "info_bits": latest["post"]["info_bits"],
            "champ_deltas": [[t, round(prev_now[t]["champion"], 4),
                              round(now_probs[t]["champion"], 4)]
                             for t in sorted(now_probs, key=lambda t: -now_probs[t]["champion"])[:5]
                             if t in prev_now],
            "lam_obs": rec["lam_obs"] if rec else None,
            "lam_exp": rec["lam_exp"] if rec else None}
    corrections = CORRECTIONS.read_text() if CORRECTIONS.exists() else ""
    narrative_text, _src = di.draft_revision(pack, corrections, use_api)

    # Track B data — needed by figures and ctx
    _latest_post = next(
        (r for r in reversed(trajectory)
         if r["phase"] == "post" and r["match"] == match), None)
    champion_b = (_latest_post.get("champion_b") or {}) if _latest_post else {}
    if champion_b:
        stats["champ_b_top"] = sorted(champion_b.items(), key=lambda kv: -kv[1])[:3]

    # figures (optional, never block)
    live_fig = two_fig = False
    try:
        import plot_trajectory_live
        plot_trajectory_live.build(trajectory, through_match=match,
                                   out=PAPER / "figs" / "fig_trajectory_live.pdf")
        live_fig = True
    except Exception as ex:                      # noqa: BLE001
        print(f"trajectory figure skipped ({ex})")
    try:
        import make_live_figures as mlf
        groups = {g: sorted({cond.RATES[r][2] for r in cond.GROUPS[g]}
                            | {cond.RATES[r][3] for r in cond.GROUPS[g]})
                  for g in sorted(cond.GROUPS)}
        now_b_probs = (two_track or {}).get("learn_probs", {})
        # Track A groupqual figure
        mlf.group_qual_fig(frozen, now_probs, groups,
                           PAPER / "figs" / "fig_live_groupqual.pdf",
                           label="Track A", color="#3b6ea5")
        # Track B groupqual figure (true Track B stage probs when available)
        mlf.group_qual_fig(frozen, now_b_probs or now_probs, groups,
                           PAPER / "figs" / "fig_live_groupqual_b.pdf",
                           label="Track B", color="#3d8c40")
        # Champdist with Frozen + Track A (+ Track B if available)
        track_b_champ = champion_b if champion_b else None
        mlf.champdist_fig(frozen, now_probs,
                          PAPER / "figs" / "fig_live_champdist.pdf",
                          track_b=track_b_champ)
        if state["history"]:
            mlf.two_track_fig(state["history"],
                              PAPER / "figs" / "fig_two_track_live.pdf")
            two_fig = True
        # Market figure (four bars: Frozen/Track A/Track B/Market)
        market = next(
            (r.get("market_champion") for r in reversed(trajectory)
             if r.get("phase") == "post" and r.get("market_champion")), None)
        if market:
            mlf.market_fig(frozen, now_probs, track_b_champ, market,
                           PAPER / "figs" / "fig_live_market.pdf")
        # Knockout brackets (Track A / Track B): generated every edition so they
        # are ready; bracket_live_unit only displays them once KO results exist.
        ko_done = res.get("ko", {})
        elim = _bracket_eliminated(ko_done)
        mlf.bracket_fig(now_probs, PAPER / "figs" / "fig_live_bracket_a.pdf",
                        "Track A", eliminated=elim)
        mlf.bracket_fig(now_b_probs or now_probs,
                        PAPER / "figs" / "fig_live_bracket_b.pdf",
                        "Track B", eliminated=elim)
    except Exception as ex:                      # noqa: BLE001
        print(f"live figures skipped ({ex})")

    # render every unit
    _lookup = _stats_lookup(trajectory)
    match_stats = {}
    for _en in entries:
        _s = _lookup(_en["match"])
        if _s is not None:
            match_stats[_en["match"]] = _s

    latest_snap = (state["history"][-1].get("info_snapshot")
                   if state["history"] else None) or None

    _market = next(
        (r.get("market_champion") for r in reversed(trajectory)
         if r.get("phase") == "post" and r.get("market_champion")), None)
    ctx = {"match": match, "entries": entries, "match_stats": match_stats,
           "learning": state, "prev_now": prev_now, "now": now_probs,
           "vintages_rows": rows, "revision_narrative": narrative_text,
           "implications": _implications(latest, expectations, res, learn_ratings),
           "frozen": frozen, "frozen_finish": _load(GROUP_QUAL_PATH, {}),
           "results": res, "expectations": expectations,
           "n_results": stats["documented"],
           "cum_points": stats["cum_points"],
           "mean_brier": stats["mean_brier"],
           "champ_now_top": stats["champ_now_top"],
           "champ_b_top": stats.get("champ_b_top", []),
           "two_track": two_track,
           "now_b": (two_track or {}).get("learn_probs", {}),
           "info_snapshot": latest_snap or {},
           "champion_b": champion_b,
           "market": _market,
           "group_state": group_st,
           "champion_movers": sorted(
               [[t, round(prev_now.get(t, {}).get("champion", 0.0), 4),
                 round(now_probs[t]["champion"], 4)]
                for t in now_probs if t in prev_now],
               key=lambda x: -abs(x[2] - x[1])),
           }
    # 1. stats first — every other unit can reference these macros
    rl.write_unit(LIVE_DIR, "stats", ls.render_macros(stats))
    # 2. champ table
    rl.write_unit(LIVE_DIR, "champ_table",
                  rl.champ_table_unit(frozen, now_probs, len(entries),
                                      champion_b=champion_b))
    # 3. trajectory-based units
    rl.write_unit(LIVE_DIR, "trajfig", rl.trajfig_unit(entries, live_fig))
    rl.write_unit(LIVE_DIR, "ledger",
                  rl.ledger(entries,
                            upcoming=_upcoming_picks(expectations, res, learn_ratings)))
    rl.write_unit(LIVE_DIR, "narrative", rl.narrative_unit(entries))
    rl.write_unit(LIVE_DIR, "divergence", rl.divergence_unit(frozen, now_probs, entries, group_st, champion_b=champion_b, now_b=ctx.get("now_b", {})))
    # 4. derived units
    rl.write_unit(LIVE_DIR, "revision_report", rl.revision_report(ctx))
    rl.write_unit(LIVE_DIR, "tracker", rl.tracker(group_st, frozen, now_probs))
    rl.write_unit(LIVE_DIR, "two_track",
                  rl.two_track_unit(two_track, state, fig=two_fig,
                                    info_snapshot=latest_snap,
                                    track_a=now_probs,
                                    champion_b=champion_b or None,
                                    frozen_stages=frozen))
    rl.write_unit(LIVE_DIR, "market_snap", rl.market_snap_unit(ctx))
    rl.write_unit(LIVE_DIR, "survival_colcomp", rl.survival_colcomp_unit(ctx))
    # 5. per-group sections
    track_b_map = _track_b_fixture_map(expectations, res, learn_ratings)
    for g in group_st:
        rl.write_unit(LIVE_DIR, f"group_{g['group']}",
                      rl.group_box(g, res, expectations, frozen, now_probs,
                                   now_b=ctx.get("now_b", {}),
                                   track_b=track_b_map))
    # 6. data and methodology sections
    rl.write_unit(LIVE_DIR, "data_revealed", rl.data_revealed_unit(ctx, use_api))
    rl.write_unit(LIVE_DIR, "simulation_note", rl.simulation_note_unit(ctx, use_api))
    rl.write_unit(LIVE_DIR, "sec36_live", rl.sec36_live_unit(ctx, use_api))
    rl.write_unit(LIVE_DIR, "champdist_live", rl.champdist_live_unit(ctx))
    # 7. analysis sections
    rl.write_unit(LIVE_DIR, "robustness_live", rl.robustness_live_unit(ctx, use_api))
    rl.write_unit(LIVE_DIR, "failure_analysis", rl.failure_analysis_unit(ctx, use_api))
    rl.write_unit(LIVE_DIR, "discussion_live", rl.discussion_live_unit(ctx, use_api))
    # 8. group qual and bracket
    rl.write_unit(LIVE_DIR, "groupqual_live", rl.groupqual_live_unit(ctx))
    rl.write_unit(LIVE_DIR, "groupqual_table", rl.groupqual_table_unit(ctx))
    rl.write_unit(LIVE_DIR, "fixture_risk", rl.fixture_risk_unit(ctx))
    rl.write_unit(LIVE_DIR, "risk_tracker", rl.risk_tracker_unit(ctx))
    rl.write_unit(LIVE_DIR, "bracket_live", rl.bracket_live_unit(ctx))
    # 9. intro second-to-last, abstract last (both reference numbers from all other units)
    rl.write_unit(LIVE_DIR, "intro_data_note", rl.intro_data_note_unit(ctx, use_api))
    rl.write_unit(LIVE_DIR, "abstract_live", rl.abstract_live_unit(ctx, use_api))
    _assert_skeleton()
    return stats


def rerender(match=None):
    """Regenerate the full living layer from already-documented entries,
    without creating a new match-book entry. `match` defaults to the latest
    documented; ledger, scorecard, and conditioning all run through it."""
    trajectory = _load(TRAJ_PATH, [])
    entries = _entries_for_stats(INDEX)
    if not entries:
        raise SystemExit("nothing documented yet")
    if match is None:
        match = max(e["match"] for e in entries)
    entries = [e for e in entries if e["match"] <= match]   # historical re-issue
    stats = _write_living_layer(trajectory, entries, match, _load(EXP_PATH, []))
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

    entries = [e for e in _entries_for_stats(INDEX) if e["match"] <= match]
    stats = _write_living_layer(trajectory, entries, match, expectations,
                                use_api=use_api)

    with REVISIONS.open("a") as fh:
        fh.write(f"\n**Rev M{match:03d} ({e['fixture']} {e['result'][0]}-{e['result'][1]}).** "
                 f"Cumulative {stats['cum_points']} pts, mean Brier {stats['mean_brier']:.2f}; "
                 f"failure-mode {e['failure_mode'] or 'none'}. "
                 f"Full living layer re-rendered (edition M{match:03d}); skeleton unchanged.\n")
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
