"""
Makes the poster QR codes: a pig-snout version and a wolf version.

Needs: pip install segno cairosvg   (cairosvg also needs the cairo library, e.g. brew install cairo)
Run:   python make_qr.py

The QR uses error level H, so it still scans with up to ~30% of it covered.
The picture in the middle only covers about 6%, which leaves plenty of room
for scuffs and glare on a printed poster.
"""

import math
import segno
import cairosvg

URL = "https://ritcanstruction.org/sponsors/?src=qr"
INK = "#1A1A1A"
UNIT = 10       # svg units per QR square
BORDER = 4      # white margin, in squares (4 is the QR standard)
HOLE = 6.3      # radius of the cleared circle in the middle, in squares

# ---------- pictures for the middle (drawn around the center point 0,0) ----------
PIG_SNOUT = """
  <ellipse cx="0" cy="3" rx="46" ry="35" fill="#F7B6C8" stroke="#E88AA4" stroke-width="5"/>
  <ellipse cx="-15" cy="3" rx="8" ry="13" fill="#9C4560"/>
  <ellipse cx="15" cy="3" rx="8" ry="13" fill="#9C4560"/>
  <ellipse cx="-20" cy="-17" rx="11" ry="5" fill="#fff" opacity=".6"/>
"""

# same wolf as on the sponsor page (its drawing is 120 x 110, so shift it to center on 0,0)
WOLF_HEAD = """
  <g transform="scale(0.86) translate(-60 -58)">
    <path d="M26 42 L28 6 L52 32 Z" fill="#5E6670"/>
    <path d="M31 35 L32 17 L45 31 Z" fill="#E8A7B5"/>
    <path d="M50 32 L66 4 L76 36 Z" fill="#5E6670"/>
    <path d="M56 31 L65 14 L70 33 Z" fill="#E8A7B5"/>
    <ellipse cx="50" cy="62" rx="38" ry="34" fill="#7C8590"/>
    <path d="M16 66 L2 76 L16 80 L8 92 L28 88 Z" fill="#7C8590"/>
    <path d="M70 50 Q108 52 114 64 Q112 80 76 86 Z" fill="#A9B1BA"/>
    <ellipse cx="111" cy="62" rx="7" ry="6" fill="#1A1A1A"/>
    <circle cx="80" cy="80" r="10" fill="#C3C9D0"/>
    <circle cx="104" cy="79" r="3.5" fill="#3A2A2A"/>
    <ellipse cx="62" cy="50" rx="8" ry="7" fill="#fff"/>
    <circle cx="65" cy="51" r="3.6" fill="#1A1A1A"/>
    <path d="M52 40 L74 46" stroke="#2E3338" stroke-width="4" stroke-linecap="round"/>
    <path d="M30 90 Q50 106 72 92 L66 104 Q50 112 34 104 Z" fill="#C3C9D0"/>
  </g>
"""

VERSIONS = {
    "pig": {"art": PIG_SNOUT, "ring": "#E88AA4", "pupil": "#B03A63"},
    "wolf": {"art": WOLF_HEAD, "ring": "#7C8590", "pupil": "#C75300"},
}


def build_svg(matrix, art, ring, pupil):
    n = len(matrix)
    size = (n + 2 * BORDER) * UNIT
    center = size / 2
    finders = [(0, 0), (n - 7, 0), (0, n - 7)]  # top-left, top-right, bottom-left corner squares

    def in_finder(x, y):
        return any(fx <= x < fx + 7 and fy <= y < fy + 7 for fx, fy in finders)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">',
             f'<rect width="{size}" height="{size}" fill="#fff"/>']

    # the little squares (slightly rounded), skipping the corners and the middle hole
    for y, row in enumerate(matrix):
        for x, dark in enumerate(row):
            if not dark or in_finder(x, y):
                continue
            px, py = (x + BORDER) * UNIT, (y + BORDER) * UNIT
            if math.hypot(px + UNIT / 2 - center, py + UNIT / 2 - center) < (HOLE + 0.35) * UNIT:
                continue
            parts.append(f'<rect x="{px}" y="{py}" width="{UNIT}" height="{UNIT}" rx="2.5" fill="{INK}"/>')

    # the three corner "eyes", rounded, with a colored pupil
    for fx, fy in finders:
        px, py = (fx + BORDER) * UNIT, (fy + BORDER) * UNIT
        parts.append(f'<rect x="{px}" y="{py}" width="{7 * UNIT}" height="{7 * UNIT}" rx="18" fill="{INK}"/>')
        parts.append(f'<rect x="{px + UNIT}" y="{py + UNIT}" width="{5 * UNIT}" height="{5 * UNIT}" rx="12" fill="#fff"/>')
        parts.append(f'<rect x="{px + 2 * UNIT}" y="{py + 2 * UNIT}" width="{3 * UNIT}" height="{3 * UNIT}" rx="9" fill="{pupil}"/>')

    # white circle in the middle with the picture on top
    parts.append(f'<circle cx="{center}" cy="{center}" r="{HOLE * UNIT}" fill="#fff" stroke="{ring}" stroke-width="4"/>')
    parts.append(f'<g transform="translate({center} {center})">{art}</g>')
    parts.append("</svg>")
    return "\n".join(parts)


if __name__ == "__main__":
    qr = segno.make(URL, error="h", micro=False, boost_error=False)
    matrix = [list(row) for row in qr.matrix]
    for name, v in VERSIONS.items():
        svg = build_svg(matrix, v["art"], v["ring"], v["pupil"])
        with open(f"sponsors-qr-{name}.svg", "w") as f:
            f.write(svg)
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"sponsors-qr-{name}.png", output_width=1800, output_height=1800)
        print("made", name)
