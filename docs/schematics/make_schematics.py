#!/usr/bin/env python3
"""Draws every schematic and build drawing as SVG files in this folder.

    python3 docs/schematics/make_schematics.py

No dependencies. Pin numbers and part values here match locator/config.py,
transmitter/main.py, PARTS.md and for_dummies.md; change them together.
"""
import math
import os
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))

C = {"pwr": "#d62728", "gnd": "#222222", "sig": "#1f77b4", "spi": "#9467bd",
     "ana": "#e377c2", "out": "#ff7f0e", "usb": "#2ca02c", "body": "#f4f4f4",
     "note": "#555555", "field": "#7fb3d5", "ferrite": "#555555", "copper": "#c87533",
     "wood": "#deb887", "pvc": "#e8e8e8", "soil": "#c9b38b"}


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h = w, h
        self.items = []
        self.rect(0, 0, w, h, fill="white", stroke="none")
        self.text(24, 40, title, size=26, weight="bold")

    # ----------------------------------------------------------- primitives --
    def rect(self, x, y, w, h, fill="none", stroke="#222", sw=2, rx=0, dash=None):
        d = ' stroke-dasharray="%s"' % dash if dash else ""
        self.items.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%d" fill="%s" '
                          'stroke="%s" stroke-width="%s"%s/>' % (x, y, w, h, rx, fill, stroke, sw, d))

    def line(self, x1, y1, x2, y2, color="#222", sw=2, dash=None):
        d = ' stroke-dasharray="%s"' % dash if dash else ""
        self.items.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                          'stroke-width="%s" stroke-linecap="round"%s/>' % (x1, y1, x2, y2, color, sw, d))

    def wire(self, pts, color="#222", sw=2.5, dash=None):
        d = ' stroke-dasharray="%s"' % dash if dash else ""
        p = " ".join("%.1f,%.1f" % q for q in pts)
        self.items.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%s" '
                          'stroke-linejoin="round" stroke-linecap="round"%s/>' % (p, color, sw, d))

    def path(self, d, color="#222", sw=2, fill="none"):
        self.items.append('<path d="%s" fill="%s" stroke="%s" stroke-width="%s" '
                          'stroke-linejoin="round"/>' % (d, fill, color, sw))

    def circle(self, x, y, r, fill="none", stroke="#222", sw=2):
        self.items.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" '
                          'stroke-width="%s"/>' % (x, y, r, fill, stroke, sw))

    def dot(self, x, y, color="#222"):
        self.circle(x, y, 4.5, fill=color, stroke=color, sw=1)

    def text(self, x, y, s, size=15, anchor="start", weight="normal", color="#222", italic=False):
        st = ' font-style="italic"' if italic else ""
        for i, part in enumerate(str(s).split("\n")):
            self.items.append('<text x="%.1f" y="%.1f" font-family="DejaVu Sans, Arial, sans-serif" '
                              'font-size="%d" text-anchor="%s" font-weight="%s" fill="%s"%s>%s</text>'
                              % (x, y + i * size * 1.25, size, anchor, weight, color, st, escape(part)))

    def arrow(self, x1, y1, x2, y2, color="#222", sw=2, head=10):
        self.line(x1, y1, x2, y2, color, sw)
        a = math.atan2(y2 - y1, x2 - x1)
        for s in (-1, 1):
            self.line(x2, y2, x2 - head * math.cos(a + s * 0.45), y2 - head * math.sin(a + s * 0.45), color, sw)

    # ------------------------------------------------------------- symbols --
    def resistor(self, x, y, length=70, vertical=False, label="", value="", color="#222"):
        """Zig-zag between (x, y) and (x+length, y) or (x, y+length)."""
        n, amp = 6, 7
        lead = length * 0.2
        pts = [(0, 0), (lead, 0)]
        step = (length - 2 * lead) / n
        for i in range(n):
            pts.append((lead + step * (i + 0.5), amp * (1 if i % 2 == 0 else -1)))
        pts += [(length - lead, 0), (length, 0)]
        if vertical:
            pts = [(x + b, y + a) for a, b in pts]
            self.wire(pts, color, 2)
            self.text(x + 14, y + length / 2 - 2, label, 14, weight="bold")
            self.text(x + 14, y + length / 2 + 15, value, 13, color=C["note"])
        else:
            pts = [(x + a, y + b) for a, b in pts]
            self.wire(pts, color, 2)
            self.text(x + length / 2, y - 14, label, 14, "middle", "bold")
            self.text(x + length / 2, y + 26, value, 13, "middle", color=C["note"])

    def fuse(self, x, y, length=70, label="", value=""):
        self.line(x, y, x + 15, y)
        self.rect(x + 15, y - 8, length - 30, 16, fill="white")
        self.line(x + 15, y, x + length - 15, y, sw=1.5)
        self.line(x + length - 15, y, x + length, y)
        self.text(x + length / 2, y - 14, label, 14, "middle", "bold")
        self.text(x + length / 2, y + 26, value, 13, "middle", color=C["note"])

    def cap_v(self, x, y, label="", value="", polar=False):
        """Vertical capacitor: top lead at (x, y), bottom lead at (x, y+50)."""
        self.line(x, y, x, y + 20)
        self.line(x - 16, y + 20, x + 16, y + 20, sw=3)
        if polar:
            self.path("M %.1f %.1f Q %.1f %.1f %.1f %.1f" % (x - 16, y + 32, x, y + 24, x + 16, y + 32), sw=3)
            self.text(x - 24, y + 18, "+", 14, "middle", "bold")
        else:
            self.line(x - 16, y + 30, x + 16, y + 30, sw=3)
        self.line(x, y + 30, x, y + 50)
        self.text(x + 22, y + 22, label, 14, weight="bold")
        self.text(x + 22, y + 38, value, 13, color=C["note"])

    def tvs_v(self, x, y, label="", value=""):
        """Bidirectional TVS, vertical, from (x, y) to (x, y+60)."""
        self.line(x, y, x, y + 14)
        # two diodes nose to nose
        self.path("M %f %f L %f %f L %f %f Z" % (x - 10, y + 14, x + 10, y + 14, x, y + 30), fill="white")
        self.path("M %f %f L %f %f L %f %f Z" % (x - 10, y + 46, x + 10, y + 46, x, y + 30), fill="white")
        self.path("M %f %f L %f %f L %f %f L %f %f" % (x - 14, y + 26, x - 10, y + 30, x + 10, y + 30, x + 14, y + 34))
        self.line(x, y + 46, x, y + 60)
        self.text(x + 20, y + 28, label, 14, weight="bold")
        self.text(x + 20, y + 44, value, 13, color=C["note"])

    def led_v(self, x, y, label="", color="#2ca02c"):
        """LED pointing down, (x, y) anode to (x, y+44) cathode."""
        self.line(x, y, x, y + 12)
        self.path("M %f %f L %f %f L %f %f Z" % (x - 10, y + 12, x + 10, y + 12, x, y + 30), fill=color)
        self.line(x - 10, y + 30, x + 10, y + 30, sw=2.5)
        self.line(x, y + 30, x, y + 44)
        for k in (0, 7):
            self.arrow(x + 12, y + 14 + k, x + 24, y + 6 + k, sw=1.5, head=5)
        self.text(x + 28, y + 30, label, 13)

    def button_v(self, x, y, label=""):
        """Momentary push button, (x, y) to (x, y+50)."""
        self.line(x, y, x, y + 15)
        self.circle(x, y + 15, 3, fill="#222")
        self.circle(x, y + 35, 3, fill="#222")
        self.line(x, y + 35, x, y + 50)
        self.line(x + 8, y + 13, x + 8, y + 37, sw=2.5)
        self.line(x + 8, y + 25, x + 20, y + 25)
        self.text(x + 24, y + 30, label, 13)

    def switch_h(self, x, y, label=""):
        self.line(x, y, x + 15, y)
        self.circle(x + 15, y, 3, fill="#222")
        self.line(x + 15, y, x + 45, y - 14, sw=2.5)
        self.circle(x + 50, y, 3, fill="#222")
        self.line(x + 50, y, x + 65, y)
        self.text(x + 32, y - 22, label, 14, "middle", "bold")

    def ground(self, x, y):
        self.line(x, y, x, y + 10)
        for i, w in enumerate((16, 10, 4)):
            self.line(x - w, y + 10 + i * 5, x + w, y + 10 + i * 5)

    def battery_v(self, x, y, label="", value=""):
        """Battery: + at (x, y), - at (x, y+60)."""
        self.line(x, y, x, y + 20)
        for i in range(2):
            self.line(x - 18, y + 20 + i * 14, x + 18, y + 20 + i * 14, sw=3)
            self.line(x - 9, y + 27 + i * 14, x + 9, y + 27 + i * 14, sw=3)
        self.line(x, y + 41, x, y + 60)
        self.text(x - 26, y + 16, "+", 16, "middle", "bold")
        self.text(x + 26, y + 30, label, 14, weight="bold")
        self.text(x + 26, y + 46, value, 13, color=C["note"])

    def post(self, x, y, color, label):
        self.circle(x, y, 11, fill=color, stroke="#222")
        self.circle(x, y, 4, fill="white", stroke="#222", sw=1)
        self.text(x + 18, y + 5, label, 14, weight="bold")

    def chip(self, x, y, w, h, title, pins, fill=None):
        """pins: list of (side, offset, name, pin_number_text). Returns name -> (x, y)."""
        self.rect(x, y, w, h, fill=fill or C["body"], rx=6)
        self.text(x + w / 2, y + 24, title, 16, "middle", "bold")
        pos = {}
        for side, off, name, num in pins:
            if side == "L":
                px, py = x, y + off
                self.line(px - 18, py, px, py)
                self.text(px + 8, py + 5, name, 13)
                if num:
                    self.text(px - 22, py - 5, num, 11, "end", color=C["note"])
                pos[name] = (px - 18, py)
            elif side == "R":
                px, py = x + w, y + off
                self.line(px, py, px + 18, py)
                self.text(px - 8, py + 5, name, 13, "end")
                if num:
                    self.text(px + 22, py - 5, num, 11, color=C["note"])
                pos[name] = (px + 18, py)
            elif side == "T":
                px, py = x + off, y
                self.line(px, py - 18, px, py)
                self.text(px + 6, py - 6, name, 12)
                pos[name] = (px, py - 18)
            else:
                px, py = x + off, y + h
                self.line(px, py, px, py + 18)
                self.text(px, py - 8, name, 12, "middle")
                pos[name] = (px, py + 18)
        return pos

    def note(self, x, y, s, size=14):
        self.text(x, y, s, size, color=C["note"])

    def save(self, name):
        body = "\n".join(self.items)
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">\n%s\n</svg>\n'
               % (self.w, self.h, self.w, self.h, body))
        with open(os.path.join(HERE, name), "w") as f:
            f.write(svg)
        print("wrote", name)


