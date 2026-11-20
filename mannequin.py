import math
import subprocess
import textwrap
from PIL import Image, ImageDraw

# (shadow, base, highlight)
RED_MAN = ((110, 6, 6), (205, 28, 28), (255, 130, 115))
WHITE_MAN = ((90, 90, 98), (188, 188, 194), (255, 255, 255))
BLACK_BG = {
    "rise": ((0, 0, 0), (16, 13, 4)),
    "crack": ((0, 0, 0), (20, 7, 7)),
    "ruin": ((0, 0, 0), (28, 4, 4)),
    "neutral": ((0, 0, 0), (10, 10, 13)),
}
NEUTRAL = ((0, 20), (0, 20), 0, 0, 0, "flat")
_cache = {}
_state = {"pose": None, "act": None}


def _smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def _back(x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def _lerp(a, b, k):
    f = lambda u, v: u + (v - u) * k
    return ((f(a[0][0], b[0][0]), f(a[0][1], b[0][1])), (f(a[1][0], b[1][0]), f(a[1][1], b[1][1])),
            f(a[2], b[2]), f(a[3], b[3]), f(a[4], b[4]), b[5])


def _make(g):
    if id(g) in _cache:
        return _cache[id(g)]["draw"]

    def cap(d, p, q, w, c):
        for col, ww, off in ((c[0], w, 0.0), (c[1], w * 0.84, -0.06 * w), (c[2], w * 0.26, -0.22 * w)):
            a, b = (p[0] + off, p[1] + off), (q[0] + off, q[1] + off)
            d.line([a, b], fill=col, width=max(1, int(ww)))
            r = ww / 2
            for t in (a, b):
                d.ellipse((t[0] - r, t[1] - r, t[0] + r, t[1] + r), fill=col)

    def ball(d, p, r, c):
        for col, rr, off in ((c[0], r, 0.0), (c[1], r * 0.88, -0.07 * r), (c[2], r * 0.34, -0.38 * r)):
            x, y = p[0] + off, p[1] + off
            d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=col)

    def fk(p, L, a):
        a = math.radians(a)
        return (p[0] + L * math.sin(a), p[1] + L * math.cos(a))

    def figure(d, x, base, height, pose="stand", col=None):
        c = RED_MAN if col is None else WHITE_MAN
        if isinstance(pose, str):
            poses = g["POSES"]
            pose = poses.get(pose, poses["stand"])
        la, ra, ll, rl, hdx, _m = pose
        f = height
        hip = (x, base - 0.44 * f * max(math.cos(math.radians(ll)), math.cos(math.radians(rl))))
        sh = (x, hip[1] - 0.29 * f)
        head = (sh[0] + hdx * f, sh[1] - 0.14 * f)
        rk = fk(hip, 0.22 * f, rl); rf = fk(rk, 0.22 * f, rl)
        lk = fk(hip, 0.22 * f, ll); lf = fk(lk, 0.22 * f, ll)
        re = fk(sh, 0.17 * f, ra[0]); rh = fk(re, 0.15 * f, ra[1])
        le = fk(sh, 0.17 * f, la[0]); lh = fk(le, 0.15 * f, la[1])
        lw, aw = 0.095 * f, 0.075 * f
        cap(d, hip, rk, lw, c); cap(d, rk, rf, lw * 0.95, c); ball(d, rk, lw * 0.55, c)
        cap(d, sh, re, aw, c); cap(d, re, rh, aw * 0.95, c); ball(d, re, aw * 0.55, c); ball(d, rh, aw * 0.6, c)
        cap(d, hip, sh, 0.17 * f, c)
        ball(d, hip, 0.09 * f, c); ball(d, sh, 0.095 * f, c)
        cap(d, hip, lk, lw, c); cap(d, lk, lf, lw * 0.95, c); ball(d, lk, lw * 0.55, c)
        cap(d, sh, le, aw, c); cap(d, le, lh, aw * 0.95, c); ball(d, le, aw * 0.55, c); ball(d, lh, aw * 0.6, c)
        ball(d, head, 0.105 * f, c)

    def background(img, act):
        top, bot = BLACK_BG.get(act, BLACK_BG["neutral"])
        W, H = img.size
        key = (act, W, H)
        if key not in _cache:
            bg = Image.new("RGB", (W, H))
            bd = ImageDraw.Draw(bg)
            for y in range(H):
                t = y / (H - 1)
                bd.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
            _cache[key] = bg
        img.paste(_cache[key])

    def draw(scene, W=1280, H=720, style="scene", t=None, dur=5.0, walk=True, start=None):
        anim = t is not None and style != "thumb"
        T = t if anim else 99.0
        ss = 2 if anim else g["SS"]
        act = scene.get("act", "neutral")
        pose = scene.get("pose", "stand")
        props = [p for p in (scene.get("props") or [])][:3]
        caption = str(scene.get("caption", "")).upper().strip()
        w, h = W * ss, H * ss
        img = Image.new("RGB", (w, h))
        background(img, act)
        d = ImageDraw.Draw(img)
        vertical = H > W
        thumb = style == "thumb"
        if (act == "crack" and (not anim or T >= 0.9)) or thumb:
            g["crack_line"](d, w, h)
        ground = h * (0.80 if not thumb else 0.93)
        d.line([(0, ground), (w, ground)], fill=(225, 225, 230), width=max(2, int(h * 0.005)))
        draw_prop = g["draw_prop"]
        if thumb:
            fh, fx_t = h * 0.66, w * 0.20
        elif vertical:
            fh, fx_t = h * 0.30, w * 0.27
        else:
            fh, fx_t = h * 0.50, w * 0.25
        target = g["POSES"].get(pose, g["POSES"]["stand"])
        fx, cur, bob = fx_t, target, 0.0
        if anim:
            WT = 1.2
            walking = walk and T < WT
            if walking:
                k = T / WT
                amp = 24 * (1 - _smooth((T - 0.85) / 0.35))
                sw = math.sin(T * 8)
                cur = ((amp * 0.8 * sw, amp * 0.8 * sw + 20), (-amp * 0.8 * sw, -amp * 0.8 * sw + 20),
                       -amp * sw, amp * sw, 0, "flat")
                fx = fx_t - 0.5 * w * (1 - k) ** 1.5
                bob = abs(math.sin(T * 8)) * 0.01 * fh
            else:
                t_since = T - WT if walk else T
                begin = NEUTRAL if (walk or start is None) else start
                cur = _lerp(begin, target, _smooth(t_since / 0.6))
                sway = 4.0 * math.sin(T * 2.4) * _smooth(t_since / 0.8)
                cur = ((cur[0][0] + sway, cur[0][1]), (cur[1][0] - sway, cur[1][1]), cur[2], cur[3], cur[4], cur[5])
                bob = 0.003 * fh * (1 + math.sin(T * 2.4))
        figure(d, fx, ground - bob, fh, cur)
        n = max(1, len(props))
        if vertical and not thumb:
            props = props[:2]
            zone_x0, zone_x1 = w * 0.50, w * 0.96
            size = min((zone_x1 - zone_x0) * 0.95, h * 0.26)
        elif thumb:
            zone_x0, zone_x1 = w * 0.42, w * 0.97
            size = min(h * 0.72, (zone_x1 - zone_x0) / n * 0.95)
        else:
            zone_x0, zone_x1 = w * 0.44, w * 0.96
            size = min(h * 0.52, (zone_x1 - zone_x0) / n * 0.9)
        for i, p in enumerate(props):
            sc = _smooth((T - 0.45 - 0.2 * i) / 0.4) if anim else 1.0
            if sc <= 0.03:
                continue
            if vertical and not thumb:
                draw_prop(d, p, (zone_x0 + zone_x1) / 2, ground - i * h * 0.29, size * sc)
            else:
                draw_prop(d, p, zone_x0 + (zone_x1 - zone_x0) * (i + 0.5) / n, ground, size * sc)
        if vertical and not thumb:
            cap_y, cap_size, cap_w = h * 0.08, w * 0.105, 16
        elif thumb:
            cap_y, cap_size, cap_w = h * 0.17, h * 0.2, 14
        else:
            cap_y, cap_size, cap_w = h * 0.12, h * 0.085, 26
        k = (T - 0.1) / 0.3
        if caption and k > 0:
            font, text_center = g["font"], g["text_center"]
            lines = textwrap.wrap(caption, cap_w)[:3]
            size = cap_size
            while size > cap_size * 0.55 and max(d.textlength(l, font=font(size)) for l in lines) > w * 0.94:
                size *= 0.92
            fade = min(1.0, k)
            if anim:
                size *= 0.85 + 0.15 * _smooth(k)
            base_c = g["RED"] if act in ("ruin", "crack") else g["WHITE"]
            colr = tuple(int(c * fade) for c in base_c)
            y = cap_y
            for ln in lines:
                text_center(d, w / 2, y, ln, size, colr, stroke=size * 0.06, stroke_fill=(0, 0, 0))
                y += size * 1.12
        if anim:
            z = 1.03 + 0.03 * min(T / max(dur, 0.5), 1.0)
            sx = sy = 0.0
            t0 = None
            if t0 is not None and t0 <= T < t0 + 0.45:
                a = 14 * (1 - (T - t0) / 0.45)
                sx, sy = a * math.sin(T * 55), a * math.cos(T * 47)
            bw, bh = w / z, h / z
            x0 = min(max(w / 2 - bw / 2 + sx, 0.0), w - bw)
            y0 = min(max(h / 2 - bh / 2 + sy, 0.0), h - bh)
            box = (x0, y0, x0 + bw, y0 + bh)
            return img.resize((W, H), Image.LANCZOS, box=box)
        return img.resize((W, H), Image.LANCZOS)

    _cache[id(g)] = {"draw": draw, "figure": figure, "background": background}
    return draw


