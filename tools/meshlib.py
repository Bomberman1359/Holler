import os
import struct

import numpy as np

from maplib import out_dir

F_TANGENT, F_COLOR, F_UV2, F_BONES = 1, 2, 4, 8


def write_hmesh(folder, name, pos, nrm, uv, idx, tangent=None, color=None, uv2=None, bones=None, weights=None, skeleton=None):
    pos = np.asarray(pos, dtype="<f4").reshape(-1, 3)
    nrm = np.asarray(nrm, dtype="<f4").reshape(-1, 3)
    uv = np.asarray(uv, dtype="<f4").reshape(-1, 2)
    idx = np.asarray(idx, dtype="<u4").reshape(-1)
    flags = 0
    parts = [pos.tobytes(), nrm.tobytes(), uv.tobytes()]
    if tangent is not None:
        flags |= F_TANGENT
        parts.append(np.asarray(tangent, dtype="<f4").reshape(-1, 4).tobytes())
    if color is not None:
        flags |= F_COLOR
        c = np.asarray(color, dtype=np.float32).reshape(-1, 4)
        parts.append((np.clip(c, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
    if uv2 is not None:
        flags |= F_UV2
        parts.append(np.asarray(uv2, dtype="<f4").reshape(-1, 2).tobytes())
    if bones is not None:
        flags |= F_BONES
        parts.append(np.asarray(bones, dtype="<u2").reshape(-1, 4).tobytes())
        parts.append(np.asarray(weights, dtype="<f4").reshape(-1, 4).tobytes())
    parts.append(idx.tobytes())
    skeleton = skeleton or []
    path = os.path.join(out_dir(folder), name + ".hmesh")
    with open(path, "wb") as f:
        f.write(struct.pack("<4sIIIII", b"HMSH", 1, len(pos), len(idx), flags, len(skeleton)))
        for p in parts:
            f.write(p)
        for bone in skeleton:
            nm = bone["name"].encode()
            f.write(struct.pack("<H", len(nm)))
            f.write(nm)
            f.write(struct.pack("<i", bone["parent"]))
            f.write(np.asarray(bone["rest"], dtype="<f4").reshape(12).tobytes())
    return path


class Builder:

    def __init__(self):
        self.pos, self.nrm, self.uv, self.uv2, self.col, self.idx = [], [], [], [], [], []

    def vertex(self, p, n, uv, uv2=(0.0, 0.0), col=(1.0, 1.0, 1.0, 1.0)):
        self.pos.append(p)
        self.nrm.append(n)
        self.uv.append(uv)
        self.uv2.append(uv2)
        self.col.append(col)
        return len(self.pos) - 1

    def tri(self, a, b, c):
        self.idx.extend((a, b, c))

    def quad(self, pts, uvs, normal, uv2=(0.0, 0.0), col=(1.0, 1.0, 1.0, 1.0), normals=None):
        ids = [self.vertex(pts[k], normals[k] if normals else normal, uvs[k], uv2 if not isinstance(uv2[0], (tuple, list)) else uv2[k], col) for k in range(4)]
        self.tri(ids[0], ids[1], ids[2])
        self.tri(ids[0], ids[2], ids[3])
        return ids

    def tube(self, centers, radii, sides, u_wrap, v_values, uv2s, col, cap_end=False):
        rings = []
        for i, (c, r) in enumerate(zip(centers, radii)):
            c = np.asarray(c, dtype=np.float64)
            if i == 0:
                along = np.asarray(centers[1]) - c
            elif i == len(centers) - 1:
                along = c - np.asarray(centers[i - 1])
            else:
                along = np.asarray(centers[i + 1]) - np.asarray(centers[i - 1])
            along = along / max(np.linalg.norm(along), 1e-9)
            ref = np.array([1.0, 0.0, 0.0]) if abs(along[0]) < 0.9 else np.array([0.0, 0.0, 1.0])
            side = np.cross(along, ref)
            side /= np.linalg.norm(side)
            up = np.cross(side, along)
            ring = []
            for s in range(sides + 1):
                a = 2 * np.pi * s / sides
                d = side * np.cos(a) + up * np.sin(a)
                ring.append(self.vertex(tuple(c + d * r), tuple(d), (u_wrap * s / sides, v_values[i]), uv2s[i], col))
            rings.append(ring)
        for i in range(len(rings) - 1):
            for s in range(sides):
                a, b = rings[i][s], rings[i][s + 1]
                c2, d2 = rings[i + 1][s + 1], rings[i + 1][s]
                self.tri(a, d2, c2)
                self.tri(a, c2, b)
        if cap_end:
            c = np.asarray(centers[-1], dtype=np.float64)
            n = c - np.asarray(centers[-2])
            n = n / max(np.linalg.norm(n), 1e-9)
            mid = self.vertex(tuple(c), tuple(n), (0.5, v_values[-1]), uv2s[-1], col)
            for s in range(sides):
                self.tri(rings[-1][s], mid, rings[-1][s + 1])

    def write(self, folder, name, **extra):
        return write_hmesh(folder, name, self.pos, self.nrm, self.uv, self.idx, color=self.col, uv2=self.uv2, **extra)

    def triangles(self):
        return len(self.idx) // 3
