*==============================================================================
* 03_backtest.do  --  Does the model carry skill? (2018 + 2022, 128 matches)
*
* For each historical match we turn the Elo gap into (P_home,P_draw,P_away),
* compare to what actually happened, and score the forecast with the Brier score,
* the ranked probability score (RPS), and a calibration table. This is the
* honest "sanity check" of the paper: roughly calibrated, modest skill over a
* weak uniform baseline, two tournaments support no stronger claim.
*==============================================================================
clear all
set more off
mata: mata clear
import delimited "backtest.csv", varnames(1) clear stringcols(2 3 8)

* ---- Elo win expectancy with a draw component ------------------------------
*   e0 = 1/(1+10^(-d/400)),  pd = 0.30*exp(-|d|/700),  ph = e0 - pd/2 ...
gen hb = 40*(home==host)                       // host gets +40 Elo at home
gen d  = (elo_home + hb) - elo_away
gen e0 = 1/(1+10^(-d/400))
gen pd_ = 0.30*exp(-abs(d)/700)
gen ph = max(.01, e0 - pd_/2)
gen pa = max(.01, 1 - ph - pd_)
gen ps = ph + pd_ + pa
replace ph = ph/ps
gen pdraw = pd_/ps
replace pa = pa/ps

* ---- realized outcome (1=home,2=draw,3=away) and indicators ----------------
gen oH = hg>ag
gen oD = hg==ag
gen oA = hg<ag

* ---- Brier score (multiclass) ----------------------------------------------
gen brier = (ph-oH)^2 + (pdraw-oD)^2 + (pa-oA)^2
gen brier_unif = (1/3-oH)^2 + (1/3-oD)^2 + (1/3-oA)^2

* ---- ranked probability score (ordered H > D > A) --------------------------
gen rps      = 0.5*((ph-oH)^2 + (ph+pdraw-oH-oD)^2)
gen rps_unif = 0.5*((1/3-oH)^2 + (2/3-oH-oD)^2)

bys year: egen mB=mean(brier)
bys year: egen mBu=mean(brier_unif)
bys year: egen mR=mean(rps)
bys year: egen mRu=mean(rps_unif)
di _n "{txt}=== Brier and RPS by tournament (skill = 1 - model/uniform) ==="
table year, stat(mean brier brier_unif rps rps_unif) nformat(%6.3f)

* ---- calibration: bin the model's TOP pick by its probability ---------------
gen pmax = max(ph,pdraw,pa)
gen tophit = (pmax==ph & oH) | (pmax==pdraw & oD) | (pmax==pa & oA)
gen bin = floor(pmax*10)*10
di _n "{txt}=== Calibration of the top pick: predicted bin vs actual hit rate ==="
table bin, stat(count tophit) stat(mean tophit) nformat(%5.2f)
di "Hit rate should rise with the predicted bin (monotone), but bins are small,"
di "so the intervals are wide -- the honest 'not grossly miscalibrated' reading."