# =========================================================== 1. the system ==
def draw_system():
    s = Svg(1500, 860, "PowerlineLocator: the whole system")
    # ground surface and buried line
    gy = 560
    s.rect(0, gy, 1500, 300, fill=C["soil"], stroke="none")
    s.line(0, gy, 1500, gy, "#8b7355", 3)
    s.text(1480, gy + 26, "ground", 14, "end", color="#5a4630")
    ly = 780
    s.line(80, ly, 1440, ly, "#111", 9)
    s.text(480, ly + 34, "buried cable, 4 to 6 ft down (seen side-on)", 15, weight="bold")
    s.arrow(980, ly - 20, 1180, ly - 20, C["out"], 3)
    s.arrow(1180, ly + 18, 980, ly + 18, C["out"], 2, 8)
    s.text(1080, ly - 30, "8 or 33 kHz current flows out along the cable...", 13, "middle", color=C["out"])
    s.text(1080, ly + 50, "...and comes back through the earth", 13, "middle", color=C["out"])

    # transmitter, left
    s.rect(60, 330, 230, 150, fill=C["body"], rx=8)
    s.text(175, 360, "TRANSMITTER", 18, "middle", "bold")
    s.rect(60, 300 - 2, 82, 22, fill="#ff7f0e", stroke="none", rx=4)
    s.text(101, 314, "STAGE 2", 12, "middle", "bold", "white")
    s.text(175, 384, "Pico + DRV8871 H-bridge", 13, "middle", color=C["note"])
    s.text(175, 402, "12 V LiFePO4 battery", 13, "middle", color=C["note"])
    s.text(175, 420, "8 kHz / 33 kHz / 90 Hz CAL", 13, "middle", color=C["note"])
    s.post(110, 455, "#d62728", "")
    s.post(240, 455, "#222", "")
    s.text(110, 500, "RED", 12, "middle", "bold")
    s.text(240, 500, "BLACK", 12, "middle", "bold")
    # option A: direct connection to a dead line's exposed end
    s.wire([(110, 466), (110, 530), (160, 530), (160, ly - 6)], C["pwr"], 3)
    s.rect(140, gy - 10, 40, 20, fill="#bbb", stroke="#222")
    s.note(186, gy + 40, "A: clip RED to the exposed end of\n   a DEAD line (riser, stub-up)", 13)
    s.wire([(240, 466), (240, 520), (380, 520), (380, gy + 90)], C["gnd"], 3)
    s.path("M 372 %d L 388 %d L 380 %d Z" % (gy + 90, gy + 90, gy + 118), fill="#666")
    s.note(392, gy + 106, "ground stake, 10 ft or more\noff to the side", 13)
    s.note(60, 270, "B (live lines): no contact at all. RED and BLACK go to\n"
                    "the CLAMP, which snaps around the cable or its ground wire.", 13)

    # the staff
    sx = 620
    s.rect(sx - 14, 120, 28, 438, fill=C["wood"], stroke="#8b5a2b")
    s.rect(sx - 70, 110, 140, 70, fill="#333", rx=6)
    s.rect(sx - 52, 120, 104, 44, fill="#cfd8c8", stroke="#222", sw=1)
    s.text(sx, 148, "4' 7\"", 18, "middle", "bold")
    s.text(sx + 90, 136, "head box: Pi 4, screen,\nbuttons, buzzer", 13)
    s.rect(sx - 60, 236, 120, 46, fill="#3a3a3a", rx=4)
    s.text(sx, 264, "UMC404HD", 14, "middle", "bold", "white")
    s.text(sx + 90, 256, "USB audio interface:\n4 preamps + ADC", 13)
    for (cy, lab) in ((380, "top coils"), (520, "bottom coils")):
        s.rect(sx - 55, cy - 7, 110, 14, fill=C["ferrite"], rx=4)
        s.rect(sx - 7, cy - 55, 14, 110, fill="#888", rx=4)
        s.text(sx + 90, cy - 4, lab + ":", 13, weight="bold")
        s.text(sx + 90, cy + 14, "H on the front, V on the back", 13)
    s.wire([(sx - 30, 236), (sx - 30, 200), (sx - 30, 180)], C["usb"], 3)
    s.note(sx - 70, 214, "USB", 13)
    for i, cy in enumerate((380, 520)):
        s.wire([(sx + 20 + i * 8, cy - 12), (sx + 20 + i * 8, 282)], C["ana"], 2, dash="5,4")
    s.note(sx + 40, 320, "XLR leads", 13)
    s.text(sx, gy + 30, "tip on the ground", 12, "middle", color="#5a4630")
    s.rect(sx - 41, 76, 82, 22, fill="#2ca02c", stroke="none", rx=4)
    s.text(sx, 92, "STAGE 1", 12, "middle", "bold", "white")

    # field circles around the line, drawn as a cross-section inset
    ix, iy = 1250, 300
    s.rect(ix - 170, iy - 160, 340, 360, fill="white", stroke="#999", rx=8)
    s.text(ix, iy - 132, "looking ALONG the cable", 15, "middle", "bold")
    s.text(ix, iy - 110, "the field circles it: B = μ₀ I / (2π r)", 13, "middle", color=C["note"])
    s.rect(ix - 168, iy + 40, 336, 158, fill=C["soil"], stroke="none")
    s.line(ix - 168, iy + 40, ix + 168, iy + 40, "#8b7355", 2)
    s.circle(ix, iy + 130, 8, fill="#111")
    for r in (25, 48, 66):
        s.circle(ix, iy + 130, r, stroke=C["field"], sw=1.6)
    s.rect(ix - 4, iy - 90, 8, 130, fill=C["wood"], stroke="#8b5a2b", sw=1)
    s.rect(ix - 16, iy + 15, 32, 7, fill=C["ferrite"])
    s.rect(ix - 16, iy - 55, 32, 7, fill=C["ferrite"])
    s.note(ix + 22, iy + 24, "bottom", 12)
    s.note(ix + 22, iy - 47, "top", 12)
    s.save("system.svg")


