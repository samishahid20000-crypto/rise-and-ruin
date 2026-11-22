import math
from mfigure import font

WHITE = (233, 233, 237)
GREY = (120, 120, 128)
RED = (228, 44, 36)
YEL = (255, 214, 10)
INK = (18, 18, 20)


def _w(s):
    return max(3, int(s * 0.022))


def _e(d, x, y, r, **k):
    d.ellipse((x - r, y - r, x + r, y + r), **k)


def clock(d, x, b, s, t, down):
    lw = _w(s); r = s * 0.4; cy = b - r - s * 0.05
    _e(d, x, cy, r, outline=WHITE, width=lw, fill=INK)
    for i in range(12):
        a = math.radians(i * 30)
        d.line((x + math.sin(a) * r * 0.82, cy - math.cos(a) * r * 0.82, x + math.sin(a) * r * 0.94,
                cy - math.cos(a) * r * 0.94), fill=GREY, width=lw)
    a = math.radians(t * 90)
    d.line((x, cy, x + math.sin(a) * r * 0.55, cy - math.cos(a) * r * 0.55), fill=WHITE, width=lw + 2)
    a = math.radians(t * 360 * 0.6)
    d.line((x, cy, x + math.sin(a) * r * 0.8, cy - math.cos(a) * r * 0.8), fill=RED, width=lw)
    _e(d, x, cy, lw * 1.3, fill=RED)


def hourglass(d, x, b, s, t, down):
    lw = _w(s); w = s * 0.4; top = b - s * 0.9
    d.polygon([(x - w, top), (x + w, top), (x, b - s * 0.45)], outline=WHITE)
    d.polygon([(x - w, b), (x + w, b), (x, b - s * 0.45)], outline=WHITE)
    d.line((x - w, top, x + w, top), fill=WHITE, width=lw + 2)
    d.line((x - w, b, x + w, b), fill=WHITE, width=lw + 2)
    p = min(1.0, t / 3.5)
    d.polygon([(x - w * 0.8 * (1 - p), top + s * 0.06 + p * s * 0.3), (x + w * 0.8 * (1 - p), top + s * 0.06 + p * s * 0.3),
               (x, b - s * 0.46)], fill=YEL)
    d.polygon([(x - w * 0.7 * p, b - 3), (x + w * 0.7 * p, b - 3), (x, b - s * 0.1 - p * s * 0.25)], fill=YEL)
    d.line((x, b - s * 0.45, x, b - s * 0.05), fill=YEL, width=2)


def calendar(d, x, b, s, t, down):
    lw = _w(s); w, h = s * 0.8, s * 0.75; x0, y0 = x - w / 2, b - h
    d.rectangle((x0, y0, x0 + w, b), outline=WHITE, width=lw, fill=INK)
    d.rectangle((x0, y0, x0 + w, y0 + h * 0.2), fill=RED)
    n = 0
    for r in range(4):
        for c in range(5):
            cx_, cy_ = x0 + w * (0.12 + c * 0.19), y0 + h * (0.35 + r * 0.17)
            if t > 0.2 + n * 0.12:
                d.line((cx_ - 9, cy_ - 9, cx_ + 9, cy_ + 9), fill=RED, width=3)
                d.line((cx_ - 9, cy_ + 9, cx_ + 9, cy_ - 9), fill=RED, width=3)
            else:
                _e(d, cx_, cy_, 4, fill=GREY)
            n += 1


def globe(d, x, b, s, t, down):
    lw = _w(s); r = s * 0.4; cy = b - r - s * 0.05
    _e(d, x, cy, r, outline=WHITE, width=lw, fill=INK)
    d.line((x - r, cy, x + r, cy), fill=GREY, width=lw)
    for k in (-0.5, 0.5):
        d.arc((x - r * 1.0, cy + k * r - r * 0.35, x + r * 1.0, cy + k * r + r * 0.35), 0, 360, fill=GREY, width=2)
    for i in range(3):
        wd = abs(math.cos(t * 0.8 + i * 1.05)) * r
        d.ellipse((x - wd, cy - r, x + wd, cy + r), outline=GREY, width=2)
    d.arc((x - r, cy - r, x + r, cy + r), 200, 250, fill=RED, width=lw + 2)


