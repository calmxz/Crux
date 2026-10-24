"""Generate frontend/public/favicon.ico from the Logo mark geometry.

Pillow cannot rasterise SVG, and cairosvg needs a cairo DLL that is not
present on Windows, so this script draws the mark directly with
ImageDraw at a supersampled size and downscales with LANCZOS for each
target icon size. Colours are the light (non-dark-mode) variant only,
since .ico has no media-query support.

Run, from the repo root:
    uv run --no-project --with pillow python frontend/scripts/gen-favicon.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

INK = (27, 27, 26, 255)  # #1b1b1a
TAB = (184, 53, 44, 255)  # #b8352c

SUPERSAMPLE = 512
SCALE = SUPERSAMPLE / 32
SIZES = [16, 32, 48]

OUT_PATH = Path(__file__).resolve().parent.parent / "public" / "favicon.ico"


def s(v):
    return v * SCALE


def draw_mark(img):
    draw = ImageDraw.Draw(img)

    # Red tab: rounded-top quadrilateral above the rect, y from 5.5 to 9.5,
    # x from 3.5 to 14.5, with rx=2 corners at the top (approximated as a
    # rounded rectangle covering the tab region, then squared off at the
    # bottom where it meets the card rect).
    tab_x0, tab_y0 = 3.5, 5.5
    tab_x1, tab_y1 = 14.5, 9.5
    draw.rounded_rectangle(
        [s(tab_x0), s(tab_y0), s(tab_x1), s(tab_y1) + s(2)],
        radius=s(2),
        fill=TAB,
    )
    # Square off the bottom overhang so the tab does not bulge past y=9.5.
    draw.rectangle([s(tab_x0), s(tab_y1), s(tab_x1), s(tab_y1) + s(2)], fill=(0, 0, 0, 0))
    draw.rectangle(
        [s(tab_x0) - 1, s(tab_y0), s(tab_x1) + 1, s(tab_y1)],
        fill=TAB,
    )

    # Card outline: rect 25x19 at (3.5, 9.5), rx=2, stroke width 2.5.
    rect_x0, rect_y0 = 3.5, 9.5
    rect_x1, rect_y1 = rect_x0 + 25, rect_y0 + 19
    stroke_w = s(2.5)
    draw.rounded_rectangle(
        [s(rect_x0), s(rect_y0), s(rect_x1), s(rect_y1)],
        radius=s(2),
        outline=INK,
        width=round(stroke_w),
    )

    # Two horizontal text lines, round-capped, stroke width 2.5.
    line_w = round(s(2.5))
    cap_r = line_w / 2

    def round_capped_line(x0, y0, x1, y1):
        draw.line([(x0, y0), (x1, y1)], fill=INK, width=line_w)
        draw.ellipse([x0 - cap_r, y0 - cap_r, x0 + cap_r, y0 + cap_r], fill=INK)
        draw.ellipse([x1 - cap_r, y1 - cap_r, x1 + cap_r, y1 + cap_r], fill=INK)

    round_capped_line(s(9), s(16), s(23), s(16))
    round_capped_line(s(9), s(21.5), s(17), s(21.5))


def main():
    img = Image.new("RGBA", (SUPERSAMPLE, SUPERSAMPLE), (0, 0, 0, 0))
    draw_mark(img)

    largest = max(SIZES)
    base = img.resize((largest, largest), Image.LANCZOS)
    base.save(
        OUT_PATH,
        format="ICO",
        sizes=[(size, size) for size in SIZES],
    )

    print(f"[OK] wrote {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")
    with Image.open(OUT_PATH) as check:
        print(f"[OK] sizes in ico: {check.info.get('sizes')}")


if __name__ == "__main__":
    main()
