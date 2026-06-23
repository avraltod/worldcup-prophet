
**Rev M001 (Mexico v South Africa 2-0).** Cumulative 1 pts, mean Brier 0.17; failure-mode none. Updated evolution table + narrative; no frozen content changed.

**Rev M002 (South Korea v Czechia 2-1).** Cumulative 1 pts, mean Brier 0.39; failure-mode none. Updated evolution table + narrative; no frozen content changed.

## 2026-06-12 — Authorship

Jeronimo Luza (github.com/jeronimoluza) joined the project as coauthor and
appears on the title page from this date forward. Issued editions M000–M002
predate the change and are not regenerated. The author block sits inside the
frozen-hash region, so this edit advances the frozen-hash baseline by one
step; CI's frozen-hash guard (render_evolution.frozen_hash) continues to
enforce byte-identity of the frozen region within every subsequent revision
run from this baseline forward. This entry exists so the mid-tournament
authorship change is transparent and non-retroactive.

**Rev M003 (Canada v Bosnia and Herzegovina 1-1).** Cumulative 1 pts, mean Brier 0.56; failure-mode none. Updated evolution table + narrative; no frozen content changed.

**Structural revision (12 June 2026, post-M003).** The living layer moves from
marker-delimited blocks inside the paper source to generated files under
`paper/live/`, and it widens substantially: every edition now re-states the
champion table, the divergence table, per-group appendix boxes with real
results and standings, the stage-distribution table, a group-stage tracker, a
live two-track (frozen vs. learning) section, and a per-edition revision
report with a forecast-vintages table. This is a presentation-layer change:
the model, the locked picks, and all frozen prose are untouched, and the
pre-registration guarantee strengthens — the entire skeleton file is now
hash-pinned (`data/skeleton_sha256.txt`) and asserted on every pipeline run,
where previously only the text outside the marker blocks was. This advances
the frozen-hash baseline one step, exactly as the 12 June authorship entry
did. Editions M000–M003 are issued artifacts and are not regenerated; their
headline numbers are backfilled into the vintages table.

**Rev M004 (United States v Paraguay 4-1).** Cumulative 2 pts, mean Brier 0.52; failure-mode none. Full living layer re-rendered (edition M004); skeleton unchanged.

**Rev M007 (Brazil v Morocco 1-1).** Cumulative 2 pts, mean Brier 0.61; failure-mode systematic_rating_error. Full living layer re-rendered (edition M007); skeleton unchanged.

**Rev M008 (Qatar v Switzerland 1-1).** Cumulative 2 pts, mean Brier 0.71; failure-mode systematic_rating_error. Full living layer re-rendered (edition M008); skeleton unchanged.

**Rev M005 (Haiti v Scotland 0-1).** Cumulative 4 pts, mean Brier 0.46; failure-mode none. Full living layer re-rendered (edition M005); skeleton unchanged.

**Rev M006 (Australia v Turkey 2-0).** Cumulative 4 pts, mean Brier 0.54; failure-mode systematic_rating_error. Full living layer re-rendered (edition M006); skeleton unchanged.

**Rev M010 (Germany v Curaçao 7-1).** Cumulative 5 pts, mean Brier 0.61; failure-mode none. Full living layer re-rendered (edition M010); skeleton unchanged.

**Rev M011 (Netherlands v Japan 2-2).** Cumulative 5 pts, mean Brier 0.63; failure-mode none. Full living layer re-rendered (edition M011); skeleton unchanged.

**Rev M009 (Ivory Coast v Ecuador 1-0).** Cumulative 4 pts, mean Brier 0.69; failure-mode none. Full living layer re-rendered (edition M009); skeleton unchanged.

**Rev M012 (Sweden v Tunisia 5-1).** Cumulative 6 pts, mean Brier 0.62; failure-mode none. Full living layer re-rendered (edition M012); skeleton unchanged.

**Rev M014 (Spain v Cape Verde 0-0).** Cumulative 6 pts, mean Brier 0.70; failure-mode systematic_rating_error. Full living layer re-rendered (edition M014); skeleton unchanged.

**Rev M016 (Belgium v Egypt 1-1).** Cumulative 6 pts, mean Brier 0.71; failure-mode systematic_rating_error. Full living layer re-rendered (edition M016); skeleton unchanged.

**Rev M013 (Saudi Arabia v Uruguay 1-1).** Cumulative 6 pts, mean Brier 0.65; failure-mode systematic_rating_error. Full living layer re-rendered (edition M013); skeleton unchanged.

**Rev M015 (Iran v New Zealand 2-2).** Cumulative 6 pts, mean Brier 0.73; failure-mode none. Full living layer re-rendered (edition M015); skeleton unchanged.

**Rev M017 (France v Senegal 3-1).** Cumulative 7 pts, mean Brier 0.71; failure-mode none. Full living layer re-rendered (edition M017); skeleton unchanged.

**Rev M018 (Iraq v Norway 1-4).** Cumulative 8 pts, mean Brier 0.68; failure-mode none. Full living layer re-rendered (edition M018); skeleton unchanged.

**Rev M019 (Argentina v Algeria 3-0).** Cumulative 9 pts, mean Brier 0.65; failure-mode none. Full living layer re-rendered (edition M019); skeleton unchanged.

