import math
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


def install(g):
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
        poses = g["POSES"]
        la, ra, ll, rl, hdx, _mood = poses.get(pose, poses["stand"])
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
        d = ImageDraw.Draw(img)
        W, H = img.size
        for y in range(H):
            t = y / (H - 1)
            d.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))

    def render_scene(scene, W=1280, H=720, path=None, style="scene"):
        SS = g["SS"]
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
            g["crack_line"](d, w, h)
        ground = h * (0.80 if not thumb else 0.93)
        d.line([(0, ground), (w, ground)], fill=(225, 225, 230), width=max(2, int(h * 0.005)))
        draw_prop = g["draw_prop"]
        if vertical:
            props = props[:2]
            fh, fx = h * 0.30, w * 0.27
            zone_x0, zone_x1 = w * 0.50, w * 0.96
            figure(d, fx, ground, fh, pose)
            size = min((zone_x1 - zone_x0) * 0.95, h * 0.26)
            for i, p in enumerate(props):
                draw_prop(d, p, (zone_x0 + zone_x1) / 2, ground - i * h * 0.29, size)
            cap_y, cap_size, cap_w = h * 0.08, w * 0.105, 16
        elif thumb:
            figure(d, w * 0.20, ground, h * 0.66, pose)
            n = max(1, len(props))
            zone_x0, zone_x1 = w * 0.42, w * 0.97
            size = min(h * 0.72, (zone_x1 - zone_x0) / n * 0.95)
            for i, p in enumerate(props):
                draw_prop(d, p, zone_x0 + (zone_x1 - zone_x0) * (i + 0.5) / n, ground, size)
            cap_y, cap_size, cap_w = h * 0.17, h * 0