# ========================================================= 2. the receiver ==
def draw_receiver():
    s = Svg(1500, 900, "Receiver wiring (head box)")
    # Pi header as a two-column block
    px, py = 120, 110
    pins = {1: "3V3", 2: "5V", 6: "GND", 12: "GPIO18", 19: "MOSI (GPIO10)", 22: "GPIO25",
            23: "SCLK (GPIO11)", 29: "GPIO5", 30: "GND", 31: "GPIO6", 34: "GND", 39: "GND"}
    HW = 300
    s.rect(px, py, HW, 20 * 21 + 30, fill="#e8f0e8", rx=8)
    s.text(px + HW / 2, py + 24, "Raspberry Pi 4 header", 15, "middle", "bold")
    pin_xy = {}
    for n in range(1, 41):
        row = (n - 1) // 2
        col = (n - 1) % 2
        x = px + 130 + col * 40
        y = py + 46 + row * 21
        used = n in pins
        s.circle(x, y, 6, fill="#222" if used else "white", stroke="#222", sw=1.2)
        if used:
            pin_xy[n] = (x, y)
            if col == 0:
                s.text(x - 12, y + 5, "%d %s" % (n, pins[n]), 12, "end")
            else:
                s.text(x + 12, y + 5, "%d %s" % (n, pins[n]), 12)
    s.note(px, py + 20 * 21 + 60, "odd pins: inner row\neven pins: board edge", 12)

    # display
    dx, dy = 820, 110
    dpos = s.chip(dx, dy, 300, 230, "Sharp Memory LCD 2.7\"\nAdafruit 4694", [
        ("L", 70, "VIN", ""), ("L", 100, "GND", ""), ("L", 130, "CLK", ""),
        ("L", 160, "DI", ""), ("L", 190, "CS", ""),
        ("R", 70, "3V3 (out)", ""), ("R", 100, "EMD", ""), ("R", 130, "DISP", ""), ("R", 160, "EIN", "")])
    s.note(dx + 320, dy + 70, "leave unconnected", 12)
    s.note(dx + 320, dy + 100, "leave unconnected", 12)
    s.note(dx + 320, dy + 130, "only if blank: to 3V3 (out)", 12)
    s.note(dx + 320, dy + 160, "leave unconnected", 12)

    def route(n, to, color, xmid):
        x0, y0 = pin_xy[n]
        s.line(x0, y0, px + HW if n % 2 == 0 else px, y0, color, 1, dash="2,3")
        start = (px + HW, y0) if (n % 2 == 0) else (px, y0)
        if n % 2 == 1:
            # odd pins exit left then go around the top
            s.wire([start, (px - 30 - (n % 7) * 6, y0), (px - 30 - (n % 7) * 6, py - 20 - (n % 5) * 6),
                    (xmid, py - 20 - (n % 5) * 6), (xmid, to[1]), to], color)
        else:
            s.wire([start, (xmid, y0), (xmid, to[1]), to], color)

    route(2, dpos["VIN"], C["pwr"], 560)
    route(6, dpos["GND"], C["gnd"], 590)
    route(23, dpos["CLK"], C["spi"], 640)
    route(19, dpos["DI"], C["spi"], 670)
    route(22, dpos["CS"], C["spi"], 700)
    s.note(560, dy + 245 + 60, "CS is active HIGH on this panel, so it's a plain GPIO\n"
                               "(GPIO25), not the Pi's CE0/CE1.", 13)

    # buttons and buzzer
    bx, by = 820, 520
    s.rect(bx - 30, by - 40, 560, 330, fill="#fafafa", stroke="#bbb", rx=8)
    s.text(bx - 14, by - 14, "Panel parts on the lid", 15, weight="bold")
    # MODE
    s.button_v(bx + 40, by + 40, "MODE")
    s.button_v(bx + 180, by + 40, "SOUND")
    s.resistor(bx + 320, by + 40, 70, vertical=True, label="R1", value="100 Ω")
    s.circle(bx + 320, by + 150, 18, fill="#ffd27f")
    s.text(bx + 320, by + 156, "+", 16, "middle", "bold")
    s.text(bx + 350, by + 156, "piezo buzzer (passive)", 13)
    s.line(bx + 320, by + 110, bx + 320, by + 132)
    for x in (bx + 40, bx + 180):
        s.wire([(x, by + 90), (x, by + 230)], C["gnd"])
    s.wire([(bx + 320, by + 168), (bx + 320, by + 230)], C["gnd"])
    s.wire([(bx + 40, by + 230), (bx + 320, by + 230)], C["gnd"])
    s.dot(bx + 180, by + 230)
    s.text(bx + 180, by + 256, "all to GND", 13, "middle")

    def route2(n, to, color, ylane):
        x0, y0 = pin_xy[n]
        s.line(x0, y0, px + HW if n % 2 == 0 else px, y0, color, 1, dash="2,3")
        start = (px + HW, y0) if n % 2 == 0 else (px, y0)
        lx = px + HW + 30 + (n % 9) * 14
        if n % 2 == 1:
            s.wire([start, (px - 60 - (n % 3) * 8, y0), (px - 60 - (n % 3) * 8, ylane), (to[0], ylane), to], color)
        else:
            s.wire([start, (lx, y0), (lx, ylane), (to[0], ylane), to], color)

    route2(29, (bx + 40, by + 40), C["sig"], by + 10)
    route2(31, (bx + 180, by + 40), C["sig"], by + 20)
    route2(12, (bx + 320, by + 40), C["out"], by + 30)
    x0, y0 = pin_xy[34]
    s.line(x0, y0, px + HW, y0, C["gnd"], 1, dash="2,3")
    s.wire([(px + HW, y0), (px + HW + 20, y0), (px + HW + 20, by + 290), (bx + 180, by + 290),
            (bx + 180, by + 230)], C["gnd"])

    # USB side
    s.rect(120, 640, 260, 70, fill="#3a3a3a", rx=6)
    s.text(250, 670, "UMC404HD", 16, "middle", "bold", "white")
    s.text(250, 692, "inputs 1-4 = coils (XLR)", 12, "middle", color="white")
    s.rect(120, 760, 260, 60, fill="#dfe8f5", rx=6)
    s.text(250, 795, "USB-C power bank, 5 V 3 A", 14, "middle", "bold")
    s.rect(520, 690, 200, 80, fill="#e8f0e8", rx=6)
    s.text(620, 718, "Pi 4 ports", 14, "middle", "bold")
    s.text(620, 738, "USB-A (black, USB 2)", 12, "middle")
    s.text(620, 756, "USB-C (power in)", 12, "middle")
    s.wire([(380, 675), (480, 675), (480, 734), (520, 734)], C["usb"], 3)
    s.wire([(380, 790), (480, 790), (480, 752), (520, 752)], C["usb"], 3)
    s.note(120, 860, "Inputs: 1 = bottom H, 2 = bottom V, 3 = top H, 4 = top V.  Gain knobs fully clockwise,"
                     " then taped.  +48V phantom OFF.  PAD buttons out.", 13)
    s.save("receiver.svg")