def bank(d, x, b, s, t, down):
    lw = _w(s)
    d.polygon([(x - s * 0.5, b - s * 0.6), (x, b - s * 0.9), (x + s * 0.5, b - s * 0.6)], outline=WHITE, fill=INK)
    for i in range(4):
        cx = x - s * 0.36 + i * s * 0.24
        d.rectangle((cx - s * 0.05, b - s * 0.55, cx + s * 0.05, b - s * 0.12), outline=WHITE, width=lw)
    d.rectangle((x - s * 0.52, b - s * 0.12, x + s * 0.52, b), outline=WHITE, width=lw)
    d.text((x, b - s * 0.7), "$", font=font(s * 0.16), fill=YEL, anchor="mm")


def store(d, x, b, s, t, down):
    lw = _w(s); w, h = s * 0.9, s * 0.5
    d.rectangle((x - w / 2, b - h, x + w / 2, b), outline=WHITE, width=lw, fill=INK)
    for i in range(6):
        d.rectangle((x - w / 2 + i * w / 6, b - h - s * 0.12, x - w / 2 + (i + 1) * w / 6, b - h + s * 0.05),
                    fill=RED if i % 2 == 0 else WHITE)
    d.rectangle((x - w * 0.1, b - h * 0.6, x + w * 0.1, b), outline=WHITE, width=lw)
    d.rectangle((x + w * 0.2, b - h * 0.7, x + w * 0.42, b - h * 0.35), outline=YEL, width=lw)


def cart(d, x, b, s, t, down):
    lw = _w(s)
    d.polygon([(x - s * 0.35, b - s * 0.62), (x + s * 0.4, b - s * 0.62), (x + s * 0.3, b - s * 0.28),
               (x - s * 0.25, b - s * 0.28)], outline=WHITE, fill=INK)
    d.line((x - s * 0.35, b - s * 0.62, x - s * 0.48, b - s * 0.78, x - s * 0.6, b - s * 0.78), fill=WHITE, width=lw)
    _e(d, x - s * 0.15, b - s * 0.1, s * 0.07, outline=WHITE, width=lw)
    _e(d, x + s * 0.2, b - s * 0.1, s * 0.07, outline=WHITE, width=lw)


def truck(d, x, b, s, t, down):
    lw = _w(s); off = math.sin(t * 4) * 3
    d.rectangle((x - s * 0.5, b - s * 0.55 + off, x + s * 0.15, b - s * 0.14), outline=WHITE, width=lw, fill=INK)
    d.polygon([(x + s * 0.15, b - s * 0.45 + off), (x + s * 0.42, b - s * 0.45 + off), (x + s * 0.52, b - s * 0.28 + off),
               (x + s * 0.52, b - s * 0.14 + off), (x + s * 0.15, b - s * 0.14 + off)], outline=RED, fill=INK)
    for cx in (x - s * 0.3, x + s * 0.32):
        _e(d, cx, b - s * 0.1, s * 0.09, outline=WHITE, width=lw, fill=INK)


def plane(d, x, b, s, t, down):
    lw = _w(s); y = b - s * 0.5 - math.sin(t * 2) * s * 0.03
    d.ellipse((x - s * 0.5, y - s * 0.07, x + s * 0.5, y + s * 0.07), outline=WHITE, width=lw, fill=INK)
    d.polygon([(x - s * 0.05, y), (x - s * 0.3, y - s * 0.36), (x - s * 0.18, y - s * 0.36), (x + s * 0.15, y)], outline=WHITE)
    d.polygon([(x - s * 0.05, y), (x - s * 0.3, y + s * 0.3), (x - s * 0.18, y + s * 0.3), (x + s * 0.15, y)], outline=WHITE)
    d.polygon([(x - s * 0.46, y), (x - s * 0.56, y - s * 0.2), (x - s * 0.4, y - s * 0.02)], fill=RED)


