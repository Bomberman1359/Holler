#!/usr/bin/env python3
import math
import os

import numpy as np
from PIL import Image

import maplib
import texlib
from meshlib import write_hmesh

rng = np.random.default_rng(31)


def cover_map():
    ctl = np.asarray(Image.open(os.path.join(maplib.GEN, "terrain", "control.png")).convert("RGBA"), dtype=np.float32) / 255.0
    tint = np.asarray(Image.open(os.path.join(maplib.GEN, "terrain", "tint.png")).convert("RGBA"), dtype=np.float32) / 255.0
    n = ctl.shape[0]
    forest, meadow, scree, dirt = ctl[..., 0], ctl[..., 1], ctl[..., 2], ctl[..., 3]
    wet = tint[..., 3]
    bare = np.clip(1.0 - dirt * 1.6, 0.0, 1.0) * np.clip(1.0 - (wet - 0.35) * 3.0, 0.0, 1.0)
    fern = np.clip(forest * 0.75 + meadow * 0.12, 0, 1) * bare
    grass = np.clip(meadow * 0.95 + forest * 0.3, 0, 1) * bare
    rock = np.clip(scree * 0.85 + forest * 0.05 + meadow * 0.03, 0, 1) * np.clip(1.0 - dirt * 1.6, 0.0, 1.0)
    built = os.path.join(maplib.GEN, "sites", "keepout.npy")
    if os.path.exists(built):
        size = int(n - 1) * 2
        mask = np.unpackbits(np.load(built), axis=1)[:, :size].astype(bool)
        h = mask.shape[0] // 2 * 2
        w = mask.shape[1] // 2 * 2
        small = mask[:h, :w].reshape(h // 2, 2, w // 2, 2).any(axis=(1, 3))
        blocked = np.zeros((n, n), dtype=bool)
        blocked[:small.shape[0], :small.shape[1]] = small
        blocked = blocked | np.roll(blocked, 1, 0) | np.roll(blocked, 1, 1) | np.roll(blocked, -1, 0) | np.roll(blocked, -1, 1)
        fern[blocked] = 0.0
        grass[blocked] = 0.0
        rock[blocked] = 0.0
    img = np.stack([fern, grass, rock, np.ones_like(fern)], axis=2)
    texlib.write_texture("terrain", "cover.png", Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA"),
                         compressed=False, mips=False, fix_alpha=False)
    print("cover map: fern %.2f, grass %.2f, rock %.2f on average" % (fern.mean(), grass.mean(), rock.mean()))


class Parts:
    def __init__(self):
        self.pos, self.nrm, self.uv, self.col, self.idx = [], [], [], [], []

    def vert(self, p, n, uv, c):
        self.pos.append(p)
        self.nrm.append(n)
        self.uv.append(uv)
        self.col.append(c)
        return len(self.pos) - 1

    def tri(self, a, b, c):
        self.idx += [a, b, c]

    def write(self, name):
        write_hmesh("mesh", name, self.pos, self.nrm, self.uv, np.asarray(self.idx).reshape(-1, 3)[:, ::-1].reshape(-1), color=self.col)
        print("%s: %d triangles" % (name, len(self.idx) // 3))


def unit(v):
    v = np.asarray(v, dtype=np.float64)
    return v / max(np.linalg.norm(v), 1e-9)


def fern():
    m = Parts()
    fronds = 8
    for k in range(fronds):
        a = k / fronds * 2 * math.pi + rng.uniform(-0.3, 0.3)
        out = np.array([math.cos(a), 0.0, math.sin(a)])
        side = np.array([-out[2], 0.0, out[0]])
        length = rng.uniform(0.7, 1.05)
        rise = rng.uniform(0.3, 0.5)
        brown = rng.random() < 0.5
        base_col = np.array([0.36, 0.22, 0.1]) * rng.uniform(0.75, 1.05) if brown else np.array([0.14, 0.2, 0.08]) * rng.uniform(0.85, 1.15)
        segs = 12
        ribs = []
        for i in range(segs + 1):
            t = i / segs
            c = out * length * t + np.array([0.0, rise * math.sin(t * math.pi * 0.8) - 0.16 * t * t, 0.0])
            ribs.append(c)
        for i in range(segs):
            t = i / segs
            c0, c1 = ribs[i], ribs[i + 1]
            ahead = unit(c1 - c0)
            up = unit(np.cross(side, ahead))
            shade = base_col * (0.6 + 0.5 * t)
            col = [shade[0], shade[1], shade[2], 1.0]
            w = 0.012 * (1.0 - t) + 0.004
            r0 = m.vert((c0 + side * w).tolist(), up.tolist(), [t, 0.45], col)
            r1 = m.vert((c0 - side * w).tolist(), up.tolist(), [t, 0.55], col)
            r2 = m.vert((c1 + side * w * 0.8).tolist(), up.tolist(), [t, 0.45], col)
            r3 = m.vert((c1 - side * w * 0.8).tolist(), up.tolist(), [t, 0.55], col)
            m.tri(r0, r2, r3)
            m.tri(r0, r3, r1)
            if i == 0:
                continue
            leaf = 0.19 * math.sin(min(t + 0.08, 1.0) * math.pi) ** 0.8
            for sgn in (1.0, -1.0):
                tip = c0 + side * sgn * leaf + ahead * leaf * 0.45 - up * leaf * 0.35
                b0 = m.vert((c0 - ahead * 0.02).tolist(), up.tolist(), [t, 0.5], col)
                b1 = m.vert((c0 + ahead * 0.05).tolist(), up.tolist(), [t, 0.5], col)
                tt = m.vert(tip.tolist(), up.tolist(), [t, 0.0 if sgn > 0 else 1.0], [col[0] * 1.1, col[1] * 1.1, col[2] * 1.1, 1.0])
                m.tri(b0, tt, b1)
    m.write("cover_fern")


def grass():
    m = Parts()
    blades = 11
    for k in range(blades):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.0, 0.12)
        base = np.array([math.cos(a) * r, 0.0, math.sin(a) * r])
        lean_dir = unit([math.cos(a) + rng.uniform(-0.4, 0.4), 0.0, math.sin(a) + rng.uniform(-0.4, 0.4)])
        side = np.array([-lean_dir[2], 0.0, lean_dir[0]])
        tall = rng.uniform(0.28, 0.62)
        lean = rng.uniform(0.1, 0.32)
        dry = rng.random() < 0.6
        col0 = np.array([0.32, 0.28, 0.15]) if dry else np.array([0.18, 0.22, 0.1])
        segs = 3
        prev = None
        for i in range(segs + 1):
            t = i / segs
            c = base + lean_dir * lean * t * t + np.array([0.0, tall * t, 0.0])
            w = 0.022 * (1.0 - t) + 0.002
            n = unit(np.cross(side, [0.0, 1.0, 0.0]) + np.array([0.0, 0.4, 0.0]))
            shade = col0 * (0.55 + 0.6 * t)
            col = [shade[0], shade[1], shade[2], 1.0]
            l = m.vert((c + side * w).tolist(), n.tolist(), [0.0, t], col)
            rr = m.vert((c - side * w).tolist(), n.tolist(), [1.0, t], col)
            if prev is not None:
                m.tri(prev[0], l, rr)
                m.tri(prev[0], rr, prev[1])
            prev = (l, rr)
    m.write("cover_grass")


def rock():
    m = Parts()
    t = (1.0 + 5 ** 0.5) / 2.0
    verts = [unit(v) for v in [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
                                (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]]
    faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
             (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    cache = {}

    def mid(a, b):
        key = (min(a, b), max(a, b))
        if key not in cache:
            verts.append(unit(verts[a] + verts[b]))
            cache[key] = len(verts) - 1
        return cache[key]

    sub = []
    for a, b, c in faces:
        ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
        sub += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
    pts = []
    for v in verts:
        bump = 1.0 + 0.22 * math.sin(v[0] * 5.1 + 1.3) * math.cos(v[2] * 4.3) + 0.12 * math.sin(v[1] * 7.7)
        p = v * bump * np.array([0.55, 0.36, 0.45])
        p[1] = max(p[1], -0.12)
        pts.append(p)
    for a, b, c in sub:
        n = unit(np.cross(pts[b] - pts[a], pts[c] - pts[a]))
        if np.dot(n, pts[a] + pts[b] + pts[c]) < 0:
            n = -n
            b, c = c, b
        g = 0.36 + 0.1 * rng.random()
        moss = max(n[1], 0.0) * 0.5
        col = [g * (1.0 - moss * 0.3), g * (1.0 - moss * 0.05), g * (1.0 - moss * 0.45), 1.0]
        ia = m.vert(pts[a].tolist(), n.tolist(), [0, 0], col)
        ib = m.vert(pts[b].tolist(), n.tolist(), [1, 0], col)
        ic = m.vert(pts[c].tolist(), n.tolist(), [0, 1], col)
        m.tri(ia, ib, ic)
    m.write("cover_rock")


if __name__ == "__main__":
    cover_map()
    fern()
    grass()
    rock()
