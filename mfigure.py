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
          