def newspaper(d, x, b, s, t, down):
    lw = _w(s); w, h = s * 0.7, s * 0.8
    d.rectangle((x - w / 2, b - h, x + w / 2, b), outline=WHITE, width=lw, fill=INK)
    d.rectangle((x - w * 0.42, b - h * 0.92, x + w * 0.42, b - h * 0.74), fill=RED if down else YEL)
    d.rectangle((x - w * 0.42, b - h * 0.65, x - w * 0.05, b - h * 0.35), outline=GREY, width=2)
    for k in range(5):
        d.line((x, b - h * 0.62 + k * h * 0.1, x + w * 0.42, b - h * 0.62 + k * h * 0.1), fill=GREY, width=3)
    for k in range(3):
        d.line((x - w * 0.42, b - h * 0.28 + k * h * 0.08, x + w * 0.42, b - h * 0.28 + k * h * 0.08), fill=GREY, width=3)


def contract(d, x, b, s, t, down):
    lw = _w(s); w, h = s * 0.62, s * 0.82
    d.rectangle((x - w / 2, b - h, x + w / 2, b), outline=WHITE, width=lw, fill=INK)
    for k in range(6):
        d.line((x - w * 0.38, b - h * 0.85 + k * h * 0.09, x + w * 0.38, b - h * 0.85 + k * h * 0.09), fill=GREY, width=3)
    p = min(1.0, t / 1.2)
    pts = [(x - w * 0.3 + i * w * 0.05, b - h * 0.2 + math.sin(i * 1.3) * h * 0.04) for i in range(int(12 * p) + 1)]
    if len(pts) > 1:
        d.line(pts, fill=RED, width=lw)
    _e(d, x + w * 0.3, b - h * 0.18, s * 0.06, fill=YEL)


def magnifier(d, x, b, s, t, down):
    lw = _w(s); r = s * 0.27; cx = x - s * 0.06 + math.sin(t * 2) * s * 0.04; cy = b - s * 0.6
    _e(d, cx, cy, r, outline=WHITE, width=int(lw * 1.5), fill=INK)
    d.line((cx + r * 0.7, cy + r * 0.7, cx + s * 0.4, b - s * 0.05), fill=YEL, width=lw * 2)
    d.text((cx, cy), "?", font=font(r * 1.1), fill=RED, anchor="mm")


def crown(d, x, b, s, t, down, crack=False):
    lw = _w(s); w, h = s * 0.8, s * 0.55; x0, x1 = x - w / 2, x + w / 2
    sh = math.sin(t * 40) * 3 if crack and t > 0.5 else 0
    pts = [(x0 + sh, b), (x0 + sh, b - h * 0.6), (x0 + w * 0.2 + sh, b - h * 0.3), (x + sh, b - h),
           (x1 - w * 0.2 + sh, b - h * 0.3), (x1 + sh, b - h * 0.6), (x1 + sh, b)]
    d.polygon(pts, outline=YEL, fill=INK)
    d.line(pts + [pts[0]], fill=YEL, width=lw + 1)
    for dx in (-0.2, 0, 0.2):
        _e(d, x + dx * s + sh, b - h * 0.2, s * 0.04, fill=RED)
    if crack:
        k = min(1.0, max(0.0, (t - 0.4) / 1.0))
        z = [(x + s * 0.02, b - s * 0.55), (x - s * 0.06, b - s * 0.42), (x + s * 0.07, b - s * 0.3),
             (x - s * 0.05, b - s * 0.16), (x + s * 0.03, b)]
        n = max(0, int(len(z) * k))
        if n >= 2:
            d.line(z[:n], fill=RED, width=lw * 2)


def crown_crack(d, x, b, s, t, down):
    crown(d, x, b, s, t, down, True)


def lock(d, x, b, s, t, down):
    lw = _w(s); w, h = s * 0.5, s * 0.4
    d.arc((x - w * 0.34, b - h - s * 0.4, x + w * 0.34, b - h + s * 0.1), 180, 360, fill=WHITE, width=lw * 2)
    d.rounded_rectangle((x - w / 2, b - h, x + w / 2, b), radius=int(s * 0.04), outline=WHITE, width=lw, fill=INK)
    _e(d, x, b - h * 0.55, s * 0.04, fill=YEL)
    d.line((x, b - h * 0.55, x, b - h * 0.2), fill=YEL, width=lw)


