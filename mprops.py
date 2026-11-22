import math, re
from mfigure import ease, lerp, font, RED, WHITE, LINE, GREEN, GOLD


# ------------------------------------------------------------ keyword -> prop engine
# order of appearance in the narration decides which prop shows first
PROP_KEYS = [
    ("phone", r"\b(phones?|mobiles?|smartphones?|nokia|iphone|android|handsets?|ringtones?|calls?|texting|sms)\b"),
    ("tech", r"\b(technolog\w*|tech|software|internet|computers?|digital|online|chips?|processors?|app|apps|ai|"
             r"platforms?|operating system|network|web|silicon|tower|laptop)\b"),
    ("building", r"\b(buildings?|compan(?:y|ies)|offices?|headquarters?|hq|corporations?|firms?|empire|"
                r"stores?|shops?|bank|banks|brand|giant|enterprise|business)\b"),
    ("gear", r"\b(factor(?:y|ies)|production|manufactur\w*|engineer\w*|machines?|assembly|plants?)\b"),
    ("bulb", r"\b(ideas?|innovat\w*|invent\w*|creative|breakthrough|patent\w*|discover\w*)\b"),
    ("coin", r"\b(profits?|revenues?|money|dollars?|cash|sales|earn\w*|billions?|millions?|rich|wealth\w*|"
            r"invest\w*|valuation|price|funding|salary|income|shares?|stocks?|coins?)\b"),
    ("chart_up", r"chart_up|arrow_up|\b(growth|grew|growing|boom|soar\w*|skyrocket\w*|surge\w*|record|market share|expand\w*|"
                r"rose|rising|climb\w*|peak)\b"),
    ("chart_down", r"chart_down|arrow_down|\b(decline\w*|declin\w*|fell|falling|drop\w*|plunge\w*|collaps\w*|crash\w*|slump\w*|"
                   r"downfall|lost|losing|losses|loss|debt|bankrupt\w*|deficit)\b"),
    ("trophy", r"\b(win|won|winner|leader|leading|number one|dominat\w*|champion\w*|success\w*|victory|"
               r"top|best)\b"),
    ("cross", r"xmark|\b(fail\w*|fired|layoffs?|lawsuit\w*|banned|shut ?down|closed|scandal\w*|mistakes?|"
              r"disaster|bust)\b"),
]
GOOD = r"\b(profits?|growth|grew|boom|soar\w*|skyrocket\w*|surge\w*|record|success\w*|won|win|victory|leader|" \
       r"dominat\w*|rich|billions?|millions?|rose|rising|peak|breakthrough|champion\w*|top)\b"
BAD = r"\b(loss|losses|lost|losing|decline\w*|fell|falling|drop\w*|plunge\w*|collaps\w*|crash\w*|bankrupt\w*|" \
      r"debt|fail\w*|fired|layoffs?|lawsuit\w*|banned|scandal\w*|disaster|slump\w*|downfall|deficit|struggl\w*|" \
      r"worr\w*|trouble|crisis|bust)\b"
PANIC = r"\b(crash\w*|collaps\w*|bankrupt\w*|fired|layoffs?|crisis|disaster|plunge\w*|scandal\w*)\b"


def scene_text(sc):
    parts = []
    for k in ("narration", "voice", "line", "text", "script", "caption", "title", "visual", "keywords"):
        v = sc.get(k)
        if v:
            parts.append(" ".join(v) if isinstance(v, (list, tuple)) else str(v))
    for v in (sc.get("labels") or []):
        parts.append(str(v))
    p = sc.get("props")
    if p:
        parts.append(" ".join(p) if isinstance(p, (list, tuple)) else str(p))
    return " ".join(parts).lower()


