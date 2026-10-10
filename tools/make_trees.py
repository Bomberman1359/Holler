#!/usr/bin/env python3
import json
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw

import texlib as T
from meshlib import Builder
from texlib import Layer, cells, fbm, remap, smoothstep

SIZE = 1024
SS = 2

BOUGH = (0.0, 0.0, 0.5, 0.5)
FAN = (0.5, 0.0, 1.0, 0.5)
TWIGS = (0.0, 0.5, 0.5, 0.75)
CORE = (0.0, 0.75, 0.5, 1.0)
TOP = (0.5, 0.5, 1.0, 1.0)
BOUGH_AXIS = 0.22
FILL = 1.5
FILL_FROM = 0.34
EDGE = 4.0
GUTTER = 5

LAYER_BARK, LAYER_BRANCH, LAYER_WHOLE = 0.0, 0.5, 1.0


def green(rng):
    k = rng.random()
    if k < 0.05:
        return (62, 64, 30)
    if k < 0.35:
        return (36, 58, 32)
    if k < 0.75:
        return (22, 40, 22)
    return (12, 24, 14)


class Canvas:
    def __init__(self):
        s = SIZE * SS
        self.rgb = Image.new("RGB", (s, s), (20, 34, 20))
        self.a = Image.new("L", (s, s), 0)
        self.d = ImageDraw.Draw(self.rgb)
        self.da = ImageDraw.Draw(self.a)

    def draw(self, fn, reg, rng):
        before_rgb, before_a = self.rgb.copy(), self.a.copy()
        fn(self, reg, rng)
        x0, y0, w, h = [int(v) for v in region_px(reg)]
        g = GUTTER * SS
        box = (x0 + g, y0 + g, x0 + w - g, y0 + h - g)
        before_rgb.paste(self.rgb.crop(box), box)
        before_a.paste(self.a.crop(box), box)
        self.rgb, self.a = before_rgb, before_a
        self.d = ImageDraw.Draw(self.rgb)
        self.da = ImageDraw.Draw(self.a)

    def line(self, pts, color, width):
        w = max(int(round(width)), 1)
        self.d.line(pts, fill=color, width=w)
        self.da.line(pts, fill=255, width=w)

    def needles(self, p, tangent, rng, length=(13, 21), angle=0.75, width=3, both=True):
        ang = math.atan2(tangent[1], tangent[0])
        for side in ((-1, 1) if both else (1,)):
            a = ang + side * angle * rng.uniform(0.8, 1.2)
            L = rng.uniform(*length)
            self.line([p, (p[0] + math.cos(a) * L, p[1] + math.sin(a) * L)], green(rng), width)

    def twig(self, start, direction, length, rng, width=(4, 1.5), bend=0.0, step=5.0, color=(46, 36, 27), needle=(13, 21), density=1.0):
        pts = [start]
        ang = math.atan2(direction[1], direction[0])
        n = max(int(length / step), 2)
        for k in range(n):
            ang += bend / n + rng.uniform(-0.03, 0.03)
            last = pts[-1]
            pts.append((last[0] + math.cos(ang) * step, last[1] + math.sin(ang) * step))
        for k in range(len(pts) - 1):
            self.line([pts[k], pts[k + 1]], color, width[0] + (width[1] - width[0]) * k / n)
        for k in range(1, len(pts)):
            if rng.random() < density:
                self.needles(pts[k], (pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]), rng, needle)
        return pts

    def image(self):
        from scipy import ndimage
        rgb = np.asarray(self.rgb, dtype=np.float32) / 255.0
        a = np.asarray(self.a, dtype=np.float32) / 255.0
        soft = ndimage.gaussian_filter(a, FILL * SS)
        mask = (a > 0.5) | (soft > FILL_FROM)
        x0, y0, w, h = region_px(TWIGS)
        y0, y1, x0, x1 = int(y0), int(y0 + h), int(x0), int(x0 + w)
        mask[y0:y1, x0:x1] = a[y0:y1, x0:x1] > 0.5
        wsum = ndimage.gaussian_filter(a, 4.0 * SS) + 1e-4
        fill = np.stack([ndimage.gaussian_filter(rgb[..., c] * a, 4.0 * SS) / wsum for c in range(3)], axis=2) * 0.62
        rgb = rgb * a[..., None] + fill * (1.0 - a[..., None])
        rgb = T.bleed(rgb, mask)
        alpha = T.edge_alpha(mask, EDGE * SS)
        self.mask = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).resize((SIZE, SIZE), Image.BOX), dtype=np.float32) / 255.0
        rgb_img = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).resize((SIZE, SIZE), Image.LANCZOS)
        a_img = Image.fromarray((np.clip(alpha, 0, 1) * 255).astype(np.uint8)).resize((SIZE, SIZE), Image.BOX)
        return np.asarray(rgb_img, dtype=np.float32) / 255.0, np.asarray(a_img, dtype=np.float32) / 255.0