def _stick(d, x, b, h, col, lw, arm=0):
    r = h * 0.12
    _e(d, x, b - h + r, r, outline=col, width=lw, fill=INK)
    d.line((x, b - h + 2 * r, x, b - h * 0.4), fill=col, width=lw)
    d.line((x, b - h * 0.4, x - h * 0.15, b), fill=col, width=lw)
    d.line((x, b - h * 0.4, x + h * 0.15, b), fill=col, width=lw)
    d.line((x - h * 0.2, b - h * 0.45 - arm, x, b - h * 0.68, x + h * 0.2, b - h * 0.45 - arm), fill=col, width=lw)


def people(d, x, b, s, t, down):
    h = s * 0.5; lw = max(3, int(s * 0.018))
    for i in range(5):
        px = x + (i - 2) * s * 0.2
        _stick(d, px, b, h * (0.85 + 0.15 * (i % 2)), RED if i == 2 else WHITE, lw,
               arm=h * 0.3 * abs(math.sin(t * 3 + i)))


def explosion(d, x, b, s, t, down):
    cy = b - s * 0.5; k = min(1.0, t / 0.4); pulse = 1 + 0.06 * math.sin(t * 12)
    pts = []
    for i in range(16):
        a = math.pi * 2 * i / 16
        r = s * (0.5 if i % 2 == 0 else 0.26) * k * pulse
        pts.append((x + math.cos(a) * r, cy + math.sin(a) * r))
    d.polygon(pts, fill=RED)
    d.polygon([(x + (px - x) * 0.55, cy + (py - cy) * 0.55) for px, py in pts], fill=YEL)


def question(d, x, b, s, t, down):
    d.text((x, b - s * 0.5), "?", font=font(s * 0.95), fill=YEL, anchor="mm")


def laptop(d, x, b, s, t, down):
    lw = _w(s)
    d.rounded_rectangle((x - s * 0.4, b - s * 0.68, x + s * 0.4, b - s * 0.1), radius=int(s * 0.03), outline=WHITE, width=lw, fill=INK)
    for i in range(4):
        d.line((x - s * 0.3, b - s * 0.55 + i * s * 0.09, x - s * 0.3 + s * (0.25 + 0.12 * ((i + int(t * 2)) % 3)), b - s * 0.55 + i * s * 0.09), fill=RED if i == 1 else GREY, width=4)
    d.polygon([(x - s * 0.5, b), (x + s * 0.5, b), (x + s * 0.4, b - s * 0.1), (x - s * 0.4, b - s * 0.1)], outline=WHITE)


