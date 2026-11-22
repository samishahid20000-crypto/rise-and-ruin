import math, re, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter


def install(g=None):
    # kept so stickman.py's mannequin.install(globals()) never fails
    return None


# ------------------------------------------------------------ helpers
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


_FONTS = {}


def font(size):
    size = int(size)
    if size in _FONTS:
        return _FONTS[size]
    f = None
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
              "DejaVuSans-Bold.ttf"):
        try:
            f = ImageFont.truetype(p, size)
            break
        except Exception:
            pass
    if f is None:
        try:
            f = ImageFont.load_default(size)
        except TypeError:
            f = ImageFont.load_default()
    _FONTS[size] = f
    return f


ACT = {"rise": 1, "crack": 1, "ruin": 1, "neutral": 1}
WHITE = (233, 233, 237)
RED = (228, 44, 36)
LINE = (215, 215, 220)
GREEN = (52, 199, 89)
GOLD = (244, 190, 40)

# ------------------------------------------------------------ 3D-looking sprites
_SPR = {}


def sphere(r, base):
    r = max(2, int(round(r)))
    key = (r, base)
    if key in _SPR:
        return _SPR[key]
    big_n = 4 * r + 4
    R = 2 * r
    c = big_n / 2.0
    dark = tuple(int(v * 0.72) for v in base)
    light = tuple(min(255, int(v + 40)) for v in base)
    big = Image.new("RGBA", (big_n, big_n), dark + (0,))
    d = ImageDraw.Draw(big)
    steps = 16
    for i in range(steps):
        k = i / (steps - 1)
        rad = R * (1 - 0.86 * k)
        cx = c - R * 0.34 * k
        cy = c - R * 0.42 * k
        d.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=lerp(dark, light, k ** 0.9) + (255,))
    hx, hy = c - R * 0.36, c - R * 0.44
    d.ellipse((hx - R * 0.15, hy - R * 0.10, hx + R * 0.15, hy + R * 0.10), fill=(255, 255, 255, 235))
    mask = Image.new("L", (big_n, big_n), 0)
    ImageDraw.Draw(mask).ellipse((c - R, c - R, c + R, c + R), fill=255)
    alpha = Image.new("L", (big_n, big_n), 0)
    alpha.paste(mask)
    big.putalpha(alpha)
    sp = big.resize((big_n // 2, big_n // 2), Image.LANCZOS)
    _SPR[key] = sp
    return sp


def put(img, sp, x, y):
    img.paste(sp, (int(x - sp.width / 2), int(y - sp.height / 2)), sp)


def limb(img, p0, p1, r0, r1, col):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy)
    n = max(2, int(L / max(2.0, min(r0, r1) * 0.22)))
    for i in range(n + 1):
        t = i / n
        put(img, sphere(r0 + (r1 - r0) * t, col), p0[0] + dx * t, p0[1] + dy * t)


_SHADOW = {}


def shadow(img, x, y, w):
    w = int(w)
    if w not in _SHADOW:
        h = max(6, int(w * 0.22))
        pad = 24
        s = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
        ImageDraw.Draw(s).ellipse((pad, pad, pad + w, pad + h), fill=(0, 0, 0, 120))
        _SHADOW[w] = s.filter(ImageFilter.GaussianBlur(8))
    s = _SHADOW[w]
    img.paste(s, (int(x - s.width / 2), int(y - s.height / 2)), s)


# ------------------------------------------------------------ the mannequin
def pose_mode(name):
    n = str(name or "").lower()
    for keys, mode in ((("cheer", "happy", "celebr", "win", "joy", "victory"), "cheer"),
                       (("sad", "cry", "defeat", "lose", "down", "broke"), "sad"),
                       (("panic", "scare", "shock", "fear", "run", "worr"), "panic"),
                       (("think", "ponder", "doubt", "confus"), "think"),
                       (("shrug",), "shrug"),
                       (("point", "present", "explain"), "point")):
        if any(k in n for k in keys):
            return mode
    return None


def angles(mode, t):
    w = 2 * math.pi
    a = dict(lean=0.0, tilt=0.0, bob=0.0, la1=-7, la2=-4, ra1=7, ra2=4, lt=2, ls=2, rt=-2, rs=-2)
    if mode == "walk":
        p = w * 1.7 * t
        s, c = math.sin(p), math.cos(p)
        a.update(lt=26 * s, rt=-26 * s, ls=26 * s - 28 * max(0, c), rs=-26 * s - 28 * max(0, -c),
                 la1=-22 * s, la2=-22 * s + 10, ra1=22 * s, ra2=22 * s + 10, bob=abs(s) * 0.014, lean=0.06)
    elif mode == "idle":
        s = math.sin(w * 0.7 * t)
        a.update(la1=-8 + 3 * s, la2=-4 + 3 * s, ra1=8 - 3 * s, ra2=4 - 3 * s, bob=0.004 * s,
                 tilt=0.04 * math.sin(w * 0.4 * t))
    elif mode == "cheer":
        s = math.sin(w * 1.6 * t)
        k = math.sin(w * 3 * t)
        a.update(bob=abs(s) * 0.05, la1=-150 + 12 * k, la2=-168 + 12 * k, ra1=150 - 12 * k, ra2=168 - 12 * k,
                 lt=10, ls=10, rt=-10, rs=-10)
    elif mode == "sad":
        s = math.sin(w * 0.5 * t)
        a.update(lean=0.22 + 0.02 * s, tilt=0.28, la1=-4, la2=-2, ra1=4, ra2=2, lt=3, ls=3, rt=-3, rs=-3,
                 bob=-0.006)
    elif mode == "panic":
        p = w * 5 * t
        s, c = math.sin(p), math.cos(p)
        a.update(la1=-125 + 25 * s, la2=-150 + 30 * s, ra1=125 - 25 * c, ra2=150 - 30 * c,
                 lt=30 * s, rt=-30 * s, ls=30 * s - 30 * max(0, c), rs=-30 * s - 30 * max(0, -c),
                 bob=abs(s) * 0.02, lean=0.1)
    elif mode == "think":
        s = math.sin(w * 0.6 * t)
        a.update(la1=-6, la2=-4, ra1=35, ra2=168, tilt=0.12 + 0.03 * s, lean=0.03, lt=4, ls=4, rt=-4, rs=-4)
    elif mode == "shrug":
        s = math.sin(w * 0.8 * t)
        a.update(la1=-40, la2=-100, ra1=40, ra2=100, bob=0.01 * s, tilt=0.08 * s)
    elif mode == "point":
        s = math.sin(w * 0.9 * t)
        a.update(ra1=85 + 4 * s, ra2=88, la1=-6, la2=-4, lean=0.05, bob=0.004 * s)
    elif mode == "push":
        p = w * 1.4 * t
        s, c = math.sin(p), math.cos(p)
        a.update(lean=0.28, la1=75, la2=85, ra1=80, ra2=88, lt=22 * s, rt=-22 * s,
                 ls=22 * s - 24 * max(0, c), rs=-22 * s - 24 * max(0, -c), bob=abs(s) * 0.01)
    elif mode == "climb":
        p = w * 1.2 * t
        s = math.sin(p)
        a.update(la1=-150 + 30 * s, la2=-170 + 30 * s, ra1=150 + 30 * s, ra2=170 + 30 * s,
                 lt=14 * s, ls=14 * s - 20 * max(0, math.cos(p)), rt=-14 * s, rs=-14 * s - 20 * max(0, -math.cos(p)),
                 bob=0.006 * s)
    return a


def vec(angle_deg, length):
    r = math.radians(angle_deg)
    return math.sin(r) * length, math.cos(r) * length


def figure(img, ox, oy, fh, a, BODY):
    """ox, oy = point on the ground between the feet, fh = figure height in px.
    Returns (head_x, head_y, head_radius)."""
    thigh, shin, torso, neck = 0.235 * fh, 0.235 * fh, 0.30 * fh, 0.03 * fh
    ua, fa, sw, hw, hr = 0.165 * fh, 0.16 * fh, 0.085 * fh, 0.032 * fh, 0.07 * fh

    def leg_dy(t1, t2):
        return thigh * math.cos(math.radians(t1)) + shin * math.cos(math.radians(t2))

    hip_y = oy - max(leg_dy(a["lt"], a["ls"]), leg_dy(a["rt"], a["rs"])) - a["bob"] * fh
    hip = (ox, hip_y)
    lean = a["lean"]
    up = (math.sin(lean), -math.cos(lean))
    perp = (math.cos(lean), math.sin(lean))
    nk = (hip[0] + up[0] * torso, hip[1] + up[1] * torso)
    ls_ = (nk[0] - perp[0] * sw, nk[1] - perp[1] * sw + 0.015 * fh)
    rs_ = (nk[0] + perp[0] * sw, nk[1] + perp[1] * sw + 0.015 * fh)
    hl = (hip[0] - hw, hip[1])
    hrr = (hip[0] + hw, hip[1])

    r_th, r_sh = 0.032 * fh, 0.024 * fh
    for hp, t1, t2 in ((hl, a["lt"], a["ls"]), (hrr, a["rt"], a["rs"])):
        dx, dy = vec(t1, thigh)
        knee = (hp[0] + dx, hp[1] + dy)
        dx, dy = vec(t2, shin)
        foot = (knee[0] + dx, knee[1] + dy)
        limb(img, hp, knee, r_th, r_sh * 1.05, BODY)
        limb(img, knee, foot, r_sh * 1.05, r_sh * 0.85, BODY)
        put(img, sphere(r_sh * 1.1, BODY), foot[0] + 0.02 * fh, foot[1] - 0.01 * fh)
    limb(img, hip, nk, 0.05 * fh, 0.064 * fh, BODY)
    r_ua, r_fa = 0.025 * fh, 0.02 * fh
    for sp_, a1, a2 in ((ls_, a["la1"], a["la2"]), (rs_, a["ra1"], a["ra2"])):
        dx, dy = vec(a1, ua)
        el = (sp_[0] + dx, sp_[1] + dy)
        dx, dy = vec(a2, fa)
        wr = (el[0] + dx, el[1] + dy)
        limb(img, sp_, el, r_ua, r_ua * 0.9, BODY)
        limb(img, el, wr, r_fa * 1.1, r_fa, BODY)
        put(img, sphere(0.024 * fh, BODY), wr[0], wr[1])
    hang = lean + a["tilt"]
    hup = (math.sin(hang), -math.cos(hang))
    hc = (nk[0] + hup[0] * (neck + hr), nk[1] + hup[1] * (neck + hr))
    limb(img, nk, hc, 0.022 * fh, 0.022 * fh, BODY)
    put(img, sphere(hr, BODY), hc[0], hc[1])
    return hc[0], hc[1], hr


# ------------------------------------------------------------ scene pieces
def wrap(draw, text, fnt, maxw):
    words, lines, cur = str(text).split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if draw.textlength(t, font=fnt) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines[:3]


def text_c(d, xy, text, size, fill=(255, 255, 255)):
    d.text(xy, text, font=font(size), fill=fill, anchor="mm")


def block(d, x0, y0, x1, y1, col):
    d.rectangle((x0, y0, x1, y1), fill=col)
    d.rectangle((x0, y0, x0 + (x1 - x0) * 0.18, y1), fill=lerp(col, (255, 255, 255), 0.30))
    d.rectangle((x1 - (x1 - x0) * 0.16, y0, x1, y1), fill=lerp(col, (0, 0, 0), 0.35))


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


def p_gear(d, x