def region_px(reg):
    s = SIZE * SS
    return reg[0] * s, reg[1] * s, (reg[2] - reg[0]) * s, (reg[3] - reg[1]) * s


def draw_bough(c, reg, rng, hang=0.74):
    x0, y0, w, h = region_px(reg)
    axis = []
    for k in range(60):
        t = k / 59.0
        axis.append((x0 + 6 + t * (w - 30), y0 + h * (BOUGH_AXIS - 0.085 * math.sin(math.pi * t * 0.95) + 0.05 * t * t)))
    for k in range(len(axis) - 1):
        c.line([axis[k], axis[k + 1]], (40, 31, 24), 11 - 8 * k / 59.0)
    for k in range(2, len(axis)):
        t = k / 59.0
        tangent = (axis[k][0] - axis[k - 1][0], axis[k][1] - axis[k - 1][1])
        c.needles(axis[k], tangent, rng)
        if k % 2 == 0:
            L = h * hang * (0.25 + 0.75 * math.sin(math.pi * min(t * 1.08, 1.0)) ** 0.7) * rng.uniform(0.55, 1.0)
            L = min(L, y0 + h - 12 - axis[k][1])
            pts = c.twig(axis[k], (rng.uniform(0.02, 0.3), 1.0), L, rng, bend=rng.uniform(-0.25, 0.1))
            for j in range(6, len(pts) - 4, rng.integers(5, 9)):
                side = 1 if rng.random() < 0.5 else -1
                c.twig(pts[j], (side * 0.75, 0.66), rng.uniform(26, 70), rng, width=(2.5, 1), bend=side * -0.5)
        if k % 3 == 1 and t < 0.92:
            c.twig(axis[k], (0.55, -0.83), rng.uniform(40, 110) * (1.0 - 0.5 * t), rng, bend=0.5, width=(3, 1))


def draw_fan(c, reg, rng):
    x0, y0, w, h = region_px(reg)
    mid = y0 + h * 0.5
    axis = [(x0 + 14 + (k / 59.0) * (w - 40), mid + math.sin(k * 0.21) * 5) for k in range(60)]
    for k in range(len(axis) - 1):
        c.line([axis[k], axis[k + 1]], (40, 31, 24), 10 - 7 * k / 59.0)
    for k in range(2, len(axis)):
        t = k / 59.0
        c.needles(axis[k], (1.0, 0.0), rng)
        if k % 3 == 0:
            for side in (-1, 1):
                L = min(h * 0.45 * (1.0 - t) ** 0.5 * rng.uniform(0.6, 1.0) + 18, h * 0.45)
                pts = c.twig(axis[k], (0.55, side * 0.83), L, rng, bend=side * -0.45, width=(3.5, 1))
                for j in range(5, len(pts) - 3, rng.integers(6, 10)):
                    c.twig(pts[j], (0.9, -side * 0.15 + side * 0.5 * (rng.random() < 0.5)), rng.uniform(20, 44), rng, width=(2, 1))


