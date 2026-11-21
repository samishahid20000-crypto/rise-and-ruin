import math, textwrap
from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
GOLD = (245, 197, 66)
WHITE = (245, 245, 245)
RED = (226, 62, 62)
GREY = (140, 140, 150)
DARK = (34, 34, 40)
BLUE = (80, 150, 225)
GREEN = (70, 190, 110)
ORANGE = (255, 145, 40)
SS = 2  # supersampling

BG = {
    "rise": ((30, 26, 14), (84, 62, 18)),
    "crack": ((26, 26, 30), (66, 40, 40)),
    "ruin": ((26, 12, 12), (84, 26, 26)),
    "neutral": ((22, 22, 28), (46, 46, 58)),
}


def font(size):
    try:
        return ImageFont.truetype(FONT, int(size))
    except Exception:
        return ImageFont.load_default()


def lw_of(s):
    return max(3, int(s * 0.035))


def dot(d, x, y, r, fill):
    d.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def seg(d, p, q, w, col):
    d.line([p, q], fill=col, width=int(w))
    dot(d, p[0], p[1], w / 2, col)
    dot(d, q[0], q[1], w / 2, col)


def text_center(d, x, y, txt, size, fill, stroke=0, stroke_fill=(0, 0, 0)):
    f = font(size)
    w = d.textlength(txt, font=f)
    d.text((x - w / 2, y - size / 2), txt, font=f, fill=fill,
           stroke_width=int(stroke), stroke_fill=stroke_fill)


# ---------------- stick figure ----------------
POSES = {
    #        left arm (upper, lower)  right arm       left leg right leg  head dx  mood
    "stand": ((-15, -10), (15, 10), -10, 10, 0, "smile"),
    "point": ((-15, -10), (88, 90), -10, 10, 0, "smile"),
    "cheer": ((-125, -158), (125, 158), -14, 14, 0, "smile"),
    "sad": ((-22, -12), (22, 12), -6, 6, 0.05, "sad"),
    "think": ((-12, -8), (35, 155), -10, 10, 0, "flat"),
    "shrug": ((-50, -160), (50, 160), -10, 10, 0, "flat"),
    "run": ((60, 20), (-60, -20), -38, 30, 0.03, "flat"),
    "panic": ((-118, -152), (118, 152), -30, 30, 0, "shock"),
}


def vec(angle, length):
    a = math.radians(angle)
    return math.sin(a) * length, math.cos(a) * length


def figure(d, cx, base, h, pose="stand", col=WHITE):
    la, ra, ll, rl, hdx, mood = POSES.get(pose, POSES["stand"])
    w = max(4, h * 0.035)
    head_r = h * 0.11
    leg = h * 0.34
    body = h * 0.30
    hip = (cx, base - leg)
    neck = (cx, hip[1] - body)
    head_c = (cx + hdx * h, neck[1] - head_r * 1.05)
    # legs
    for ang in (ll, rl):
        dx, dy = vec(ang, leg)
        seg(d, hip, (hip[0] + dx, hip[1] + dy), w, col)
    # body
    seg(d, neck, hip, w, col)
    # arms
    sh = (cx, neck[1] + h * 0.05)
    for up, lo in (la, ra):
        ux, uy = vec(up, h * 0.16)
        elbow = (sh[0] + ux, sh[1] + uy)
        lx, ly = vec(lo, h * 0.16)
        seg(d, sh, elbow, w, col)
        seg(d, elbow, (elbow[0] + lx, elbow[1] + ly), w, col)
    # tie (brand touch)
    d.polygon([(cx, neck[1] + h * 0.01), (cx - h * 0.03, neck[1] + h * 0.09),
               (cx, neck[1] + h * 0.15), (cx + h * 0.03, neck[1] + h * 0.09)], fill=GOLD)
    # head
    d.ellipse((head_c[0] - head_r, head_c[1] - head_r, head_c[0] + head_r, head_c[1] + head_r),
              fill=col, outline=col)
    ex = head_r * 0.38
    ey = head_c[1] - head_r * 0.12
    er = max(2, head_r * 0.11)
    dot(d, head_c[0] - ex, ey, er, DARK)
    dot(d, head_c[0] + ex, ey, er, DARK)
    my = head_c[1] + head_r * 0.42
    mw = head_r * 0.45
    lwm = max(2, int(head_r * 0.10))
    if mood == "smile":
        d.arc((head_c[0] - mw, my - mw * 0.9, head_c[0] + mw, my + mw * 0.5), 10, 170, fill=DARK, width=lwm)
    elif mood == "sad":
        d.arc((head_c[0] - mw, my - mw * 0.2, head_c[0] + mw, my + mw * 1.2), 190, 350, fill=DARK, width=lwm)
    elif mood == "shock":
        d.ellipse((head_c[0] - mw * 0.4, my - mw * 0.2, head_c[0] + mw * 0.4, my + mw * 0.6), outline=DARK, width=lwm)
    else:
        d.line([(head_c[0] - mw * 0.6, my + mw * 0.1), (head_c[0] + mw * 0.6, my + mw * 0.1)], fill=DARK, width=lwm)


