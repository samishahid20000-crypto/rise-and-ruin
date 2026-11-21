import math, subprocess
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
    # keep only the circle: everything outside the mask is transparent
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
    """ox, oy = point on the ground between the feet, fh = figure height in px."""
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
    # torso (accent coloured shirt)
    limb(img, hip, nk, 0.05 * fh, 0.064 * fh, BODY)
    # arms
    r_ua, r_fa = 0.025 * fh, 0.02 * fh
    for sp_, a1, a2 in ((ls_, a["la1"], a["la2"]), (rs_, a["ra1"], a["ra2"])):
        dx, dy = vec(a1, ua)
        el = (sp_[0] + dx, sp_[1] + dy)
        dx, dy = vec(a2, fa)
        wr = (el[0] + dx, el[1] + dy)
        limb(img, sp_, el, r_ua, r_ua * 0.9, BODY)
        limb(img, el, wr, r_fa * 1.1, r_fa, BODY)
        put(img, sphere(0.024 * fh, BODY), wr[0], wr[1])
    # neck + head
    hang = lean + a["tilt"]
    hup = (math.sin(hang), -math.cos(hang))
    hc = (nk[0] + hup[0] * (neck + hr), nk[1] + hup[1] * (neck + hr))
    limb(img, nk, hc, 0.022 * fh, 0.022 * fh, BODY)
    put(img, sphere(hr, BODY), hc[0], hc[1])


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


# ------------------------------------------------------------ build + render
def build(sc, W, H):
    act = sc.get("act") if sc.get("act") in ACT else "neutral"
    vertical = H > W
    floor_y = int(H * 0.80)
    fh = min(0.5 * H, 0.4 * W)
    bg = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(bg)
    d.line((0, floor_y, W, floor_y), fill=LINE, width=3)
    cap = str(sc.get("caption") or "")
    size = int(H * 0.06) if not vertical else int(W * 0.085)
    fnt = font(size)
    lines = wrap(d, cap, fnt, W * 0.9)
    y = H * (0.09 if not vertical else 0.08)
    for ln in lines:
        text_c(d, (W / 2, y), ln, size)
        y += size * 1.2
    labs = [str(x) for x in (sc.get("labels") or []) if str(x).strip()][:3]
    if sc.get("scene") == "versus":
        labs = []
    if labs and (labs[0].strip().lower() == cap.strip().lower()):
        labs = labs[1:]
    lsize = int(H * 0.042) if not vertical else int(W * 0.06)
    if labs:
        n = len(labs)
        for i, t_ in enumerate(labs):
            col = RED if i == n - 1 else (255, 255, 255)
            text_c(d, (W * (i + 1) / (n + 1), y + lsize * 0.6), t_, lsize, col)
        y += lsize * 1.8
    region_top = y + H * 0.05
    if vertical:
        region = (W * 0.08, region_top, W * 0.92, floor_y - fh * 1.12)
        cx, fx_in = W * 0.5, W * 0.1
    else:
        region = (W * 0.45, region_top, W * 0.95, floor_y)
        cx, fx_in = W * 0.24, -W * 0.05
    hero = RED if act in ("rise", "ruin") else WHITE
    return dict(sc=sc, W=W, H=H, bg=bg, act=act, fh=fh, floor_y=floor_y, region=region,
                cx=cx, fx_in=fx_in, vertical=vertical, hero=hero, mode=pose_mode(sc.get("pose")))


def ground_at_steps(x, xs, sw, n, floor_y, sh, down):
    def top(i):
        return floor_y - ((n - i) if down else (i + 1)) * sh

    if x <= xs:
        return top(0) if down else floor_y
    if x >= xs + n * sw:
        return floor_y if down else top(n - 1)
    return top(int((x - xs) / sw))