def draw_dead(c, reg, rng):
    x0, y0, w, h = region_px(reg)

    def branch(p, ang, L, width, depth):
        steps = max(int(L / 9), 2)
        pts = [p]
        for k in range(steps):
            ang += rng.uniform(-0.12, 0.12)
            pts.append((pts[-1][0] + math.cos(ang) * 9, pts[-1][1] + math.sin(ang) * 9))
            if pts[-1][0] > x0 + w - 6 or not (y0 + 6 < pts[-1][1] < y0 + h - 6):
                break
        shade = rng.integers(70, 110)
        for k in range(len(pts) - 1):
            c.line([pts[k], pts[k + 1]], (shade, shade - 6, shade - 16), max(width * (1 - k / len(pts)), 1))
        if depth > 0:
            for k in range(2, len(pts) - 1, rng.integers(3, 6)):
                branch(pts[k], ang + rng.choice([-1, 1]) * rng.uniform(0.4, 0.9), L * rng.uniform(0.3, 0.55), width * 0.6, depth - 1)
    branch((x0 + 4, y0 + h * 0.5), 0.0, w * 0.95, 7, 3)
    branch((x0 + 4, y0 + h * 0.5), 0.25, w * 0.6, 5, 2)


def draw_core(c, reg, rng):
    x0, y0, w, h = region_px(reg)
    for _ in range(260):
        p = (x0 + rng.uniform(20, w - 20), y0 + rng.uniform(16, h - 16))
        d = rng.uniform(-1, 1), rng.uniform(0.2, 1)
        c.twig(p, d, rng.uniform(30, 90), rng, width=(2.5, 1), bend=rng.uniform(-0.6, 0.6))


def draw_top(c, reg, rng):
    x0, y0, w, h = region_px(reg)
    cx = x0 + w * 0.5
    c.line([(cx, y0 + h - 4), (cx, y0 + 14)], (40, 31, 24), 9)
    tiers = 15
    for k in range(tiers):
        t = k / (tiers - 1.0)
        y = y0 + 30 + t * (h - 60)
        reach = w * (0.06 + 0.40 * t ** 0.85)
        for side in (-1, 1):
            for _ in range(2):
                L = reach * rng.uniform(0.7, 1.0)
                pts = c.twig((cx, y + rng.uniform(-8, 8)), (side, 0.25), L, rng, bend=side * 0.55, width=(4, 1))
                for j in range(4, len(pts) - 2, 4):
                    c.twig(pts[j], (side * 0.2, 1.0), rng.uniform(18, 52) * (0.5 + t), rng, width=(2, 1))
        c.twig((cx, y), (rng.uniform(-0.3, 0.3), 1.0), reach * 0.5, rng, width=(3, 1))


def bark_layer():
    warp_x = fbm(SIZE, 9, 3, 0.5, 208) * 14.0
    warp_y = fbm(SIZE, 9, 3, 0.5, 209) * 22.0
    _d1, edge, ident = cells(SIZE, 620, 201, stretch=(1.0, 0.5), jitter=1.0)
    yy, xx = np.mgrid[0:SIZE, 0:SIZE]
    sx = np.mod(xx + warp_x, SIZE).astype(np.int32)
    sy = np.mod(yy + warp_y, SIZE).astype(np.int32)
    edge, ident = edge[sy, sx], ident[sy, sx]
    rs = np.random.default_rng(202)
    per = rs.random(ident.max() + 1).astype(np.float32)
    ragged = edge + fbm(SIZE, 70, 3, 0.6, 210) * 1.6
    plate = smoothstep(0.2, 2.6, ragged)
    lift = smoothstep(1.0, 9.0, ragged)
    crack_n = np.abs(fbm(SIZE, 7, 4, 0.55, 203, stretch=(3.2, 0.45)))
    crack = 1.0 - smoothstep(0.0, 0.16, crack_n)
    grain = fbm(SIZE, 40, 4, 0.6, 204, stretch=(2.5, 0.5))
    height = plate * (4.0 + 5.0 * per[ident]) - lift * 2.2 - crack * 7.0 + grain * 1.6 + fbm(SIZE, 4, 3, 0.5, 211) * 3.0
    v = remap(per[ident] * 0.5 + grain * 0.3 + fbm(SIZE, 5, 3, 0.5, 205) * 0.35)
    color = T.ramp(v, [(0.0, (0.10, 0.082, 0.07)), (0.4, (0.19, 0.155, 0.13)), (0.75, (0.27, 0.22, 0.18)), (1.0, (0.36, 0.31, 0.27))])
    color *= (0.62 + 0.38 * plate)[..., None] * (1.0 - 0.55 * crack)[..., None]
    lichen = smoothstep(0.25, 0.5, fbm(SIZE, 6, 4, 0.6, 206)) * smoothstep(-0.2, 0.3, fbm(SIZE, 55, 2, 0.5, 207)) * plate
    color = color * (1.0 - lichen[..., None] * 0.55) + np.array([0.42, 0.46, 0.38], dtype=np.float32) * lichen[..., None] * 0.55
    return Layer("bark", color, height, 0.9, normal_strength=1.1)


