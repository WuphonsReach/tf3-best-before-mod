"""Draw the gallery image that answers "what do I set the Non-perishable delivery time to?" (1920x1080 JPG), in the cover's style.

One bar per cargo type, in the order and the colours of the game's company window > Delivery Time tab (tallest on the left),
each with the game's own icon. The bar heights follow the cargo files' base delivery times (`timeToDeliverInSeconds`) but the
chart has no time scale on purpose: the tab shows those times multiplied by a factor that falls with the game year (1.5 in 1900,
0.75 from 2020), while the mod's setting compares the base time, so the slider values it prints do not change with the year.
A cargo is perishable when its base time is below the slider value (probe.script.tl: `fileSeconds < nonPerishableSeconds`),
so for each step between two delivery-time classes the image prints the slider values that put everything to its right in the
perishable group, worked out from the data and the slider's range in mod.json.

The data is kept in the repo, not read from the game: art/delivery-times/cargos.json (name, `order`, `timeToDeliverInSeconds` and
`color` of every cargo file in base/content/cargos, passengers left out) and icons/<id>.png (the 48 px icon of each cargo
file). The bar colours are the files' `color` x 255; they equal the bars in a 25 Oct 2026 screenshot of the tab. `--extract GAME_DIR`
rebuilds both from the game folder (the one that holds base/content/cargos); the picture itself ships no game files beyond
those icons and colours.

Usage: python3 tools/make_delivery_times.py [OUT_FILE] [--extract GAME_DIR]
OUT_FILE defaults to best_before_1/_metadata/3-non-perishable-slider.jpg. Needs rsvg-convert and Lato.
"""
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_preview  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "art/delivery-times"
W, H = make_preview.W, make_preview.H
AMBER = make_preview.AMBER
DEFAULT_MIN = make_preview.SHOWN_DEFAULTS["nonPerishableMinutes"]

# The slider in mod.json: 15 to 75 minutes in 5 minute steps.
SLIDER = list(range(15, 76, 5))

X_LEFT, SLOT, GROUP_GAP = 94, 44, 14
BASE_Y, MAX_BAR, BAR_W, ICON = 770, 470, 28, 38


def extract(game):
    """Rebuild art/delivery-times from the game folder's cargo archives."""
    from PIL import Image as _I
    import io
    rows = []
    (DATA / "icons").mkdir(parents=True, exist_ok=True)
    for z in sorted((Path(game) / "base/content/cargos").glob("*.zip")):
        with zipfile.ZipFile(z) as zf:
            lua = [n for n in zf.namelist() if n.endswith(".cargo.lua")]
            if not lua:
                continue
            text = zf.read(lua[0]).decode()
            cid = Path(lua[0]).name.split(".")[0]
            if cid == "passengers":
                continue
            icon = next(n for n in zf.namelist() if n.endswith("@2x.tga"))
            _I.open(io.BytesIO(zf.read(icon))).convert("RGBA").save(DATA / "icons" / f"{cid}.png")
            rows.append({
                "id": cid,
                "name": re.search(r'name\s*=\s*_\("([^"]+)"', text).group(1),
                "order": int(re.search(r"order\s*=\s*(\d+)", text).group(1)),
                "seconds": int(re.search(r"timeToDeliverInSeconds\s*=\s*(\d+)", text).group(1)),
                "color": [float(x) for x in re.search(r"color\s*=\s*\{([^}]*)\}", text).group(1).split(",")],
            })
    rows.sort(key=lambda r: r["order"])
    (DATA / "cargos.json").write_text(json.dumps(rows, indent=1) + "\n")
    print(f"{len(rows)} cargos written to {DATA}")


def hexcolor(c):
    return "#%02x%02x%02x" % tuple(round(x * 255) for x in c)


def slider_range(perishable_max, kept_min):
    """Slider values v (minutes) with perishable_max < 60 v <= kept_min: the cargo below the cut is perishable, the rest is not."""
    return [v for v in SLIDER if perishable_max < v * 60 <= kept_min]


def span(values):
    return str(values[0]) if len(values) == 1 else f"{values[0]}–{values[-1]}"


def layout(cargos):
    """Bars in the game's order (longest base time first, then the later cargo file first), with a gap after each class."""
    bars = sorted(cargos, key=lambda c: (-c["seconds"], -c["order"]))
    x, out, cuts = X_LEFT, [], []
    for i, c in enumerate(bars):
        if i and c["seconds"] != bars[i - 1]["seconds"]:
            x += GROUP_GAP
            cuts.append((x - GROUP_GAP / 2 - 2, bars[i]["seconds"], bars[i - 1]["seconds"]))
        out.append((x + SLOT / 2, c))
        x += SLOT
    return out, cuts, x