**Rev M020 (Austria v Jordan 3-1).** Cumulative 10 pts, mean Brier 0.63; failure-mode none. Full living layer re-rendered (edition M020); skeleton unchanged.

**Rev M023 (Portugal v Congo DR 1-1).** Cumulative 10 pts, mean Brier 0.65; failure-mode systematic_rating_error. Full living layer re-rendered (edition M023); skeleton unchanged.

**Rev M022 (England v Croatia 4-2).** Cumulative 11 pts, mean Brier 0.61; failure-mode none. Full living layer re-rendered (edition M022); skeleton unchanged.

**Rev M021 (Ghana v Panama 1-0).** Cumulative 12 pts, mean Brier 0.62; failure-mode none. Full living layer re-rendered (edition M021); skeleton unchanged.

**Rev M024 (Uzbekistan v Colombia 1-3).** Cumulative 14 pts, mean Brier 0.61; failure-mode none. Full living layer re-rendered (edition M024); skeleton unchanged.

**Rev M025 (Czechia v South Africa 1-1).** Cumulative 14 pts, mean Brier 0.62; failure-mode none. Full living layer re-rendered (edition M025); skeleton unchanged.

**Rev M026 (Switzerland v Bosnia and Herzegovina 4-1).** Cumulative 15 pts, mean Brier 0.60; failure-mode none. Full living layer re-rendered (edition M026); skeleton unchanged.

**Rev M027 (Canada v Qatar 6-0).** Cumulative 16 pts, mean Brier 0.58; failure-mode none. Full living layer re-rendered (edition M027); skeleton unchanged.

**Rev M028 (Mexico v South Korea 1-0).** Cumulative 18 pts, mean Brier 0.58; failure-mode none. Full living layer re-rendered (edition M028); skeleton unchanged.

**Rev M032 (United States v Australia 2-0).** Cumulative 19 pts, mean Brier 0.57; failure-mode none. Full living layer re-rendered (edition M032); skeleton unchanged.

**Rev M030 (Scotland v Morocco 0-1).** Cumulative 20 pts, mean Brier 0.57; failure-mode none. Full living layer re-rendered (edition M030); skeleton unchanged.

**Rev M029 (Brazil v Haiti 3-0).** Cumulative 19 pts, mean Brier 0.56; failure-mode none. Full living layer re-rendered (edition M029); skeleton unchanged.

**Rev M031 (Turkey v Paraguay 0-1).** Cumulative 21 pts, mean Brier 0.56; failure-mode none. Full living layer re-rendered (edition M031); skeleton unchanged.

**Rev M035 (Netherlands v Sweden 5-1).** Cumulative 23 pts, mean Brier 0.54; failure-mode none. Full living layer re-rendered (edition M035); skeleton unchanged.

**Rev M033 (Germany v Ivory Coast 2-1).** Cumulative 25 pts, mean Brier 0.54; failure-mode none. Full living layer re-rendered (edition M033); skeleton unchanged.

**Rev M034 (Ecuador v Curaçao 0-0).** Cumulative 25 pts, mean Brier 0.56; failure-mode systematic_rating_error. Full living layer re-rendered (edition M034); skeleton unchanged.

**Rev M036 (Tunisia v Japan 0-4).** Cumulative 27 pts, mean Brier 0.55; failure-mode none. Full living layer re-rendered (edition M036); skeleton unchanged.

**Rev M038 (Spain v Saudi Arabia 4-0).** Cumulative 28 pts, mean Brier 0.54; failure-mode none. Full living layer re-rendered (edition M038); skeleton unchanged.

**Rev M039 (Belgium v Iran 0-0).** Cumulative 28 pts, mean Brier 0.55; failure-mode systematic_rating_error. Full living layer re-rendered (edition M039); skeleton unchanged.

**Rev M037 (Uruguay v Cape Verde 2-2).** Cumulative 27 pts, mean Brier 0.56; failure-mode systematic_rating_error. Full living layer re-rendered (edition M037); skeleton unchanged.

**Rev M040 (New Zealand v Egypt 1-3).** Cumulative 29 pts, mean Brier 0.56; failure-mode none. Full living layer re-rendered (edition M040); skeleton unchanged.

**Rev M043 (Argentina v Austria 2-0).** Cumulative 31 pts, mean Brier 0.54; failure-mode none. Full living layer re-rendered (edition M043); skeleton unchanged.

**Rev M042 (France v Iraq 3-0).** Cumulative 32 pts, mean Brier 0.54; failure-mode none. Full living layer re-rendered (edition M042); skeleton unchanged.

**Rev M041 (Norway v Senegal 3-2).** Cumulative 31 pts, mean Brier 0.55; failure-mode none. Full living layer re-rendered (edition M041); skeleton unchanged.

**Rev M044 (Jordan v Algeria 1-2).** Cumulative 39 pts, mean Brier 0.53; failure-mode none. Full living layer re-rendered (edition M044); skeleton unchanged.

**Rev M047 (Portugal v Uzbekistan 5-0).** Cumulative 40 pts, mean Brier 0.52; failure-mode none. Full living layer re-rendered (edition M047); skeleton unchanged.

**Rev M045 (England v Ghana 0-0).** Cumulative 39 pts, mean Brier 0.56; failure-mode systematic_rating_error. Full living layer re-rendered (edition M045); skeleton unchanged.