def uv_of(reg, u, v):
    return (reg[0] + (reg[2] - reg[0]) * u, reg[1] + (reg[3] - reg[1]) * v)


def norm(v):
    v = np.asarray(v, dtype=np.float64)
    return v / max(np.linalg.norm(v), 1e-9)


def build_tree(b, kind, seed, cards):
    rng = np.random.default_rng(seed)
    young = kind == 3
    dead = kind == 2
    top = 0.86 if dead else 1.0
    r_base = 0.013 if young else 0.0125 if not dead else 0.0135
    crown_from = {0: 0.38, 1: 0.50, 2: 9.0, 3: 0.10}[kind]
    reach = {0: 0.125, 1: 0.10, 2: 0.0, 3: 0.33}[kind]
    whorl_gap = {0: 0.036, 1: 0.038, 2: 1.0, 3: 0.075}[kind]
    per_whorl = {0: 5, 1: 5, 2: 0, 3: 5}[kind]
    bend_x, bend_z = rng.uniform(-0.012, 0.012, 2)
    up = np.array([0.0, 1.0, 0.0])

    def center(t):
        return np.array([bend_x * math.sin(t * 2.6), t, bend_z * math.sin(t * 2.1 + 1.0)])

    def radius(t):
        return r_base * ((1.0 - t / top) ** 0.8 * 0.92 + 0.08) + r_base * 0.75 * math.exp(-t / 0.012)

    def panel(pts, reg, normal, sway, shade, layer=LAYER_BRANCH):
        uvs = [uv_of(reg, 0, 0), uv_of(reg, 1, 0), uv_of(reg, 1, 1), uv_of(reg, 0, 1)]
        b.quad([tuple(q) for q in pts], uvs, tuple(norm(normal)), [(kind, w) for w in sway], (shade, shade, shade, layer))
        cards.append(("card", pts, reg, shade))

    wood = (0.80, 0.78, 0.74) if dead else (1.0, 1.0, 1.0)
    ts = [0.0, 0.006, 0.018, 0.05, 0.12, 0.25, 0.42, 0.6, 0.78, 0.92, 1.0]
    if young:
        top = 0.2
    ts = [t for t in ts if t < top] + [top]
    sides = 6 if young else 7
    b.tube([center(t) for t in ts], [radius(t) * (1.0 if t < top or dead else 0.25) for t in ts], sides, 2.0, [t * 20.0 for t in ts],
           [(kind, 0.15 * t) for t in ts], wood + (LAYER_BARK,), cap_end=dead)
    cards.append(("trunk", [center(t) for t in ts], [radius(t) for t in ts]))

    if young:
        for a in (0.3, 1.35, 2.4):
            out = np.array([math.cos(a), 0.0, math.sin(a)])
            side = np.array([-math.sin(a), 0.0, math.cos(a)])
            w = 0.36
            p = [-out * w + up * 1.0, out * w + up * 1.0, out * w + up * 0.04, -out * w + up * 0.04]
            panel(p, TOP, side + up * 0.6, (1.0, 1.0, 0.2, 0.2), 0.95)
        return

    stubs = {0: 16, 1: 22, 2: 30}[kind]
    for i in range(stubs):
        t = rng.uniform(0.07, (0.84 if dead else crown_from + 0.05))
        a = rng.uniform(0, 2 * math.pi)
        L = rng.uniform(0.02, 0.065) * (2.2 if dead and t > 0.4 else 1.0)
        out = norm([math.cos(a), rng.uniform(-0.5, 0.05), math.sin(a)])
        base = center(t) + norm([out[0], 0, out[2]]) * radius(t) * 0.7
        tip = base + out * L
        b.tube([base, tip], [0.0028, 0.0004], 3, 1.0, [0.0, 1.0], [(kind, 0.2)] * 2, (0.62, 0.60, 0.56, LAYER_BARK))
        cards.append(("stub", base, tip))
        if rng.random() < 0.3:
            fork = tip - out * L * 0.4
            side = norm(np.cross(out, up)) * (1 if rng.random() < 0.5 else -1)
            tip2 = fork + norm(out + side * 0.8 + up * 0.2) * L * 0.5
            b.tube([fork, tip2], [0.0012, 0.0003], 3, 1.0, [0.0, 1.0], [(kind, 0.3)] * 2, (0.62, 0.60, 0.56, LAYER_BARK))
            cards.append(("stub", fork, tip2))
    if dead:
        return

    t = crown_from
    whorl = 0
    while t < 0.955:
        u = (t - crown_from) / (1.0 - crown_from)
        for k in range(per_whorl):
            a = whorl * 2.399963 + k * 2 * math.pi / per_whorl + rng.uniform(-0.2, 0.2)
            L = reach * (1.0 - u ** 1.3) * rng.uniform(0.85, 1.12) + 0.014
            out = np.array([math.cos(a), 0.0, math.sin(a)])
            side = np.array([-math.sin(a), 0.0, math.cos(a)])
            base = center(t + rng.uniform(-0.008, 0.008)) + out * radius(t) * 0.4
            drop = L * math.tan(0.55 * (1.0 - u) + 0.08 + rng.uniform(-0.08, 0.08))
            tip = base + out * L - up * drop
            shade = 0.55 + 0.45 * u
            wv = L * 0.46
            sag = up * (wv * 0.35)
            panel([base - side * wv - sag, tip - side * wv * 0.9 - sag, tip + side * wv * 0.9 - sag, base + side * wv - sag],
                  FAN, up + out * 0.35, (0.2, 1.0, 1.0, 0.2), shade)
            H = L * 0.55
            for sgn in (-1.0, 1.0):
                lean = side * (sgn * H * 0.42)
                top0 = base + up * (BOUGH_AXIS * H)
                top1 = tip + up * (BOUGH_AXIS * H * 0.6)
                panel([top0, top1, top1 - up * H * 0.8 + lean, top0 - up * H + lean],
                      BOUGH, side * sgn + up * 0.5, (0.25, 1.0, 1.0, 0.4), shade * 0.9)
        if whorl % 2 == 0 and u < 0.9:
            for a in (0.4, 1.45, 2.5):
                out = np.array([math.cos(a), 0.0, math.sin(a)])
                side = np.array([-math.sin(a), 0.0, math.cos(a)])
                w = reach * (1.0 - u) * 0.6 + 0.012
                hh = whorl_gap * 2.6
                c0 = center(t)
                panel([c0 - out * w + up * hh, c0 + out * w + up * hh, c0 + out * w - up * hh * 0.2, c0 - out * w - up * hh * 0.2],
                      CORE, side + up * 0.5, (0.3, 0.3, 0.3, 0.3), 0.42)
        t += whorl_gap * rng.uniform(0.85, 1.15)
        whorl += 1
    for a in (0.3, 1.35, 2.4):
        out = np.array([math.cos(a), 0.0, math.sin(a)])
        side = np.array([-math.sin(a), 0.0, math.cos(a)])
        w, hh = 0.034, 0.085
        c0 = center(1.0)
        panel([c0 - out * w + up * 0.004, c0 + out * w + up * 0.004, c0 + out * w - up * hh, c0 - out * w - up * hh],
              TOP, side + up * 0.6, (1.0, 1.0, 0.6, 0.6), 1.0)