def detect(sc, act):
    """returns (props list max 2, mood or None) using the order the words are spoken in"""
    low = scene_text(sc)
    hits = []
    for kind, pat in PROP_KEYS:
        m = re.search(pat, low)
        if m:
            hits.append((m.start(), kind))
    hits.sort()
    kinds = []
    for _, k in hits:
        if k not in kinds:
            kinds.append(k)
    good = [m.start() for m in re.finditer(GOOD, low)]
    bad = [m.start() for m in re.finditer(BAD, low)]
    mood = None
    if good or bad:
        if good and not bad:
            mood = "cheer"
        elif bad and not good:
            mood = "panic" if re.search(PANIC, low) else "sad"
        else:
            mood = "cheer" if max(good) > max(bad) else ("panic" if re.search(PANIC, low) else "sad")
    elif act == "rise":
        mood = "cheer"
    elif act == "ruin":
        mood = "sad"
    # chart direction follows the mood
    out = []
    for k in kinds:
        if k in ("chart_up", "chart_down") and mood in ("sad", "panic") and k == "chart_up":
            k = "chart_down"
        if k == "chart_down" and mood == "cheer":
            k = "chart_up"
        if k not in out:
            out.append(k)
    if not out:
        if mood == "cheer":
            out = ["chart_up"]
        elif mood in ("sad", "panic"):
            out = ["chart_down"]
    return out[:2], mood, bool(kinds)


# ------------------------------------------------------------ prop drawers (thin clean line art, flat accents)
def _lw(s):
    return max(3, int(s * 0.022))


def p_building(d, x, base, s, t, down):
    lw = _lw(s)
    g = ease((t - 0.05) / 0.8)
    shake = 0
    if down:
        shake = math.sin(t * 45) * s * 0.012 * ease((t - 0.5) / 0.3) * (1 - ease((t - 1.6) / 0.6))
    shrink = 1 - 0.35 * ease((t - 0.6) / 0.9) if down else 1
    for (ox, wr, hr_) in ((-0.36, 0.22, 0.5), (0.34, 0.2, 0.38), (0.0, 0.42, 0.95)):
        w = s * wr
        h = s * hr_ * g * shrink
        x0 = x + ox * s - w / 2 + shake
        d.rectangle((x0, base - h, x0 + w, base), outline=LINE, width=lw)
        cols = 3 if wr > 0.3 else 2
        rows = max(1, int(hr_ * 7))
        ww = w / (cols * 2 + 1)
        wh = s * 0.045
        for r in range(rows):
            for c in range(cols):
                wy = base - h + (r + 0.6) * (h / (rows + 0.4))
                if wy + wh > base - 4:
                    continue
                wx = x0 + ww * (1 + 2 * c)
                lit = ((r * 3 + c * 5) % 4 != 0)
                col = (RED if down else WHITE) if lit else (70, 70, 76)
                d.rectangle((wx, wy, wx + ww, wy + wh), fill=col)
    if down and t > 0.8:
        k = ease((t - 0.8) / 0.6)
        bx = x + shake
        top = base - s * 0.95 * g * shrink
        pts = [(bx - s * 0.02, top), (bx + s * 0.04, top + s * 0.18), (bx - s * 0.04, top + s * 0.33),
               (bx + s * 0.03, top + s * 0.5)]
        n = max(2, int(len(pts) * k + 0.999))
        d.line(pts[:n], fill=RED, width=lw + 2)