def tv(d, x, b, s, t, down):
    lw = _w(s)
    d.rounded_rectangle((x - s * 0.45, b - s * 0.65, x + s * 0.45, b - s * 0.05), radius=int(s * 0.05), outline=WHITE, width=lw, fill=INK)
    d.rectangle((x - s * 0.38, b - s * 0.58, x + s * 0.2, b - s * 0.12), outline=GREY, width=2)
    d.line((x, b - s * 0.65, x - s * 0.18, b - s * 0.86), fill=WHITE, width=lw // 2 + 1)
    d.line((x, b - s * 0.65, x + s * 0.18, b - s * 0.86), fill=WHITE, width=lw // 2 + 1)
    _e(d, x + s * 0.32, b - s * 0.45, s * 0.03, fill=RED)


def fire(d, x, b, s, t, down):
    for sc_, col in ((1.0, RED), (0.7, (255, 140, 30)), (0.42, YEL)):
        w, h = s * 0.5 * sc_, s * 0.85 * sc_ * (1 + 0.05 * math.sin(t * 9 + sc_))
        d.polygon([(x - w * 0.5, b), (x - w * 0.55, b - h * 0.4), (x - w * 0.2, b - h * 0.55), (x - w * 0.1, b - h),
                   (x + w * 0.15, b - h * 0.6), (x + w * 0.55, b - h * 0.35), (x + w * 0.5, b)], fill=col)


def moneybag(d, x, b, s, t, down):
    lw = _w(s)
    d.polygon([(x - s * 0.1, b - s * 0.7), (x + s * 0.1, b - s * 0.7), (x + s * 0.3, b - s * 0.4), (x + s * 0.38, b - s * 0.1),
               (x + s * 0.3, b), (x - s * 0.3, b), (x - s * 0.38, b - s * 0.1), (x - s * 0.3, b - s * 0.4)], outline=WHITE, fill=INK)
    d.line((x - s * 0.12, b - s * 0.7, x + s * 0.12, b - s * 0.7), fill=RED, width=lw * 2)
    d.text((x, b - s * 0.28), "$", font=font(s * 0.3), fill=YEL, anchor="mm")


def target(d, x, b, s, t, down):
    lw = _w(s); cy = b - s * 0.45
    for i, r in enumerate((0.4, 0.28, 0.16)):
        _e(d, x, cy, s * r, outline=RED if i % 2 == 0 else WHITE, width=lw)
    _e(d, x, cy, s * 0.04, fill=YEL)
    k = min(1.0, t / 0.6)
    d.line((x + s * 0.5 * (1 - k), cy - s * 0.5 * (1 - k), x + s * 0.04, cy - s * 0.04), fill=YEL, width=lw)


def rocket(d, x, b, s, t, down):
    lw = _w(s); lift = min(1.0, t / 3.0) * s * 0.3; yb = b - lift
    d.polygon([(x, yb - s * 0.85), (x + s * 0.13, yb - s * 0.5), (x + s * 0.13, yb - s * 0.2), (x - s * 0.13, yb - s * 0.2),
               (x - s * 0.13, yb - s * 0.5)], outline=WHITE, fill=INK)
    _e(d, x, yb - s * 0.52, s * 0.05, outline=RED, width=lw)
    d.polygon([(x - s * 0.13, yb - s * 0.3), (x - s * 0.26, yb - s * 0.1), (x - s * 0.13, yb - s * 0.2)], fill=RED)
    d.polygon([(x + s * 0.13, yb - s * 0.3), (x + s * 0.26, yb - s * 0.1), (x + s * 0.13, yb - s * 0.2)], fill=RED)
    f = s * (0.18 + 0.06 * math.sin(t * 20))
    d.polygon([(x - s * 0.08, yb - s * 0.2), (x + s * 0.08, yb - s * 0.2), (x, yb - s * 0.2 + f)], fill=YEL)


def book(d, x, b, s, t, down):
    lw = _w(s); w, h = s * 0.62, s * 0.8
    d.rectangle((x - w / 2, b - h, x + w / 2, b), outline=WHITE, width=lw, fill=INK)
    d.rectangle((x - w / 2, b - h, x - w / 2 + w * 0.12, b), fill=RED)
    d.rectangle((x - w * 0.2, b - h * 0.75, x + w * 0.35, b - h * 0.6), fill=YEL)


def camera(d, x, b, s, t, down):
    lw = _w(s)
    d.rounded_rectangle((x - s * 0.45, b - s * 0.55, x + s * 0.45, b - s * 0.05), radius=int(s * 0.06), outline=WHITE, width=lw, fill=INK)
    _e(d, x, b - s * 0.3, s * 0.16, outline=WHITE, width=lw)
    _e(d, x, b - s * 0.3, s * 0.07, fill=RED)
    d.rectangle((x - s * 0.3, b - s * 0.65, x - s * 0.05, b - s * 0.55), outline=WHITE)


def lightning(d, x, b, s, t, down):
    k = 1 if int(t * 6) % 2 == 0 else 0.85
    d.polygon([(x + s * 0.1, b - s * 0.9), (x - s * 0.25, b - s * 0.4 * k), (x - s * 0.02, b - s * 0.4 * k),
               (x - s * 0.12, b - s * 0.02), (x + s * 0.28, b - s * 0.52 * k), (x + s * 0.04, b - s * 0.52 * k)], fill=YEL)


EXTRA = {"clock": clock, "hourglass": hourglass, "calendar": calendar, "globe": globe, "bank": bank, "store": store,
         "cart": cart, "truck": truck, "plane": plane, "newspaper": newspaper, "contract": contract,
         "magnifier": magnifier, "crown": crown, "crown_crack": crown_crack, "lock": lock, "people": people,
         "explosion": explosion, "question": question, "laptop": laptop, "tv": tv, "fire": fire,
         "moneybag": moneybag, "target": target, "rocket": rocket, "book": book, "camera": camera,
         "lightning": lightning}


def draw_extra(d, kind, x, base, s, t, down):
    f = EXTRA.get(kind)
    if f:
        f(d, x, base, s, t, down)
        return True
    return False
  
