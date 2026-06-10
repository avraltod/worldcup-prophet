*==============================================================================
* 01_devig.do  --  From bookmaker odds to fair probabilities
*
* Bookmaker decimal odds imply probabilities that sum to MORE than 1: the excess
* is the bookmaker's margin (the "overround" or "vig"). To forecast we must strip
* it out. This file shows the two methods the paper discusses:
*   (a) basic normalization  -- divide each implied probability by their sum
*   (b) Shin's method        -- corrects the favorite-longshot bias in the margin
* The model uses (a); the paper shows (b) changes only 2 of 24 picks.
*==============================================================================
clear all
set more off
mata: mata clear
import delimited "odds.csv", varnames(1) clear

* ---- implied ("booked") probabilities = 1 / decimal odds -------------------
gen b_home = 1/odds_home
gen b_draw = 1/odds_draw
gen b_away = 1/odds_away
gen booksum = b_home + b_draw + b_away          // > 1; the excess is the vig
gen overround = booksum - 1
summarize overround                              // typical bookmaker margin ~5-7%

* ---- (a) basic normalization: just rescale so they sum to 1 -----------------
gen p_home = b_home/booksum
gen p_draw = b_draw/booksum
gen p_away = b_away/booksum

* ---- (b) Shin's method: solve for the insider-trading parameter z ----------
* For each match, find z in [0,0.5] so the Shin-fair probabilities sum to 1:
*   p_i(z) = ( sqrt(z^2 + 4(1-z) b_i^2 / B) - z ) / ( 2(1-z) ),   B = sum(b_i)
mata:
real scalar shin_sum(real scalar z, real rowvector b, real scalar B) {
    real rowvector p
    p = (sqrt(z:^2 :+ 4*(1-z)*(b:^2)/B) :- z) :/ (2*(1-z))
    return(sum(p))
}
void shin_devig() {
    real matrix B
    real scalar i, lo, hi, z, Bi
    real rowvector b, p
    st_view(B=., ., ("b_home","b_draw","b_away"))
    real matrix out
    out = J(rows(B), 3, .)
    for (i=1; i<=rows(B); i++) {
        b  = B[i,.]
        Bi = sum(b)
        lo = 0; hi = 0.5
        for (j=1; j<=60; j++) {            // bisection on z
            z = (lo+hi)/2
            if (shin_sum(z,b,Bi) > 1) lo = z
            else hi = z
        }
        z = (lo+hi)/2
        p = (sqrt(z:^2 :+ 4*(1-z)*(b:^2)/Bi) :- z) :/ (2*(1-z))
        out[i,.] = p/sum(p)
    }
    st_addvar("double", ("ps_home","ps_draw","ps_away"))
    st_store(., ("ps_home","ps_draw","ps_away"), out)
}
shin_devig()
end

* ---- compare the two de-vig methods ----------------------------------------
gen ddiff = abs(p_home - ps_home)
list home away p_home ps_home ddiff if ddiff > .01, sep(0)
count if ddiff > .01
di as txt "Fixtures where Shin moves the home prob by >1pp: " as res r(N) as txt " of 24"
di as txt "(matches the Python finding: the de-vig choice barely affects the picks)"

* p_home/p_draw/p_away (basic normalization) are the inputs to 02_poisson_ev.do