def p_phone(d, x, base, s, t, down):
    lw = _lw(s)
    w, h = s * 0.4, s * 0.74
    cy = base - h / 2 - s * 0.06 + math.sin(t * 5) * s * 0.012
    x0, y0, x1, y1 = x - w / 2, cy - h / 2, x + w / 2, cy + h / 2
    d.rounded_rectangle((x0, y0, x1, y1), radius=int(w * 0.14), outline=LINE, width=lw, fill=(14, 14, 16))
    d.rounded_rectangle((x0 + w * 0.08, y0 + h * 0.09, x1 - w * 0.08, y1 - h * 0.1), radius=int(w * 0.06),
                        fill=(30, 30, 34))
    gw = (w * 0.84 - w * 0.08) / 3
    for r in range(3):
        for c in range(3):
            ix = x0 + w * 0.12 + c * (w * 0.76 / 3)
            iy = y0 + h * 0.15 + r * (h * 0.7 / 4)
            col = RED if (r + c) % 4 == 0 else (210, 210, 214)
            d.rounded_rectangle((ix, iy, ix + gw * 0.7, iy + gw * 0.7), radius=4, fill=col)
    d.ellipse((x - 4, y1 - h * 0.06, x + 4, y1 - h * 0.06 + 8), outline=LINE, width=2)
    # ringing arcs
    for i in range(3):
        ph = (t * 1.4 + i * 0.33) % 1.0
        rr = s * (0.12 + 0.2 * ph)
        a_ = int(255 * (1 - ph))
        col = (RED[0] * a_ // 255, RED[1] * a_ // 255, RED[2] * a_ // 255)
        d.arc((x1 - rr * 0.2, y0 - rr * 0.9, x1 + rr * 1.6, y0 + rr * 0.9), -70, 70, fill=col, width=lw)


def p_tech(d, x, base, s, t, down):
    lw = _lw(s)
    cy = base - s * 0.42
    half = s * 0.24
    d.rectangle((x - half, cy - half, x + half, cy + half), outline=LINE, width=lw, fill=(20, 20, 24))
    d.rectangle((x - half * 0.5, cy - half * 0.5, x + half * 0.5, cy + half * 0.5), outline=RED, width=lw)
    for i in range(4):
        o = -half * 0.66 + i * half * 0.44
        d.line((x + o, cy - half, x + o, cy - half - s * 0.09), fill=LINE, width=lw)
        d.line((x + o, cy + half, x + o, cy + half + s * 0.09), fill=LINE, width=lw)
        d.line((x - half, cy + o, x - half - s * 0.09, cy + o), fill=LINE, width=lw)
        d.line((x + half, cy + o, x + half + s * 0.09, cy + o), fill=LINE, width=lw)
    ph = (t * 0.9) % 1.0
    rr = half * (1.0 + 1.1 * ph)
    a_ = int(255 * (1 - ph))
    d.ellipse((x - rr, cy - rr, x + rr, cy + rr), outline=(RED[0] * a_ // 255, RED[1] * a_ // 255, RED[2] * a_ // 255),
              width=lw)
    # wifi
    wx, wy = x, cy - half - s * 0.2
    for i in range(3):
        rr = s * (0.05 + 0.05 * i)
        d.arc((wx - rr, wy - rr, wx + rr, wy + rr), 215, 325, fill=LINE, width=lw)
    d.ellipse((wx - 4, wy + s * 0.02, wx + 4, wy + s * 0.02 + 8), fill=RED)


def _coin(d, x, y, r, lw):
    d.ellipse((x - r, y - r, x + r, y + r), fill=GOLD, outline=(150, 105, 10), width=lw)
    d.ellipse((x - r * 0.72, y - r * 0.72, x + r * 0.72, y + r * 0.72), outline=(170, 120, 10), width=max(2, lw - 1))
    d.text((x, y), "$", font=font(max(10, r * 1.15)), fill=(120, 80, 5), anchor="mm")


def p_coin(d, x, base, s, t, down):
    lw = _lw(s)
    r = s * 0.28
    if down:
        cy = base - r - s * 0.05 - ease((t - 0.3) / 1.0) * s * 0.0
        _coin(d, x, cy, r, lw)
        k = ease((t - 0.4) / 0.6)
        ax = x
        d.line((ax, base - s * 0.9, ax, base - s * 0.9 + s * 0.35 * k), fill=RED, width=lw + 4)
        if k > 0.7:
            ey = base - s * 0.9 + s * 0.35 * k
            d.polygon([(ax - s * 0.08, ey - s * 0.02), (ax + s * 0.08, ey - s * 0.02), (ax, ey + s * 0.08)], fill=RED)
        return
    for i, dy in enumerate((0.0, 0.09, 0.18)):
        ey = base - s * 0.04 - dy * s
        d.ellipse((x - r * 1.1, ey - r * 0.32, x + r * 1.1, ey + r * 0.32), fill=GOLD, outline=(150, 105, 10), width=lw)
    _coin(d, x, base - s * 0.33 - r, r, lw)
    for i in range(5):
        st = 0.25 + i * 0.28
        pr = ((t - st) / 1.1)
        if 0 < pr < 1:
            fx = x + (i - 2) * s * 0.22
            fy = base - s * 1.0 + pr * (s * 0.95)
            _coin(d, fx, fy, s * 0.075, 2)


def p_chart(d, x, base, s, t, down, up):
    lw = _lw(s)
    gx0, gx1 = x - s * 0.5, x + s * 0.5
    gy1, gy0 = base - s * 0.04, base - s * 0.9
    d.line((gx0, gy0, gx0, gy1), fill=LINE, width=lw)
    d.line((gx0, gy1, gx1, gy1), fill=LINE, width=lw)
    data = [(0, 0.12), (0.2, 0.3), (0.4, 0.5), (0.6, 0.78), (0.8, 0.92), (1.0, 1.0)] if up else \
        [(0, 0.95), (0.2, 0.8), (0.4, 0.82), (0.6, 0.5), (0.8, 0.3), (1.0, 0.06)]
    col = GREEN if up else RED
    pp = ease((t - 0.05) / 1.1)
    pts = []
    for i, (px, py) in enumerate(data):
        if px <= pp:
            pts.append((px, py))
        else:
            a0 = data[i - 1]
            f_ = (pp - a0[0]) / (px - a0[0])
            pts.append((pp, a0[1] + (py - a0[1]) * f_))
            break
    pts = [(gx0 + 6 + a * (gx1 - gx0 - 12), gy1 - b * (gy1 - gy0 - 8)) for a, b in pts]
    if len(pts) >= 2:
        d.line(pts, fill=col, width=lw + 4, joint="curve")
        ex, ey = pts[-1]
        d.ellipse((ex - lw * 2, ey - lw * 2, ex + lw * 2, ey + lw * 2), fill=(255, 255, 255))


def p_gear(d, x, base, s, t, down):
    lw = _lw(s)
    cy = base - s * 0.42
    R, r = s * 0.36, s * 0.27
    n = 10
    pts = []
    for i in range(n * 2):
        ang = t * 0.9 + i * math.pi / n
        rr = R if (i % 2 == 0) else r
        for off in (-0.18, 0.18):
            a2 = ang + off * math.pi / n
            pts.append((x + math.cos(a2) * rr, cy + math.sin(a2) * rr))
    d.polygon(pts, outline=LINE, fill=(22, 22, 26))
    d.line(pts + [pts[0]], fill=LINE, width=lw)
    d.ellipse((x - s * 0.12, cy - s * 0.12, x + s * 0.12, cy + s * 0.12), outline=RED, width=lw + 1)


def p_bulb(d, x, base, s, t, down):
    lw = _lw(s)
    cy = base - s * 0.55
    r = s * 0.24
    on = 0.5 + 0.5 * math.sin(t * 6)
    fill = lerp((40, 40, 46), GOLD, 0.55 + 0.45 * on)
    d.ellipse((x - r, cy - r, x + r, cy + r), fill=fill, outline=LINE, width=lw)
    d.rectangle((x - r * 0.5, cy + r * 0.85, x + r * 0.5, cy + r * 1.45), outline=LINE, width=lw, fill=(60, 60, 66))
    for i in range(7):
        ang = math.radians(-160 + i * 23)
        d.line((x + math.cos(ang) * r * 1.3, cy + math.sin(ang) * r * 1.3,
                x + math.cos(ang) * r * (1.55 + 0.1 * on), cy + math.sin(ang) * r * (1.55 + 0.1 * on)),
               fill=GOLD, width=lw)


def p_trophy(d, x, base, s, t, down):
    lw = _lw(s)
    top = base - s * 0.85
    w = s * 0.5
    d.polygon([(x - w / 2, top), (x + w / 2, top), (x + w * 0.3, top + s * 0.38), (x - w * 0.3, top + s * 0.38)],
              fill=GOLD, outline=(150, 105, 10))
    d.arc((x - w * 0.8, top + s * 0.02, x - w * 0.3, top + s * 0.3), 90, 270, fill=GOLD, width=lw + 1)
    d.arc((x + w * 0.3, top + s * 0.02, x + w * 0.8, top + s * 0.3), -90, 90, fill=GOLD, width=lw + 1)
    d.rectangle((x - s * 0.05, top + s * 0.38, x + s * 0.05, top + s * 0.55), fill=GOLD)
    d.rectangle((x - w * 0.35, top + s * 0.55, x + w * 0.35, top + s * 0.68), fill=(90, 90, 96), outline=LINE)
    sp = (t * 1.6) % 1.0
    for i, (ox, oy) in enumerate(((-0.4, 0.05), (0.42, 0.25), (0.0, -0.1))):
        a_ = abs(math.sin((sp + i * 0.3) * math.pi))
        rr = s * 0.04 * (0.5 + a_)
        d.line((x + ox * s - rr, top + oy * s, x + ox * s + rr, top + oy * s), fill=WHITE, width=2)
        d.line((x + ox * s, top + oy * s - rr, x + ox * s, top + oy * s + rr), fill=WHITE, width=2)


def p_cross(d, x, base, s, t, down):
    lw = _lw(s) + 4
    cy = base - s * 0.45
    r = s * 0.32
    pp = ease((t - 0.05) / 0.4)
    r2 = r * (0.4 + 0.6 * pp)
    d.ellipse((x - r2, cy - r2, x + r2, cy + r2), outline=RED, width=lw)
    k = r2 * 0.55
    d.line((x - k, cy - k, x + k, cy + k), fill=RED, width=lw + 2)
    d.line((x - k, cy + k, x + k, cy - k), fill=RED, width=lw + 2)


def draw_prop(d, kind, x, base, s, t, down):
    if kind == "building":
        p_building(d, x, base, s, t, down)
    elif kind == "phone":
        p_phone(d, x, base, s, t, down)
    elif kind == "tech":
        p_tech(d, x, base, s, t, down)
    elif kind == "coin":
        p_coin(d, x, base, s, t, down)
    elif kind == "chart_up":
        p_chart(d, x, base, s, t, down, True)
    elif kind == "chart_down":
        p_chart(d, x, base, s, t, down, False)
    elif kind == "gear":
        p_gear(d, x, base, s, t, down)
    elif kind == "bulb":
        p_bulb(d, x, base, s, t, down)
    elif kind == "trophy":
        p_trophy(d, x, base, s, t, down)
    elif kind == "cross":
        p_cross(d, x, base, s, t, down)


def tension(d, hx, hy, hr, t, fh, panic):
    """sweat drops + stress lines around the head"""
    lw = max(3, int(fh * 0.012))
    for i in range(3):
        ph = (t * 1.3 + i * 0.37) % 1.0
        sx = hx + (-1 if i % 2 == 0 else 1) * hr * (1.5 + 0.3 * i)
        sy = hy - hr * 0.5 + ph * hr * 2.6
        a_ = int(255 * (1 - ph * 0.6))
        col = (120 * a_ // 255 + 40, 190 * a_ // 255 + 30, 255 * a_ // 255)
        rr = hr * 0.2
        d.polygon([(sx, sy - rr * 1.9), (sx - rr, sy), (sx + rr, sy)], fill=col)
        d.ellipse((sx - rr, sy - rr, sx + rr, sy + rr), fill=col)
    if panic:
        for i in range(5):
            ang = math.radians(-150 + i * 30)
            wob = 0.12 * math.sin(t * 22 + i)
            r0 = hr * (1.55 + wob)
            r1 = hr * (2.1 + wob)
            d.line((hx + math.cos(ang) * r0, hy + math.sin(ang) * r0,
                    hx + math.cos(ang) * r1, hy + math.sin(ang) * r1), fill=RED, width=lw)
                                                   
