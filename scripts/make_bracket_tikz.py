"""Generate a two-sided TikZ knockout bracket (mini-flag + 3-letter code) for the
locked 2026 entry, resolved from the submitted picks (Avraa_Prediction_WC2026.md /
ko_scores_321.json) and the slot allocation in condition.py (R32 m73-88 -> R16 ->
QF -> SF -> Final m103). Spain emerges from the left half, Argentina from the
right; Spain is champion. Flags are drawn inline in TikZ (simplified but
recognizable) so the figure needs no flag package and no network. Writes a
standalone, compilable paper/figs/fig_bracket.tex.
"""
from pathlib import Path
FIGS = Path(__file__).parent.parent / "paper" / "figs"

# name: (3-letter code, flag-spec). Flag kinds: solid/v/h/hw/vw/plus/nordic/circle/
# diamond/triangle/canton/crescent. Colours are palette names defined in the preamble.
TEAM = {
 "Germany": ("GER", ("h", ["fk", "fr", "fy"])), "Paraguay": ("PAR", ("h", ["fr", "fw", "fb"])),
 "France": ("FRA", ("v", ["fb", "fw", "fr"])), "Sweden": ("SWE", ("nordic", "fb", "fy")),
 "South Korea": ("KOR", ("circle", "fw", "fr")), "Canada": ("CAN", ("v", ["fr", "fw", "fr"])),
 "Netherlands": ("NED", ("h", ["fr", "fw", "fb"])), "Morocco": ("MAR", ("solid", "fr")),
 "Colombia": ("COL", ("hw", ["fy", "fb", "fr"])), "Croatia": ("CRO", ("h", ["fr", "fw", "fb"])),
 "Spain": ("ESP", ("hw", ["fr", "fy", "fr"])), "Austria": ("AUT", ("h", ["fr", "fw", "fr"])),
 "United States": ("USA", ("canton", "fr", "fw", "fb")), "Bosnia and Herzegovina": ("BIH", ("triangle", "fb", "fy")),
 "Belgium": ("BEL", ("v", ["fk", "fy", "fr"])), "Czechia": ("CZE", ("triangle", "fw2", "fb")),
 "Brazil": ("BRA", ("diamond", "fg", "fy", "fb")), "Japan": ("JPN", ("circle", "fw", "fr")),
 "Ecuador": ("ECU", ("hw", ["fy", "fb", "fr"])), "Norway": ("NOR", ("nordic", "fr", "fw")),
 "Mexico": ("MEX", ("v", ["fg", "fw", "fr"])), "Ivory Coast": ("CIV", ("v", ["fo", "fw", "fg"])),
 "England": ("ENG", ("plus", "fw", "fr")), "Algeria": ("ALG", ("v", ["fg", "fw"])),
 "Argentina": ("ARG", ("h", ["fs", "fw", "fs"])), "Uruguay": ("URU", ("canton", "fw", "fb", "fy")),
 "Turkey": ("TUR", ("crescent", "fr", "fw")), "Egypt": ("EGY", ("h", ["fr", "fw", "fk"])),
 "Switzerland": ("SUI", ("plus", "fr", "fw")), "Iran": ("IRN", ("h", ["fg", "fw", "fr"])),
 "Portugal": ("POR", ("vw", ["fg", "fr"])), "Senegal": ("SEN", ("v", ["fg", "fy", "fr"])),
}

# Group origin of each R32 team: letter = group, digit = finishing place
# (1 winner, 2 runner-up, 3 best-third). The eight 3s are exactly the eight
# best third-placers that fill out the 32-team bracket.
SEED = {
 "Mexico": "A1", "South Korea": "A2", "Czechia": "A3",
 "Switzerland": "B1", "Canada": "B2", "Bosnia and Herzegovina": "B3",
 "Brazil": "C1", "Morocco": "C2",
 "United States": "D1", "Turkey": "D2", "Paraguay": "D3",
 "Germany": "E1", "Ecuador": "E2", "Ivory Coast": "E3",
 "Netherlands": "F1", "Japan": "F2", "Sweden": "F3",
 "Belgium": "G1", "Egypt": "G2", "Iran": "G3",
 "Spain": "H1", "Uruguay": "H2",
 "France": "I1", "Norway": "I2", "Senegal": "I3",
 "Argentina": "J1", "Austria": "J2", "Algeria": "J3",
 "Portugal": "K1", "Colombia": "K2",
 "England": "L1", "Croatia": "L2",
}