# ====================================================== 3. the transmitter ==
def draw_transmitter():
    s = Svg(1500, 900, "Transmitter schematic")
    # battery and power switch
    s.battery_v(100, 200, "BT1", "12.8 V LiFePO4, 6 Ah")
    s.wire([(100, 200), (100, 150), (140, 150)], C["pwr"])
    s.fuse(140, 150, 80, "F1", "3 A blade, in-line")
    s.switch_h(220, 150, "SW1 power")
    vb = 285
    s.wire([(vb, 150), (1180, 150)], C["pwr"])
    s.text(330, 140, "V+ (about 13 V)", 13, color=C["pwr"])
    s.wire([(100, 260), (100, 760), (1180, 760)], C["gnd"])
    s.ground(100, 760)
    s.text(330, 780, "GND (common to everything)", 13, color=C["gnd"])

    # bulk capacitor
    s.dot(320, 150)
    s.wire([(320, 150), (320, 300)], C["pwr"])
    s.cap_v(320, 300, "C1", "470 µF 35 V", polar=True)
    s.wire([(320, 350), (320, 760)], C["gnd"])
    s.dot(320, 760)

    # buck converter
    buck = s.chip(450, 230, 180, 120, "5 V buck\nPololu D24V10F5", [
        ("T", 40, "VIN", ""), ("B", 40, "GND", ""), ("R", 70, "VOUT", "")])
    s.dot(490, 150)
    s.wire([(490, 150), buck["VIN"]], C["pwr"])
    s.wire([buck["GND"], (490, 760)], C["gnd"])
    s.dot(490, 760)

    # Pico
    pico = s.chip(740, 230, 220, 380, "Raspberry Pi Pico", [
        ("L", 70, "VSYS", "pin 39"), ("L", 110, "GND", "pin 38"),
        ("L", 170, "GP14", "pin 19"), ("L", 210, "GP15", "pin 20"),
        ("R", 70, "GP0", "pin 1"), ("R", 110, "GP1", "pin 2"),
        ("R", 200, "GP2", "pin 4"), ("R", 250, "GP3", "pin 5"), ("R", 300, "GP4", "pin 6")])
    # D2: Schottky so the Pico's USB can't back-feed the regulator
    s.wire([buck["VOUT"], (652, 300)], C["pwr"])
    s.path("M 652 290 L 652 310 L 668 300 Z", fill="#222")
    s.line(668, 290, 668, 310, sw=2.5)
    s.wire([(668, 300), (pico["VSYS"][0], 300)], C["pwr"])
    s.text(660, 282, "D2 1N5819", 11, "middle", "bold")
    s.wire([pico["GND"], (690, 340), (690, 760)], C["gnd"])
    s.dot(690, 760)
    # buttons
    for name, x, lab in (("GP14", 650, "S1 FREQ"), ("GP15", 540, "S2 LEVEL")):
        y = pico[name][1]
        s.wire([pico[name], (x, y), (x, 640)], C["sig"])
        s.button_v(x, 640, "")
        s.text(x - 8, 668, lab, 13, "end")
        s.wire([(x, 690), (x, 760)], C["gnd"])
        s.dot(x, 760)
    s.note(120, 700, "buttons pull to GND;\nthe Pico has internal pull-ups", 11)
    # LEDs
    for name, x, lab, col in (("GP2", 1010, "green\n8 kHz", "#2ca02c"), ("GP3", 1070, "yellow\n33 kHz", "#e6c200"),
                              ("GP4", 1130, "red\n90 Hz CAL", "#d62728")):
        y = pico[name][1]
        s.wire([pico[name], (x, y), (x, 560)], C["sig"])
        s.resistor(x, 560, 50, vertical=True)
        s.led_v(x, 610, "", col)
        s.text(x, 690, lab.split("\n")[0], 11, "middle")
        s.text(x, 703, lab.split("\n")[1], 11, "middle")
        s.wire([(x, 654), (x, 676)], C["gnd"])
        s.wire([(x, 712), (x, 760)], C["gnd"])
        s.dot(x, 760)
    s.note(1000, 742, "R2-R4: 330 Ω", 12)

    # DRV8871
    drv = s.chip(1180, 230, 200, 200, "DRV8871\n(Adafruit 3190)", [
        ("L", 70, "IN1", ""), ("L", 110, "IN2", ""), ("L", 160, "GND / power −", ""),
        ("T", 60, "VM", ""), ("R", 70, "OUT1", ""), ("R", 140, "OUT2", "")])
    s.wire([(1180, 150), (1240, 150), drv["VM"]], C["pwr"])
    s.wire([pico["GP0"], (1100, pico["GP0"][1]), (1100, drv["IN1"][1]), drv["IN1"]], C["spi"])
    s.wire([pico["GP1"], (1090, pico["GP1"][1]), (1090, drv["IN2"][1]), drv["IN2"]], C["spi"])
    g = drv["GND / power −"]
    s.wire([g, (1150, g[1]), (1150, 760)], C["gnd"])
    s.dot(1150, 760)
    s.note(1180, 452, "current-limit resistor (30 kΩ) is on\nthe board already: trips at about 2 A", 11)

    # output stage: OUT1 -> node A; TVS from A to OUT2; A -> R1 -> F2 -> RED
    o1, o2 = drv["OUT1"], drv["OUT2"]
    s.wire([o1, (1420, o1[1]), (1420, 470)], C["out"])
    s.dot(1420, 470)
    s.wire([o2, (1470, o2[1]), (1470, 820)], C["gnd"])
    s.post(1470, 832, "#222", "")
    s.text(1460, 872, "BLACK post", 14, "end", "bold")
    s.tvs_v(1420, 470)
    s.wire([(1420, 530), (1420, 560), (1470, 560)], C["out"])
    s.dot(1470, 560)
    s.text(1414, 600, "D1 TVS", 14, "end", "bold")
    s.text(1414, 616, "1.5KE20CA", 13, "end", color=C["note"])
    s.wire([(1420, 470), (1330, 470)], C["out"])
    s.resistor(1330, 470, 70, vertical=True)
    s.text(1316, 500, "R1", 14, "end", "bold")
    s.text(1316, 516, "22 \u03a9 25 W", 13, "end", color=C["note"])
    s.wire([(1330, 540), (1330, 660)], C["out"])
    s.fuse(1250, 660, 80, "F2", "1 A fast")
    s.wire([(1250, 660), (1200, 660), (1200, 820)], C["out"])
    s.post(1200, 832, "#d62728", "")
    s.text(1214, 872, "RED post", 14, "end", "bold")
    s.note(40, 820, "Signal path: Pico GP0/GP1 → H-bridge → TVS clamp → 22 Ω → 1 A fuse → RED.  "
                    "BLACK comes straight from OUT2.\nIf RED ever touches a live 120/240 V wire: the 22 Ω limits the "
                    "current, the TVS clamps the bridge to about 28 V, and the fuse blows in milliseconds.", 13)
    s.save("transmitter.svg")