# ---------------- props ----------------
def p_phone(d, cx, b, s):
    w, h, L = s * 0.36, s * 0.82, lw_of(s)
    d.rounded_rectangle((cx - w / 2, b - h, cx + w / 2, b), radius=s * 0.05, fill=(58, 60, 72), outline=WHITE, width=L)
    d.rectangle((cx - w * 0.36, b - h * 0.92, cx + w * 0.36, b - h * 0.66), fill=(125, 205, 150))
    for i in range(3):
        for j in range(3):
            dot(d, cx - w * 0.22 + i * w * 0.22, b - h * 0.5 + j * h * 0.11, s * 0.022, GREY)
    d.rectangle((cx + w * 0.18, b - h - s * 0.1, cx + w * 0.26, b - h), fill=WHITE)


def p_smartphone(d, cx, b, s):
    w, h, L = s * 0.42, s * 0.84, lw_of(s)
    d.rounded_rectangle((cx - w / 2, b - h, cx + w / 2, b), radius=s * 0.07, fill=(18, 18, 22), outline=WHITE, width=L)
    d.rounded_rectangle((cx - w * 0.43, b - h * 0.95, cx + w * 0.43, b - h * 0.12), radius=s * 0.03, fill=BLUE)
    dot(d, cx, b - h * 0.06, s * 0.025, GREY)


def p_tower(d, cx, b, s):
    L = lw_of(s)
    top = (cx, b - s * 0.92)
    l, r = (cx - s * 0.24, b), (cx + s * 0.24, b)
    seg(d, top, l, L, WHITE)
    seg(d, top, r, L, WHITE)
    for t in (0.3, 0.5, 0.7, 0.88):
        y = top[1] + (b - top[1]) * t
        hw = s * 0.24 * t
        seg(d, (cx - hw, y), (cx + hw, y), L * 0.7, WHITE)
        if t < 0.85:
            y2 = top[1] + (b - top[1]) * (t + 0.18)
            hw2 = s * 0.24 * (t + 0.18)
            seg(d, (cx - hw, y), (cx + hw2, y2), L * 0.6, GREY)
            seg(d, (cx + hw, y), (cx - hw2, y2), L * 0.6, GREY)
    dot(d, top[0], top[1], s * 0.04, GOLD)
    for k in (1, 2, 3):
        rr = s * 0.09 * k
        d.arc((top[0] - rr, top[1] - rr, top[0] + rr, top[1] + rr), 300, 60, fill=GOLD, width=L)
        d.arc((top[0] - rr, top[1] - rr, top[0] + rr, top[1] + rr), 120, 240, fill=GOLD, width=L)


def p_wires(d, cx, b, s):
    L = lw_of(s)
    x0, x1 = cx - s * 0.45, cx + s * 0.45
    ty = b - s * 0.8
    for x in (x0, x1):
        d.rectangle((x - L, ty, x + L, b), fill=(120, 90, 60))
        seg(d, (x - s * 0.1, ty + s * 0.06), (x + s * 0.1, ty + s * 0.06), L, (120, 90, 60))
    for k, col in enumerate((WHITE, GREY, GOLD)):
        pts = []
        for i in range(31):
            t = i / 30
            x = x0 + (x1 - x0) * t
            y = ty + s * 0.02 + k * s * 0.07 + math.sin(math.pi * t) * s * 0.12
            pts.append((x, y))
        d.line(pts, fill=col, width=int(L * 0.8))