LEFT_R32 = [("Germany", "Paraguay", "Germany"), ("France", "Sweden", "France"),
            ("South Korea", "Canada", "Canada"), ("Netherlands", "Morocco", "Netherlands"),
            ("Colombia", "Croatia", "Croatia"), ("Spain", "Austria", "Spain"),
            ("United States", "Bosnia and Herzegovina", "United States"), ("Belgium", "Czechia", "Belgium")]
LEFT_R16, LEFT_QF, LEFT_SF = ["France", "Netherlands", "Spain", "Belgium"], ["France", "Spain"], "Spain"
RIGHT_R32 = [("Brazil", "Japan", "Brazil"), ("Ecuador", "Norway", "Norway"),
             ("Mexico", "Ivory Coast", "Mexico"), ("England", "Algeria", "England"),
             ("Argentina", "Uruguay", "Argentina"), ("Turkey", "Egypt", "Turkey"),
             ("Switzerland", "Iran", "Switzerland"), ("Portugal", "Senegal", "Portugal")]
RIGHT_R16, RIGHT_QF, RIGHT_SF = ["Brazil", "England", "Argentina", "Portugal"], ["England", "Argentina"], "Argentina"
CHAMPION = "Spain"

YS, XS, BW, FW, FH = 0.64, 2.7, 2.0, 0.46, 0.30   # row, col, box width, flag w/h (cm)


