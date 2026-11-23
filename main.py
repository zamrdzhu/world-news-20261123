#!/usr/bin/env python3
"""World news of Monday 23 November 2026, in one image.

Renders a 1024x1024 PNG front page: one lead story plus 57 sourced stories
from seven regions, drawn with a hand-built 5x7 bitmap font and a stdlib-only
PNG encoder. No network, no randomness, no timestamps in the output: running
it twice produces byte-identical files.

Usage:  python3 main.py            (writes $MAKEFUN_OUTPUT_DIR/entry.png,
                                     or ./out/entry.png when unset)
"""

import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stories import LEAD, SECTIONS, SOURCES, TOTAL_STORIES  # noqa: E402

WIDTH, HEIGHT = 1024, 1024

# ---------------------------------------------------------------- font ----
# 5x7 bitmap font, one glyph per character. Each glyph is 7 rows of 5 cells;
# '#' is ink, '.' is empty. Only the characters the front page uses are
# defined; anything else renders as a blank.
FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "(": ("...##", "..#..", ".#...", ".#...", ".#...", "..#..", "...##"),
    ")": ("##...", "..#..", "...#.", "...#.", "...#.", "..#..", "##..."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "&": (".##..", "#..#.", "#..#.", ".#...", "#.#.#", "#..#.", ".##.#"),
    "%": ("##..#", "##.#.", "...#.", "..#..", ".#...", "#.##.", "#..##"),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "=": (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    "*": (".....", ".#.#.", "..#..", "#####", "..#..", ".#.#.", "....."),
    "#": (".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "@": (".###.", "#...#", "#.###", "#.#.#", "#.#..", "#....", ".###."),
    "_": (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
    "<": ("...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."),
    ">": (".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."),
    "[": (".###.", ".#...", ".#...", ".#...", ".#...", ".#...", ".###."),
    "]": (".###.", "...#.", "...#.", "...#.", "...#.", "...#.", ".###."),
}

BLANK = (".....",) * 7


def text_width(text, scale, spacing=1):
    """Pixel width of text at the given scale."""
    return len(text) * (5 * scale + spacing) - spacing


# -------------------------------------------------------------- canvas ----
def hex_to_rgb(value):
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


class Canvas:
    def __init__(self, width, height, background):
        self.w = width
        self.h = height
        self.px = bytearray(background * (width * height))

    def _set(self, x, y, rgb):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(rgb)

    def rect(self, x, y, w, h, rgb):
        for yy in range(y, y + h):
            base = (yy * self.w + x) * 3
            self.px[base:base + w * 3] = bytes(rgb) * w

    def hline(self, x, y, w, rgb):
        self.rect(x, y, w, 1, rgb)

    def vline(self, x, y, h, rgb):
        self.rect(x, y, 1, h, rgb)

    def circle_outline(self, cx, cy, r, rgb):
        # Midpoint circle, outline only.
        x, y, d = 0, r, 1 - r
        while x <= y:
            for dx, dy in ((x, y), (y, x), (-x, y), (-y, x),
                           (x, -y), (y, -x), (-x, -y), (-y, -x)):
                self._set(cx + dx, cy + dy, rgb)
            if d < 0:
                d += 2 * x + 3
            else:
                d += 2 * (x - y) + 5
                y -= 1
            x += 1

    def text(self, x, y, s, scale, rgb, spacing=1):
        """Draw text with the bitmap font; returns the x after the text."""
        s = s.upper()
        cx = x
        for ch in s:
            glyph = FONT.get(ch, BLANK)
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits[col] == "#":
                        self.rect(cx + col * scale, y + row * scale,
                                  scale, scale, rgb)
            cx += 5 * scale + spacing
        return cx

    def text_right(self, right, y, s, scale, rgb, spacing=1):
        self.text(right - text_width(s, scale, spacing), y, s, scale, rgb,
                  spacing)


# ----------------------------------------------------------------- png ----
def encode_png(canvas):
    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        return out + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    raw = bytearray()
    for y in range(canvas.h):
        raw.append(0)  # filter: none
        start = y * canvas.w * 3
        raw += canvas.px[start:start + canvas.w * 3]
    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


# --------------------------------------------------------------- layout ---
BG = hex_to_rgb("#0B1220")
PANEL = hex_to_rgb("#111C30")
PANEL2 = hex_to_rgb("#16233C")
INK = hex_to_rgb("#E8EEF7")
DIM = hex_to_rgb("#8A97AD")
RULE = hex_to_rgb("#24344F")
ACCENT = hex_to_rgb("#E63946")
GOLD = hex_to_rgb("#F2C14E")

MARGIN = 24
COL_GUT = 16
COL_W = (WIDTH - 2 * MARGIN - COL_GUT) // 2  # 480


def draw_masthead(cv):
    # Kicker.
    cv.text(MARGIN, 18, "THE WORLD IN ONE DAY", 2, ACCENT)
    cv.text_right(WIDTH - MARGIN - 130, 18, "57 STORIES", 2, GOLD)
    # Date, big.
    cv.text(MARGIN, 44, "MONDAY 23 NOVEMBER 2026", 4, INK)
    # Globe: circle with meridians, top right.
    cx, cy, r = WIDTH - 78, 58, 36
    cv.circle_outline(cx, cy, r, DIM)
    cv.circle_outline(cx, cy, r - 12, DIM)
    for dy in (-18, 0, 18):
        cv.hline(cx - r + 6, cy + dy, 2 * r - 12, DIM)
    for dx in (-18, 0, 18):
        cv.vline(cx + dx, cy - r + 6, 2 * r - 12, DIM)
    # Subtitle.
    cv.text(MARGIN, 86, "57 STORIES FROM SEVEN REGIONS - FIRST REPORTED 23 NOV 2026",
            2, DIM)
    cv.hline(MARGIN, 108, WIDTH - 2 * MARGIN, RULE)


def draw_lead(cv):
    y0, y1 = 116, 228
    cv.rect(MARGIN, y0, WIDTH - 2 * MARGIN, y1 - y0, PANEL)
    cv.rect(MARGIN, y0, 6, y1 - y0, ACCENT)
    cv.text(MARGIN + 20, y0 + 12, LEAD["kicker"], 2, ACCENT)
    cv.text_right(WIDTH - MARGIN - 20, y0 + 12, LEAD["source"], 2, DIM)
    cv.text(MARGIN + 20, y0 + 36, LEAD["headline"], 5, INK)
    cv.text(MARGIN + 20, y0 + 72, LEAD["line1"], 2, INK)
    cv.text(MARGIN + 20, y0 + 92, LEAD["line2"], 2, INK)


def draw_section(cv, y, index, name, colour_hex, stories):
    colour = hex_to_rgb(colour_hex)
    # Header strip.
    cv.rect(MARGIN, y, 8, 24, colour)
    cv.text(MARGIN + 16, y + 5, name, 2, INK)
    cv.text_right(WIDTH - MARGIN, y + 5, "%d STORIES" % len(stories), 2, DIM)
    cv.hline(MARGIN, y + 24, WIDTH - 2 * MARGIN, RULE)
    # Stories in two columns, four rows each.
    row_h = 20
    for i, story in enumerate(stories):
        col = i // 4
        row = i % 4
        x = MARGIN + col * (COL_W + COL_GUT)
        sy = y + 28 + row * row_h
        num = str(index * 8 + i + 2)  # lead story is #1
        # Number chip.
        cv.rect(x, sy, 18, 16, colour)
        cv.text(x + 9 - text_width(num, 1) // 2, sy + 4, num, 1,
                hex_to_rgb("#0B1220"))
        cv.text(x + 24, sy + 1, story, 2, INK)
    return y + 28 + 4 * row_h


def draw_footer(cv):
    y = 996
    cv.hline(MARGIN, y - 6, WIDTH - 2 * MARGIN, RULE)
    cv.text(MARGIN, y, SOURCES, 1, DIM)
    cv.text_right(WIDTH - MARGIN, y, "STDLIB ONLY", 1, DIM)


def render():
    assert TOTAL_STORIES == 57, "expected 57 stories, got %d" % TOTAL_STORIES
    for _name, _colour, stories in SECTIONS:
        assert len(stories) == 8, "each section needs 8 stories"
        for story in stories:
            assert text_width(story, 2) <= COL_W + COL_GUT - 26, story
    cv = Canvas(WIDTH, HEIGHT, BG)
    draw_masthead(cv)
    draw_lead(cv)
    y = 236
    for i, (name, colour, stories) in enumerate(SECTIONS):
        y = draw_section(cv, y, i, name, colour, stories)
    draw_footer(cv)
    return encode_png(cv)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    os.makedirs(out_dir, exist_ok=True)
    data = render()
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as fh:
        fh.write(data)
    print("wrote %s (%d bytes)" % (path, len(data)))


if __name__ == "__main__":
    main()