WHOLE_W, WHOLE_H = 256, 1024
HALF_WIDTH = [0.25, 0.25, 0.25, 0.42]
EDGE_WHOLE = 3.0


def render_whole(cards, kind, branch_rgba, bark_rgb):
    ss = 2
    W, H = WHOLE_W * ss, WHOLE_H * ss
    half = HALF_WIDTH[kind]
    canvas = np.zeros((H, W, 4), dtype=np.float32)

    def to_px(p):
        return [(p[0] / half * 0.5 + 0.5) * W, (1.0 - p[1]) * (H - 8) + 4]

    items = []
    for c in cards:
        if c[0] == "card":
            depth = float(np.mean([q[2] for q in c[1]]))
            items.append((depth, c))
    items.sort(key=lambda it: it[0])
    if kind == 3:
        w = 0.36
        items = [(0.01, ("card", [np.array([-w, 1.0, 0.0]), np.array([w, 1.0, 0.0]), np.array([w, 0.04, 0.0]), np.array([-w, 0.04, 0.0])], TOP, 0.95))]
    trunk = [c for c in cards if c[0] == "trunk"][0]
    stubs = [c for c in cards if c[0] == "stub"]

    def draw_trunk():
        pil = Image.fromarray((np.clip(canvas, 0, 1) * 255).astype(np.uint8), "RGBA")
        d = ImageDraw.Draw(pil)
        centers, radii = trunk[1], trunk[2]
        for i in range(len(centers) - 1):
            a, b2 = to_px(centers[i]), to_px(centers[i + 1])
            ra, rb = radii[i] / half * 0.5 * W, radii[i + 1] / half * 0.5 * W
            shade = 40 if kind != 2 else 62
            d.polygon([(a[0] - ra, a[1]), (a[0] + ra, a[1]), (b2[0] + rb, b2[1]), (b2[0] - rb, b2[1])], fill=(shade, int(shade * 0.82), int(shade * 0.68), 255))
        for s in stubs:
            a, b2 = to_px(s[1]), to_px(s[2])
            d.line([tuple(a), tuple(b2)], fill=(70, 66, 58, 255), width=3)
        return np.asarray(pil, dtype=np.float32) / 255.0

    half_done = False
    for depth, c in items:
        if not half_done and depth > 0.0:
            canvas = draw_trunk()
            half_done = True
        _, pts, reg, shade = c
        x0, y0, x1, y1 = int(reg[0] * SIZE), int(reg[1] * SIZE), int(reg[2] * SIZE), int(reg[3] * SIZE)
        piece = branch_rgba[y0:y1, x0:x1]
        src = np.float32([[0, 0], [x1 - x0, 0], [x1 - x0, y1 - y0], [0, y1 - y0]])
        dst = np.float32([to_px(q) for q in pts])
        dark = shade * (0.7 + 0.3 * (depth > 0.0))
        for tri in ((0, 1, 2), (0, 2, 3)):
            d3 = dst[list(tri)]
            e1, e2 = d3[1] - d3[0], d3[2] - d3[0]
            area = abs(float(e1[0] * e2[1] - e1[1] * e2[0])) * 0.5
            if area < 8.0:
                continue
            bx0, by0 = np.floor(d3.min(axis=0)).astype(int)
            bx1, by1 = np.ceil(d3.max(axis=0)).astype(int) + 1
            bx0, by0, bx1, by1 = max(bx0, 0), max(by0, 0), min(bx1, W), min(by1, H)
            if bx1 <= bx0 or by1 <= by0:
                continue
            local = d3 - np.float32([bx0, by0])
            M = cv2.getAffineTransform(src[list(tri)], local)
            warped = cv2.warpAffine(piece, M, (bx1 - bx0, by1 - by0), flags=cv2.INTER_LINEAR)
            mask = np.zeros((by1 - by0, bx1 - bx0), dtype=np.float32)
            cv2.fillConvexPoly(mask, np.round(local).astype(np.int32), 1.0)
            a = (warped[..., 3:4] > 0.5) * mask[..., None]
            view = canvas[by0:by1, bx0:bx1]
            view[..., :3] = view[..., :3] * (1.0 - a) + warped[..., :3] * dark * a
            view[..., 3:4] = view[..., 3:4] * (1.0 - a) + a
    if not half_done:
        canvas = draw_trunk()
    mask = canvas[..., 3] > 0.5
    canvas[..., :3] = T.bleed(canvas[..., :3], mask)
    canvas[..., 3] = T.edge_alpha(mask, EDGE_WHOLE * ss)
    out = cv2.resize(canvas, (WHOLE_W, WHOLE_H), interpolation=cv2.INTER_AREA)
    return out


