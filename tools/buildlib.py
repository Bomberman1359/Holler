import json
import math
import os

import numpy as np

import maplib
from make_textures import STRUCTURE_SCALE
from meshlib import write_hmesh

LAYERS = open(os.path.join(maplib.GEN, "tex", "structure_layers.txt")).read().split()
UP = np.array([0.0, 1.0, 0.0])
_heights = None


def v3(x, y, z):
    return np.array([x, y, z], dtype=np.float64)


def unit(v):
    v = np.asarray(v, dtype=np.float64)
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def terrain_height(x, z):
    global _heights
    if _heights is None:
        n = maplib.N + 1
        _heights = np.fromfile(os.path.join(maplib.GEN, "terrain", "height.bin"), dtype=np.float32).reshape(n, n)
    fx = np.clip((x + maplib.HALF) / maplib.CELL, 0, maplib.N - 0.001)
    fz = np.clip((z + maplib.HALF) / maplib.CELL, 0, maplib.N - 0.001)
    i, j = int(fx), int(fz)
    tx, tz = fx - i, fz - j
    h = _heights
    a = h[j, i] * (1 - tx) + h[j, i + 1] * tx
    b = h[j + 1, i] * (1 - tx) + h[j + 1, i + 1] * tx
    return float(a * (1 - tz) + b * tz)


class Mat:

    def __init__(self, layer, tint=(0.5, 0.5, 0.5), sky=1.0, glow=0.0, scale=None, turn=False):
        self.layer = LAYERS.index(layer)
        self.name = layer
        self.tint = tuple(tint)
        self.sky = sky
        self.glow = glow
        self.scale = scale or STRUCTURE_SCALE[layer]
        self.turn = turn

    def but(self, **kw):
        m = Mat(self.name, self.tint, self.sky, self.glow, self.scale, self.turn)
        for k, v in kw.items():
            setattr(m, k, v)
        return m

    def indoors(self, sky=0.06):
        return self.but(sky=sky)


def mat(m):
    return m if isinstance(m, Mat) else Mat(m)


def ruin_top(width, height, seed, low=0.35, step=0.5, course=0.15, rough=1.0):
    rng = np.random.default_rng(seed)
    out = []
    u = 0.0
    h = height * rng.uniform(low + 0.2 * (1 - low), 1.0)
    while u < width:
        out.append((u, max(round(h / course) * course, course)))
        u += rng.uniform(step * 0.6, step * 1.5)
        h += rng.normal(0.0, height * 0.11 * rough)
        h = float(np.clip(h, height * low, height))
        if rng.random() < 0.08:
            h = height * rng.uniform(low, 1.0)
    return out


