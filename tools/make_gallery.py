"""Draw the listing's second gallery image (1920x1080 JPG): the mod's settings at their defaults, as a screenshot of the dialog's
Settings box, with each group of settings explained beside it. The dialog shows no tooltips for mod settings, so this image
and the description are where a player learns what they do. The background is the cover's (tools/make_preview.py) with its
grid but not its curve, which would run through the text.

The source is a full 3840x2160 screenshot kept in art/gallery/ (outside the mod folder, so it does not ship): the settings
dialog on a save that never had the mod (Load Game > Mods > Activate > gear, 30 Oct 2026). The tool cuts CROP from it, the
dialog's title and Settings box; a new shot of the same dialog at the same resolution keeps the setting rows where GROUPS
expects them. The same cut, scaled down, is the settings image in docs/changing-settings.md, which the tool also writes.

Usage: python3 tools/make_gallery.py [OUT_FILE] [--shot SCREENSHOT.png]
OUT_FILE defaults to best_before_1/_metadata/2-settings.jpg (the gallery's second image, see docs/publishing.md), SCREENSHOT.png to SHOT. Needs rsvg-convert and Lato.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_preview  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
W, H = make_preview.W, make_preview.H
AMBER = make_preview.AMBER
RADIUS = 22  # the dialog's rounded corners, in screenshot pixels

SHOT = ROOT / "art/gallery/settings-defaults-20261030-082413.png"
CROP = (567, 278, 1280, 1411)  # in the screenshot: the dialog's title and Settings box
DOCS_IMAGE, DOCS_SCALE = ROOT / "docs/images/mod-settings-dialog.png", 0.6
CARD_X, CARD_Y, CARD_H = 60, 40, 1000
TEXT_X, TEXT_W = 830, 1040
BRACKET_X = 722  # the brackets beside the screenshot; an S-curve joins each to its note's heading
FONTS = Path("/usr/share/fonts/truetype/lato")

HEAD_SIZE, BODY_SIZE, BODY_LEAD = 34, 28, 39
HEAD_GAP = 46  # heading baseline to the first body line's baseline
BOTTOM = H - 40  # the last note ends here

# Each group: the rows it covers in the cut (top, bottom, in screenshot pixels from the top of CROP), its heading and its text.
GROUPS = [
    (285, 725, "THE PAY CURVE",
     "Fresh cargo earns 120% of normal pay down to 40% freshness. Below that, pay falls in a straight line to normal pay at "
     "20%, then on to the lowest pay (nothing) at 0%. Spoiled cargo earns the spoiled pay, also nothing. Freshness is 100% "
     "at pickup and falls to 0% at the cargo's delivery limit."),
    (745, 875, "STALE CARGO WARNINGS",
     "A line that delivers mostly cargo below 10% freshness, or spoiled cargo, for several months gets a warning. Pay is not "
     "affected. Untick the box to turn the warnings off."),
    (895, 1100, "NON-PERISHABLE CARGO",
     "Cargo with a base delivery time of 25 min or more (everything but food) gets half the bonus, so 110% at most, and the "
     "full penalties. The other choices are Full\u00a0bonus, No\u00a0bonus and No\u00a0effect."),
]
TITLE = "3 SETTING CATEGORIES"
SUBTITLE = ("Set them under Mods (the gear next to the mod) in New Game or Load Game.",  # one line each, wrapped apart
            "Shown at their defaults. Settings are stored in the save; change them on any load.")


def wrap(text, size, width, weight="Regular"):
    font = ImageFont.truetype(str(FONTS / f"Lato-{weight}.ttf"), size)
    lines, line = [], ""
    for word in text.split(" "):  # not at the no-break spaces that keep a choice's name together
        trial = f"{line} {word}".strip()
        if font.getlength(trial) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line]


def text_block(x, y, lines, size, lead, attrs):
    spans = "".join(f'<tspan x="{x}" y="{y + i * lead}">{line}</tspan>' for i, line in enumerate(lines))
    return f'<text font-family="Lato" font-size="{size}" {attrs}>{spans}</text>'


def notes(scale):
    out = [f'<text x="{TEXT_X}" y="128" font-family="Lato" font-weight="800" font-size="62" fill="{AMBER}" letter-spacing="8">{TITLE}</text>']
    sub = [line for part in SUBTITLE for line in wrap(part, BODY_SIZE, TEXT_W)]
    out.append(text_block(TEXT_X, 186, sub, BODY_SIZE, BODY_LEAD, 'fill="#fff" fill-opacity=".8"'))
    # The notes share the space under the subtitle in even gaps; a line from each bracket's middle leads to its heading.
    blocks = []
    for top, end, head, body in GROUPS:
        lines = wrap(body, BODY_SIZE, TEXT_W)
        height = HEAD_SIZE + HEAD_GAP + (len(lines) - 1) * BODY_LEAD + 10
        blocks.append((CARD_Y + top * scale, CARD_Y + end * scale, head, lines, height))
    start = 186 + len(sub) * BODY_LEAD
    gap = (BOTTOM - start - sum(b[4] for b in blocks)) / (len(blocks) + 1)
    if gap < 24:
        sys.exit("the notes do not fit under the title; shorten them")
    top = start + gap
    for y0, y1, head, lines, height in blocks:
        y = top + HEAD_SIZE  # the heading's baseline
        mid, cap = (y0 + y1) / 2, y - HEAD_SIZE * 0.36  # the bracket's middle, the middle of the heading's capitals
        line = f'fill="none" stroke="{AMBER}" stroke-opacity=".7" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"'
        # The bracket along the rows the group covers, its ends turned towards the screenshot.
        out.append(f'<path d="M {BRACKET_X - 14} {y0:.0f} H {BRACKET_X} V {y1:.0f} H {BRACKET_X - 14}" {line}/>')
        x0, x1 = BRACKET_X, TEXT_X - 18
        out.append(f'<path d="M {x0} {mid:.0f} C {x0 + (x1 - x0) * 0.6:.0f} {mid:.0f} {x1 - (x1 - x0) * 0.6:.0f} {cap:.0f} {x1} {cap:.0f}" {line}/>')
        out.append(f'<text x="{TEXT_X}" y="{y:.0f}" font-family="Lato" font-weight="800" font-size="{HEAD_SIZE}" fill="{AMBER}" '
                   f'letter-spacing="4">{head}</text>')
        out.append(text_block(TEXT_X, round(y + HEAD_GAP), lines, BODY_SIZE, BODY_LEAD, 'fill="#fff"'))
        top += height + gap
    return "\n".join(out)


def card(im):
    im = im.convert("RGBA")
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, im.width - 1, im.height - 1), RADIUS, fill=255)
    im.putalpha(mask)
    scale = CARD_H / im.height
    return im.resize((round(im.width * scale), CARD_H), Image.LANCZOS), scale


def render(svg_body):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
           f'<defs>{make_preview.BACKGROUND_DEFS}</defs>{svg_body}</svg>')
    with tempfile.TemporaryDirectory() as tmp:
        src, png = Path(tmp) / "gallery.svg", Path(tmp) / "gallery.png"
        src.write_text(svg)
        subprocess.run(["rsvg-convert", "-w", str(W), "-h", str(H), "-o", str(png), str(src)], check=True)
        return Image.open(png).convert("RGBA")


def main():
    args = sys.argv[1:]
    shot = SHOT
    if "--shot" in args:
        i = args.index("--shot")
        shot = Path(args[i + 1])
        del args[i:i + 2]
    out = Path(args[0]) if args else ROOT / "best_before_1/_metadata/2-settings.jpg"
    cut = Image.open(shot).convert("RGB").crop(CROP)
    cut.resize((round(cut.width * DOCS_SCALE), round(cut.height * DOCS_SCALE)), Image.LANCZOS).save(DOCS_IMAGE, optimize=True)
    print(DOCS_IMAGE)
    c, scale = card(cut)
    image = render(make_preview.background(curve=False) + notes(scale))
    # The preview's drop shadow (its "shadow" filter): 6 pixels down, blur 7, black at 45%.
    shadow = Image.new("RGBA", c.size, (0, 0, 0, 0))
    shadow.putalpha(c.getchannel("A").point(lambda a: a * 0.45))
    image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(7)), (CARD_X, CARD_Y + 6))
    image.alpha_composite(c, (CARD_X, CARD_Y))
    out.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(out, quality=92, optimize=True, progressive=True)
    print(out)


if __name__ == "__main__":
    main()