def build():
    cargos = json.loads((DATA / "cargos.json").read_text())
    bars, cuts, x_end = layout(cargos)
    s = [make_preview.background(curve=False)]
    s.append(f'<text x="80" y="104" font-family="Lato" font-weight="800" font-size="60" fill="{AMBER}" letter-spacing="8">'
             "WHERE TO SET THE NON-PERISHABLE SLIDER</text>")
    sub = ["Cargo whose base delivery time is below the slider is perishable and gets the full pay curve.",
           "Pick the line just left of the first cargo you want perishable; every cargo to its right is perishable too."]
    for i, line in enumerate(sub):
        s.append(f'<text x="80" y="{156 + i * 36}" font-family="Lato" font-size="27" fill="#fff" fill-opacity=".85">{line}</text>')

    default_x = None
    chip_rows = {}
    for x, perish, kept in cuts:
        v = slider_range(perish, kept)
        chip_rows[x] = v
        if DEFAULT_MIN in v:
            default_x = x
    # The default's shaded zone: everything to its right is perishable at the default.
    s.append(f'<rect x="{default_x:.0f}" y="262" width="{x_end - default_x + 12:.0f}" height="{BASE_Y + 168 - 262}" rx="10" fill="#fff" fill-opacity=".06"/>')
    # The baseline.
    s.append(f'<line x1="{X_LEFT - 14}" x2="{x_end + 6}" y1="{BASE_Y}" y2="{BASE_Y}" stroke="#fff" stroke-opacity=".35" stroke-width="2"/>')
    # Bars, then the names under the icons.
    for x, c in bars:
        h = MAX_BAR * c["seconds"] / 4500
        s.append(f'<rect x="{x - BAR_W / 2:.1f}" y="{BASE_Y - h:.1f}" width="{BAR_W}" height="{h:.1f}" rx="2" fill="{hexcolor(c["color"])}"/>')
        s.append(f'<text transform="translate({x + 5:.1f} {BASE_Y + ICON + 20}) rotate(-90)" text-anchor="end" font-family="Lato" '
                 f'font-size="17" fill="#fff" fill-opacity=".85" dy="0">{c["name"]}</text>')
    # The cuts: a line, and a chip with the slider values that put everything right of it in the perishable group.
    for k, (x, perish, kept) in enumerate(cuts):
        v = chip_rows[x]
        is_default = x == default_x
        label = span(v) + " min" if v else "no setting"
        row = 1 if is_default else 0
        cw = 14 + 11.5 * len(label)
        cy = 300 + row * 0  # all chips sit on the same band, except the default, which sits above it
        cy = 232 if is_default else 292
        if len(v) == 0:
            fill, stroke, txt = "#1b2a3f", "#8896a8", "#a8b3c2"
        elif is_default:
            fill, stroke, txt = AMBER, AMBER, make_preview.INK
        else:
            fill, stroke, txt = "#1b2a3f", AMBER, "#fff"
        dash = "" if is_default else ' stroke-dasharray="7 7"'
        s.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{cy + 16}" y2="{BASE_Y + 6}" stroke="{AMBER if v else "#8896a8"}" '
                 f'stroke-opacity="{1 if is_default else .65}" stroke-width="{4 if is_default else 2.5}"{dash}/>')
        s.append(f'<rect x="{x - cw / 2:.1f}" y="{cy - 16}" width="{cw:.1f}" height="32" rx="16" fill="{fill}" stroke="{stroke}" stroke-width="2.5"/>')
        s.append(f'<text x="{x:.1f}" y="{cy + 7}" text-anchor="middle" font-family="Lato" font-weight="800" font-size="21" fill="{txt}">{label}</text>')
    s.append(f'<text x="{default_x:.0f}" y="{232 - 28}" text-anchor="middle" font-family="Lato" font-weight="800" font-size="19" fill="{AMBER}" letter-spacing="2">DEFAULT</text>')
    s.append(f'<rect x="{(default_x + x_end) / 2 - 100:.0f}" y="528" width="200" height="68" rx="10" fill="#1b2a3f" fill-opacity=".92"/>')
    s.append(f'<text x="{(default_x + x_end) / 2:.0f}" y="560" text-anchor="middle" font-family="Lato" font-weight="800" font-size="24" fill="#fff" letter-spacing="2">'
             f'<tspan x="{(default_x + x_end) / 2:.0f}">PERISHABLE</tspan><tspan x="{(default_x + x_end) / 2:.0f}" dy="30" font-weight="400" font-size="22">at the default</tspan></text>')
    s.append(f'<text x="{X_LEFT}" y="{BASE_Y - MAX_BAR - 56}" font-family="Lato" font-weight="800" font-size="24" fill="#fff" fill-opacity=".75" letter-spacing="2">'
             "NOT PERISHABLE AT THE DEFAULT</text>")
    # Notes under the chart.
    lo = SLIDER[0]
    notes = [f"At {lo} min nothing is perishable. The next step, {lo + 5} min, makes meat, fish, vegetables and beverages perishable, so meat cannot be picked on its own.",
             f"Sand, steel, iron ore and stone take {SLIDER[-1]} min, the top of the slider, so they are never perishable.",
             "Bar heights follow the cargo files' base delivery times. Those do not change with the year; the game's Delivery Time tab displays "
             "them at 150% in 1900, falling to 75% in 2020."]
    for i, line in enumerate(notes):
        s.append(f'<text x="80" y="{978 + i * 33}" font-family="Lato" font-size="22" fill="#fff" fill-opacity=".8">{line}</text>')
    return "\n".join(s), bars


def main():
    args = sys.argv[1:]
    if "--extract" in args:
        i = args.index("--extract")
        extract(args[i + 1])
        del args[i:i + 2]
        if not args:
            return
    out = Path(args[0]) if args else ROOT / "best_before_1/_metadata/3-non-perishable-slider.jpg"
    body, bars = build()
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
           f'<defs>{make_preview.BACKGROUND_DEFS}</defs>{body}</svg>')
    with tempfile.TemporaryDirectory() as tmp:
        src, png = Path(tmp) / "dt.svg", Path(tmp) / "dt.png"
        src.write_text(svg)
        subprocess.run(["rsvg-convert", "-w", str(W), "-h", str(H), "-o", str(png), str(src)], check=True)
        image = Image.open(png).convert("RGBA")
    for x, c in bars:
        ic = Image.open(DATA / "icons" / f"{c['id']}.png").convert("RGBA").resize((ICON, ICON), Image.LANCZOS)
        image.alpha_composite(ic, (round(x - ICON / 2), BASE_Y + 8))
    out.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(out, quality=92, optimize=True, progressive=True)
    print(out)


if __name__ == "__main__":
    main()