def p_money(d, cx, b, s):
    w, h, L = s * 0.9, s * 0.46, lw_of(s)
    y0 = b - h
    d.rounded_rectangle((cx - w / 2, y0, cx + w / 2, b), radius=s * 0.04, fill=(48, 130, 80), outline=WHITE, width=L)
    d.ellipse((cx - h * 0.32, y0 + h * 0.18, cx + h * 0.32, y0 + h * 0.82), outline=WHITE, width=L)
    text_center(d, cx, y0 + h / 2, "$", h * 0.42, WHITE)


def p_coins(d, cx, b, s):
    cw, ch = s * 0.62, s * 0.16
    for i in range(5):
        y = b - ch * 0.5 - i * ch * 0.62
        d.ellipse((cx - cw / 2, y - ch / 2, cx + cw / 2, y + ch / 2), fill=GOLD, outline=(150, 105, 20), width=lw_of(s) // 2 + 1)


def _chart(d, cx, b, s, up):
    L = lw_of(s)
    x0, x1, y1, y0 = cx - s * 0.5, cx + s * 0.5, b, b - s * 0.9
    seg(d, (x0, y0), (x0, y1), L, WHITE)
    seg(d, (x0, y1), (x1, y1), L, WHITE)
    vals = [0.1, 0.28, 0.2, 0.45, 0.4, 0.68, 0.9]
    if not up:
        vals = [0.9, 0.7, 0.75, 0.45, 0.5, 0.25, 0.08]
    col = GREEN if up else RED
    pts = [(x0 + s * 0.06 + i * (x1 - x0 - s * 0.12) / 6, y1 - s * 0.05 - v * s * 0.78) for i, v in enumerate(vals)]
    d.line(pts, fill=col, width=int(L * 1.8))
    for p in pts:
        dot(d, p[0], p[1], L, col)
    e = pts[-1]
    dy = -1 if up else 1
    d.polygon([(e[0] + s * 0.07, e[1] + dy * s * 0.0), (e[0] - s * 0.05, e[1] - s * 0.07), (e[0] - s * 0.05, e[1] + s * 0.07)], fill=col)


def p_chart_up(d, cx, b, s):
    _chart(d, cx, b, s, True)


def p_chart_down(d, cx, b, s):
    _chart(d, cx, b, s, False)


def p_building(d, cx, b, s):
    w, h, L = s * 0.46, s * 0.95, lw_of(s)
    d.rectangle((cx - w / 2, b - h, cx + w / 2, b), fill=(66, 78, 104), outline=WHITE, width=L)
    for i in range(3):
        for j in range(6):
            col = GOLD if (i + j) % 3 else (40, 46, 62)
            x = cx - w * 0.36 + i * w * 0.27
            y = b - h * 0.93 + j * h * 0.14
            d.rectangle((x, y, x + w * 0.17, y + h * 0.09), fill=col)


def p_factory(d, cx, b, s):
    w, h, L = s * 0.9, s * 0.4, lw_of(s)
    d.rectangle((cx - w / 2, b - h, cx + w / 2, b), fill=(86, 70, 62), outline=WHITE, width=L)
    for i in range(3):
        x = cx - w / 2 + i * w / 3
        d.polygon([(x, b - h), (x + w / 3, b - h), (x + w / 3, b - h - s * 0.14)], fill=(110, 90, 80), outline=WHITE)
    cxm = cx + w * 0.32
    d.rectangle((cxm - s * 0.05, b - h - s * 0.4, cxm + s * 0.05, b - h), fill=(120, 100, 90), outline=WHITE, width=L // 2 + 1)
    for k in range(3):
        dot(d, cxm + k * s * 0.05, b - h - s * (0.5 + k * 0.1), s * (0.05 + k * 0.02), (150, 150, 160))


def p_store(d, cx, b, s):
    w, h, L = s * 0.9, s * 0.55, lw_of(s)
    d.rectangle((cx - w / 2, b - h, cx + w / 2, b), fill=(70, 70, 84), outline=WHITE, width=L)
    n = 6
    for i in range(n):
        x = cx - w / 2 + i * w / n
        d.rectangle((x, b - h - s * 0.12, x + w / n, b - h + s * 0.08), fill=RED if i % 2 == 0 else WHITE)
    d.rectangle((cx - w * 0.1, b - h * 0.62, cx + w * 0.1, b), fill=(40, 40, 48), outline=WHITE, width=L // 2 + 1)
    d.rectangle((cx + w * 0.2, b - h * 0.7, cx + w * 0.42, b - h * 0.3), fill=(125, 190, 235))


def p_cart(d, cx, b, s):
    L = lw_of(s)
    d.polygon([(cx - s * 0.35, b - s * 0.62), (cx + s * 0.4, b - s * 0.62), (cx + s * 0.3, b - s * 0.28), (cx - s * 0.25, b - s * 0.28)],
              outline=WHITE, fill=(60, 66, 80), width=L)
    seg(d, (cx - s * 0.35, b - s * 0.62), (cx - s * 0.48, b - s * 0.78), L, WHITE)
    seg(d, (cx - s * 0.48, b - s * 0.78), (cx - s * 0.6, b - s * 0.78), L, WHITE)
    dot(d, cx - s * 0.15, b - s * 0.1, s * 0.07, WHITE)
    dot(d, cx + s * 0.2, b - s * 0.1, s * 0.07, WHITE)
    seg(d, (cx - s * 0.25, b - s * 0.28), (cx - s * 0.15, b - s * 0.1), L, WHITE)


def p_truck(d, cx, b, s):
    L = lw_of(s)
    d.rectangle((cx - s * 0.5, b - s * 0.55, cx + s * 0.15, b - s * 0.12), fill=(70, 100, 140), outline=WHITE, width=L)
    d.polygon([(cx + s * 0.15, b - s * 0.45), (cx + s * 0.42, b - s * 0.45), (cx + s * 0.52, b - s * 0.28), (cx + s * 0.52, b - s * 0.12), (cx + s * 0.15, b - s * 0.12)],
              fill=(210, 90, 60), outline=WHITE, width=L)
    for x in (cx - s * 0.3, cx + s * 0.32):
        dot(d, x, b - s * 0.1, s * 0.09, DARK)
        dot(d, x, b - s * 0.1, s * 0.09, DARK)
        d.ellipse((x - s * 0.09, b - s * 0.19, x + s * 0.09, b - s * 0.01), outline=WHITE, width=L)


def p_plane(d, cx, b, s):
    L = lw_of(s)
    y = b - s * 0.45
    d.ellipse((cx - s * 0.5, y - s * 0.08, cx + s * 0.5, y + s * 0.08), fill=(225, 228, 235), outline=WHITE)
    d.polygon([(cx - s * 0.05, y), (cx - s * 0.3, y - s * 0.38), (cx - s * 0.18, y - s * 0.38), (cx + s * 0.15, y)], fill=(180, 190, 205))
    d.polygon([(cx - s * 0.05, y), (cx - s * 0.3, y + s * 0.34), (cx - s * 0.18, y + s * 0.34), (cx + s * 0.15, y)], fill=(160, 170, 188))
    d.polygon([(cx - s * 0.46, y), (cx - s * 0.56, y - s * 0.2), (cx - s * 0.4, y - s * 0.02)], fill=RED)
    for i in range(5):
        dot(d, cx + s * 0.05 + i * s * 0.07, y - s * 0.01, s * 0.015, DARK)


def p_book(d, cx, b, s):
    w, h, L = s * 0.62, s * 0.8, lw_of(s)
    d.rectangle((cx - w / 2, b - h, cx + w / 2, b), fill=(60, 90, 150), outline=WHITE, width=L)
    d.rectangle((cx - w / 2, b - h, cx - w / 2 + w * 0.12, b), fill=(40, 60, 110))
    d.rectangle((cx - w * 0.2, b - h * 0.75, cx + w * 0.35, b - h * 0.6), fill=GOLD)
    for k in range(3):
        seg(d, (cx - w * 0.2, b - h * 0.45 + k * h * 0.1), (cx + w * 0.35, b - h * 0.45 + k * h * 0.1), L * 0.5, WHITE)


def p_laptop(d, cx, b, s):
    L = lw_of(s)
    d.rounded_rectangle((cx - s * 0.4, b - s * 0.68, cx + s * 0.4, b - s * 0.1), radius=s * 0.03, fill=(20, 22, 30), outline=WHITE, width=L)
    d.rectangle((cx - s * 0.34, b - s * 0.62, cx + s * 0.34, b - s * 0.16), fill=(70, 130, 200))
    d.polygon([(cx - s * 0.5, b), (cx + s * 0.5, b), (cx + s * 0.4, b - s * 0.1), (cx - s * 0.4, b - s * 0.1)], fill=(150, 152, 165), outline=WHITE)


def p_tv(d, cx, b, s):
    L = lw_of(s)
    d.rounded_rectangle((cx - s * 0.45, b - s * 0.65, cx + s * 0.45, b - s * 0.05), radius=s * 0.05, fill=(40, 34, 30), outline=WHITE, width=L)
    d.rectangle((cx - s * 0.38, b - s * 0.58, cx + s * 0.2, b - s * 0.12), fill=(120, 190, 220))
    dot(d, cx + s * 0.32, b - s * 0.45, s * 0.03, RED)
    dot(d, cx + s * 0.32, b - s * 0.3, s * 0.03, GREY)
    seg(d, (cx, b - s * 0.65), (cx - s * 0.18, b - s * 0.86), L * 0.6, WHITE)
    seg(d, (cx, b - s * 0.65), (cx + s * 0.18, b - s * 0.86), L * 0.6, WHITE)


def p_camera(d, cx, b, s):
    L = lw_of(s)
    d.rounded_rectangle((cx - s * 0.45, b - s * 0.55, cx + s * 0.45, b - s * 0.05), radius=s * 0.06, fill=(60, 60, 70), outline=WHITE, width=L)
    d.rectangle((cx - s * 0.3, b - s * 0.65, cx - s * 0.05, b - s * 0.55), fill=(90, 90, 100))
    dot(d, cx, b - s * 0.3, s * 0.17, (25, 25, 30))
    dot(d, cx, b - s * 0.3, s * 0.1, BLUE)
    dot(d, cx + s * 0.33, b - s * 0.45, s * 0.03, GOLD)


def p_disc(d, cx, b, s):
    L = lw_of(s)
    r = s * 0.42
    cy = b - r - s * 0.03
    dot(d, cx, cy, r, (200, 205, 220))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=WHITE, width=L)
    dot(d, cx, cy, r * 0.38, (90, 100, 130))
    dot(d, cx, cy, r * 0.14, DARK)


def p_newspaper(d, cx, b, s):
    w, h, L = s * 0.7, s * 0.8, lw_of(s)
    d.rectangle((cx - w / 2, b - h, cx + w / 2, b), fill=(232, 228, 214), outline=WHITE, width=L // 2 + 1)
    d.rectangle((cx - w * 0.42, b - h * 0.9, cx + w * 0.42, b - h * 0.72), fill=(40, 40, 44))
    d.rectangle((cx - w * 0.42, b - h * 0.65, cx - w * 0.05, b - h * 0.35), fill=GREY)
    for k in range(5):
        y = b - h * 0.62 + k * h * 0.1
        seg(d, (cx, y), (cx + w * 0.42, y), L * 0.4, (70, 70, 74))
    for k in range(3):
        y = b - h * 0.28 + k * h * 0.08
        seg(d, (cx - w * 0.42, y), (cx + w * 0.42, y), L * 0.4, (70, 70, 74))


def p_bulb(d, cx, b, s):
    L = lw_of(s)
    cy = b - s * 0.55
    dot(d, cx, cy, s * 0.3, (255, 226, 110))
    for a in range(0, 360, 45):
        x, y = vec(a, s * 0.42)
        x2, y2 = vec(a, s * 0.5)
        seg(d, (cx + x, cy + y), (cx + x2, cy + y2), L * 0.7, GOLD)
    d.rectangle((cx - s * 0.12, cy + s * 0.26, cx + s * 0.12, cy + s * 0.4), fill=GREY)


def p_gear(d, cx, b, s):
    r = s * 0.4
    cy = b - r - s * 0.05
    pts = []
    n = 8
    for i in range(n * 2):
        ang = math.pi * 2 * i / (n * 2)
        rr = r if (i // 1) % 2 == 0 else r * 0.78
        for off in (-0.01, 0.01):
            pts.append((cx + math.cos(ang + off) * rr, cy + math.sin(ang + off) * rr))
    d.polygon(pts, fill=(120, 126, 142), outline=WHITE)
    dot(d, cx, cy, r * 0.38, DARK)
    dot(d, cx, cy, r * 0.18, (120, 126, 142))


def p_lock(d, cx, b, s):
    L = lw_of(s)
    w, h = s * 0.5, s * 0.4
    d.arc((cx - w * 0.34, b - h - s * 0.4, cx + w * 0.34, b - h + s * 0.1), 180, 360, fill=WHITE, width=int(L * 1.8))
    d.rounded_rectangle((cx - w / 2, b - h, cx + w / 2, b), radius=s * 0.04, fill=GOLD, outline=WHITE, width=L)
    dot(d, cx, b - h * 0.55, s * 0.04, DARK)
    d.rectangle((cx - s * 0.015, b - h * 0.55, cx + s * 0.015, b - h * 0.2), fill=DARK)


def _crown_pts(cx, b, s):
    w, h = s * 0.8, s * 0.55
    x0, x1 = cx - w / 2, cx + w / 2
    return [(x0, b), (x0, b - h * 0.6), (x0 + w * 0.2, b - h * 0.3), (cx, b - h), (x1 - w * 0.2, b - h * 0.3), (x1, b - h * 0.6), (x1, b)], (x0, x1, h)


def p_crown(d, cx, b, s):
    pts, (x0, x1, h) = _crown_pts(cx, b, s)
    d.polygon(pts, fill=GOLD, outline=(160, 112, 20))
    for x in (x0, cx, x1):
        pass
    for fx, col in ((cx - s * 0.2, RED), (cx, BLUE), (cx + s * 0.2, GREEN)):
        dot(d, fx, b - h * 0.2, s * 0.05, col)


def p_crown_crack(d, cx, b, s):
    p_crown(d, cx, b, s)
    L = lw_of(s)
    pts = [(cx + s * 0.02, b - s * 0.55), (cx - s * 0.06, b - s * 0.42), (cx + s * 0.07, b - s * 0.3), (cx - s * 0.05, b - s * 0.16), (cx + s * 0.03, b)]
    d.line(pts, fill=RED, width=int(L * 1.6))


def p_contract(d, cx, b, s):
    w, h, L = s * 0.62, s * 0.82, lw_of(s)
    d.rectangle((cx - w / 2, b - h, cx + w / 2, b), fill=(240, 238, 228), outline=WHITE, width=L // 2 + 1)
    for k in range(6):
        y = b - h * 0.85 + k * h * 0.09
        seg(d, (cx - w * 0.38, y), (cx + w * 0.38, y), L * 0.4, GREY)
    sig = [(cx - w * 0.3 + i * w * 0.05, b - h * 0.2 + math.sin(i * 1.3) * h * 0.04) for i in range(12)]
    d.line(sig, fill=BLUE, width=int(L * 0.7))


def p_magnifier(d, cx, b, s):
    L = lw_of(s)
    r = s * 0.28
    cy = b - s * 0.6
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(120, 180, 230), outline=WHITE, width=int(L * 1.5))
    seg(d, (cx + r * 0.7, cy + r * 0.7), (cx + s * 0.42, b - s * 0.05), L * 2, (150, 110, 70))


def p_clock(d, cx, b, s):
    L = lw_of(s)
    r = s * 0.4
    cy = b - r - s * 0.05
    dot(d, cx, cy, r, (240, 240, 235))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=WHITE, width=L)
    seg(d, (cx, cy), (cx, cy - r * 0.7), L, DARK)
    seg(d, (cx, cy), (cx + r * 0.5, cy + r * 0.1), L, DARK)
    dot(d, cx, cy, L, RED)


def p_globe(d, cx, b, s):
    L = lw_of(s)
    r = s * 0.42
    cy = b - r - s * 0.03
    dot(d, cx, cy, r, (50, 110, 190))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=WHITE, width=L)
    d.ellipse((cx - r * 0.45, cy - r, cx + r * 0.45, cy + r), outline=WHITE, width=L // 2 + 1)
    seg(d, (cx - r, cy), (cx + r, cy), L // 2 + 1, WHITE)
    d.polygon([(cx - r * 0.5, cy - r * 0.4), (cx - r * 0.1, cy - r * 0.55), (cx - r * 0.05, cy - r * 0.15), (cx - r * 0.4, cy - r * 0.05)], fill=GREEN)


def p_fire(d, cx, b, s):
    def flame(scale, col):
        w, h = s * 0.5 * scale, s * 0.85 * scale
        d.polygon([(cx - w * 0.5, b), (cx - w * 0.55, b - h * 0.4), (cx - w * 0.2, b - h * 0.55), (cx - w * 0.1, b - h),
                   (cx + w * 0.15, b - h * 0.6), (cx + w * 0.55, b - h * 0.35), (cx + w * 0.5, b)], fill=col)
    flame(1.0, (225, 60, 40))
    flame(0.7, ORANGE)
    flame(0.42, (255, 225, 90))


def p_bank(d, cx, b, s):
    L = lw_of(s)
    d.polygon([(cx - s * 0.5, b - s * 0.6), (cx, b - s * 0.9), (cx + s * 0.5, b - s * 0.6)], fill=(214, 206, 180), outline=WHITE)
    for i in range(4):
        x = cx - s * 0.36 + i * s * 0.24
        d.rectangle((x - s * 0.05, b - s * 0.55, x + s * 0.05, b - s * 0.12), fill=(230, 224, 205), outline=WHITE)
    d.rectangle((cx - s * 0.52, b - s * 0.12, cx + s * 0.52, b), fill=(190, 182, 158), outline=WHITE)


def p_arrow_up(d, cx, b, s):
    w = s * 0.5
    d.polygon([(cx, b - s * 0.9), (cx + w / 2, b - s * 0.45), (cx + w * 0.17, b - s * 0.45), (cx + w * 0.17, b), (cx - w * 0.17, b),
               (cx - w * 0.17, b - s * 0.45), (cx - w / 2, b - s * 0.45)], fill=GREEN)


def p_arrow_down(d, cx, b, s):
    w = s * 0.5
    d.polygon([(cx, b), (cx + w / 2, b - s * 0.45), (cx + w * 0.17, b - s * 0.45), (cx + w * 0.17, b - s * 0.9), (cx - w * 0.17, b - s * 0.9),
               (cx - w * 0.17, b - s * 0.45), (cx - w / 2, b - s * 0.45)], fill=RED)


def p_question(d, cx, b, s):
    text_center(d, cx, b - s * 0.45, "?", s * 0.95, GOLD, stroke=s * 0.02, stroke_fill=(0, 0, 0))


def p_xmark(d, cx, b, s):
    L = lw_of(s) * 3
    seg(d, (cx - s * 0.3, b - s * 0.8), (cx + s * 0.3, b - s * 0.2), L, RED)
    seg(d, (cx + s * 0.3, b - s * 0.8), (cx - s * 0.3, b - s * 0.2), L, RED)


def p_check(d, cx, b, s):
    L = lw_of(s) * 3
    seg(d, (cx - s * 0.32, b - s * 0.45), (cx - s * 0.08, b - s * 0.2), L, GREEN)
    seg(d, (cx - s * 0.08, b - s * 0.2), (cx + s * 0.35, b - s * 0.8), L, GREEN)


def p_explosion(d, cx, b, s):
    cy = b - s * 0.5
    pts = []
    for i in range(16):
        ang = math.pi * 2 * i / 16
        r = s * (0.5 if i % 2 == 0 else 0.26)
        pts.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))
    d.polygon(pts, fill=ORANGE)
    pts2 = [(cx + (x - cx) * 0.6, cy + (y - cy) * 0.6) for x, y in pts]
    d.polygon(pts2, fill=(255, 225, 90))


def p_crowd(d, cx, b, s):
    for i, pose in enumerate(("stand", "cheer", "stand", "shrug")):
        x = cx + (i - 1.5) * s * 0.26
        figure(d, x, b, s * 0.55, pose, col=(190, 190, 200))


def p_label(d, cx, b, s, text="?"):
    L = lw_of(s)
    lines = textwrap.fill(text.upper(), 10).split("\n")[:3]
    w = s * 1.0
    size = s * 0.2
    while size > s * 0.08 and max(d.textlength(ln, font=font(size)) for ln in lines) > w * 0.86:
        size *= 0.92
    h = size * 1.3 * len(lines) + s * 0.16
    d.rounded_rectangle((cx - w / 2, b - h, cx + w / 2, b), radius=s * 0.06, fill=(44, 44, 54), outline=GOLD, width=L)
    for i, ln in enumerate(lines):
        text_center(d, cx, b - h + s * 0.08 + size * 0.65 + i * size * 1.3, ln, size, WHITE)


PROPS = {
    "phone": p_phone, "smartphone": p_smartphone, "tower": p_tower, "wires": p_wires, "money": p_money, "coins": p_coins,
    "chart_up": p_chart_up, "chart_down": p_chart_down, "building": p_building, "factory": p_factory, "store": p_store,
    "cart": p_cart, "truck": p_truck, "plane": p_plane, "book": p_book, "laptop": p_laptop, "tv": p_tv, "camera": p_camera,
    "disc": p_disc, "newspaper": p_newspaper, "bulb": p_bulb, "gear": p_gear, "lock": p_lock, "crown": p_crown,
    "crown_crack": p_crown_crack, "contract": p_contract, "magnifier": p_magnifier, "clock": p_clock, "globe": p_globe,
    "fire": p_fire, "bank": p_bank, "arrow_up": p_arrow_up, "arrow_down": p_arrow_down, "question": p_question,
    "xmark": p_xmark, "check": p_check, "explosion": p_explosion, "crowd": p_crowd,
}
POSE_NAMES = list(POSES.keys())
PROP_NAMES = list(PROPS.keys())


def draw_prop(d, name, cx, b, s):
    name = str(name).strip()
    if name.lower().startswith("label:"):
        p_label(d, cx, b, s, name[6:].strip() or "?")
    elif name.lower() in PROPS:
        PROPS[name.lower()](d, cx, b, s)
    else:
        p_label(d, cx, b, s, name)


# ---------------- scene ----------------
def background(img, act):
    top, bot = BG.get(act, BG["neutral"])
    d = ImageDraw.Draw(img)
    W, H = img.size
    for y in range(H):
        t = y / (H - 1)
        d.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))


