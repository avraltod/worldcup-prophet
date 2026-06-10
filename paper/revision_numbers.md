# Revision analysis results (computed for the post-tournament pass)
- B6 Shin de-vig: 2/24 odds-based picks change (insensitivity demonstrated)
- B7 Poisson GOF: lambda-constraint binds 6/72; mean RMS H/D/A residual 0.0028 (max 0.0093)
- B5 Dixon-Coles realized pool points (3/2/1): independent 115, rho=+0.1 -> 120 (+5/+4%), rho=-0.1 -> 113; picks change 5/72 (+0.1), 11/72 (-0.1). DC HELPS on the decision metric, in-sample.
- B1 calibration bins (n=128): 30-40%:50%(n14) 40-50%:45%(n20) 50-60%:48%(n29) 60-70%:56%(n25) 70-80%:66%(n32) 80-90%:75%(n8). Roughly monotonic, WIDE CIs.
- RPS skill 11% vs uniform; Brier skill 10% vs uniform (weak baseline; no per-match historical market odds available)
- B8 rotation penalty (120 Elo) per tournament: 2022 Brier 0.794->0.716 (+9.8% better); 2018 Brier 0.630->0.693 (10.1% WORSE). NOT robust across tournaments; pooled +2.7% is driven entirely by 2022.
