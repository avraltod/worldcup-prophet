*==============================================================================
* 00_master.do  --  Run the whole Stata replication of the WC2026 model
*
* Set your working directory to this folder, then:  do 00_master.do
* Each file is standalone and verifiable against the Python model.
*==============================================================================
do 01_devig.do        // bookmaker odds  -> fair probabilities  (de-vig)
do 02_poisson_ev.do   // probabilities   -> EV-optimal scoreline (THE HEART; 72/72 picks)
do 03_backtest.do     // historical Elo  -> Brier / RPS / calibration (skill check)
di _n "{txt}All three stages complete. Compare the printed numbers to the paper."