def install(g):
    draw = _make(g)
    c = _cache[id(g)]

    def render_scene(scene, W=1280, H=720, path=None, style="scene"):
        img = draw(scene, W, H, style)
        if path:
            img.save(path, quality=93)
        return img

    g["figure"] = c["figure"]
    g["background"] = c["background"]
    g["render_scene"] = render_scene


def clip(S, sc, W, H, frames, FPS, out, png=None):
    """Animated clip for one visual segment (replaces static png + zoompan)."""
    try:
        draw = _make(S.__dict__)
        dur = frames / FPS
        poses = S.__dict__["POSES"]
        act_now = sc.get("act", "neutral")
        target_pose = poses.get(sc.get("pose", "stand"), poses["stand"])
        walk = _state["pose"] is None or _state["act"] != act_now
        start = _state["pose"]
        p = subprocess.Popen(
            ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
             "-i", "-", "-an", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", out],
            stdin=subprocess.PIPE)
        last_q, last_b = None, None
        for k in range(frames):
            tt = k / FPS
            q = round(tt * 15) / 15 if tt < 2.0 else round(tt * 6) / 6
            if q != last_q:
                last_b = draw(sc, W, H, "scene", q, dur, walk, start).tobytes()
                last_q = q
            p.stdin.write(last_b)
        p.stdin.close()
        p.wait()
        if p.returncode != 0:
            raise RuntimeError("ffmpeg failed")
        _state["pose"], _state["act"] = target_pose, act_now
    except Exception as e:
        print("animation fallback:", e)
        img_path = png or out + ".png"
        S.render_scene(sc, W, H, path=img_path)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", img_path, "-frames:v", str(frames),
                        "-r", str(FPS), "-an", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", out],
                       check=True)