def render(c, t, dur):
    W, H = c["W"], c["H"]
    img = c["bg"].copy()
    d = ImageDraw.Draw(img)
    kind = c["sc"].get("scene") or "generic"
    fh, fy, hero = c["fh"], c["floor_y"], c["hero"]
    rx0, ry0, rx1, ry1 = c["region"]
    cx = c["cx"]
    labels = c["sc"].get("labels") or []
    mode = c["mode"]
    walk_in = min(1.1, dur * 0.3)
    fx, gy = cx, fy
    fmode = mode or "idle"
    extra = []

    if kind in ("stairs_up", "stairs_down"):
        down = kind == "stairs_down"
        n = 5
        xs = rx0
        sw = (rx1 - rx0) / n
        sh = min(H * 0.04, (fy - ry0) / (n + 0.5))
        fh = fh * 0.7
        pts = []
        if down:
            pts.append((0, fy - n * sh))
            for i in range(n):
                hgt = (n - i) * sh
                pts += [(xs + i * sw, fy - hgt), (xs + i * sw, fy - hgt + sh)]
            pts += [(xs + n * sw, fy), (W, fy)]
        else:
            pts.append((0, fy))
            for i in range(n):
                pts += [(xs + i * sw, fy - i * sh), (xs + i * sw, fy - (i + 1) * sh)]
            pts += [(xs + n * sw, fy - n * sh), (W, fy - n * sh)]
        d.line(pts, fill=LINE, width=4)
        p = ease(t / max(0.5, dur * 0.85))
        xa = (xs - fh * 0.3) if not down else (xs + sw * 0.4)
        xb = (xs + n * sw - sw * 0.5) if not down else (xs + n * sw + fh * 0.25)
        fx = xa + (xb - xa) * p
        gy = ground_at_steps(fx, xs, sw, n, fy, sh, down)
        fmode = "walk" if p < 0.98 else (mode or ("sad" if down else "cheer"))
    elif kind in ("bars_up", "bars_down"):
        up = kind == "bars_up"
        nb = 5
        bw = (rx1 - rx0) / (nb * 1.7)
        maxh = (fy - ry0) * 0.85
        hs = [0.06, 0.08, 0.1, 0.12, 1.0] if up else [1.0, 0.12, 0.1, 0.08, 0.06]
        hi = nb - 1 if up else 0
        d.line((rx0 - 14, ry0, rx0 - 14, fy), fill=LINE, width=3)
        for i in range(nb):
            g = ease((t - 0.15 - 0.18 * i) / 0.9)
            bx = rx0 + i * bw * 1.7
            hh = maxh * hs[i] * g
            if hh > 2:
                block(d, bx, fy - hh, bx + bw, fy, RED if i == hi else (205, 205, 210))
        if labels:
            hx = rx0 + hi * bw * 1.7 + bw / 2
            text_c(d, (hx, fy - maxh - H * 0.04), str(labels[0]), int(H * 0.04), RED)
        fmode = "walk" if t < walk_in else (mode or ("cheer" if up else "sad"))
        fx = c["fx_in"] + (cx - c["fx_in"]) * ease(t / walk_in)
    elif kind == "versus":
        lx, rx = W * 0.27, W * 0.73
        names = (list(labels) + ["A", "B"])[:2]
        fsz = int(H * 0.05) if not c["vertical"] else int(W * 0.06)
        text_c(d, (lx, fy - fh * 1.22), str(names[0]), fsz, (255, 255, 255))
        text_c(d, (rx, fy - fh * 1.22), str(names[1]), fsz, RED)
        figure(img, rx, fy, fh, angles("cheer" if t > 0.3 else "idle", t), RED)
        fx = lx
        gy = fy
        fmode = "walk" if t < walk_in * 0.5 else "think"
        hero = WHITE
    elif kind == "ladder":
        lx = (rx0 + rx1) / 2
        lw = fh * 0.3
        d.line((lx - lw, ry0, lx - lw, fy), fill=LINE, width=4)
        d.line((lx + lw, ry0, lx + lw, fy), fill=LINE, width=4)
        yy = fy - 14
        while yy > ry0:
            d.line((lx - lw, yy, lx + lw, yy), fill=LINE, width=2)
            yy -= fh * 0.13
        p = ease(t / max(0.5, dur * 0.9))
        fx = lx
        gy = fy - p * max(10, (fy - ry0 - fh * 0.95))
        fmode = "climb"
    elif kind == "push":
        p = ease(t / max(0.5, dur))
        r = H * 0.05 + p * H * 0.14
        bx = rx0 + (rx1 - rx0) * (0.2 + 0.55 * p)
        put(img, sphere(r, WHITE), bx, fy - r)
        fx = bx - r - fh * 0.22
        fmode = "push"
        if c["vertical"]:
            fx = max(fx, fh * 0.3)
    elif kind == "crown_crack":
        w_ = (rx1 - rx0) * 0.6
        h_ = min((fy - ry0) * 0.7, w_ * 0.9)
        sh_ = math.sin(t * 40) * 3 * ease((t - 0.4) / 0.4) * (1 - ease((t - 1.4) / 0.6))
        x0 = (rx0 + rx1) / 2 - w_ / 2 + sh_
        y0 = fy - h_ - H * 0.03
        pts = [(0, 1), (0, 0.35), (0.25, 0.65), (0.5, 0.1), (0.75, 0.65), (1, 0.35), (1, 1)]
        poly = [(x0 + px * w_, y0 + py * h_) for px, py in pts]
        d.polygon(poly, fill=RED)
        d.line(poly + [poly[0]], fill=(255, 255, 255), width=4)
        zz = [(0.52, 0.12), (0.46, 0.3), (0.56, 0.46), (0.44, 0.66), (0.54, 0.82), (0.48, 1.0)]
        cp = ease((t - 0.4) / 1.3)
        k = max(1, int(len(zz) * cp + 0.999)) if cp > 0 else 0
        if k >= 2:
            d.line([(x0 + px * w_, y0 + py * h_) for px, py in zz[:k]], fill=(0, 0, 0), width=7)
        fmode = "walk" if t < walk_in else (mode or "sad")
        fx = c["fx_in"] + (cx - c["fx_in"]) * ease(t / walk_in)
    elif kind == "line_graph":
        gx0, gy0, gx1, gy1 = rx0, ry0 + H * 0.03, rx1, fy - H * 0.04
        d.line((gx0, gy0, gx0, gy1), fill=LINE, width=3)
        d.line((gx0, gy1, gx1, gy1), fill=LINE, width=3)
        data = [(0, 0.12), (0.2, 0.3), (0.4, 0.55), (0.6, 0.85), (0.72, 0.95), (0.82, 0.5), (1.0, 0.04)]
        pp = ease(t / max(0.5, dur * 0.8))
        shown = []
        for i in range(len(data) - 1):
            a0, a1 = data[i], data[i + 1]
            if pp >= a1[0]:
                shown.append(a0)
                if i == len(data) - 2:
                    shown.append(a1)
            elif pp > a0[0]:
                f_ = (pp - a0[0]) / (a1[0] - a0[0])
                shown.append(a0)
                shown.append((pp, a0[1] + (a1[1] - a0[1]) * f_))
                break
        pts = [(gx0 + 8 + px * (gx1 - gx0 - 16), gy1 - py * (gy1 - gy0 - 10)) for px, py in shown]
        if len(pts) >= 2:
            d.line(pts, fill=RED, width=8, joint="curve")
            d.ellipse((pts[-1][0] - 11, pts[-1][1] - 11, pts[-1][0] + 11, pts[-1][1] + 11), fill=(255, 255, 255))
        fmode = "walk" if t < walk_in else (mode or ("panic" if pp > 0.8 else "think"))
        fx = c["fx_in"] + (cx - c["fx_in"]) * ease(t / walk_in)
    else:
        gx = W * 0.5 if not c["vertical"] else cx
        fx = c["fx_in"] + (gx - c["fx_in"]) * ease(t / walk_in)
        fmode = "walk" if t < walk_in else (mode or "point")

    figure(img, fx, gy, fh, angles(fmode, t), hero)
    return img


def clip(S, sc, W, H, frames, FPS, out, png):
    frames = max(2, int(frames))
    dur = frames / float(FPS)
    ctx = build(sc, W, H)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
           "-pix_fmt", "yuv420p", "-r", str(FPS), out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for fi in range(frames):
            proc.stdin.write(render(ctx, fi / float(FPS), dur).tobytes())
    except BrokenPipeError:
        pass
    try:
        proc.stdin.close()
    except Exception:
        pass
    err = proc.stderr.read().decode("utf-8", "ignore")
    proc.wait()
    if proc.returncode != 0:
        print(err[-800:])
        raise SystemExit("clip failed")
                  
