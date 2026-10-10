import math

import numpy as np

from meshlib import write_hmesh

_rng = np.random.default_rng(7)
_LATTICE = _rng.random((48, 48, 48)).astype(np.float32)


def noise3(P, freq=1.0, octaves=3, seed=0):
    out = np.zeros(len(P), dtype=np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        q = P * (freq * (2 ** o)) + (seed * 17.3 + o * 7.1)
        i = np.floor(q).astype(np.int64)
        f = (q - i).astype(np.float32)
        f = f * f * (3.0 - 2.0 * f)
        n = _LATTICE.shape[0]
        x0, y0, z0 = i[:, 0] % n, i[:, 1] % n, i[:, 2] % n
        x1, y1, z1 = (x0 + 1) % n, (y0 + 1) % n, (z0 + 1) % n
        c00 = _LATTICE[x0, y0, z0] * (1 - f[:, 0]) + _LATTICE[x1, y0, z0] * f[:, 0]
        c10 = _LATTICE[x0, y1, z0] * (1 - f[:, 0]) + _LATTICE[x1, y1, z0] * f[:, 0]
        c01 = _LATTICE[x0, y0, z1] * (1 - f[:, 0]) + _LATTICE[x1, y0, z1] * f[:, 0]
        c11 = _LATTICE[x0, y1, z1] * (1 - f[:, 0]) + _LATTICE[x1, y1, z1] * f[:, 0]
        c0 = c00 * (1 - f[:, 1]) + c10 * f[:, 1]
        c1 = c01 * (1 - f[:, 1]) + c11 * f[:, 1]
        out += (c0 * (1 - f[:, 2]) + c1 * f[:, 2] - 0.5) * 2.0 * amp
        total += amp
        amp *= 0.5
    return out / total


def smin(a, b, k):
    if k <= 0.0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def d_capsule(P, a, b, ra, rb):
    a, b = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
    ab = b - a
    L2 = max(float(ab @ ab), 1e-12)
    t = np.clip(((P - a) @ ab) / L2, 0.0, 1.0)
    c = a + t[:, None] * ab
    return np.linalg.norm(P - c, axis=1) - (ra + (rb - ra) * t)


def d_ball(P, c, r, squash=(1.0, 1.0, 1.0), turn=None):
    q = P - np.asarray(c, dtype=np.float32)
    if turn is not None:
        q = q @ np.asarray(turn, dtype=np.float32)
    s = np.asarray(squash, dtype=np.float32) * r
    k = np.linalg.norm(q / s, axis=1)
    return (k - 1.0) * float(s.min())


def turn_matrix(yaw=0.0, pitch=0.0, roll=0.0):
    cy, sy, cp, sp, cr, sr = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch), math.cos(roll), math.sin(roll)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    return Ry @ Rx @ Rz