def crack_line(d, W, H):
    x = W * 0.5
    pts = [(x, 0)]
    y = 0
    k = 0
    while y < H:
        y += H / 9
        x += (W * 0.05) * (1 if k % 2 == 0 else -1.4)
        pts.append((x, y))
        k += 1
    d.line(pts, fill=(150, 40, 40), width=int(W * 0.006))


def render_scene(scene, W=1280, H=720, path=None, style="scene"):
    act = scene.get("act", "neutral")
    pose = scene.get("pose", "stand")
    props = [p for p in (scene.get("props") or [])][:3]
    caption = str(scene.get("caption", "")).upper().strip()
    w, h = W * SS, H * SS
    img = Image.new("RGB", (w, h))
    background(img, act)
    d = ImageDraw.Draw(img)
    vertical = H > W
    thumb = style == "thumb"
    if act == "crack" or thumb:
        crack_line(d, w, h)

    ground = h * (0.80 if not thumb else 0.93)
    d.line([(0, ground), (w, ground)], fill=(96, 96, 108), width=int(h * 0.004))
    if vertical:
        props = props[:2]
        fh = h * 0.30
        fx = w * 0.27
        zone_x0, zone_x1 = w * 0.50, w * 0.96
        figure(d, fx, ground, fh, pose)
        size = min((zone_x1 - zone_x0) * 0.95, h * 0.26)
        for i, p in enumerate(props):
            draw_prop(d, p, (zone_x0 + zone_x1) / 2, ground - i * h * 0.29, size)
        cap_y, cap_size, cap_w = h * 0.08, w * 0.105, 16
    elif thumb:
        fh = h * 0.66
        figure(d, w * 0.20, ground, fh, pose)
        n = max(1, len(props))
        zone_x0, zone_x1 = w * 0.42, w * 0.97
        size = min(h * 0.72, (zone_x1 - zone_x0) / n * 0.95)
        for i, p in enumerate(props):
            draw_prop(d, p, zone_x0 + (zone_x1 - zone_x0) * (i + 0.5) / n, ground, size)
        cap_y, cap_size, cap_w = h * 0.17, h * 0.2, 14
    else:
        fh = h * 0.50
        figure(d, w * 0.25, ground, fh, pose)
        n = max(1, len(props))
        zone_x0, zone_x1 = w * 0.44, w * 0.96
        size = min(h * 0.52, (zone_x1 - zone_x0) / n * 0.9)
        for i, p in enumerate(props):
            draw_prop(d, p, zone_x0 + (zone_x1 - zone_x0) * (i + 0.5) / n, ground, size)
        cap_y, cap_size, cap_w = h * 0.12, h * 0.085, 26

    if caption:
        lines = textwrap.wrap(caption, cap_w)[:3]
        size = cap_size
        while size > cap_size * 0.55 and max(d.textlength(l, font=font(size)) for l in lines) > w * 0.94:
            size *= 0.92
        y = cap_y
        for ln in lines:
            text_center(d, w / 2, y, ln, size, GOLD, stroke=size * 0.09, stroke_fill=(0, 0, 0))
            y += size * 1.12
    img = img.resize((W, H), Image.LANCZOS)
    if path:
        img.save(path, quality=93)
    return img
import mannequin
if hasattr(mannequin, "install"):
    mannequin.install(globals())