# =============================================================== 4. a coil ==
def draw_coil():
    s = Svg(1500, 760, "Coil construction (make four, plus a spare)")
    x0, y0 = 150, 260
    L = 1000  # 100 mm rod at 10 px/mm
    s.rect(x0, y0 - 50, L, 100, fill="#666", rx=10)
    s.text(x0 + L, y0 + 82, "ferrite rod, 10 mm Ø × 100 mm", 15, "end", "bold")
    # chuck tape
    s.rect(x0 - 10, y0 - 56, 150, 112, fill="#333", rx=6, stroke="#111")
    s.text(x0 + 65, y0 + 82, "electrical tape\ncushion (chuck here)", 12, "middle")
    # paper former + winding
    wx0, wx1 = x0 + 150, x0 + 850
    s.rect(wx0 - 20, y0 - 56, (wx1 - wx0) + 40, 112, fill="#f5f0dc", stroke="#999")
    for i in range(0, 700, 9):
        s.line(wx0 + i, y0 - 62, wx0 + i + 5, y0 + 62, C["copper"], 2)
    s.rect(wx0, y0 - 64, wx1 - wx0, 128, stroke=C["copper"], sw=1)
    s.text((wx0 + wx1) / 2, y0 - 82, "1000 turns of 30 AWG magnet wire over the middle 70 mm", 15, "middle", "bold")
    # dimensions
    s.arrow((wx0 + wx1) / 2 - 60, y0 + 108, wx0, y0 + 108, sw=1.5)
    s.arrow((wx0 + wx1) / 2 + 60, y0 + 108, wx1, y0 + 108, sw=1.5)
    s.text((wx0 + wx1) / 2, y0 + 113, "70 mm", 14, "middle")
    s.arrow(x0 + 70, y0 + 150, x0, y0 + 150, sw=1.5)
    s.arrow(x0 + L - 70, y0 + 150, x0 + L, y0 + 150, sw=1.5)
    s.line(x0, y0 + 140, x0, y0 + 160, sw=1)
    s.line(x0 + L, y0 + 140, x0 + L, y0 + 160, sw=1)
    s.text(x0 + L / 2, y0 + 155, "100 mm rod: winding centred, 15 mm bare at each end", 13, "middle")
    # leads
    s.wire([(wx0, y0 - 56), (wx0 - 30, y0 - 120), (1300, y0 - 120)], C["copper"], 2)
    s.wire([(wx1, y0 - 56), (wx1 + 20, y0 - 100), (1300, y0 - 100)], C["copper"], 2)
    s.text(1310, y0 - 115, "start  → pin 2", 14)
    s.text(1310, y0 - 95, "finish → pin 3", 14)

    # layer stack, below
    sx, sy = 150, 520
    s.text(sx, sy - 20, "Layers, inside to outside (cut-away)", 17, weight="bold")
    layers = [("ferrite rod", "#666"), ("2 wraps of paper + tape: the former", "#f5f0dc"),
              ("winding, 1000 turns", C["copper"]), ("1 wrap of electrical tape", "#333"),
              ("copper foil tape: the shield", "#e0a060"), ("tape over everything", "#333")]
    for i, (lab, col) in enumerate(layers):
        s.rect(sx + i * 34, sy, 34, 160, fill=col, stroke="#222", sw=1)
        s.text(sx + 260, sy + 18 + i * 26, "%d. %s" % (i + 1, lab), 14)
        s.line(sx + i * 34 + 17, sy + 10 + i * 26, sx + 250, sy + 13 + i * 26, "#999", 1)

    # shield gap detail
    gx, gy = 820, 500
    s.text(gx, gy, "The shield must NOT close into a ring", 17, weight="bold")
    s.circle(gx + 110, gy + 120, 70, stroke="#e0a060", sw=12)
    s.rect(gx + 165, gy + 98, 30, 44, fill="white", stroke="none")
    s.text(gx + 200, gy + 125, "3 mm gap", 14, weight="bold")
    s.circle(gx + 110, gy + 120, 50, fill=C["copper"], stroke="#222", sw=1)
    s.circle(gx + 110, gy + 120, 30, fill="#666", stroke="#222", sw=1)
    s.note(gx + 230, gy + 60, "Lap the foil all round EXCEPT a 3 mm\nlengthways gap. A closed ring is a\n"
                              "shorted turn: it cancels the very\nfield you're trying to sense.", 13)
    s.note(gx + 230, gy + 150, "Solder a thin bare drain wire to the\nfoil at one end: it goes to XLR pin 1\n"
                               "with the cable's braided shield.", 13)
    s.save("coil.svg")


