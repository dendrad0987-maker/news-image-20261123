#!/usr/bin/env python3
"""The World in One Day -- front page for Monday 23 November 2026.

Draws a complete newspaper front page (masthead, lead story, markets
chart, four more stories, news strip) with the Python standard library
only, and writes it as a PNG. No network, no files read, no randomness:
two runs write byte-identical output.
"""
import math
import os
import struct
import zlib

W, H = 1024, 1024

PAPER = (250, 247, 240)
INK = (18, 18, 18)
SOFT = (70, 66, 60)
RULE = (18, 18, 18)
RED = (176, 28, 28)
BLUE = (28, 62, 118)
SKY = (203, 222, 236)
SEA = (64, 110, 158)
LAND = (86, 140, 88)
SAND = (233, 226, 205)
GREEN = (24, 108, 58)
ORANGE = (214, 96, 20)
FLAME = (226, 84, 20)
GREY = (128, 124, 116)
LIGHT = (236, 232, 222)
PANEL = (243, 239, 230)


def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(path, pixels, w, h):
    """pixels: bytes of RGB rows, top to bottom. Deterministic output."""
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += pixels[y * stride:(y + 1) * stride]
    png = bytearray(b"\x89PNG\r\n\x1a\n")
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)


class Canvas:
    def __init__(self, w, h, color):
        self.w = w
        self.h = h
        self.px = bytearray(color * (w * h))

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def rect(self, x, y, rw, rh, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + rw)
        y1 = min(self.h, y + rh)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:(x1 - x0) * 3 + i] = bytes(color) * (x1 - x0)

    def hline(self, x, y, length, color, thick=1):
        for t in range(thick):
            self.rect(x, y + t, length, 1, color)

    def vline(self, x, y, length, color, thick=1):
        for t in range(thick):
            self.rect(x + t, y, 1, length, color)

    def line(self, x0, y0, x1, y1, color, thick=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            for ox in range(thick):
                for oy in range(thick):
                    self.set(x + ox, y + oy, color)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def disc(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            half = int((r * r - (yy - cy) ** 2) ** 0.5) if abs(yy - cy) <= r else 0
            self.rect(cx - half, yy, half * 2 + 1, 1, color)

    def ring(self, cx, cy, r, color, thick=2):
        for yy in range(cy - r - thick, cy + r + thick + 1):
            for xx in range(cx - r - thick, cx + r + thick + 1):
                d = ((xx - cx) ** 2 + (yy - cy) ** 2) ** 0.5
                if r - thick / 2 <= d <= r + thick / 2:
                    self.set(xx, yy, color)

    def ellipse(self, cx, cy, rx, ry, color, thick=2):
        steps = max(48, int(3.2 * max(rx, ry)))
        for i in range(steps):
            a = 2 * 3.141592653589793 * i / steps
            x = int(cx + rx * math.cos(a))
            y = int(cy + ry * math.sin(a))
            for ox in range(thick):
                for oy in range(thick):
                    self.set(x + ox, y + oy, color)

    def poly(self, pts, color):
        """Scanline fill for a simple polygon."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            nodes = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    nodes.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            nodes.sort()
            for i in range(0, len(nodes) - 1, 2):
                self.rect(int(nodes[i]), y, int(nodes[i + 1]) - int(nodes[i]) + 1, 1, color)

    def dots(self, x, y, rw, rh, color, gap=6):
        for yy in range(y + gap // 2, y + rh, gap):
            for xx in range(x + gap // 2, x + rw, gap):
                self.set(xx, yy, color)

# A 5x7 bitmap font, drawn from scratch for this page. Each glyph is
# seven rows of five pixels, "1" = ink. Headlines set in capitals.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11100", "10010", "10001", "10001", "10001", "10010", "11100"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
}
FONT.update({
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "*": ("00000", "00100", "10101", "01110", "10101", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
})


def glyph_width(scale, tracking):
    return 5 * scale + tracking


def text_width(text, scale, tracking=1):
    if not text:
        return 0
    return len(text) * glyph_width(scale, tracking) - tracking


def draw_text(cv, x, y, text, scale, color, tracking=1):
    """Draw capitals text; unknown chars render as space. Returns width."""
    cx = x
    for ch in text:
        glyph = FONT.get(ch, FONT[" "])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    cv.rect(cx + col * scale, y + row * scale, scale, scale, color)
        cx += glyph_width(scale, tracking)
    return cx - x - tracking


def draw_centered(cv, cx, y, text, scale, color, tracking=1):
    draw_text(cv, cx - text_width(text, scale, tracking) // 2, y, text, scale, color, tracking)


def wrap_text(text, scale, max_width, tracking=1):
    """Greedy word wrap; returns a list of lines that fit max_width."""
    words = text.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale, tracking) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_block(cv, x, y, text, scale, color, max_width, leading, tracking=1):
    """Draw a wrapped block; returns the y just below the last line."""
    line_h = 7 * scale + leading
    for line in wrap_text(text, scale, max_width, tracking):
        draw_text(cv, x, y, line, scale, color, tracking)
        y += line_h
    return y


def draw_globe(cv, x, y, w, h):
    cx, cy = x + w // 2, y + h // 2
    r = min(w, h) // 2 - 6
    cv.disc(cx, cy, r, SKY)
    cv.disc(cx, cy, r - 2, SEA)
    cv.ellipse(cx, cy, int(r * 0.45), r - 2, (140, 178, 205), 2)
    cv.ellipse(cx, cy, int(r * 0.8), r - 2, (140, 178, 205), 2)
    cv.hline(cx - r + 2, cy - r // 3, 2 * r - 4, (140, 178, 205), 2)
    cv.hline(cx - r + 2, cy + r // 3, 2 * r - 4, (140, 178, 205), 2)
    cv.poly([(cx - r + 18, cy - 26), (cx - r + 44, cy - 40), (cx - r + 62, cy - 24),
             (cx - r + 52, cy - 4), (cx - r + 30, cy - 8)], LAND)
    cv.poly([(cx + 8, cy + 6), (cx + 34, cy - 2), (cx + 52, cy + 14),
             (cx + 40, cy + 34), (cx + 14, cy + 30)], LAND)
    cv.poly([(cx - 8, cy + 30), (cx + 6, cy + 24), (cx + 10, cy + 42),
             (cx - 4, cy + 48)], LAND)
    cv.ring(cx, cy, r, INK, 3)
    cv.line(cx - r + 14, cy - r + 30, cx - r + 34, cy - r + 52, RED, 4)
    cv.line(cx - r + 34, cy - r + 52, cx - r + 26, cy - r + 70, RED, 4)
    cv.line(cx - r + 26, cy - r + 70, cx - r + 44, cy - r + 88, RED, 4)
    cv.line(cx + r - 30, cy + r - 34, cx + r - 44, cy + r - 52, RED, 4)
    cv.line(cx + r - 44, cy + r - 52, cx + r - 34, cy + r - 66, RED, 4)


def draw_chart(cv, x, y, w, h):
    cv.rect(x, y, w, h, PANEL)
    rows = [("NIKKEI", "-5.06%", RED, 5.06), ("S&P", "-3.7%", RED, 3.7),
            ("GOLD", "+2.72%", GREEN, 2.72)]
    zero = x + 96 + (w - 96 - 84) // 2
    track = w - 96 - 84
    for i, (name, val, color, mag) in enumerate(rows):
        ry = y + 12 + i * 30
        draw_text(cv, x + 10, ry + 2, name, 2, INK, 1)
        cv.vline(zero, ry, 16, INK, 2)
        length = int(mag / 6.0 * (track // 2))
        if val.startswith("-"):
            cv.rect(zero - length, ry, length, 16, color)
        else:
            cv.rect(zero, ry, length, 16, color)
        draw_text(cv, x + w - 10 - text_width(val, 2, 1), ry + 2, val, 2, color, 1)


def draw_city(cv, x, y, w, h):
    cv.rect(x, y, w, h, (222, 226, 228))
    base = y + h - 8
    cv.rect(x, base, w, 8, INK)
    cv.rect(x + 12, base - 58, 34, 58, INK)
    cv.rect(x + 52, base - 44, 30, 44, SOFT)
    cv.poly([(x + 88, base), (x + 88, base - 66), (x + 100, base - 74),
             (x + 108, base - 62), (x + 118, base - 68), (x + 128, base - 54),
             (x + 128, base)], INK)
    cv.rect(x + 134, base - 52, 30, 52, SOFT)
    cv.rect(x + 170, base - 68, 32, 68, INK)
    for wx in (x + 20, x + 60, x + 142, x + 178):
        cv.rect(wx, base - 48, 8, 8, (222, 226, 228))
    for (sx, sy, sr) in ((x + 108, y + 30, 12), (x + 96, y + 18, 15), (x + 82, y + 12, 10)):
        cv.disc(sx, sy, sr, (150, 148, 142))
    cv.disc(x + 176, y + 20, 10, (240, 220, 120))


def draw_capitol(cv, x, y, w, h):
    cv.rect(x, y, w, h, PANEL)
    base = y + h - 8
    cx = x + w // 2
    cv.rect(x + 16, base, w - 32, 8, INK)
    cv.rect(cx - 58, base - 14, 116, 14, INK)
    cv.rect(cx - 58, base - 46, 116, 32, INK)
    for i in range(6):
        cv.rect(cx - 50 + i * 20, base - 42, 7, 28, PAPER)
    cv.rect(cx - 8, base - 20, 16, 20, PAPER)
    cv.disc(cx, base - 20, 8, PAPER)
    cv.rect(cx - 64, base - 52, 128, 6, INK)
    cv.disc(cx, base - 52, 20, INK)
    cv.rect(cx - 20, base - 54, 40, 6, INK)
    cv.disc(cx, base - 56, 6, PAPER)
    cv.rect(cx - 2, base - 70, 4, 18, INK)
    cv.poly([(cx + 2, base - 70), (cx + 26, base - 64), (cx + 2, base - 58)], RED)


def draw_factory(cv, x, y, w, h):
    cv.rect(x, y, w, h, (222, 226, 228))
    base = y + h - 8
    cv.rect(x, base, w, 8, INK)
    cv.poly([(x + 14, base), (x + 14, base - 52), (x + 44, base - 52),
             (x + 44, base - 34), (x + 74, base - 52), (x + 74, base - 34),
             (x + 104, base - 52), (x + 104, base - 34), (x + 134, base - 52),
             (x + 134, base)], INK)
    cv.rect(x + 146, base - 60, 14, 60, INK)
    cv.rect(x + 142, base - 66, 22, 8, INK)
    for (sx, sy, sr) in ((x + 152, y + 30, 12), (x + 140, y + 20, 14), (x + 128, y + 12, 10)):
        cv.disc(sx, sy, sr, (150, 148, 142))
    cv.poly([(x + 58, base - 26), (x + 66, base - 50), (x + 74, base - 34),
             (x + 82, base - 52), (x + 90, base - 32), (x + 96, base - 44),
             (x + 100, base - 24), (x + 58, base - 24)], FLAME)
    cv.poly([(x + 70, base - 24), (x + 76, base - 40), (x + 84, base - 30),
             (x + 88, base - 38), (x + 90, base - 22)], (240, 200, 60))


def draw_racecar(cv, x, y, w, h):
    cv.rect(x, y, w, h, PANEL)
    ground = y + h - 26
    cv.hline(x + 8, ground, w - 16, INK, 3)
    fx, fy = x + w - 54, y + 12
    for r in range(3):
        for c in range(4):
            cv.rect(fx + c * 10, fy + r * 10, 10, 10, INK if (r + c) % 2 == 0 else PAPER)
    cv.hline(fx, fy, 40, INK, 2)
    cv.hline(fx, fy + 30, 40, INK, 2)
    cv.vline(fx, fy, 30, INK, 2)
    cv.vline(fx + 40, fy, 30, INK, 2)
    cv.line(fx - 4, fy - 6, fx - 4, fy + 44, INK, 3)
    body_y = ground - 22
    cv.poly([(x + 18, body_y), (x + 34, body_y - 10), (x + 78, body_y - 12),
             (x + 118, body_y - 4), (x + 132, body_y), (x + 132, body_y + 10),
             (x + 18, body_y + 10)], RED)
    cv.poly([(x + 52, body_y - 11), (x + 62, body_y - 22), (x + 84, body_y - 22),
             (x + 92, body_y - 11)], INK)
    cv.rect(x + 118, body_y - 20, 22, 5, INK)
    cv.rect(x + 136, body_y - 20, 5, 20, INK)
    cv.disc(x + 44, ground - 2, 13, INK)
    cv.disc(x + 44, ground - 2, 6, PAPER)
    cv.disc(x + 110, ground - 2, 13, INK)
    cv.disc(x + 110, ground - 2, 6, PAPER)
    cv.line(x + 8, ground - 34, x + 30, ground - 34, BLUE, 3)
    cv.line(x + 34, ground - 34, x + 48, ground - 40, BLUE, 3)

FONT["•"] = ("00000", "00000", "01110", "01110", "01110", "00000", "00000")

MARGIN = 36
CW = W - 2 * MARGIN


def kicker(cv, x, y, text, scale=2):
    draw_text(cv, x, y, text, scale, RED, 1)
    return y + 7 * scale + 4


def rule(cv, y, thick=2):
    cv.hline(MARGIN, y, CW, RULE, thick)


def render():
    cv = Canvas(W, H, PAPER)
    # Top line
    draw_text(cv, MARGIN, 20, "MONDAY EDITION", 2, SOFT, 1)
    right = "ONE DAY, ONE PAGE"
    draw_text(cv, W - MARGIN - text_width(right, 2, 1), 20, right, 2, SOFT, 1)
    cv.hline(MARGIN, 40, CW, RULE, 2)
    # Masthead
    draw_centered(cv, W // 2, 52, "THE WORLD IN ONE DAY", 7, INK, 2)
    cv.hline(MARGIN, 112, CW, RULE, 4)
    cv.hline(MARGIN, 118, CW, RULE, 1)
    # Dateline
    draw_centered(cv, W // 2, 130, "MONDAY, 23 NOVEMBER 2026", 4, INK, 2)
    cv.hline(MARGIN, 168, CW, RULE, 2)

    # ---- Lead story: COP31 ----
    y = kicker(cv, MARGIN, 180, "CLIMATE SUMMIT  •  ANTALYA, TURKEY")
    draw_text(cv, MARGIN, y, "COP31 ENDS WITH NO DEAL", 6, INK, 2)
    y += 7 * 6 + 8
    gx, gw = 648, W - MARGIN - 648
    cv.rect(gx, y, gw, 128, PANEL)
    draw_globe(cv, gx + 8, y + 6, gw - 16, 116)
    cap_y = draw_block(cv, gx, y + 134, "DEADLOCK. NO FOSSIL FUEL DEAL.",
                       2, SOFT, gw, 5, 1)
    lx, lw = MARGIN, gx - MARGIN - 16
    dy = draw_block(cv, lx, y, "EU AND ABOUT 130 PARTIES REJECT A DRAFT WITH NO FOSSIL FUEL "
                               "LANGUAGE AFTER TWO DAYS OF OVERTIME TALKS.", 3, INK, lw, 6, 1)
    dy += 4
    dy = draw_block(cv, lx, dy, "THE SUMMIT CLOSED ON SUNDAY WITHOUT AN OVERALL AGREEMENT. "
                                "NEGOTIATORS LEFT THE FOSSIL FUEL QUESTION OPEN AS THE WORLD'S "
                                "LARGEST CLIMATE MEETING ENDED IN DEADLOCK.", 2, INK, lw, 5, 1)
    y = max(cap_y, dy) + 8
    rule(cv, y)
    y += 10

    # ---- Markets band ----
    y = kicker(cv, MARGIN, y, "MARKETS  •  TOKYO AND NEW YORK")
    mx, mw = 560, W - MARGIN - 560
    draw_chart(cv, mx, y - 6, mw, 92)
    draw_text(cv, MARGIN, y, "AI FEARS RATTLE STOCKS", 4, INK, 1)
    y += 7 * 4 + 8
    y = draw_block(cv, MARGIN, y, "NIKKEI FALLS 5.06% AS THE SELL-OFF SPREADS ACROSS ASIA. "
                                  "GOLD RISES 2.72% AS INVESTORS MOVE TO SAFER ASSETS.", 2, INK,
                   mx - MARGIN - 16, 5, 1)
    y += 8
    rule(cv, y)
    y += 10

    # ---- Row A: Ukraine / Washington ----
    col_w = (CW - 24) // 2
    x2 = MARGIN + col_w + 24
    y0 = y
    ya = kicker(cv, MARGIN, y0, "WAR IN UKRAINE  •  KYIV REGION")
    draw_text(cv, MARGIN, ya, "STRIKES KILL 10 NEAR KYIV", 3, INK, 1)
    ya += 7 * 3 + 8
    draw_city(cv, MARGIN, ya, col_w, 84)
    ya += 92
    ya = draw_block(cv, MARGIN, ya, "HOMES HIT IN DYMER. BOY, 7, PULLED ALIVE FROM THE RUBBLE.",
                    2, INK, col_w, 5, 1)
    ya = draw_block(cv, MARGIN, ya, "RUSSIAN STRIKES NORTH OF KYIV KILLED AT LEAST 10 PEOPLE.",
                    2, SOFT, col_w, 5, 1)
    yb = kicker(cv, x2, y0, "WASHINGTON  •  CONGRESS")
    draw_text(cv, x2, yb, "DEMOCRATS TAKE 258 SEATS", 3, INK, 1)
    yb += 7 * 3 + 8
    draw_capitol(cv, x2, yb, col_w, 84)
    yb += 92
    yb = draw_block(cv, x2, yb, "LARGEST HOUSE MAJORITY SINCE 1992, THE ASSOCIATED PRESS REPORTS.",
                    2, INK, col_w, 5, 1)
    yb = draw_block(cv, x2, yb, "DEMOCRATS CLINCHED AT LEAST 258 SEATS IN THE U.S. HOUSE.",
                    2, SOFT, col_w, 5, 1)
    y = max(ya, yb) + 8
    cv.vline(MARGIN + col_w + 12, y0, y - y0 - 8, RULE, 1)
    rule(cv, y)
    y += 12

    # ---- Row B: Indonesia / Sport ----
    y0 = y
    ya = kicker(cv, MARGIN, y0, "DISASTER  •  BANTEN, INDONESIA")
    draw_text(cv, MARGIN, ya, "24 DEAD IN FACTORY FIRE", 3, INK, 1)
    ya += 7 * 3 + 8
    draw_factory(cv, MARGIN, ya, col_w, 66)
    ya += 74
    ya = draw_block(cv, MARGIN, ya, "ABOUT 30 STILL MISSING AFTER THE CANDY PLANT BLAZE.",
                    2, INK, col_w, 5, 1)
    yb = kicker(cv, x2, y0, "SPORT  •  LAS VEGAS")
    draw_text(cv, x2, yb, "VERSTAPPEN WINS IN VEGAS", 3, INK, 1)
    yb += 7 * 3 + 8
    draw_racecar(cv, x2, yb, col_w, 66)
    yb += 74
    yb = draw_block(cv, x2, yb, "HOLDS OFF NORRIS AS MERCEDES FADE LATE IN THE GRAND PRIX.",
                    2, INK, col_w, 5, 1)
    y = max(ya, yb) + 8
    cv.vline(MARGIN + col_w + 12, y0, y - y0 - 8, RULE, 1)
    rule(cv, y)
    y += 10

    # ---- Also today strip ----
    y = kicker(cv, MARGIN, y, "ALSO TODAY")
    strip = ("DELTA OUTAGE DELAYS 1,000+ FLIGHTS  •  WARSHIP SINKS OFF LIBYA  •  "
             "MAYON STIRS FEARS  •  NEPAL PM MEETS MODI  •  IRAN CLAIMS DRONE DOWNED  •  "
             "LIVERPOOL 4-0 MAN UNITED")
    y = draw_block(cv, MARGIN, y, strip, 2, INK, CW, 5, 1)
    return cv


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if not outdir:
        outdir = "/output" if os.path.isdir("/output") else "out"
    os.makedirs(outdir, exist_ok=True)
    cv = render()
    path = os.path.join(outdir, "entry.png")
    write_png(path, bytes(cv.px), W, H)
    print("wrote", path, os.path.getsize(path), "bytes", W, "x", H)


if __name__ == "__main__":
    main()
