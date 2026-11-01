"""Draw the mod's preview image (1920x1080 JPG, the size other mods ship) from SVG with rsvg-convert and Lato.

The background curve is the default curve from mod.json. The upper right corner is kept clear for a version number.

Usage: python3 tools/make_preview.py [OUT_FILE] [--version 0.1] [--keep-svg SVG_FILE]
--keep-svg also writes the SVG the image is rendered from (for example to local/preview/cover.svg); keep it out of best_before_1/.
OUT_FILE defaults to best_before_1/_metadata/0.jpg, the cover (the uploader's Preview slot), and then also writes a copy to
1-cover.jpg, the first gallery image, so the cover opens the gallery too; see docs/publishing.md.
"""
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

W, H = 1920, 1080

# Default curve from mod.json: 120% down to freshness 40%, 100% at 20%, 0% at 0% and for spoiled cargo.
X0, X1 = 80, 1840          # freshness 100% .. 0%
Y_TOP, Y0 = 440, 1000      # pay 120% .. 0%


def fx(f):
    return X0 + (1 - f) * (X1 - X0)


def py(p):
    return Y0 - p / 1.2 * (Y0 - Y_TOP)


LIFT = 50   # the title block, the feature list and the version sit this far up, which halves the empty band above the title

GREEN, AMBER, RED = "#6cc04a", "#f2b33d", "#e0533f"
INK = "#152031"

# The background's gradient, glow and curve colours, drawn by background(); tools/make_gallery.py lays its cards on the same background.
BACKGROUND_DEFS = f'''<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#22334b"/><stop offset="1" stop-color="#0e1521"/></linearGradient>
  <radialGradient id="glow" cx="0.62" cy="0.82" r="0.55"><stop offset="0" stop-color="#3a5a7e" stop-opacity=".45"/><stop offset="1" stop-color="#3a5a7e" stop-opacity="0"/></radialGradient>
  <linearGradient id="curveGrad" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{W}" y2="0">
    <stop offset="0" stop-color="{GREEN}"/><stop offset="{fx(0.4) / W:.3f}" stop-color="{GREEN}"/>
    <stop offset="{fx(0.2) / W:.3f}" stop-color="{AMBER}"/><stop offset="{fx(0.0) / W:.3f}" stop-color="{RED}"/><stop offset="1" stop-color="{RED}"/>
  </linearGradient>'''


