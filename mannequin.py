import math, re, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from mfigure import *
from mprops import detect, draw_prop, tension
from mprops2 import draw_extra, EXTRA



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
YEL = (255, 214, 10)
BASE_VIS = ("building", "phone", "tech", "coin", "chart_up", "chart_down", "gear", "bulb", "trophy", "cross")


def key_color(word, act, last):
    if any(ch.isdigit() for ch in word) or "$" in word or "%" in word:
        return YEL
    if last:
        return RED if act in ("crack", "ruin") else YEL
    return (255, 255, 255)


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
    texts = []
    y = H * (0.09 if not vertical else 0.08)
    k = 0
    nwords = max(1, len(cap.split()))
    for ln in lines:
        ws = ln.split()
        total = d.textlength(ln, font=fnt)
        x = W / 2 - total / 2
        for w_ in ws:
            texts.append((w_, x, y, size, key_color(w_, act, k == nwords - 1), 0.1 + 0.28 * k))
            x += d.textlength(w_ + " ", font=fnt)
            k += 1
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
            col = key_color(t_, act, i == n - 1) if i == n - 1 or any(ch.isdigit() for ch in t_) else (255, 255, 255)
            texts.append((t_, W * (i + 1) / (n + 1) - d.textlength(t_, font=font(lsize)) / 2, y + lsize * 0.6, lsize, col,
                          0.45 + 0.4 * i))
        y += lsize * 1.8
    region_top = y + H * 0.05
    if vertical:
        region = (W * 0.08, region_top, W * 0.92, floor_y - fh * 1.12)
        cx, fx_in = W * 0.5, W * 0.1
    else:
        region = (W * 0.45, region_top, W * 0.95, floor_y)
        cx, fx_in = W * 0.24, -W * 0.05
    props, mood, explicit = detect(sc, act)
    vis = [v for v in (sc.get("visuals") or []) if v in EXTRA or v in BASE_VIS][:2]
    sc = dict(sc)
    if vis:
        props = vis
    if (explicit and sc.get("narration")) or vis:
        sc["scene"] = "generic"
    if sc.get("visuals") and sc["visuals"][0] == "versus":
        sc["scene"] = "versus"
    return dict(sc=sc, W=W, H=H, bg=bg, act=act, fh=fh, floor_y=floor_y, region=region,
                cx=cx, fx_in=fx_in, vertical=vertical, hero=RED, mode=pose_mode(sc.get("pose")),
                props=props, mood=mood, region_top=region_top, texts=texts)


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
    blend_k = None
    fmode = mode or "idle"
    props, mood = c["props"], c["mood"]
    # the scene's own story pose wins, else the mood of the narration
    mood_pose = mode or mood

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
        # generic scene: props that match the spoken words
        gx = W * 0.5 if not c["vertical"] else cx
        if props:
            gx = W * 0.26 if c["vertical"] else cx
            px0, px1 = (W * 0.47, W * 0.98) if c["vertical"] else (rx0, rx1)
            top = c["region_top"]
            n = len(props)
            size = min((px1 - px0) * 0.98, (fy - top) * 0.98)
            down = mood in ("sad", "panic")
            seg = dur / float(n)
            idx = min(n - 1, int(t / seg))
            local = max(0.0, t - idx * seg)
            pop = ease((local - 0.05) / 0.3)
            if pop > 0.02:
                if not draw_extra(d, props[idx], (px0 + px1) / 2, fy, size * pop, local, down):
                    draw_prop(d, props[idx], (px0 + px1) / 2, fy, size * pop, local, down)
        # the mannequin stays on screen (no walking in); it only moves with the voice
        fx = gx
        fmode = mood_pose or "idle"
        blend_k = ease(t / 0.35)

    a = angles(fmode, t)
    if blend_k is not None:
        a0 = angles("idle", t)
        a = {k_: a0[k_] + (a[k_] - a0[k_]) * blend_k for k_ in a}
    hx, hy, hr = figure(img, fx, gy, fh, a, hero)
    d = ImageDraw.Draw(img)
    if fmode in ("sad", "panic") and t >= walk_in * 0.5:
        tension(d, hx, hy, hr, t, fh, fmode == "panic")
    for txt, x, y, size, col, t0 in c["texts"]:
        if t >= t0:
            k = ease((t - t0) / 0.15)
            d.text((x, y), txt, font=font(size), fill=lerp((0, 0, 0), col, k), anchor="lm")
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
    