def parents(ys):
    return [(ys[2 * i] + ys[2 * i + 1]) / 2 for i in range(len(ys) // 2)]


def draw_flag(o, spec, cx, cy):
    """Draw a mini flag centred at (cx,cy), size FW x FH, clipped to its rect."""
    x1, y1, x2, y2 = cx - FW / 2, cy - FH / 2, cx + FW / 2, cy + FH / 2
    o.append(r"\begin{scope}\clip (%.3f,%.3f) rectangle (%.3f,%.3f);" % (x1, y1, x2, y2))
    k = spec[0]
    def R(a, b, c, d, col): o.append(r"\fill[%s](%.3f,%.3f)rectangle(%.3f,%.3f);" % (col, a, b, c, d))
    if k == "solid":
        R(x1, y1, x2, y2, spec[1])
    elif k == "v":
        cols = spec[1]; n = len(cols); w = (x2 - x1) / n
        for i, c in enumerate(cols): R(x1 + i * w, y1, x1 + (i + 1) * w, y2, c)
    elif k == "h":
        cols = spec[1]; n = len(cols); h = (y2 - y1) / n
        for i, c in enumerate(cols): R(x1, y2 - (i + 1) * h, x2, y2 - i * h, c)
    elif k == "hw":            # 3 horizontal, middle double height
        c = spec[1]; q = (y2 - y1) / 4
        R(x1, y2 - q, x2, y2, c[0]); R(x1, y1 + q, x2, y2 - q, c[1]); R(x1, y1, x2, y1 + q, c[2])
    elif k == "vw":            # 2 vertical, left 2/5
        c = spec[1]; xm = x1 + (x2 - x1) * 0.4
        R(x1, y1, xm, y2, c[0]); R(xm, y1, x2, y2, c[1])
    elif k == "plus":          # centred cross (England/Switzerland)
        field, cr = spec[1], spec[2]; t = (y2 - y1) * 0.30
        R(x1, y1, x2, y2, field)
        R((x1 + x2) / 2 - t / 2, y1, (x1 + x2) / 2 + t / 2, y2, cr)
        R(x1, (y1 + y2) / 2 - t / 2, x2, (y1 + y2) / 2 + t / 2, cr)
    elif k == "nordic":        # offset cross
        field, cr = spec[1], spec[2]; t = (y2 - y1) * 0.24; vx = x1 + (x2 - x1) * 0.34
        R(x1, y1, x2, y2, field)
        R(vx - t / 2, y1, vx + t / 2, y2, cr)
        R(x1, (y1 + y2) / 2 - t / 2, x2, (y1 + y2) / 2 + t / 2, cr)
    elif k == "circle":
        field, disc = spec[1], spec[2]; R(x1, y1, x2, y2, field)
        o.append(r"\fill[%s](%.3f,%.3f)circle(%.3fcm);" % (disc, cx, cy, FH * 0.32))
    elif k == "diamond":       # Brazil
        f, d, c = spec[1], spec[2], spec[3]; R(x1, y1, x2, y2, f)
        o.append(r"\fill[%s](%.3f,%.3f)--(%.3f,%.3f)--(%.3f,%.3f)--(%.3f,%.3f)--cycle;"
                 % (d, cx, y2 - 0.02, x2 - 0.04, cy, cx, y1 + 0.02, x1 + 0.04, cy))
        o.append(r"\fill[%s](%.3f,%.3f)circle(%.3fcm);" % (c, cx, cy, FH * 0.20))
    elif k == "triangle":      # hoist triangle over field
        field, tri = spec[1], spec[2]; R(x1, y1, x2, y2, field)
        o.append(r"\fill[%s](%.3f,%.3f)--(%.3f,%.3f)--(%.3f,%.3f)--cycle;" % (tri, x1, y2, x1, y1, x2, y1))
    elif k == "canton":        # stripes + corner block (USA / Uruguay)
        stripe, base, canton = spec[1], spec[2], spec[3]
        R(x1, y1, x2, y2, base); n = 5; h = (y2 - y1) / n
        for i in range(0, n, 2): R(x1, y1 + i * h, x2, y1 + (i + 1) * h, stripe)
        R(x1, y2 - (y2 - y1) * 0.5, x1 + (x2 - x1) * 0.42, y2, canton)
    elif k == "crescent":      # Turkey: red field + white crescent
        field, cr = spec[1], spec[2]; R(x1, y1, x2, y2, field)
        o.append(r"\fill[%s](%.3f,%.3f)circle(%.3fcm);" % (cr, cx - 0.02, cy, FH * 0.30))
        o.append(r"\fill[%s](%.3f,%.3f)circle(%.3fcm);" % (field, cx + 0.03, cy, FH * 0.26))
    o.append(r"\end{scope}")
    o.append(r"\draw[gray!50,line width=0.12pt](%.3f,%.3f)rectangle(%.3f,%.3f);" % (x1, y1, x2, y2))


def box(o, name, x, y, side, win=True, champ=False, seed=None):
    code, spec = TEAM[name]
    left = x if side == "L" else x - BW                 # box left edge
    cy = y
    if champ:
        st = "fill=yellow!88!orange, draw=orange!80!black, line width=0.6pt"
    elif win:
        st = "fill=blue!6, draw=blue!30"
    else:
        st = "fill=gray!7, draw=gray!30"
    o.append(r"\draw[%s, rounded corners=1pt](%.3f,%.3f)rectangle(%.3f,%.3f);"
             % (st, left, cy - 0.21, left + BW, cy + 0.21))
    draw_flag(o, spec, left + 0.07 + FW / 2, cy)
    tcol = "black" if (win or champ) else "gray!60"
    weight = r"\bfseries" if champ else ""
    o.append(r"\node[anchor=west, inner sep=0pt, font=\sffamily\scriptsize%s, text=%s] at (%.3f,%.3f){%s};"
             % (weight, tcol, left + 0.12 + FW, cy, code))
    if seed:                                            # group-seed pill on the outer edge (R32 only)
        sx, anc = (left - 0.07, "east") if side == "L" else (left + BW + 0.07, "west")
        o.append(r"\node[anchor=%s, inner sep=1.1pt, rounded corners=1pt, fill=gray!12, "
                 r"font=\sffamily\tiny, text=gray!80] at (%.3f,%.3f){%s};" % (anc, sx, cy, seed))


def connect(o, cy1, cy2, cxc, cxp):
    mid = (cxc + cxp) / 2; py = (cy1 + cy2) / 2
    for cy in (cy1, cy2):
        o.append(r"\draw[gray!50,line width=0.4pt](%.3f,%.3f)--(%.3f,%.3f);" % (cxc, cy, mid, cy))
    o.append(r"\draw[gray!50,line width=0.4pt](%.3f,%.3f)--(%.3f,%.3f);" % (mid, cy1, mid, cy2))
    o.append(r"\draw[gray!50,line width=0.4pt](%.3f,%.3f)--(%.3f,%.3f);" % (mid, py, cxp, py))


def render_side(o, R32, R16, QF, SF, side):
    sgn = 1 if side == "L" else -1
    x0 = 0.0 if side == "L" else 10 * XS
    ty = [(15 - i) * YS for i in range(16)]
    w32 = parents(ty); r16 = parents(w32); qf = parents(r16); sf = parents(qf)
    cx = [x0 + sgn * d * XS for d in range(5)]
    for j, (t, b, w) in enumerate(R32):
        box(o, t, cx[0], ty[2 * j], side, win=(t == w), seed=SEED[t])
        box(o, b, cx[0], ty[2 * j + 1], side, win=(b == w), seed=SEED[b])
        connect(o, ty[2 * j], ty[2 * j + 1], cx[0] + sgn * BW, cx[1])
    for j, (t, b, w) in enumerate(R32):
        box(o, w, cx[1], w32[j], side)
    for kk in range(4):
        box(o, R16[kk], cx[2], r16[kk], side)
        connect(o, w32[2 * kk], w32[2 * kk + 1], cx[1] + sgn * BW, cx[2])
    for kk in range(2):
        box(o, QF[kk], cx[3], qf[kk], side)
        connect(o, r16[2 * kk], r16[2 * kk + 1], cx[2] + sgn * BW, cx[3])
    box(o, SF, cx[4], sf[0], side)
    connect(o, qf[0], qf[1], cx[3] + sgn * BW, cx[4])
    return cx[4], sf[0]


def main():
    o = [r"\begin{tikzpicture}"]
    for lab, d in [("ROUND OF 32", 0), ("R16", 1), ("QF", 2), ("SF", 3)]:
        for xx in (d * XS + BW / 2, 10 * XS - d * XS - BW / 2):
            o.append(r"\node[gray!65,font=\bfseries\scriptsize] at (%.2f,10.2){%s};" % (xx, lab))
    lx, ly = render_side(o, LEFT_R32, LEFT_R16, LEFT_QF, LEFT_SF, "L")
    rx, ry = render_side(o, RIGHT_R32, RIGHT_R16, RIGHT_QF, RIGHT_SF, "R")
    cx, cy = 5 * XS, ly + 1.7
    o.append(r"\node[gray!65,font=\bfseries\scriptsize] at (%.2f,10.2){FINAL};" % cx)
    o.append(r"\draw[gray!50,line width=0.4pt](%.3f,%.3f)--(%.3f,%.3f)--(%.3f,%.3f);" % (lx + BW, ly, cx, ly, cx, cy - 0.3))
    o.append(r"\draw[gray!50,line width=0.4pt](%.3f,%.3f)--(%.3f,%.3f)--(%.3f,%.3f);" % (rx - BW, ry, cx, ry, cx, cy - 0.3))
    box(o, CHAMPION, cx - BW / 2, cy, "L", champ=True)
    o.append(r"\node[font=\bfseries\footnotesize,text=orange!55!black] at (%.2f,%.2f){$\bigstar$ CHAMPION};" % (cx, cy + 0.5))
    o.append(r"\end{tikzpicture}")

    palette = "\n".join(r"\definecolor{%s}{HTML}{%s}" % kv for kv in [
        ("fr", "CE1126"), ("fb", "0033A0"), ("fy", "FCD116"), ("fg", "009639"),
        ("fk", "000000"), ("fw", "FFFFFF"), ("fw2", "F2F2F2"), ("fo", "F77F00"),
        ("fs", "75AADB")])
    pre = (r"\documentclass[border=8pt]{standalone}" "\n"
           r"\usepackage{tikz}\usepackage{amssymb}\usepackage{xcolor}" "\n" + palette +
           "\n" r"\begin{document}" "\n")
    (FIGS / "fig_bracket.tex").write_text(pre + "\n".join(o) + "\n\\end{document}\n")
    print("wrote paper/figs/fig_bracket.tex")


if __name__ == "__main__":
    main()