FAR_ROWS = 11


def far_mesh():
    b = Builder()
    rows = []
    for r in range(FAR_ROWS):
        y = r / (FAR_ROWS - 1.0)
        left = b.vertex((-0.25, y, 0.0), (0.0, 0.0, 1.0), (-1.0, y), (float(r), y), (1.0, 1.0, 1.0, LAYER_WHOLE))
        right = b.vertex((0.25, y, 0.0), (0.0, 0.0, 1.0), (1.0, y), (float(r), y), (1.0, 1.0, 1.0, LAYER_WHOLE))
        rows.append((left, right))
    for r in range(FAR_ROWS - 1):
        a, c = rows[r], rows[r + 1]
        b.tri(a[0], a[1], c[1])
        b.tri(a[0], c[1], c[0])
    return b


def far_bands(whole):
    table = []
    for kind in range(4):
        alpha = whole[:, kind * WHOLE_W:(kind + 1) * WHOLE_W, 3] > 0.3
        xs = np.abs(np.arange(WHOLE_W) + 0.5 - WHOLE_W * 0.5) / (WHOLE_W * 0.5)
        reach = np.where(alpha, xs[None, :], 0.0).max(axis=1)
        widths = []
        for band in range(FAR_ROWS - 1):
            y0, y1 = band / (FAR_ROWS - 1.0), (band + 1) / (FAR_ROWS - 1.0)
            p0 = int(np.clip((1.0 - y1) * (WHOLE_H - 4) + 2 - 2, 0, WHOLE_H - 1))
            p1 = int(np.clip((1.0 - y0) * (WHOLE_H - 4) + 2 + 3, 1, WHOLE_H))
            widths.append(float(reach[p0:p1].max()))
        for r in range(FAR_ROWS):
            near = [widths[k] for k in (r - 1, r) if 0 <= k < len(widths)]
            table.append(round(min(max(near) + 0.07, 1.0), 4))
    return table