# ============================================================== 5. the clamp ==
def draw_clamp():
    s = Svg(1300, 640, "The clamp: puts the signal on a cable with no contact at all")
    cx, cy = 360, 330
    s.circle(cx + 13, cy + 4, 150, stroke="#444", sw=46)
    s.line(cx - 170, cy + 4, cx + 196, cy + 4, "white", 8)
    s.text(cx + 13, cy + 210, "two Fair-Rite 0431177081 split cores, stacked back to back\n"
           "(end-on they look like one ring; the split runs across the middle)", 14, "middle")
    s.circle(cx + 13, cy + 4, 46, fill="#111")
    s.text(cx + 13, cy + 10, "cable", 14, "middle", "bold", "white")
    # winding on the top half
    for i in range(10):
        a = math.radians(205 + i * 13)
        x = cx + 13 + 150 * math.cos(a)
        y = cy + 4 + 150 * math.sin(a)
        s.circle(x, y, 30, stroke=C["copper"], sw=3)
    s.text(cx + 13, cy - 200, "10 turns of 20 AWG wire around ONE half,\nthrough the hole and back round the outside", 14, "middle", "bold")
    s.wire([(cx - 120, cy - 80), (cx - 200, cy - 120), (cx - 230, cy - 120)], C["pwr"], 3)
    s.wire([(cx + 160, cy - 90), (cx + 300, cy - 140), (cx + 520, cy - 140)], C["gnd"], 3)
    s.text(cx - 238, cy - 115, "to RED", 14, "end", "bold")
    s.text(cx + 530, cy - 135, "to BLACK (no stake needed)", 14, weight="bold")
    s.note(780, 300, "How it works: the clamp is a transformer.\n"
                     "Its 10 turns are the primary; the cable inside\n"
                     "is a 1-turn secondary. Volts on the cable\n"
                     "= drive volts / 10. Current flows round the loop\n"
                     "made by the cable, its grounds at both ends\n"
                     "and the earth between them.", 14)
    s.note(780, 470, "Fits cables up to 25 mm (1 in) across.\n"
                     "Steel conduit blocks it; PVC conduit doesn't.\n"
                     "Use 33 kHz: it couples best.", 14)
    s.save("clamp.svg")


