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
GOLD_MAN = ((120, 80, 8), (205, 150, 20), (255, 225, 110))
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

    def figure(d, x, base, height, pose="stand", col=None, rot=0.0):
        c = RED_MAN if col is None else WHITE_MAN
        if isinstance(pose, str):
            poses = g["POSES"]
            pose = poses.get(pose, poses["stand"])
        la, ra, ll, rl, hdx, _m = pose
        f = height
        hip = (x, base - 0.44 * f * max(math.cos(math.radians(ll)), math.cos(math.radians(rl))))
        sh = (x, hip[1] - 0.29 * f)
        P = {"hip": hip, "sh": sh, "head": (sh[0] + hdx * f, sh[1] - 0.14 * f)}
        P["rk"] = fk(hip, 0.22 * f, rl); P["rf"] = fk(P["rk"], 0.22 * f, rl)
        P["lk"] = fk(hip, 0.22 * f, ll); P["lf"] = fk(P["lk"], 0.22 * f, ll)
        P["re"] = fk(sh, 0.17 * f, ra[0]); P["rh"] = fk(P["re"], 0.15 * f, ra[1])
        P["le"] = fk(sh, 0.17 * f, la[0]); P["lh"] = fk(P["le"], 0.15 * f, la[1])
        if rot:
            ca, sa = math.cos(rot), math.sin(rot)
            P = {k: (hip[0] + (v[0] - hip[0]) * ca - (v[1] - hip[1]) * sa,
                     hip[1] + (v[0] - hip[0]) * sa + (v[1] - hip[1]) * ca) for k, v in P.items()}
        lw, aw = 0.095 * f, 0.075 * f
        cap(d, P["hip"], P["rk"], lw, c); cap(d, P["rk"], P["rf"], lw * 0.95, c); ball(d, P["rk"], lw * 0.55, c)
        cap(d, P["sh"], P["re"], aw, c); cap(d, P["re"], P["rh"], aw * 0.95, c)
        ball(d, P["re"], aw * 0.55, c); ball(d, P["rh"], aw * 0.6, c)
        cap(d, P["hip"], P["sh"], 0.17 * f, c)
        ball(d, P["hip"], 0.09 * f, c); ball(d, P["sh"], 0.095 * f, c)
        cap(d, P["hip"], P["lk"], lw, c); cap(d, P["lk"], P["lf"], lw * 0.95, c); ball(d, P["lk"], lw * 0.55, c)
        cap(d, P["sh"], P["le"], aw, c); cap(d, P["le"], P["lh"], aw * 0.95, c)
        ball(d, P["le"], aw * 0.55, c); ball(d, P["lh"], aw * 0.6, c)
        ball(d, P["head"], 0.105 * f, c)

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

    # ---------------- metaphor scene templates (like the reference video) ----------------
    WHITE_C, RED_C = (245, 245, 245), (226, 62, 62)
    LINE_C = (232, 232, 236)

    def _out(x):
        x = max(0.0, min(1.0, x))
        return 1 - (1 - x) ** 3

    def label(d, s, cx, cy, size, col, alpha=1.0, max_w=None):
        if not s or alpha <= 0.02:
            return
        f = g["font"](size)
        wl = d.textlength(s, font=f)
        if max_w and wl > max_w:
            size = size * max_w / wl
        c = tuple(int(v * min(1.0, alpha)) for v in col)
        half = d.textlength(s, font=g["font"](size)) / 2 + size * 0.2
        cx = min(max(cx, half), d.im.size[0] - half)
        g["text_center"](d, cx, cy, s, size, c, stroke=size * 0.05, stroke_fill=(0, 0, 0))

    def lab_size(w, h, v):
        return h * 0.052 if not v else w * 0.072

    def walk_pose(ph, amp):
        sw = math.sin(ph)
        return ((amp * 0.8 * sw, amp * 0.8 * sw + 20), (-amp * 0.8 * sw, -amp * 0.8 * sw + 20),
                -amp * sw, amp * sw, 0, "flat")

    def stair_geo(w, h, v, N):
        ground = h * (0.82 if not v else 0.76)
        sh = h * (0.058 if not v else 0.04)
        x0, x1 = w * 0.07, w * 0.93
        return ground, sh, x0, (x1 - x0) / N

    def elev(x, x0, sw, sh, N):
        return sh * sum(_smooth((x - (x0 + k * sw)) / (0.3 * sw)) for k in range(N))

    def stair_line(d, w, h, ground, sh, x0, sw, n_steps, lw):
        pts = [(0, ground), (x0, ground)]
        for k in range(n_steps):
            e = ground - (k + 1) * sh
            pts += [(x0 + k * sw, e), (x0 + (k + 1) * sw, e)]
        d.line(pts, fill=LINE_C, width=lw, joint="curve")

    def t_stairs_up(d, w, h, v, T, dur, L):
        N = 6
        ground, sh, x0, sw = stair_geo(w, h, v, N)
        lw = max(3, int(h * 0.006))
        stair_line(d, w, h, ground, sh, x0, sw, N, lw)
        fh = h * (0.28 if not v else 0.2)
        p = _smooth(T / (dur * 0.78))
        xs, xe = x0 - 0.5 * sw, x0 + (N - 0.5) * sw
        fx = xs + (xe - xs) * p
        base = ground - elev(fx, x0, sw, sh, N)
        if p < 1.0:
            pose, bob = walk_pose(T * 7.0, 26), abs(math.sin(T * 7.0)) * 0.012 * fh
        else:
            pose, bob = ((-150 + 8 * math.sin(T * 3), -165), (150 - 8 * math.sin(T * 3), 165), -6, 6, 0, "f"), 0
        figure(d, fx, base - bob, fh, pose)
        ls = lab_size(w, h, v)
        label(d, L[0], w / 2, h * 0.09, ls, WHITE_C, _smooth((T - 0.15) / 0.3), w * 0.92)
        if len(L) > 1:
            label(d, L[1], fx, base - fh * 1.3, ls, RED_C, _smooth((T - dur * 0.78) / 0.3), w * 0.5)

    def t_stairs_down(d, w, h, v, T, dur, L):
        N = 6
        ground, sh, x0, sw = stair_geo(w, h, v, N)
        lw = max(3, int(h * 0.006))
        stair_line(d, w, h, ground, sh, x0, sw, N - 1, lw)
        fh = h * (0.28 if not v else 0.2)
        bx0 = x0 + (N - 1) * sw
        top_y = ground - N * sh
        cx = bx0 + sw / 2
        t_c, t_f = 0.8, 1.7
        ls = lab_size(w, h, v)
        label(d, L[0], w / 2, h * 0.09, ls, WHITE_C, _smooth((T - 0.1) / 0.3), w * 0.92)
        G = h * 1.9
        if T < t_f:
            d.rectangle((bx0, top_y, bx0 + sw, top_y + sh), outline=LINE_C, width=lw)
            if T >= t_c:
                fl = 0.5 + 0.5 * math.sin(T * 40)
                for dx in (-0.3, 0.0, 0.3):
                    xx = cx + dx * sw
                    d.line([(xx, top_y), (xx + sw * 0.05, top_y + sh * 0.5), (xx - sw * 0.03, top_y + sh)],
                           fill=(int(150 + 90 * fl), 30, 30), width=lw)
            tr = 0.0 if T < t_c else 3.0 * math.sin(T * 50)
            pose = ((-150, -165), (150, 165), -6, 6, 0, "f") if T < t_c else ((-25, -20), (25, 20), -6, 6, 0.04, "s")
            figure(d, cx + tr, top_y, fh, pose)
        else:
            tf = T - t_f
            seeds = (-0.35, -0.1, 0.12, 0.4)
            for i, sd in enumerate(seeds):
                px = bx0 + i * sw / 4 + sd * sw * 0.6 * tf
                py = top_y + 0.5 * G * tf * tf
                a = (1.6 + i * 0.7) * tf * (1 if i % 2 else -1)
                c0 = (px + sw / 8, py + sh / 2)
                cs = [(px, py), (px + sw / 4, py), (px + sw / 4, py + sh), (px, py + sh)]
                poly = []
                for q in cs:
                    dx, dy = q[0] - c0[0], q[1] - c0[1]
                    poly.append((c0[0] + dx * math.cos(a) - dy * math.sin(a), c0[1] + dx * math.sin(a) + dy * math.cos(a)))
                d.polygon(poly, outline=LINE_C, width=lw)
            hipy = top_y + 0.5 * G * tf * tf
            figure(d, cx + h * 0.05 * tf, hipy, fh, ((-160, -170), (160, 170), -12, 12, 0, "p"), None, 2.2 * tf)
            label(d, L[1] if len(L) > 1 else "", w / 2, h * 0.24, ls * 1.5, RED_C, _smooth((tf - 0.3) / 0.3), w * 0.9)

    def t_bars(d, w, h, v, T, dur, L, up):
        lw = max(3, int(h * 0.006))
        if not v:
            cx0, cx1, by, Hc = w * 0.10, w * 0.66, h * 0.80, h * 0.46
            fx, fgr, fh = w * 0.83, h * 0.80, h * 0.31
        else:
            cx0, cx1, by, Hc = w * 0.10, w * 0.90, h * 0.62, h * 0.34
            fx, fgr, fh = w * 0.5, h * 0.88, h * 0.2
        d.line([(cx0, by - Hc * 1.08), (cx0, by), (cx1, by)], fill=LINE_C, width=lw, joint="curve")
        n = 5
        slot = (cx1 - cx0) / n
        bw = slot * 0.5
        small = (0.07, 0.11, 0.0, 0.09, 0.06)
        pr = _out(T / (dur * 0.8))
        hero = 0.95 * (pr if up else 1 - pr) + 0.03
        for i in range(n):
            x = cx0 + (i + 0.5) * slot
            val = (hero if i == 2 else small[i]) * Hc
            if val < 2:
                continue
            col = RED_MAN if i == 2 else WHITE_MAN
            d.rectangle((x - bw / 2, by - val, x + bw / 2, by), fill=col[1])
            d.rectangle((x - bw / 2, by - val, x - bw / 2 + bw * 0.22, by), fill=col[2])
        ls = lab_size(w, h, v)
        label(d, L[0], (cx0 + cx1) / 2, h * 0.09, ls, WHITE_C, _smooth((T - 0.1) / 0.3), w * 0.92)
        hx = cx0 + 2.5 * slot
        if len(L) > 1:
            label(d, L[1], hx, by - hero * Hc - h * 0.045, ls * 0.9, RED_C, _smooth((T - 0.5) / 0.3), slot * 3)
        pose = ((-150, -165), (150, 165), -8, 8, 0, "c") if up else ((-22, -12), (22, 12), -6, 6, 0.05, "s")
        sway = 4 * math.sin(T * 2.4)
        figure(d, fx, fgr, fh, ((pose[0][0] + sway, pose[0][1]), (pose[1][0] - sway, pose[1][1]), pose[2], pose[3], pose[4], "x"))

    def t_versus(d, w, h, v, T, dur, L):
        ground = h * (0.78 if not v else 0.7)
        fh = h * (0.34 if not v else 0.19)
        lx, rx = w * 0.27, w * 0.73
        lw = max(3, int(h * 0.006))
        d.line([(0, ground), (w, ground)], fill=LINE_C, width=lw)
        ls = lab_size(w, h, v)
        a = math.sin(T * 8)
        left = ((-15, -10), (105 + 50 * a, 112 + 50 * a), -8, 8, 0, "p")
        sway = 6 * math.sin(T * 1.6)
        right = ((-28 + sway, -20), (28 - sway, 20), -8, 8, 0, "r")
        figure(d, lx, ground - abs(a) * 0.006 * fh, fh, left, WHITE_MAN)
        figure(d, rx, ground, fh, right, None)
        label(d, L[0], lx, ground - fh * 1.35, ls, WHITE_C, _smooth((T - 0.1) / 0.3), w * 0.45)
        if len(L) > 1:
            label(d, L[1], rx, ground - fh * 1.35, ls, RED_C, _smooth((T - 0.25) / 0.3), w * 0.45)
        bar = w * 0.3
        pr = _out(T / (dur * 0.85))
        y0, bh = ground + h * 0.05, h * 0.028
        d.rectangle((lx - bar / 2, y0, lx - bar / 2 + bar * 0.35 * pr, y0 + bh), fill=WHITE_MAN[1])
        d.rectangle((rx - bar / 2, y0, rx - bar / 2 + bar * pr, y0 + bh), fill=RED_MAN[1])

    def t_ladder(d, w, h, v, T, dur, L):
        ground = h * (0.86 if not v else 0.82)
        top = h * 0.22
        fh = h * (0.2 if not v else 0.13)
        gap = fh * 0.40
        cx = w * 0.5
        rail = fh * 0.34
        lw = max(3, int(h * 0.006))
        d.line([(cx - rail, ground), (cx - rail, top)], fill=LINE_C, width=lw)
        d.line([(cx + rail, ground), (cx + rail, top)], fill=LINE_C, width=lw)
        y = ground - gap
        while y > top:
            d.line([(cx - rail, y), (cx + rail, y)], fill=LINE_C, width=max(2, lw // 2))
            y -= gap
        nr = int((ground - top) / gap) - 4
        pos = _smooth(T / (dur * 0.9)) * nr
        idx = int(pos) + _smooth(pos - int(pos))
        base = ground - idx * gap
        ph = pos * math.pi * 2
        pose = ((-166 + 8 * math.sin(ph), -172), (166 + 8 * math.cos(ph), 172), -10 + 14 * math.sin(ph), 10 + 14 * math.cos(ph), 0, "l")
        figure(d, cx, base, fh, pose)
        ls = lab_size(w, h, v)
        label(d, L[0], cx, top - h * 0.07, ls * 1.2, WHITE_C, _smooth((T - 0.1) / 0.3), w * 0.9)
        if len(L) > 1:
            label(d, L[1], cx + w * 0.22, (ground + top) / 2, ls, RED_C, _smooth((T - dur * 0.4) / 0.3), w * 0.36)

    def t_push(d, w, h, v, T, dur, L):
        ground = h * (0.80 if not v else 0.72)
        fh = h * (0.31 if not v else 0.19)
        lw = max(3, int(h * 0.006))
        d.line([(0, ground), (w, ground)], fill=LINE_C, width=lw)
        pr = _smooth(T / (dur * 0.9))
        rmax = min(h * 0.22, w * 0.16) if not v else min(h * 0.12, w * 0.2)
        r = rmax * (0.25 + 0.75 * pr)
        fx = w * 0.2 + w * 0.3 * pr
        bx = fx + fh * 0.30 + r
        figure(d, fx, ground, fh, ((75, 80), (88, 90), -12 * math.sin(T * 5), 12 * math.sin(T * 5), 0, "p"), None)
        ball(d, (bx, ground - r), r, WHITE_MAN)
        ang = (bx - w * 0.2) / max(r, 1)
        d.line([(bx, ground - r), (bx + r * 0.92 * math.cos(ang), ground - r + r * 0.92 * math.sin(ang))],
               fill=(70, 70, 78), width=max(3, int(r * 0.09)))
        ls = lab_size(w, h, v)
        n = min(3, max(1, len(L)))
        for i in range(n):
            cxl = w * ((0.5,) if n == 1 else (0.28, 0.72) if n == 2 else (0.18, 0.5, 0.82))[i]
            label(d, L[i], cxl, h * 0.1, ls, RED_C if i == n - 1 and n > 1 else WHITE_C, _smooth((T - dur * i / (n + 0.5)) / 0.3), w * 0.3)

    def t_crown(d, w, h, v, T, dur, L):
        cw = w * (0.30 if not v else 0.52)
        cx, cy = w * (0.55 if not v else 0.5), h * 0.5
        left = [(-1, 0.55), (-1, -0.1), (-0.5, 0.25), (0, -0.55), (0, 0.55)]
        right = [(0, 0.55), (0, -0.55), (0.5, 0.25), (1, -0.1), (1, 0.55)]
        lw = max(3, int(h * 0.006))
        t_split = 1.9
        ls = lab_size(w, h, v)
        label(d, L[0], w / 2, h * 0.09, ls, WHITE_C, _smooth((T - 0.1) / 0.3), w * 0.92)

        def poly(pts, ox, oy, a, col):
            out = []
            for px, py in pts:
                x, y = px * cw / 2, py * cw / 2
                out.append((cx + ox + x * math.cos(a) - y * math.sin(a), cy + oy + x * math.sin(a) + y * math.cos(a)))
            d.polygon(out, fill=col[1])

        if T < t_split:
            poly(left, 0, 0, 0, GOLD_MAN)
            poly(right, 0, 0, 0, GOLD_MAN)
            d.line([(cx - cw * 0.5, cy + cw * 0.275), (cx - cw * 0.25, cy + cw * 0.125), (cx, cy - cw * 0.275)],
                   fill=GOLD_MAN[2], width=lw * 2)
            if T > 0.5:
                pr = _smooth((T - 0.5) / 1.2)
                zig = [(cx, cy - cw * 0.28), (cx + cw * 0.05, cy - cw * 0.1), (cx - cw * 0.04, cy + cw * 0.05),
                       (cx + cw * 0.05, cy + cw * 0.2), (cx, cy + cw * 0.28)]
                k = max(2, int(len(zig) * pr + 1))
                d.line(zig[:k], fill=RED_C, width=lw * 2)
        else:
            tf = T - t_split
            G = h * 1.5
            poly(left, -cw * 0.25 * tf, 0.5 * G * tf * tf, -1.3 * tf, GOLD_MAN)
            poly(right, cw * 0.25 * tf, 0.5 * G * tf * tf, 1.3 * tf, GOLD_MAN)
            label(d, L[1] if len(L) > 1 else "", w / 2, h * 0.24, ls * 1.5, RED_C, _smooth((tf - 0.2) / 0.3), w * 0.9)
        sway = 4 * math.sin(T * 2.4)
        figure(d, w * (0.14 if not v else 0.17), h * (0.82 if not v else 0.9), h * (0.27 if not v else 0.17),
               ((-22 + sway, -12), (22 - sway, 12), -6, 6, 0.05, "s"))

    def t_line(d, w, h, v, T, dur, L):
        lw = max(3, int(h * 0.007))
        x0, x1 = w * 0.10, w * 0.90
        by, ty = (h * 0.78, h * 0.28) if not v else (h * 0.68, h * 0.30)
        d.line([(x0, ty - h * 0.04), (x0, by), (x1, by)], fill=LINE_C, width=max(2, lw - 2), joint="curve")
        vals = [0.12, 0.2, 0.17, 0.3, 0.38, 0.5, 0.55, 0.68, 0.8, 0.95, 0.62, 0.36, 0.18, 0.06]
        pts = [(x0 + (x1 - x0) * i / (len(vals) - 1), by - (by - ty) * val) for i, val in enumerate(vals)]
        peak = vals.index(max(vals))
        pr = _smooth(T / (dur * 0.8)) * (len(vals) - 1)
        n = int(pr)
        frac = pr - n
        draw_pts = pts[:n + 1]
        if n < len(vals) - 1:
            a, b = pts[n], pts[n + 1]
            draw_pts = draw_pts + [(a[0] + (b[0] - a[0]) * frac, a[1] + (b[1] - a[1]) * frac)]
        for i in range(len(draw_pts) - 1):
            col = LINE_C if i < peak else RED_C
            d.line([draw_pts[i], draw_pts[i + 1]], fill=col, width=lw)
        hx, hy = draw_pts[-1]
        r = lw * 1.6
        d.ellipse((hx - r, hy - r, hx + r, hy + r), fill=RED_C)
        ls = lab_size(w, h, v)
        label(d, L[0], w / 2, h * 0.09, ls, WHITE_C, _smooth((T - 0.1) / 0.3), w * 0.92)
        if len(L) > 1 and pr >= peak:
            label(d, L[1], pts[peak][0], pts[peak][1] - h * 0.05, ls * 0.9, WHITE_C, _smooth((pr - peak) / 0.6), w * 0.4)
        if len(L) > 2 and pr >= len(vals) - 1.5:
            label(d, L[2], pts[-1][0] - w * 0.08, pts[-1][1] - h * 0.07, ls * 0.9, RED_C, _smooth((pr - len(vals) + 1.5) / 0.5), w * 0.3)

    TEMPLATES = {
        "stairs_up": t_stairs_up, "stairs_down": t_stairs_down,
        "bars_up": lambda *a: t_bars(*a, True), "bars_down": lambda *a: t_bars(*a, False),
        "versus": t_versus, "ladder": t_ladder, "push": t_push, "crown_crack": t_crown, "line_graph": t_line,
    }

    def render_template(kind, scene, W, H, T, dur):
        ss = 2
        w, h = W * ss, H * ss
        img = Image.new("RGB", (w, h))
        background(img, scene.get("act", "neutral"))
        d = ImageDraw.Draw(img)
        L = [str(x).upper() for x in (scene.get("labels") or [scene.get("caption", "")]) if str(x).strip()] or [""]
        TEMPLATES[kind](d, w, h, H > W, T, dur, L)
        return img.resize((W, H), Image.LANCZOS)

    def draw(scene, W=1280, H=720, style="scene", t=None, dur=5.0, walk=True, start=None):
        anim = t is not None and style != "thumb"
        T = t if anim else 99.0
        kind = scene.get("scene")
        if anim and kind in TEMPLATES:
            return render_template(kind, scene, W, H, T, dur)
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
                fx = fx_t