def main():
    rng = np.random.default_rng(77)
    c = Canvas()
    c.draw(draw_bough, BOUGH, rng)
    c.draw(draw_fan, FAN, rng)
    c.draw(draw_dead, TWIGS, rng)
    c.draw(draw_core, CORE, rng)
    c.draw(draw_top, TOP, rng)
    rgb, alpha = c.image()

    bark = bark_layer()
    whole = np.zeros((SIZE, SIZE, 4), dtype=np.float32)
    branch_rgba = np.dstack([rgb, alpha]).astype(np.float32)
    bark_rgb = np.asarray(bark.albedo_image().convert("RGB"), dtype=np.float32) / 255.0
    counts = []
    for kind in range(4):
        cards = []
        near = Builder()
        build_tree(near, kind, 500 + kind, cards)
        counts.append(near.triangles())
        near.write("mesh", "tree_near_%d" % kind)
        pic = render_whole(cards, kind, branch_rgba, bark_rgb)
        whole[:, kind * WHOLE_W:(kind + 1) * WHOLE_W] = pic
    far = far_mesh()
    far.write("mesh", "tree_far")
    with open(os.path.join(T.out_dir("mesh"), "tree_far.json"), "w") as f:
        json.dump({"rows": FAR_ROWS, "band": far_bands(whole), "half_width": HALF_WIDTH}, f)

    zeros = np.zeros((SIZE, SIZE), dtype=np.float32)
    layers = [
        bark,
        Layer("branches", rgb, zeros, 0.85, alpha=alpha, ao=0.0),
        Layer("whole", whole[..., :3], zeros, 0.9, alpha=whole[..., 3], ao=0.0),
    ]
    T.write_array("tex", "tree", layers, cols=2)
    Image.fromarray((np.clip(np.dstack([rgb, alpha]), 0, 1) * 255).astype(np.uint8), "RGBA").save("/tmp/tree_branches.png")
    Image.fromarray((np.clip(whole, 0, 1) * 255).astype(np.uint8), "RGBA").save("/tmp/tree_whole.png")
    print("near mesh: %s triangles per kind, far mesh: %d triangles" % (counts, far.triangles()))


if __name__ == "__main__":
    main()