# ============================================================== 6. the staff ==
def draw_staff():
    s = Svg(1500, 1000, "The staff: where everything goes (dimensions from the bottom tip)")
    k = 0.62     # px per mm
    tipy = 930
    bx = 420
    bw = 89 * k * 1.6

    def Y(mm):
        return tipy - mm * k

    s.rect(bx - bw / 2, Y(1220), bw, 1220 * k, fill=C["wood"], stroke="#8b5a2b")
    s.text(bx, Y(1220) - 12, "1x4 board, 4 ft (1220 mm)", 14, "middle", "bold")
    s.line(bx - 300, tipy, bx + 300, tipy, "#8b7355", 3)
    s.text(bx - 300, tipy + 22, "ground: the tip rests here", 13, color="#5a4630")
    # coils
    for mm, lab in ((100, "BOTTOM"), (600, "TOP")):
        y = Y(mm)
        s.rect(bx - 50 * k * 1.6, y - 7, 100 * k * 1.6, 14, fill=C["ferrite"], rx=4)
        s.rect(bx - 7, y - 50 * k * 1.6, 14, 100 * k * 1.6, fill="#999", rx=4, stroke="#222", sw=1, dash="4,3")
        s.line(bx + 130, y, bx + 200, y, sw=1)
        s.text(bx + 210, y + 5, "%s coils: centres %d mm (%s) up" % (lab, mm, "4 in" if mm == 100 else "23.6 in"), 15, weight="bold")
        s.note(bx + 210, y + 25, "H coil on the FRONT face (axis across the board);\nV coil on the BACK face (axis up the board)", 13)
    # spacing dimension
    s.arrow(bx - 140, Y(350), bx - 140, Y(100), sw=1.5)
    s.arrow(bx - 140, Y(350), bx - 140, Y(600), sw=1.5)
    s.text(bx - 150, Y(350) + 5, "500 mm", 14, "end", "bold")
    s.arrow(bx - 200, Y(50), bx - 200, Y(0), sw=1.5)
    s.arrow(bx - 200, Y(50), bx - 200, Y(100), sw=1.5)
    s.text(bx - 210, Y(50) + 5, "100 mm", 14, "end")
    # interface and head box
    s.rect(bx - 80, Y(900), 160, Y(800) - Y(900), fill="#3a3a3a", rx=4)
    s.text(bx, Y(850) + 5, "UMC404HD", 14, "middle", "bold", "white")
    s.note(bx + 210, Y(850), "interface strapped to the front, 800 to 900 mm\n(keep it at least 200 mm above the top coils)", 13)
    s.rect(bx - 90, Y(1150), 180, Y(1000) - Y(1150), fill="#333", rx=6)
    s.rect(bx - 60, Y(1135), 120, 50, fill="#cfd8c8", stroke="#222", sw=1)
    s.text(bx, Y(1135) + 32, "4' 7\"", 16, "middle", "bold")
    s.circle(bx - 40, Y(1020), 8, fill="#d62728")
    s.circle(bx + 40, Y(1020), 8, fill="#1f77b4")
    s.note(bx + 210, Y(1080), "head box, 1000 to 1150 mm: Pi, screen,\nMODE (red) and SOUND (blue) buttons, buzzer.\n"
                              "Power bank in a pouch on the back.", 13)
    s.rect(bx - 40, Y(1220) - 6, 80, 16, fill="#222", rx=6)
    s.note(bx + 210, Y(1210), "handle on top", 13)
    s.note(40, 140, "Nothing metal below 750 mm:\nnylon zip ties, wood, glue, tape.\nSteel screws only up at the head.", 14)

    # how to hold it: plan view
    hx, hy = 1180, 250
    s.rect(hx - 210, hy - 150, 420, 420, fill="#fafafa", stroke="#bbb", rx=8)
    s.text(hx, hy - 120, "How to hold it (seen from above)", 16, "middle", "bold")
    s.line(hx, hy - 90, hx, hy + 190, "#111", 8)
    s.text(hx + 14, hy - 80, "cable", 13, weight="bold")
    s.rect(hx - 45, hy + 70, 90, 16, fill=C["wood"], stroke="#8b5a2b")
    s.text(hx + 55, hy + 84, "board", 13)
    s.circle(hx, hy + 150, 26, fill="#ffe0c0")
    s.text(hx, hy + 156, "you", 13, "middle", "bold")
    s.arrow(hx - 60, hy + 200, hx - 60, hy + 120, C["sig"], 2)
    s.note(hx - 200, hy + 230, "Face along the cable, board face toward you.\n"
                               "Step left/right across it; the arrow on the\n"
                               "screen points the way to go.", 13)
    s.save("staff.svg")


# =========================================================== 7. the physics ==
def draw_field():
    s = Svg(1300, 760, "What the four coils see")
    lx, ly = 470, 640
    s.rect(0, 380, 1300, 380, fill=C["soil"], stroke="none")
    s.line(0, 380, 1300, 380, "#8b7355", 3)
    for r in (60, 130, 210, 300, 400):
        s.circle(lx, ly, r, stroke=C["field"], sw=1.6)
    s.circle(lx, ly, 12, fill="#111")
    s.text(lx + 20, ly + 40, "cable, current coming toward you", 14, weight="bold")
    stx = lx + 160
    # staff
    s.rect(stx - 6, 100, 12, 282, fill=C["wood"], stroke="#8b5a2b", sw=1)
    for y, nm in ((360, "bottom"), (170, "top")):
        s.rect(stx - 26, y - 6, 52, 12, fill=C["ferrite"])
        s.rect(stx + 10, y - 26, 10, 52, fill="#999")
        # field vector at the coil (perpendicular to radius)
        dx, dy = stx - lx, y - ly
        r = math.hypot(dx, dy)
        bx, by = -dy / r, dx / r
        Lb = 70 * 300 / r
        s.arrow(stx, y, stx - bx * Lb, y - by * Lb, C["out"], 3)
        s.text(stx + 34, y + 5, nm + " pair", 14, weight="bold")
    s.line(lx, ly, stx, 360, "#999", 1.5, dash="6,5")
    s.wire([(lx, ly), (lx, 360), (stx, 360)], "#999", 1.5, dash="3,4")
    s.text(lx - 12, 500, "h", 18, "end", "bold")
    s.text((lx + stx) / 2, 352, "x", 18, "middle", "bold")
    s.arrow(stx - 60, 360, stx - 60, 170, sw=1.5)
    s.text(stx - 68, 270, "d = 0.5 m", 14, "end", "bold")
    s.rect(800, 70, 480, 300, fill="white", stroke="#ccc", rx=8)
    lines = [("Field of a long straight current:", False),
             ("B = μ₀ I / (2π r)", True),
             ("At a coil x to the side and h above it:", False),
             ("Bx = k h / (x² + h²)", True),
             ("By = k x / (x² + h²)", True),
             ("Right overhead (x = 0), By = 0 and", False),
             ("h = d · Bx(top) / (Bx(bottom) − Bx(top))", True),
             ("The current (inside k) cancels. Four readings,", False),
             ("three unknowns (x, h, k): the spare one checks", False),
             ("that the field really is one straight line.", False)]
    y = 100
    for t, eq in lines:
        s.text(820 + (20 if eq else 0), y, t, 15, weight="bold" if eq else "normal",
               color="#222" if eq else C["note"])
        y += 28 if eq else 26
    s.save("field.svg")


