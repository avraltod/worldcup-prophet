*==============================================================================
* 02_poisson_ev.do  --  THE HEART OF THE MODEL
*
* Given a match's (P_home, P_draw, P_away), we:
*   (1) fit two Poisson goal rates (lambda_h, lambda_a) that reproduce those
*       three outcome probabilities -- this turns a 1X2 forecast into a full
*       distribution over every scoreline;
*   (2) score every candidate scoreline by its EXPECTED POINTS under the pool's
*       three-tier rule (3 exact / 2 result+goal-difference / 1 result) and pick
*       the maximizer. That maximizer is the locked prediction.
*
* The key formula. For a prediction (h,a) with result r and goal difference g:
*   EV(h,a) = P(exact h-a) + P(result=r AND GD=g) + P(result=r)
* because the exact score earns all three tiers, the right margin the lower two,
* the right result the lowest. This is why favorites get a 1-0 (a one-goal margin
* is most common, and the GD tier rewards getting the margin right) and why the
* most even games get a 1-1 (every draw shares GD 0, so 1-1 banks the 2-pt tier
* on ANY draw).
*==============================================================================
clear all
set more off
mata: mata clear
import delimited "predictions.csv", varnames(1) clear   // has pH pD pA + python's pick

mata:
// ---- Poisson pmf and the outcome probabilities implied by (lh,la) -----------
// Poisson pmf via log-gamma (Mata has no factorial(); lngamma(k+1) = ln k!)
real scalar pois(real scalar k, real scalar lam) {
    return(exp(-lam + k*ln(lam) - lngamma(k+1)))
}

real rowvector outcome_probs(real scalar lh, real scalar la) {
    real scalar i, j, p, ph, pd, pa
    ph = 0; pd = 0; pa = 0
    for (i=0; i<=8; i=i+1) {
        for (j=0; j<=8; j=j+1) {
            p = pois(i,lh)*pois(j,la)
            if (i>j) ph = ph + p
            else if (i==j) pd = pd + p
            else pa = pa + p
        }
    }
    return((ph,pd,pa))
}

// ---- (1) fit (lh,la) to reproduce (pH,pD,pA) by grid search -----------------
// constrained so total goals lambda_h+lambda_a stays in [1.6,3.4] (WC scoring).
real rowvector fit_rates(real scalar pH, real scalar pD, real scalar pA) {
    real scalar lh, la, best, err, bh, ba
    real rowvector o
    best = 1e9; bh = 1; ba = 1
    for (lh=0.1; lh<=3.2; lh=lh+0.05) {
        for (la=0.1; la<=3.2; la=la+0.05) {
            if (lh+la >= 1.6 & lh+la <= 3.4) {
                o = outcome_probs(lh,la)
                err = (o[1]-pH)^2 + (o[2]-pD)^2 + (o[3]-pA)^2
                if (err < best) {
                    best = err
                    bh = lh
                    ba = la
                }
            }
        }
    }
    return((bh,ba))
}

// ---- (2) EV-optimal scoreline under the 3/2/1 rule --------------------------
real rowvector best_pick(real scalar lh, real scalar la) {
    real scalar h, a, i, j, gp, rp, pe, prg, pr, p, r, ev, bev, bh, ba
    bev = -1; bh = 1; ba = 0
    for (h=0; h<=8; h=h+1) {
        for (a=0; a<=8; a=a+1) {
            gp = h - a
            rp = (h>a) - (h<a)
            pe  = pois(h,lh)*pois(a,la)            // P(exact)
            prg = 0; pr = 0
            for (i=0; i<=8; i=i+1) {
                for (j=0; j<=8; j=j+1) {
                    p = pois(i,lh)*pois(j,la)
                    r = (i>j) - (i<j)
                    if (r==rp) {
                        pr = pr + p                // P(result)
                        if (i-j==gp) prg = prg + p // P(result AND GD)
                    }
                }
            }
            ev = pe + prg + pr
            if (ev > bev) {
                bev = ev
                bh = h
                ba = a
            }
        }
    }
    return((bh,ba))
}

// ---- run it over all 72 fixtures and compare to the locked python pick ------
void run_picks() {
    real matrix out
    real colvector pH, pD, pA, pkh, pka
    real scalar i, n_match, n_draw
    real rowvector lr, bp
    st_view(pH=., ., "ph"); st_view(pD=., ., "pd"); st_view(pA=., ., "pa")
    st_view(pkh=., ., "pick_h"); st_view(pka=., ., "pick_a")
    out = J(rows(pH), 3, .)
    n_match = 0; n_draw = 0
    for (i=1; i<=rows(pH); i=i+1) {
        lr = fit_rates(pH[i],pD[i],pA[i])
        bp = best_pick(lr[1], lr[2])
        out[i,1] = bp[1]; out[i,2] = bp[2]
        out[i,3] = (bp[1]==pkh[i] & bp[2]==pka[i])     // matches python?
        n_match = n_match + out[i,3]
        n_draw  = n_draw + (bp[1]==bp[2])
    }
    st_addvar("byte", ("stata_h","stata_a","matches_python"))
    st_store(., ("stata_h","stata_a","matches_python"), out)
    printf("\n{txt}Stata reproduces {res}%g{txt} of 72 picks exactly; {res}%g{txt} are draws\n", n_match, n_draw)
}
run_picks()
end

* ---- inspect a few illustrative matches ------------------------------------
list home away ph pd pa lambda_h lambda_a stata_h stata_a in 1/8, sep(0) noobs
di _n "A favorite (high pH) -> a one-goal win; an even match (pH~pA, high pD) -> 1-1."
di "These Stata picks should equal the locked python picks (pick_h pick_a)."