def grid():
    """Pay every 20%, freshness every 10%."""
    out = []
    for i in range(7):
        y = py(i * 0.2)
        out.append(f'<line x1="0" y1="{y:.1f}" x2="{W}" y2="{y:.1f}" stroke="#fff" stroke-opacity="0.045" stroke-width="2"/>')
    for i in range(11):
        x = fx(i / 10)
        out.append(f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{H}" stroke="#fff" stroke-opacity="0.045" stroke-width="2"/>')
    return "\n".join(out)


def chart():
    out = [grid()]
    pts = [(0, py(1.2)), (fx(0.4), py(1.2)), (fx(0.2), py(1.0)), (fx(0.0), py(0.0)), (W, py(0.0))]
    line = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    out.append(f'<path d="{line} L {W} {H} L 0 {H} Z" fill="url(#curveGrad)" fill-opacity="0.13"/>')
    # Normal pay line
    out.append(f'<line x1="0" y1="{py(1.0):.1f}" x2="{W}" y2="{py(1.0):.1f}" stroke="#fff" stroke-opacity="0.28" '
               f'stroke-width="3" stroke-dasharray="16 12"/>')
    out.append(f'<path d="{line}" fill="none" stroke="url(#curveGrad)" stroke-opacity="0.18" stroke-width="30" '
               f'stroke-linejoin="round"/>')
    out.append(f'<path d="{line}" fill="none" stroke="url(#curveGrad)" stroke-opacity="0.85" stroke-width="9" '
               f'stroke-linejoin="round"/>')
    lab = 'font-family="Lato" font-weight="700" font-size="30" fill="#fff" fill-opacity="0.55"'
    out.append(f'<text x="{X0}" y="{py(1.2) - 18:.1f}" {lab}>120%</text>')
    out.append(f'<text x="{X0}" y="{py(1.0) + 40:.1f}" {lab}>100%</text>')
    return "\n".join(out)



def background(curve=True):
    """The gradient, the glow, and the grid with the default pay curve (or the grid alone)."""
    return "\n".join([f'<rect width="{W}" height="{H}" fill="url(#bg)"/>', f'<rect width="{W}" height="{H}" fill="url(#glow)"/>',
                      chart() if curve else grid()])


# ---- produce, drawn in a flat style: fill, darker same-hue outline, light highlight ----

def scallop(cx, cy, r, n, bulge, phase=0.0):
    pts = []
    for i in range(n + 1):
        a = phase + 2 * math.pi * i / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"
    for i in range(n):
        am = phase + 2 * math.pi * (i + .5) / n
        d += f" Q {cx + r * bulge * math.cos(am):.1f} {cy + r * bulge * math.sin(am):.1f} {pts[i + 1][0]:.1f} {pts[i + 1][1]:.1f}"
    return d + " Z"


def lettuce(cx, cy, r, spoiled=False):
    outer, inner, core, edge = (("#6dbf47", "#9bd96a", "#d4f2ae", "#356e1f") if not spoiled
                                else ("#9a8c45", "#b3a25a", "#cfc08a", "#55491c"))
    spots = "" if not spoiled else "".join(
        f'<circle cx="{cx + dx * r:.1f}" cy="{cy + dy * r:.1f}" r="{r * .12:.1f}" fill="#5e4a1e" opacity=".7"/>'
        for dx, dy in ((-.5, .3), (.45, .45), (.2, -.55)))
    return f'''<g>
  <path d="{scallop(cx, cy, r, 11, 1.2)}" fill="{outer}" stroke="{edge}" stroke-width="5" stroke-linejoin="round"/>
  <path d="{scallop(cx - r * .08, cy - r * .08, r * .62, 8, 1.22, .3)}" fill="{inner}" stroke="{edge}" stroke-width="3" stroke-opacity=".5"/>
  <path d="{scallop(cx - r * .12, cy - r * .14, r * .28, 6, 1.25)}" fill="{core}"/>
  <path d="M {cx - r * .75} {cy + r * .35} Q {cx - r * .3} {cy + r * .2} {cx - r * .2} {cy + r * .75}" fill="none" stroke="{edge}" stroke-width="3" stroke-opacity=".6" stroke-linecap="round"/>
  <path d="M {cx + r * .78} {cy + r * .1} Q {cx + r * .4} {cy + r * .25} {cx + r * .45} {cy + r * .72}" fill="none" stroke="{edge}" stroke-width="3" stroke-opacity=".6" stroke-linecap="round"/>
  {spots}
</g>'''


def steak(cx, cy, s, rot=0, spoiled=False, shape=0):
    body, rim, edge = ("#c8433f", "#f2b0aa", "#7a2420") if not spoiled else ("#7f7a45", "#bdb882", "#4a4722")
    if shape == 0:   # rounded steak
        p = (f"M {-40*s} {-30*s} C {-10*s} {-62*s} {44*s} {-52*s} {50*s} {-12*s} "
             f"C {56*s} {22*s} {30*s} {28*s} {32*s} {48*s} C {34*s} {66*s} {-6*s} {66*s} {-24*s} {44*s} "
             f"C {-44*s} {22*s} {-62*s} {-6*s} {-40*s} {-30*s} Z")
    else:            # longer cut with a fat cap along one side
        p = (f"M {-58*s} {-6*s} C {-50*s} {-40*s} {20*s} {-48*s} {56*s} {-24*s} "
             f"C {72*s} {-12*s} {66*s} {22*s} {40*s} {30*s} C {6*s} {44*s} {-40*s} {40*s} {-58*s} {-6*s} Z")
    spots = "" if not spoiled else (f'<circle cx="{10*s}" cy="{8*s}" r="{7*s}" fill="#4a4722" opacity=".6"/>'
                                    f'<circle cx="{-22*s}" cy="{18*s}" r="{5*s}" fill="#4a4722" opacity=".6"/>')
    return f'''<g transform="translate({cx} {cy}) rotate({rot}) scale(1 .78)">
  <path d="{p}" fill="{rim}" stroke="{edge}" stroke-width="5" stroke-linejoin="round"/>
  <path d="{p}" fill="{body}" transform="translate({-3*s} {3*s}) scale(.8)"/>
  <path d="M {-26*s} {4*s} Q {0} {-8*s} {22*s} {10*s}" fill="none" stroke="{rim}" stroke-width="{5*s:.1f}" stroke-linecap="round"/>
  <path d="M {-14*s} {22*s} Q {4*s} {14*s} {18*s} {24*s}" fill="none" stroke="{rim}" stroke-width="{4*s:.1f}" stroke-linecap="round"/>
  {spots}
  <circle cx="{-18*s}" cy="{-18*s}" r="{8*s}" fill="#fff" opacity="{.9 if not spoiled else .35}"/>
</g>'''


def fish(cx, cy, s, rot=0, spoiled=False):
    body, edge, belly = ("#9fd5db", "#4f98a1", "#cdeef1") if not spoiled else ("#a3a77c", "#5a5f38", "#c2c39c")
    body_d = (f"M {-55*s} 0 C {-35*s} {-34*s} {25*s} {-38*s} {58*s} {-4*s} "
              f"C {28*s} {30*s} {-30*s} {32*s} {-55*s} 0 Z")
    tail_d = f"M {-50*s} 0 L {-82*s} {-26*s} L {-74*s} 0 L {-82*s} {26*s} Z"
    fin_d = f"M {-8*s} {-28*s} L {8*s} {-46*s} L {22*s} {-27*s} Z"
    if spoiled:
        ex, ey, k = 30 * s, -7 * s, 7 * s
        eye = (f'<path d="M {ex-k} {ey-k} L {ex+k} {ey+k} M {ex+k} {ey-k} L {ex-k} {ey+k}" stroke="#2a2d18" '
               f'stroke-width="{4*s:.1f}" stroke-linecap="round"/>')
    else:
        eye = (f'<circle cx="{30*s}" cy="{-7*s}" r="{8*s}" fill="#fff"/>'
               f'<circle cx="{32*s}" cy="{-7*s}" r="{4.5*s}" fill="#1d3640"/>')
    return f'''<g transform="translate({cx} {cy}) rotate({rot})">
  <path d="{fin_d}" fill="{edge}" stroke="{edge}" stroke-width="4" stroke-linejoin="round"/>
  <path d="{tail_d}" fill="{body}" stroke="{edge}" stroke-width="5" stroke-linejoin="round"/>
  <path d="{body_d}" fill="{body}" stroke="{edge}" stroke-width="5" stroke-linejoin="round"/>
  <path d="M {-40*s} {6*s} C {-10*s} {22*s} {25*s} {20*s} {48*s} {2*s}" fill="none" stroke="{belly}" stroke-width="{7*s:.1f}" stroke-linecap="round"/>
  <path d="M {14*s} {-22*s} Q {4*s} {-4*s} {14*s} {16*s}" fill="none" stroke="{edge}" stroke-width="4" stroke-linecap="round"/>
  {eye}
</g>'''


# ---- containers ----

def shade(x, y, w, h, amount):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#0b1220" opacity="{amount}"/>' if amount else ""


def crate(cx, bottom, w, h, produce="", dark=0.0):
    """Wooden crate seen from the front; with produce it is open and the produce shows over the rim."""
    x, y = cx - w / 2, bottom - h
    planks = []
    for i in range(3):
        py_ = y + i * h / 3
        planks.append(f'<rect x="{x}" y="{py_}" width="{w}" height="{h / 3}" fill="#c77b3b"/>')
        planks.append(f'<rect x="{x}" y="{py_ + 6}" width="{w}" height="6" fill="#e3a05e" opacity=".7"/>')
        planks.append(f'<line x1="{x}" y1="{py_ + h / 3}" x2="{x + w}" y2="{py_ + h / 3}" stroke="#7c4519" stroke-width="5"/>')
    posts = "".join(
        f'<rect x="{px}" y="{y}" width="24" height="{h}" fill="#a9622b"/>'
        f'<circle cx="{px + 12}" cy="{y + 20}" r="5" fill="#5e3412"/><circle cx="{px + 12}" cy="{bottom - 20}" r="5" fill="#5e3412"/>'
        for px in (x + 4, x + w - 28))
    back = f'<rect x="{x + 10}" y="{y - 24}" width="{w - 20}" height="38" rx="4" fill="#6e3a14"/>' if produce else ""
    return f'''<g>
  {back}
  {produce}
  {"".join(planks)}
  {posts}
  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="none" stroke="#5e3412" stroke-width="7"/>
  {shade(x - 4, y - 4, w + 8, h + 8, dark)}
</g>'''


def box(cx, bottom, w, h, dark=0.0):
    """Closed cardboard box with tape and a this-side-up mark."""
    x, y = cx - w / 2, bottom - h
    ax, ay = x + w - 44, y + h - 30
    arrows = "".join(f'<path d="M {ax + dx} {ay} L {ax + dx} {ay - 26} M {ax + dx - 8} {ay - 18} L {ax + dx} {ay - 28} L {ax + dx + 8} {ay - 18}" '
                     f'fill="none" stroke="#6f4f26" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'
                     for dx in (0, 20))
    return f'''<g>
  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="#c99f64"/>
  <rect x="{x}" y="{y}" width="{w}" height="16" fill="#d9b47c"/>
  <rect x="{cx - 18}" y="{y}" width="36" height="{h * .42}" fill="#e6cf9c"/>
  <line x1="{x}" y1="{y + 16}" x2="{x + w}" y2="{y + 16}" stroke="#8c6a38" stroke-width="3"/>
  {arrows}
  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="none" stroke="#6f4f26" stroke-width="6"/>
  {shade(x - 3, y - 3, w + 6, h + 6, dark)}
</g>'''


def bin_(cx, bottom, w, h, contents):
    """Metal garbage can, contents spilling over the rim."""
    top = bottom - h
    tl, tr, bl, br = cx - w / 2, cx + w / 2, cx - w * .42, cx + w * .42
    ridges = "".join(f'<line x1="{cx + k * w * .3:.1f}" y1="{top + 26}" x2="{cx + k * w * .25:.1f}" y2="{bottom - 14}" '
                     f'stroke="#9aaabb" stroke-width="7" stroke-linecap="round" opacity=".55"/>' for k in (-1, -.33, .33, 1))
    return f'''<g>
  <ellipse cx="{cx}" cy="{top + 4}" rx="{w / 2 - 6}" ry="20" fill="#2c343e"/>
  {contents}
  <path d="M {tl} {top} L {tr} {top} L {br} {bottom} L {bl} {bottom} Z" fill="#6c7c8d" stroke="#36404b" stroke-width="7" stroke-linejoin="round"/>
  {ridges}
  <rect x="{tl - 10}" y="{top - 4}" width="{w + 20}" height="24" rx="10" fill="#8b9bad" stroke="#36404b" stroke-width="6"/>
  <path d="M {tl + 30} {top + 26} L {bl + 22} {bottom - 10}" stroke="#fff" stroke-width="8" stroke-linecap="round" opacity=".18"/>
</g>'''


def face(cx, cy, r, mood):
    color = {"happy": GREEN, "neutral": AMBER, "sad": RED}[mood]
    ink = "#1b2433"
    eyes = (f'<ellipse cx="{cx - r * .33}" cy="{cy - r * .22}" rx="{r * .1}" ry="{r * .15}" fill="{ink}"/>'
            f'<ellipse cx="{cx + r * .33}" cy="{cy - r * .22}" rx="{r * .1}" ry="{r * .15}" fill="{ink}"/>')
    if mood == "happy":
        mouth = f'M {cx - r * .5} {cy + r * .12} Q {cx} {cy + r * .72} {cx + r * .5} {cy + r * .12}'
    elif mood == "neutral":
        mouth = f'M {cx - r * .38} {cy + r * .35} L {cx + r * .38} {cy + r * .35}'
    else:
        mouth = f'M {cx - r * .45} {cy + r * .52} Q {cx} {cy + r * .05} {cx + r * .45} {cy + r * .52}'
        eyes += (f'<path d="M {cx - r * .55} {cy - r * .55} L {cx - r * .18} {cy - r * .42}" stroke="{ink}" stroke-width="{r * .1}" stroke-linecap="round"/>'
                 f'<path d="M {cx + r * .55} {cy - r * .55} L {cx + r * .18} {cy - r * .42}" stroke="{ink}" stroke-width="{r * .1}" stroke-linecap="round"/>')
    return f'''<g filter="url(#shadow)">
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}" stroke="#fff" stroke-width="7"/>
  <ellipse cx="{cx - r * .3}" cy="{cy - r * .5}" rx="{r * .35}" ry="{r * .18}" fill="#fff" opacity=".25"/>
  {eyes}
  <path d="{mouth}" fill="none" stroke="{ink}" stroke-width="{r * .13}" stroke-linecap="round"/>
</g>'''


def stink(cx, top):
    out = []
    for dx, h in ((-60, 90), (0, 115), (60, 90)):
        x = cx + dx
        d = f"M {x} {top} c -18 -{h/6} 18 -{h/3} 0 -{h/2} c -18 -{h/6} 18 -{h/3} 0 -{h/2}"
        out.append(f'<path d="{d}" fill="none" stroke="#9fbf4a" stroke-width="7" stroke-linecap="round" opacity=".8"/>')
    for fx_, fy_ in ((cx - 95, top - 70), (cx + 40, top - 125), (cx + 105, top - 40)):
        out.append(f'<ellipse cx="{fx_ - 6}" cy="{fy_ - 8}" rx="8" ry="5" fill="#dfe8f0" opacity=".8" transform="rotate(-25 {fx_ - 6} {fy_ - 8})"/>'
                   f'<ellipse cx="{fx_ + 6}" cy="{fy_ - 8}" rx="8" ry="5" fill="#dfe8f0" opacity=".8" transform="rotate(25 {fx_ + 6} {fy_ - 8})"/>'
                   f'<circle cx="{fx_}" cy="{fy_}" r="7" fill="#20262e"/>')
    return "\n".join(out)


def warning_badge(cx, cy, r):
    """The Stale Cargo warning's icon: the game's line-minus glyph (three stops on a line, one marked with a minus)
    redrawn as vectors on an amber disc, in the style of the faces."""
    k = r * 1.9 / 64                       # the glyph is drawn on a 64 x 64 grid, centred on (32, 32)
    g = lambda x, y: f"{cx + (x - 32) * k:.1f} {cy + (y - 32) * k:.1f}"
    circles = "".join(f'<circle cx="{cx + (x - 32) * k:.1f}" cy="{cy + (y - 32) * k:.1f}" r="{rr * k:.1f}" fill="{INK}"/>'
                      for x, y, rr in ((16, 16, 8), (45, 19, 10), (48, 48, 8)))
    line = (f'<path d="M {g(27, 17)} C {g(31, 22)} {g(31, 28)} {g(30, 33)} C {g(29, 40)} {g(31, 45)} {g(36, 48)}" fill="none" '
            f'stroke="{INK}" stroke-width="{6.2 * k:.1f}" stroke-linecap="round"/>')
    minus = (f'<rect x="{cx + (37.5 - 32) * k:.1f}" y="{cy + (16.2 - 32) * k:.1f}" width="{15 * k:.1f}" height="{5.2 * k:.1f}" '
             f'rx="{k:.1f}" fill="{AMBER}"/>')
    return f'''<g filter="url(#shadow)">
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="{AMBER}" stroke="#fff" stroke-width="7"/>
  {circles}{line}{minus}
</g>'''


def also_includes():
    """Upper right, below the version number: the mod's other features, one row each (icon and name), right-aligned."""
    right = W - 56
    out = [f'<text x="{right}" y="{172 - LIFT}" text-anchor="end" font-family="Lato" font-weight="800" font-size="24" '
           f'fill="{AMBER}" letter-spacing="5">ALSO INCLUDES</text>']
    y = 232 - LIFT
    for text in ("Stale line warnings",):
        out.append(f'<text x="{right}" y="{y + 12}" text-anchor="end" font-family="Lato" font-weight="700" font-size="36" '
                   f'fill="#fff" fill-opacity=".88">{text}</text>')
        out.append(warning_badge(right - 362, y, 34))
        y += 84
    return "\n".join(out)


FLOOR = 960   # ground line of the scene; the captions go below it


def fresh_stack():
    """Fresh goods, left of centre: closed boxes and crates behind, open crates of lettuce, meat and fish in front."""
    g = FLOOR                     # floor line of the front row
    bk = g - 50                   # floor line of the back row (further away)
    w, h = 220, 145
    out = [f'<ellipse cx="1040" cy="{g + 6}" rx="420" ry="26" fill="#000" opacity=".35"/>']
    # back row, two high, with one box on top
    out += [box(820, bk, w, h, .3), crate(1040, bk, w, h, dark=.3), box(1260, bk, w, h, .3),
            crate(930, bk - h, w, h, dark=.3), box(1150, bk - h, w, h, .3),
            box(1040, bk - 2 * h, w - 20, h - 10, .3)]
    # front row, open
    top = g - h
    veg = "".join(lettuce(930 + dx, top + dy, r) for dx, dy, r in ((-58, -12, 44), (58, -10, 44), (0, -40, 48)))
    meat = (steak(1150 - 52, top - 14, 1.0, -14, shape=1) + steak(1150 + 56, top - 10, 1.0, 16)
            + steak(1150, top - 46, 1.05, 4, shape=1))
    fsh = (fish(710 - 30, top - 14, 1.15, 10) + fish(710 + 40, top - 24, 1.15, -12) + fish(710, top - 56, 1.2, 4))
    out += [crate(710, g, w, h, fsh), crate(930, g, w, h, veg), crate(1150, g, w, h, meat)]
    out.append(face(720, bk - 2 * h + 5, 64, "happy"))
    return f'<g transform="translate(-500 0)">{"".join(out)}</g>'


def garbage():
    """Spoiled goods on the right, where the curve falls to no pay: an overflowing bin and a pile beside it,
    drawn 1.15x so it weighs about the same as the fresh stack."""
    cx, g, w, h, k = 1581, FLOOR, 210, 250, 1.15
    top = g - h
    inside = (lettuce(cx - 50, top - 8, 46, spoiled=True) + fish(cx + 30, top - 30, 1.15, -28, spoiled=True)
              + steak(cx + 62, top - 4, .95, 30, spoiled=True))
    out = [f'<ellipse cx="{cx - 40}" cy="{g + 6}" rx="230" ry="26" fill="#000" opacity=".35"/>',
           f'<ellipse cx="{cx - 150}" cy="{g - 4}" rx="110" ry="18" fill="#4d5a2a" opacity=".55"/>',
           stink(cx - 20, top - 70),
           bin_(cx, g, w, h, inside),
           # spilled over the rim and on the ground
           fish(cx - 92, top + 40, 1.1, -62, spoiled=True),
           steak(cx - 200, g - 26, 1.0, -8, spoiled=True, shape=1),
           lettuce(cx - 115, g - 34, 40, spoiled=True)]
    scaled = f'<g transform="translate({cx} {g}) scale({k}) translate({-cx} {-g})">{"".join(out)}</g>'
    return scaled + face(cx + 150 * k + 20, g - (h + 90) * k, 64, "sad")


def caption(cx, text):
    return (f'<text x="{cx}" y="{FLOOR + 88}" text-anchor="middle" font-family="Lato" font-weight="700" font-size="42" '
            f'fill="#fff" fill-opacity=".88">{text}</text>')


def time_arrow(x0, x1, y):
    """Dashed arrow from the fresh stack to the bin, with an hourglass: cargo goes this way as it ages."""
    mid = (x0 + x1) / 2
    hx, hy = mid, y - 64
    ex = x1 - 8
    ang = math.degrees(math.atan2(34, ex - mid))   # the curve's direction where it ends, so the head follows it
    tx, ty = ex + 12 * math.cos(math.radians(ang)), y + 12 * math.sin(math.radians(ang))
    return f'''<g opacity=".6">
  <path d="M {x0} {y} Q {mid} {y - 34} {ex} {y}" fill="none" stroke="#fff" stroke-width="6" stroke-dasharray="14 11" stroke-linecap="round"/>
  <path d="M {tx - 32:.1f} {ty - 19:.1f} L {tx:.1f} {ty:.1f} L {tx - 32:.1f} {ty + 19:.1f}" transform="rotate({ang:.1f} {tx:.1f} {ty:.1f})" fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
  <g transform="translate({hx} {hy})">
    <line x1="-18" y1="-26" x2="18" y2="-26" stroke="#fff" stroke-width="6" stroke-linecap="round"/>
    <line x1="-18" y1="26" x2="18" y2="26" stroke="#fff" stroke-width="6" stroke-linecap="round"/>
    <path d="M -13 -26 L 13 -26 L 2 0 L 13 26 L -13 26 L -2 0 Z" fill="none" stroke="#fff" stroke-width="5" stroke-linejoin="round"/>
    <path d="M -6 20 L 6 20 L 0 10 Z" fill="#fff"/>
  </g>
</g>'''


def build(version=None):
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        f'''<defs>
  {BACKGROUND_DEFS}
  <filter id="shadow" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="6" stdDeviation="7" flood-color="#000" flood-opacity=".45"/></filter>
</defs>''',
        background(),
        f'<g filter="url(#shadow)"><text x="70" y="{250 - LIFT}" font-family="Lato" font-weight="900" font-size="196" fill="#fff" letter-spacing="2">BEST BEFORE</text></g>',
        f'<text x="78" y="{345 - LIFT}" font-family="Lato" font-weight="800" font-size="70" fill="{AMBER}" letter-spacing="12">CARGO FRESHNESS</text>',
        also_includes(),
        fresh_stack(),
        time_arrow(958, 1203, FLOOR - 140),
        garbage(),
        caption(480, "Fresh cargo earns a bonus."),
        caption(1546, "Spoiled cargo earns nothing."),
    ]
    if version:  # upper right corner, kept clear for it
        parts.append(f'<text x="{W - 56}" y="72" text-anchor="end" font-family="Lato" font-weight="700" font-size="54" fill="#fff" fill-opacity=".85">v{version}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def main():
    args = sys.argv[1:]
    version = None
    if "--version" in args:
        i = args.index("--version")
        version = args[i + 1]
        del args[i:i + 2]
    keep_svg = None
    if "--keep-svg" in args:
        i = args.index("--keep-svg")
        keep_svg = Path(args[i + 1])
        del args[i:i + 2]
    metadata = Path(__file__).resolve().parent.parent / "best_before_1/_metadata"
    out = Path(args[0]) if args else metadata / "0.jpg"
    from PIL import Image
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "preview.svg", Path(tmp) / "preview.png"
        svg.write_text(build(version))
        if keep_svg:
            keep_svg.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(svg, keep_svg)
        subprocess.run(["rsvg-convert", "-w", str(W), "-h", str(H), "-o", str(png), str(svg)], check=True)
        Image.open(png).convert("RGB").save(out, quality=92, optimize=True, progressive=True)
    print(out)
    if not args:
        shutil.copyfile(out, metadata / "1-cover.jpg")
        print(metadata / "1-cover.jpg")


if __name__ == "__main__":
    main()