class Kit:
    def __init__(self, name, origin, yaw=0.0, base=None):
        self.name = name
        self.ox, self.oz = float(origin[0]), float(origin[1])
        self.oy = terrain_height(self.ox, self.oz) if base is None else float(base)
        self.yaw = float(yaw)
        self.pos, self.nrm, self.uv, self.tan, self.col, self.uv2, self.idx = [], [], [], [], [], [], []
        self.solid = []
        self.c_pos, self.c_idx = [], []
        self.d_pos, self.d_nrm, self.d_uv, self.d_col, self.d_uv2, self.d_idx = [], [], [], [], [], []
        self.marks = {}
        self.glows = []
        self.see_from = 340.0
        self._decal_regions = None
        self._R = np.eye(3)
        self._t = np.zeros(3)
        self._stack = []


    def at(self, x=0.0, y=0.0, z=0.0, yaw=0.0, pitch=0.0, roll=0.0):
        return _At(self, v3(x, y, z), basis(yaw, pitch, roll))

    def _p(self, p):
        return self._R @ np.asarray(p, dtype=np.float64) + self._t

    def _d(self, d):
        return self._R @ np.asarray(d, dtype=np.float64)

    def world(self, p):
        p = self._p(p)
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        return v3(self.ox + p[0] * c + p[2] * s, self.oy + p[1], self.oz - p[0] * s + p[2] * c)

    def local(self, wx, wz):
        dx, dz = wx - self.ox, wz - self.oz
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        return (dx * c - dz * s, dx * s + dz * c)

    def ground(self, x, z):
        w = self.world((x, 0.0, z))
        return terrain_height(w[0], w[2]) - self.oy - self._t[1]

    def mark(self, name, p, yaw=0.0, **extra):
        w = self.world(p)
        turned = math.atan2(self._R[0, 2], self._R[2, 2])
        self.marks[name] = dict(pos=[round(float(v), 3) for v in w], yaw=round(self.yaw + turned + yaw, 4), **extra)

    def glow(self, p, reach, color, energy=1.0, name=""):
        w = self.world(p)
        self.glows.append(dict(pos=[round(float(v), 3) for v in w], reach=reach, color=list(color), energy=energy, name=name))


    def face(self, pts, m, T=None, U=None, solid=True, sky=None, tint=None, glow=None, normals=None, uvs=None):
        m = mat(m)
        pts = [self._p(p) for p in pts]
        if T is not None:
            T = self._d(T)
        if U is not None:
            U = self._d(U)
        if normals is not None:
            normals = [self._d(q) for q in normals]
        n = unit(np.cross(pts[1] - pts[0], pts[2] - pts[0]))
        if np.linalg.norm(n) < 1e-9:
            return
        if U is None:
            if abs(n[1]) > 0.72:
                U = v3(1.0, 0.0, 0.0) if m.turn else v3(0.0, 0.0, -1.0)
            else:
                U = unit(UP - n * n[1])
                if m.turn:
                    U = unit(np.cross(n, U))
        if T is None:
            T = unit(np.cross(U, n))
        w = 1.0 if np.dot(U, np.cross(n, T)) >= 0.0 else -1.0
        base = len(self.pos)
        col = tuple(tint or m.tint) + (m.sky if sky is None else sky,)
        g = m.glow if glow is None else glow
        for k, p in enumerate(pts):
            self.pos.append(p)
            self.nrm.append(normals[k] if normals is not None else n)
            self.uv.append(uvs[k] if uvs is not None else (np.dot(p, T) / m.scale, -np.dot(p, U) / m.scale))
            self.tan.append((T[0], T[1], T[2], w))
            self.col.append(col)
            self.uv2.append((float(m.layer), g))
        for k in range(1, len(pts) - 1):
            self.idx.extend((base, base + k + 1, base + k))
            self.solid.append(solid)

    def quad(self, a, b, c, d, m, **kw):
        self.face([a, b, c, d], m, **kw)

    def box(self, lo, hi, m, skip="", **kw):
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        sk = skip.split()
        if "x+" not in sk:
            self.face([v3(x1, y0, z1), v3(x1, y0, z0), v3(x1, y1, z0), v3(x1, y1, z1)], m, **kw)
        if "x-" not in sk:
            self.face([v3(x0, y0, z0), v3(x0, y0, z1), v3(x0, y1, z1), v3(x0, y1, z0)], m, **kw)
        if "z+" not in sk:
            self.face([v3(x0, y0, z1), v3(x1, y0, z1), v3(x1, y1, z1), v3(x0, y1, z1)], m, **kw)
        if "z-" not in sk:
            self.face([v3(x1, y0, z0), v3(x0, y0, z0), v3(x0, y1, z0), v3(x1, y1, z0)], m, **kw)
        if "y+" not in sk:
            self.face([v3(x0, y1, z1), v3(x1, y1, z1), v3(x1, y1, z0), v3(x0, y1, z0)], m, **kw)
        if "y-" not in sk:
            self.face([v3(x0, y0, z0), v3(x1, y0, z0), v3(x1, y0, z1), v3(x0, y0, z1)], m, **kw)

    def block(self, center, size, m, yaw=0.0, pitch=0.0, roll=0.0, skip="", **kw):
        B = basis(yaw, pitch, roll)
        c = np.asarray(center, dtype=np.float64)
        h = np.asarray(size, dtype=np.float64) * 0.5
        sk = skip.split()

        def P(sx, sy, sz):
            return c + B[:, 0] * (sx * h[0]) + B[:, 1] * (sy * h[1]) + B[:, 2] * (sz * h[2])
        if "x+" not in sk:
            self.face([P(1, -1, 1), P(1, -1, -1), P(1, 1, -1), P(1, 1, 1)], m, **kw)
        if "x-" not in sk:
            self.face([P(-1, -1, -1), P(-1, -1, 1), P(-1, 1, 1), P(-1, 1, -1)], m, **kw)
        if "z+" not in sk:
            self.face([P(-1, -1, 1), P(1, -1, 1), P(1, 1, 1), P(-1, 1, 1)], m, **kw)
        if "z-" not in sk:
            self.face([P(1, -1, -1), P(-1, -1, -1), P(-1, 1, -1), P(1, 1, -1)], m, **kw)
        if "y+" not in sk:
            self.face([P(-1, 1, 1), P(1, 1, 1), P(1, 1, -1), P(-1, 1, -1)], m, **kw)
        if "y-" not in sk:
            self.face([P(-1, -1, -1), P(1, -1, -1), P(1, -1, 1), P(-1, -1, 1)], m, **kw)

    def beam(self, a, b, width, m, depth=None, **kw):
        a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
        d = b - a
        L = np.linalg.norm(d)
        if L < 1e-6:
            return
        z = d / L
        x = unit(np.cross(UP, z)) if abs(z[1]) < 0.99 else v3(1.0, 0.0, 0.0)
        y = np.cross(z, x)
        hw, hd = width * 0.5, (depth or width) * 0.5
        c = [a + x * sx * hw + y * sy * hd for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        e = [p + d for p in c]
        for k in range(4):
            k2 = (k + 1) % 4
            self.face([c[k], c[k2], e[k2], e[k]], m, U=z, **kw)
        self.face([c[3], c[2], c[1], c[0]], m, **kw)
        self.face([e[0], e[1], e[2], e[3]], m, **kw)

    def unseen(self, pts):
        pts = [self._p(p) for p in pts]
        base = len(self.c_pos)
        self.c_pos.extend(pts)
        for i in range(1, len(pts) - 1):
            self.c_idx.extend((base, base + i + 1, base + i))

    def unseen_block(self, center, size, yaw=0.0):
        B = basis(yaw)
        c = np.asarray(center, dtype=np.float64)
        h = np.asarray(size, dtype=np.float64) * 0.5

        def P(sx, sy, sz):
            return c + B[:, 0] * (sx * h[0]) + B[:, 1] * (sy * h[1]) + B[:, 2] * (sz * h[2])
        for quad in (((1, -1, 1), (1, -1, -1), (1, 1, -1), (1, 1, 1)), ((-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)),
                     ((-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)), ((1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1)),
                     ((-1, 1, 1), (1, 1, 1), (1, 1, -1), (-1, 1, -1))):
            self.unseen([P(*q) for q in quad])

    def stairs(self, foot, direction, rise, run, width, m, steps=None, sides=True, under=True, **kw):
        foot = np.asarray(foot, dtype=np.float64)
        d = unit(v3(direction[0], 0.0, direction[1]))
        side = np.cross(UP, d)
        n = steps or max(int(round(rise / 0.17)), 2)
        h, t = rise / n, run / n
        hw = width / 2
        for i in range(n):
            a = foot + d * (t * i) + UP * (h * i)
            self.face([a - side * hw, a + side * hw, a + side * hw + UP * h, a - side * hw + UP * h][::-1], m, solid=False, **kw)
            b = a + UP * h
            self.face([b - side * hw, b + side * hw, b + side * hw + d * t, b - side * hw + d * t][::-1], m, solid=False, **kw)
        top = foot + d * run + UP * rise
        if sides:
            for sgn in (-1, 1):
                pts = [foot + side * hw * sgn]
                for i in range(n):
                    pts.append(foot + d * (t * i) + UP * (h * (i + 1)) + side * hw * sgn)
                    pts.append(foot + d * (t * (i + 1)) + UP * (h * (i + 1)) + side * hw * sgn)
                low = foot + d * run + side * hw * sgn
                for i in range(n):
                    a0 = foot + d * (t * i) + side * hw * sgn
                    quad = [a0, a0 + d * t, a0 + d * t + UP * (h * (i + 1)), a0 + UP * (h * (i + 1))]
                    self.face(quad if sgn > 0 else quad[::-1], m, solid=False, **kw)
        if under:
            self.face([foot - side * hw, foot + side * hw, top + side * hw, top - side * hw], m, solid=False, **kw)
        lead = d * 0.25
        self.unseen([foot - side * hw - lead, foot + side * hw - lead, top + side * hw, top - side * hw][::-1])
        self.unseen([foot - side * hw - lead, foot + side * hw - lead, top + side * hw, top - side * hw])
        return top


    def panel(self, origin, T, U, width, height, thick, front, back=None, holes=(), top=None, edge=None,
              anchor="front", ends=True, solid=True, bottom=False):
        front = mat(front)
        back = mat(back) if back is not None else front
        edge = mat(edge) if edge is not None else front
        origin = np.asarray(origin, dtype=np.float64)
        T, U = unit(T), unit(U)
        N = np.cross(T, U)
        if anchor == "back":
            origin = origin + N * thick
        elif anchor == "center":
            origin = origin + N * (thick * 0.5)
        steps = None
        if top is not None and not callable(top):
            steps = sorted(top)

        def top_at(u, side):
            if top is None:
                return height
            if callable(top):
                return float(top(u))
            h = steps[0][1]
            for (su, sh) in steps:
                if su < u - 1e-9 or (side > 0 and su <= u + 1e-9):
                    h = sh
                else:
                    break
            return h

        cuts = {0.0, float(width)}
        for (u0, u1, v0, v1) in holes:
            cuts.add(float(np.clip(u0, 0, width)))
            cuts.add(float(np.clip(u1, 0, width)))
        if steps:
            for (su, _sh) in steps:
                if 0.0 < su < width:
                    cuts.add(float(su))
        if callable(top):
            n = max(int(width / 0.5), 2)
            for k in range(1, n):
                cuts.add(width * k / n)
            cuts.add(width * 0.5)
        cuts = sorted(cuts)

        def spans(ua, ub):
            ha, hb = top_at(ua, 1), top_at(ub, -1)
            mid = (ua + ub) * 0.5
            cut_out = sorted((max(v0, 0.0), v1) for (u0, u1, v0, v1) in holes if u0 - 1e-9 <= mid <= u1 + 1e-9)
            out = []
            lo = 0.0
            lim = min(ha, hb)
            for (v0, v1) in cut_out:
                if v0 >= lim:
                    break
                if v0 > lo + 1e-9:
                    out.append((lo, v0, v0, False))
                lo = max(lo, v1)
            if lo < lim - 1e-9:
                out.append((lo, ha, hb, True))
            return out

        def P(u, v, back_side=False):
            return origin + T * u + U * v - (N * thick if back_side else 0.0)

        cols = []
        for k in range(len(cuts) - 1):
            ua, ub = cuts[k], cuts[k + 1]
            if ub - ua < 1e-6:
                continue
            sp = spans(ua, ub)
            cols.append((ua, ub, sp))
            for (lo, ha, hb, is_top) in sp:
                self.face([P(ua, lo), P(ub, lo), P(ub, hb), P(ua, ha)], front, T=T, U=U, solid=solid)
                self.face([P(ub, lo, True), P(ua, lo, True), P(ua, ha, True), P(ub, hb, True)], back, T=-T, U=U, solid=solid)
                self.face([P(ua, ha), P(ub, hb), P(ub, hb, True), P(ua, ha, True)], edge, solid=solid,
                          sky=max(front.sky, back.sky) if is_top else (front.sky + back.sky) * 0.5)
                if lo > 1e-9 or bottom:
                    self.face([P(ua, lo, True), P(ub, lo, True), P(ub, lo), P(ua, lo)], edge, solid=solid, sky=(front.sky + back.sky) * 0.5)

        def solid_at(sp, at_right):
            return [(lo, hb if at_right else ha) for (lo, ha, hb, _t) in sp]

        def minus(a, b):
            out = []
            for (lo, hi) in a:
                cur = lo
                for (blo, bhi) in sorted(b):
                    if bhi <= cur or blo >= hi:
                        continue
                    if blo > cur:
                        out.append((cur, min(blo, hi)))
                    cur = max(cur, bhi)
                if cur < hi - 1e-9:
                    out.append((cur, hi))
            return [(lo, hi) for (lo, hi) in out if hi - lo > 1e-6]

        sky_mid = (front.sky + back.sky) * 0.5
        for k in range(len(cols) + 1):
            left = solid_at(cols[k - 1][2], True) if k > 0 else []
            right = solid_at(cols[k][2], False) if k < len(cols) else []
            u = cols[k][0] if k < len(cols) else cols[-1][1]
            if (k == 0 or k == len(cols)) and not ends:
                continue
            for (lo, hi) in minus(left, right):
                self.face([P(u, lo), P(u, lo, True), P(u, hi, True), P(u, hi)], edge, U=U, solid=solid, sky=sky_mid)
            for (lo, hi) in minus(right, left):
                self.face([P(u, lo, True), P(u, lo), P(u, hi), P(u, hi, True)], edge, U=U, solid=solid, sky=sky_mid)

    def wall(self, a, b, height, thick, outside, inside=None, holes=(), top=None, edge=None, base=0.0, **kw):
        a3 = v3(a[0], base, a[1])
        T = unit(v3(b[0] - a[0], 0.0, b[1] - a[1]))
        width = math.hypot(b[0] - a[0], b[1] - a[1])
        self.panel(a3, T, UP, width, height, thick, outside, inside, holes, top, edge, anchor="front", **kw)

    def floor(self, lo, hi, y, thick, top, under=None, holes=(), **kw):
        x0, z0 = lo
        x1, z1 = hi
        hs = [(hx0 - x0, hx1 - x0, z1 - hz1, z1 - hz0) for (hx0, hx1, hz0, hz1) in holes]
        self.panel(v3(x0, y, z1), v3(1, 0, 0), v3(0, 0, -1), x1 - x0, z1 - z0, thick, top, under or top, hs, bottom=True, **kw)


    def tube(self, points, radii, sides, m, cap_start=True, cap_end=True, solid=True, around=1.0, squash=None, **kw):
        m = mat(m)
        pts = [self._p(p) for p in points]
        rings = []
        prev_x = None
        along = 0.0
        for i, p in enumerate(pts):
            d = unit((pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]))
            x = unit(np.cross(UP, d)) if abs(d[1]) < 0.99 else (prev_x if prev_x is not None else v3(1.0, 0.0, 0.0))
            if prev_x is not None and np.dot(x, prev_x) < 0:
                x = -x
            prev_x = x
            y = np.cross(d, x)
            if i > 0:
                along += np.linalg.norm(p - pts[i - 1])
            ring = []
            for s in range(sides + 1):
                a = s / sides * 2 * math.pi
                ca, sa = math.cos(a), math.sin(a)
                sq = squash or (1.0, 1.0)
                off = x * (ca * radii[i] * sq[0]) + y * (sa * radii[i] * sq[1])
                nr = unit(x * (ca / sq[0]) + y * (sa / sq[1]))
                ring.append((p + off, nr, (s / sides * around * max(round(2 * math.pi * radii[0] / m.scale), 1), along / m.scale), d))
            rings.append(ring)
        col = tuple(kw.get("tint") or m.tint) + (kw.get("sky", m.sky),)
        base = len(self.pos)
        for ring in rings:
            for (p, nr, uv, d) in ring:
                t = unit(np.cross(d, nr))
                self.pos.append(p)
                self.nrm.append(nr)
                self.uv.append(uv)
                self.tan.append((t[0], t[1], t[2], 1.0))
                self.col.append(col)
                self.uv2.append((float(m.layer), kw.get("glow", m.glow)))
        n = sides + 1
        for i in range(len(rings) - 1):
            for s in range(sides):
                a, b, c, d = base + i * n + s, base + i * n + s + 1, base + (i + 1) * n + s + 1, base + (i + 1) * n + s
                self.idx.extend((a, c, b, a, d, c))
                self.solid.extend((solid, solid))
        keep = (self._R, self._t)
        self._R, self._t = np.eye(3), np.zeros(3)
        if cap_start and radii[0] > 1e-4:
            self.face([r[0] for r in rings[0][:-1]][::-1], m, solid=solid, **{k: v for k, v in kw.items() if k in ("tint", "sky", "glow")})
        if cap_end and radii[-1] > 1e-4:
            self.face([r[0] for r in rings[-1][:-1]], m, solid=solid, **{k: v for k, v in kw.items() if k in ("tint", "sky", "glow")})
        self._R, self._t = keep

    def loft(self, rings, m, solid=True, close=True, flip=None, v_scale=1.0, inward=False, **kw):
        m = mat(m)
        R = np.asarray(rings, dtype=np.float64)
        R = R @ self._R.T + self._t
        nr, npnt = R.shape[0], R.shape[1]
        middle = R.reshape(-1, 3).mean(axis=0)
        if close:
            R = np.concatenate([R, R[:, :1]], axis=1)
            npnt += 1
        du = np.gradient(R, axis=1)
        dv = np.gradient(R, axis=0)
        if close:
            du[:, 0] = du[:, -1] = (R[:, 1] - R[:, -2]) * 0.5
        N = np.cross(dv, du)
        if flip is None:
            ring_mid = R.mean(axis=1, keepdims=True)
            outward = float(np.sum(N * (R - ring_mid)))
            if abs(outward) < 1e-9:
                outward = float(np.sum(N * (R - middle)))
            flip = (outward < 0.0) != inward
        if flip:
            N = -N
        N /= np.maximum(np.linalg.norm(N, axis=2, keepdims=True), 1e-9)
        seg = np.linalg.norm(np.diff(R, axis=1), axis=2)
        ucoord = np.concatenate([np.zeros((nr, 1)), np.cumsum(seg, axis=1)], axis=1) / m.scale
        vseg = np.linalg.norm(np.diff(R[:, 0], axis=0), axis=1)
        vcoord = np.concatenate([[0.0], np.cumsum(vseg)]) / m.scale * v_scale
        col = tuple(kw.get("tint") or m.tint) + (kw.get("sky", m.sky),)
        base = len(self.pos)
        for i in range(nr):
            for j in range(npnt):
                t = unit(du[i, j])
                self.pos.append(R[i, j])
                self.nrm.append(N[i, j])
                self.uv.append((ucoord[i, j], vcoord[i]))
                self.tan.append((t[0], t[1], t[2], 1.0))
                self.col.append(col)
                self.uv2.append((float(m.layer), kw.get("glow", m.glow)))
        for i in range(nr - 1):
            for j in range(npnt - 1):
                a, b, c, d = base + i * npnt + j, base + i * npnt + j + 1, base + (i + 1) * npnt + j + 1, base + (i + 1) * npnt + j
                if flip:
                    self.idx.extend((a, c, b, a, d, c))
                else:
                    self.idx.extend((a, b, c, a, c, d))
                self.solid.extend((solid, solid))


    def decal(self, name, center, normal, width, height=None, up=None, turn=0.0, tint=(1.0, 1.0, 1.0), alpha=1.0, lift=0.012, sky=1.0, glow=0.0):
        if self._decal_regions is None:
            self._decal_regions = json.load(open(os.path.join(maplib.GEN, "tex", "decals.json")))
        x0, y0, x1, y1 = self._decal_regions[name]
        center = self._p(center)
        normal = self._d(normal)
        if up is not None:
            up = self._d(up)
        n = unit(normal)
        if height is None:
            height = width * ((y1 - y0) * 2.0) / (x1 - x0)
        if up is None:
            up = UP if abs(n[1]) < 0.9 else v3(0.0, 0.0, -1.0)
        U = unit(np.asarray(up, dtype=np.float64) - n * np.dot(up, n))
        T = np.cross(U, n)
        if turn:
            c, s = math.cos(turn), math.sin(turn)
            T, U = T * c + U * s, U * c - T * s
        c0 = np.asarray(center, dtype=np.float64) + n * lift
        pts = [c0 - T * width / 2 - U * height / 2, c0 + T * width / 2 - U * height / 2,
               c0 + T * width / 2 + U * height / 2, c0 - T * width / 2 + U * height / 2]
        uvs = [(x0, y1), (x1, y1), (x1, y0), (x0, y0)]
        base = len(self.d_pos)
        for p, uv in zip(pts, uvs):
            self.d_pos.append(p)
            self.d_nrm.append(n)
            self.d_uv.append(uv)
            self.d_col.append(tuple(tint) + (alpha,))
            self.d_uv2.append((sky, glow))
        self.d_idx.extend((base, base + 2, base + 1, base, base + 3, base + 2))


    def write(self):
        out = maplib.out_dir("sites")
        pos = np.asarray(self.pos, dtype=np.float32).reshape(-1, 3)
        idx = np.asarray(self.idx, dtype=np.uint32)
        col = np.asarray(self.col, dtype=np.float32).reshape(-1, 4)
        write_hmesh("sites", self.name, pos, np.asarray(self.nrm, dtype=np.float32), np.asarray(self.uv, dtype=np.float32), idx,
                    tangent=np.asarray(self.tan, dtype=np.float32), color=col, uv2=np.asarray(self.uv2, dtype=np.float32))
        tri = idx.reshape(-1, 3)
        keep = tri[np.asarray(self.solid, dtype=bool)]
        used, inv = np.unique(keep.reshape(-1), return_inverse=True)
        cpos = pos[used]
        cidx = inv.astype(np.uint32)
        if self.c_idx:
            extra = np.asarray(self.c_pos, dtype=np.float32).reshape(-1, 3)
            cidx = np.concatenate([cidx, np.asarray(self.c_idx, dtype=np.uint32) + len(cpos)])
            cpos = np.concatenate([cpos, extra])
        write_hmesh("sites", self.name + "_col", cpos, np.zeros_like(cpos), np.zeros((len(cpos), 2), dtype=np.float32), cidx)
        has_decals = len(self.d_idx) > 0
        if has_decals:
            write_hmesh("sites", self.name + "_decals", np.asarray(self.d_pos, dtype=np.float32), np.asarray(self.d_nrm, dtype=np.float32),
                        np.asarray(self.d_uv, dtype=np.float32), np.asarray(self.d_idx, dtype=np.uint32),
                        color=np.asarray(self.d_col, dtype=np.float32), uv2=np.asarray(self.d_uv2, dtype=np.float32))
        lo, hi = pos.min(axis=0), pos.max(axis=0)
        info = {
            "name": self.name,
            "origin": [round(self.ox, 3), round(self.oy, 3), round(self.oz, 3)],
            "yaw": round(self.yaw, 5),
            "box": [[round(float(v), 2) for v in lo], [round(float(v), 2) for v in hi]],
            "decals": has_decals,
            "see_from": self.see_from,
            "marks": self.marks,
            "glows": self.glows,
            "triangles": int(len(idx) // 3),
        }
        with open(os.path.join(out, self.name + ".json"), "w") as f:
            json.dump(info, f, indent=1)
        np.save(os.path.join(out, self.name + "_foot.npy"), self._footprint(pos, tri))
        return info

    def _footprint(self, pos, tri):
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        wx = self.ox + pos[:, 0] * c + pos[:, 2] * s + maplib.HALF
        wz = self.oz - pos[:, 0] * s + pos[:, 2] * c + maplib.HALF
        P = np.stack([wx, wz], axis=1).astype(np.float64)
        a, b, d = P[tri[:, 0]], P[tri[:, 1]], P[tri[:, 2]]
        longest = np.sqrt(np.maximum(np.maximum(((b - a) ** 2).sum(1), ((d - b) ** 2).sum(1)), ((a - d) ** 2).sum(1)))
        steps = np.clip(np.ceil(longest / 0.6).astype(int), 1, 400)
        cells = []
        for n in np.unique(steps):
            pick = steps == n
            i, j = np.meshgrid(np.arange(n + 1), np.arange(n + 1))
            ok = i + j <= n
            u, v = i[ok] / n, j[ok] / n
            pts = a[pick][:, None, :] * (1 - u - v)[None, :, None] + b[pick][:, None, :] * u[None, :, None] + d[pick][:, None, :] * v[None, :, None]
            cells.append(np.unique(np.floor(pts.reshape(-1, 2)).astype(np.int32), axis=0))
        if not cells:
            return np.zeros((0, 2), dtype=np.int32)
        return np.unique(np.concatenate(cells), axis=0)


class _At:
    def __init__(self, kit, t, R):
        self.kit, self.t, self.R = kit, t, R

    def __enter__(self):
        k = self.kit
        k._stack.append((k._R, k._t))
        k._t = k._R @ self.t + k._t
        k._R = k._R @ self.R
        return k

    def __exit__(self, *a):
        k = self.kit
        k._R, k._t = k._stack.pop()


def basis(yaw=0.0, pitch=0.0, roll=0.0):
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cr, sr = math.cos(roll), math.sin(roll)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    return Ry @ Rx @ Rz