# ===================================================== 8. calibration loop ==
def draw_cal_loop():
    s = Svg(1500, 900, "Stage 1 calibration loop (seen from above)")
    k = 62.0                                    # px per metre
    nx, top = 1000, 110                         # near leg x, top of the loop
    L, W = 9.0, 5.0
    bot = top + L * k
    fx = nx - W * k
    s.rect(fx, top, W * k, L * k, fill="#f7f3ea", stroke="none")
    s.wire([(nx, top), (fx, top), (fx, bot), (nx, bot)], C["copper"], 4)
    s.wire([(nx, top), (nx, bot - 4)], C["copper"], 4)
    s.text((nx + fx) / 2, top - 14, "5 m (16 ft 5 in)", 15, "middle", "bold")
    s.text(fx - 14, (top + bot) / 2, "9 m", 15, "end", "bold")
    s.text(fx - 14, (top + bot) / 2 + 18, "(29 ft 6 in)", 13, "end")
    s.text((nx + fx) / 2, (top + bot) / 2, "the rest of the loop is on your LEFT", 15, "middle", color=C["note"])
    for cx, cy in ((nx, top), (fx, top), (fx, bot)):
        s.circle(cx, cy, 6, fill="#666")
    s.note(fx - 10, bot + 26, "corners pegged and square (3-4-5)", 13)
    # the user, flags
    my = (top + bot) / 2
    s.circle(nx, my + 36, 18, fill="#ffe0c0")
    s.text(nx, my + 41, "you", 12, "middle", "bold")
    s.arrow(nx + 40, my + 60, nx + 40, my - 10, C["sig"], 2)
    s.text(nx + 48, my + 20, "face along the wire", 13)
    for i, (off, lab) in enumerate(((-0.8, "31.5 in"), (-0.5, "19.7 in"), (0.5, "19.7 in"), (0.8, "31.5 in"))):
        x = nx + off * k * 2.2
        s.path("M %f %f L %f %f L %f %f Z" % (x, my - 70, x + 12, my - 64, x, my - 58), fill="#d62728")
        s.line(x, my - 70, x, my - 40, sw=2)
        s.text(x, my - 80 - (i % 2) * 16, lab, 11, "middle")
    s.note(nx - 150, my - 130, "flags, square to the wire, at its middle", 13)
    s.note(nx - 150, my - 114, "(flag spacing drawn larger than scale)", 11)
    # the corner connection, near-leg end at the bottom
    s.wire([(nx, bot - 4), (nx, bot + 40)], C["copper"], 3)
    s.wire([(nx - 12, bot), (nx - 12, bot + 40)], C["copper"], 3)
    s.circle(nx, bot + 46, 6, fill="#222")
    s.circle(nx - 12, bot + 46, 6, fill="#222")
    s.text(nx + 14, bot + 50, "the loop's two ends, clipped on here", 13)

    # the cable detail, left side
    dx, dy = 70, 140
    s.rect(dx, dy - 30, 520, 300, fill="#fafafa", stroke="#bbb", rx=8)
    s.text(dx + 16, dy - 6, "The TRS cable", 16, weight="bold")
    s.rect(dx + 20, dy + 40, 70, 34, fill="#bbb", rx=6)
    s.rect(dx + 90, dy + 48, 50, 18, fill="#ddd", stroke="#222", sw=1)
    s.line(dx + 104, dy + 48, dx + 104, dy + 66, sw=3)
    s.line(dx + 122, dy + 48, dx + 122, dy + 66, sw=3)
    s.text(dx + 20, dy + 18, "\u00bc in TRS plug into MAIN OUT L", 12)
    s.text(dx + 144, dy + 44, "T", 13, weight="bold")
    s.text(dx + 120, dy + 44, "R", 13, weight="bold")
    s.text(dx + 98, dy + 44, "S", 13, weight="bold")
    s.wire([(dx + 140, dy + 57), (dx + 200, dy + 57)], C["pwr"], 2.5)
    s.text(dx + 205, dy + 46, "tip", 12)
    s.resistor(dx + 240, dy + 57, 80, label="47 \u03a9", value="\u00bd W")
    s.wire([(dx + 200, dy + 57), (dx + 240, dy + 57)], C["pwr"], 2.5)
    s.wire([(dx + 320, dy + 57), (dx + 420, dy + 57)], C["pwr"], 2.5)
    s.text(dx + 430, dy + 62, "clip to one end", 13)
    s.wire([(dx + 122, dy + 66), (dx + 122, dy + 150), (dx + 420, dy + 150)], C["gnd"], 2.5)
    s.text(dx + 205, dy + 142, "ring", 12)
    s.text(dx + 430, dy + 155, "clip to the other", 13)
    s.wire([(dx + 104, dy + 66), (dx + 104, dy + 200)], "#999", 2, dash="4,4")
    s.text(dx + 112, dy + 205, "sleeve / shield: cut back and taped, unused", 12)
    s.note(dx + 16, dy + 248, "Interface: MIX fully to PLAYBACK, MAIN at about 3 o'clock.\n"
                              "calibrate.py plays the tone itself: 90 Hz, then 8 kHz, then 33 kHz.", 13)
    s.note(70, 520, "Why a loop and not one straight wire: a loop needs no ground\n"
                    "stakes (dry ground can be hundreds of ohms) and takes little\n"
                    "current. Its far side and ends DO bend the field the coils see,\n"
                    "by 15 to 40 % on the vertical coils, so the software calculates\n"
                    "all four sides with the finite-wire Biot-Savart formula.\n\n"
                    "If your loop isn't exactly 9 m x 5 m, measure it and set\n"
                    "CAL_LOOP_LENGTH and CAL_LOOP_WIDTH in locator/config.py.", 14)
    s.save("cal_loop.svg")


if __name__ == "__main__":
    draw_system()
    draw_receiver()
    draw_transmitter()
    draw_coil()
    draw_clamp()
    draw_staff()
    draw_field()
    draw_cal_loop()