class Body:
    def __init__(self, name):
        self.name = name
        self.bones = []
        self.index = {}
        self.shapes = []
        self.cuts = []
        self.extras = []
        self.paints = []
        self.lumps = []
        self.base = (0.6, 0.6, 0.6)


    def bone(self, name, parent, head):
        self.bones.append({"name": name, "parent": self.index[parent] if parent else -1, "head": np.asarray(head, dtype=np.float32)})
        self.index[name] = len(self.bones) - 1
        return name


    def capsule(self, bone, a, b, ra, rb=None, k=0.05):
        rb = ra if rb is None else rb
        self.shapes.append((self.index[bone], lambda P, a=a, b=b, ra=ra, rb=rb: d_capsule(P, a, b, ra, rb), k))

    def chain(self, bone, points, radii, k=0.05):
        for i in range(len(points) - 1):
            self.capsule(bone, points[i], points[i + 1], radii[i], radii[i + 1], k)

    def ball(self, bone, c, r, squash=(1.0, 1.0, 1.0), k=0.05, turn=None):
        self.shapes.append((self.index[bone], lambda P, c=c, r=r, squash=squash, turn=turn: d_ball(P, c, r, squash, turn), k))

    def extra_capsule(self, bone, a, b, ra, rb=None, k=0.004):
        rb = ra if rb is None else rb
        self.extras.append((self.index[bone], lambda P, a=a, b=b, ra=ra, rb=rb: d_capsule(P, a, b, ra, rb), k))

    def extra_ball(self, bone, c, r, squash=(1.0, 1.0, 1.0), k=0.004):
        self.extras.append((self.index[bone], lambda P, c=c, r=r, squash=squash: d_ball(P, c, r, squash), k))

    def cut_ball(self, c, r, squash=(1.0, 1.0, 1.0), k=0.02, turn=None):
        self.cuts.append((lambda P, c=c, r=r, squash=squash, turn=turn: d_ball(P, c, r, squash, turn), k))

    def cut_capsule(self, a, b, ra, rb=None, k=0.02):
        rb = ra if rb is None else rb
        self.cuts.append((lambda P, a=a, b=b, ra=ra, rb=rb: d_capsule(P, a, b, ra, rb), k))

    def paint_ball(self, c, r, rgb, soft=0.3, squash=(1.0, 1.0, 1.0), shine=None):
        self.paints.append((lambda P, c=c, r=r, squash=squash: d_ball(P, c, r, squash), rgb, soft * r, shine))

    def paint_capsule(self, a, b, r, rgb, soft=0.3, shine=None):
        self.paints.append((lambda P, a=a, b=b, r=r: d_capsule(P, a, b, r, r), rgb, soft * r, shine))

    def lumpy(self, freq, size, seed=0):
        self.lumps.append((freq, size, seed))


    def distance(self, P, detail=True):
        d = np.full(len(P), 1e9, dtype=np.float32)
        for (_bone, fn, k) in self.shapes:
            d = smin(d, fn(P).astype(np.float32), k)
        for (fn, k) in self.cuts:
            d = smax(d, -fn(P).astype(np.float32), k)
        if detail:
            for (freq, size, seed) in self.lumps:
                d = d + noise3(P, freq, 3, seed) * size
        for (_bone, fn, k) in self.extras:
            d = smin(d, fn(P).astype(np.float32), k)
        return d

    def bone_distances(self, P):
        D = np.full((len(P), len(self.bones)), 1e9, dtype=np.float32)
        for (bone, fn, _k) in self.shapes + self.extras:
            D[:, bone] = np.minimum(D[:, bone], fn(P))
        return D

    def bounds(self, pad):
        lo, hi = np.full(3, 1e9), np.full(3, -1e9)
        heads = np.array([b["head"] for b in self.bones])
        span = float((heads.max(axis=0) - heads.min(axis=0)).max())
        lo, hi = heads.min(axis=0) - 6.0 * pad - span * 0.4, heads.max(axis=0) + 6.0 * pad + span * 0.4
        step = max((hi - lo).max() / 90.0, pad * 0.5)
        ax = [np.arange(lo[i], hi[i] + step, step, dtype=np.float32) for i in range(3)]
        G = np.stack(np.meshgrid(*ax, indexing="ij"), axis=-1).reshape(-1, 3)
        d = self.distance(G, detail=False)
        near = G[d < step * 1.5]
        return near.min(axis=0) - pad, near.max(axis=0) + pad

    def build(self, voxel, triangles, folder="creatures", soft=None, wide=None, scale_ao=None):
        from skimage import measure
        import pyfqmr
        lo, hi = wide if wide else self.bounds(voxel * 3.0)
        n = np.ceil((hi - lo) / voxel).astype(int) + 1
        ax = [lo[i] + np.arange(n[i], dtype=np.float32) * voxel for i in range(3)]
        c = 4
        nc = np.ceil(n / c).astype(int) + 1
        cax = [lo[i] + (np.arange(nc[i], dtype=np.float32) * c) * voxel for i in range(3)]
        CG = np.stack(np.meshgrid(*cax, indexing="ij"), axis=-1).reshape(-1, 3)
        cd = np.empty(len(CG), dtype=np.float32)
        for i0 in range(0, len(CG), 1_000_000):
            cd[i0:i0 + 1_000_000] = self.distance(CG[i0:i0 + 1_000_000], detail=False)
        cd = cd.reshape(tuple(nc))
        near = np.abs(cd) < voxel * c * 1.9
        grow = near.copy()
        for axis in range(3):
            grow |= np.roll(near, 1, axis=axis) | np.roll(near, -1, axis=axis)
        fine_mask = np.repeat(np.repeat(np.repeat(grow, c, axis=0), c, axis=1), c, axis=2)[:n[0], :n[1], :n[2]]
        far = np.repeat(np.repeat(np.repeat(cd, c, axis=0), c, axis=1), c, axis=2)[:n[0], :n[1], :n[2]]
        vol = np.where(far > 0, 1.0, -1.0).astype(np.float32) * (voxel * 4.0)
        idx = np.argwhere(fine_mask)
        for i0 in range(0, len(idx), 1_200_000):
            part = idx[i0:i0 + 1_200_000]
            P = np.stack([ax[0][part[:, 0]], ax[1][part[:, 1]], ax[2][part[:, 2]]], axis=1)
            vol[part[:, 0], part[:, 1], part[:, 2]] = self.distance(P)
        verts, faces, _n, _v = measure.marching_cubes(vol, level=0.0, spacing=(voxel, voxel, voxel))
        verts = verts + lo
        full = len(faces)
        if len(faces) > triangles:
            s = pyfqmr.Simplify()
            s.setMesh(verts.astype(np.float64), faces.astype(np.int32))
            s.simplify_mesh(target_count=int(triangles), aggressiveness=5, preserve_border=True, verbose=False)
            verts, faces, _ = s.getMesh()
        verts = verts.astype(np.float32)
        faces = faces.astype(np.int64)
        e = voxel * 0.7
        for _ in range(2):
            g = self._gradient(verts, e)
            verts = verts - g * self.distance(verts)[:, None]
        normals = self._gradient(verts, e)
        fn = np.cross(verts[faces[:, 1]] - verts[faces[:, 0]], verts[faces[:, 2]] - verts[faces[:, 0]])
        if float(np.sum(fn * normals[faces[:, 0]])) > 0.0:
            faces = faces[:, ::-1]
        unit = scale_ao if scale_ao else float((hi - lo).max()) / 60.0
        ao = np.zeros(len(verts), dtype=np.float32)
        for r in (0.6, 1.4, 3.0):
            ao += np.clip(self.distance(verts + normals * (unit * r), detail=False) / (unit * r), 0.0, 1.0)
        ao = (ao / 3.0) ** 0.8
        rgb = np.tile(np.asarray(self.base, dtype=np.float32), (len(verts), 1))
        shine = np.zeros(len(verts), dtype=np.float32)
        for (fn_, color, softness, sh) in self.paints:
            m = np.clip(0.5 - fn_(verts) / max(softness, 1e-6), 0.0, 1.0)[:, None]
            rgb = rgb * (1 - m) + np.asarray(color, dtype=np.float32) * m
            if sh is not None:
                shine = shine * (1 - m[:, 0]) + sh * m[:, 0]
        D = self.bone_distances(verts)
        soft = soft if soft else unit * 1.2
        W = np.exp(-(D - D.min(axis=1, keepdims=True)) / soft)
        order = np.argsort(-W, axis=1)[:, :4]
        Wt = np.take_along_axis(W, order, axis=1)
        Wt[Wt < 0.02] = 0.0
        Wt /= Wt.sum(axis=1, keepdims=True)
        skeleton = []
        for b in self.bones:
            rel = b["head"] - (self.bones[b["parent"]]["head"] if b["parent"] >= 0 else 0.0)
            skeleton.append({"name": b["name"], "parent": b["parent"], "rest": [1, 0, 0, 0, 1, 0, 0, 0, 1, float(rel[0]), float(rel[1]), float(rel[2])]})
        color = np.concatenate([np.clip(rgb, 0, 1), ao[:, None]], axis=1)
        write_hmesh(folder, self.name, verts, normals, verts[:, :2], faces.reshape(-1).astype(np.uint32), color=color,
                    uv2=np.stack([verts[:, 2], shine], axis=1), bones=order.astype(np.uint16), weights=Wt.astype(np.float32), skeleton=skeleton)
        info = {"name": self.name, "triangles": int(len(faces)), "from": int(full), "vertices": int(len(verts)), "bones": len(self.bones),
                "box": [[round(float(v), 3) for v in verts.min(axis=0)], [round(float(v), 3) for v in verts.max(axis=0)]]}
        print("%-14s %6d triangles (from %d), %d vertices, %d bones, grid %s" % (self.name, info["triangles"], full, info["vertices"], info["bones"], "x".join(str(v) for v in n)))
        return info

    def _gradient(self, P, e):
        g = np.zeros_like(P)
        for i in range(3):
            o = np.zeros(3, dtype=np.float32)
            o[i] = e
            g[:, i] = self.distance(P + o) - self.distance(P - o)
        return g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9)
