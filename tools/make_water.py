#!/usr/bin/env python3
import json
import math
import os

import numpy as np

import maplib
from meshlib import Builder

S = maplib.read_sites()
HALF_WIDTH = 8.5


def main():
    b = Builder()
    up = (0.0, 1.0, 0.0)
    river = np.fromfile(os.path.join(maplib.GEN, "terrain", "river.bin"), dtype=np.float32).reshape(-1, 3).astype(np.float64)
    rows = []
    along = 0.0
    for i, p in enumerate(river):
        a, c = river[max(i - 1, 0)], river[min(i + 1, len(river) - 1)]
        d = np.array([c[0] - a[0], c[2] - a[2]])
        d /= max(np.linalg.norm(d), 1e-9)
        side = np.array([-d[1], d[0]])
        if i > 0:
            along += math.hypot(p[0] - river[i - 1][0], p[2] - river[i - 1][2])
        left = b.vertex((p[0] - side[0] * HALF_WIDTH, p[1], p[2] - side[1] * HALF_WIDTH), up, (0.0, along / 8.0), (0.0, 0.0))
        right = b.vertex((p[0] + side[0] * HALF_WIDTH, p[1], p[2] + side[1] * HALF_WIDTH), up, (1.0, along / 8.0), (0.0, 0.0))
        rows.append((left, right))
    for i in range(len(rows) - 1):
        a, c = rows[i], rows[i + 1]
        b.tri(a[0], c[1], a[1])
        b.tri(a[0], c[0], c[1])
    meta = json.load(open(os.path.join(maplib.GEN, "terrain", "meta.json")))
    for (center, heading, _side), level in zip(S["FOOTPRINTS"], meta["foot_water"]):
        c, s = math.cos(heading), math.sin(heading)
        mid = b.vertex((center[0], level, center[1]), up, (0.5, 0.5), (1.0, 0.0))
        ring = []
        n = 20
        for k in range(n):
            a = k / n * 2 * math.pi
            rx, rz = math.cos(a) * S["FOOT_WIDTH"] * 0.62, math.sin(a) * S["FOOT_LENGTH"] * 0.62
            x = center[0] + rx * c + rz * s
            z = center[1] - rx * s + rz * c
            ring.append(b.vertex((x, level, z), up, (0.5 + math.cos(a) * 0.5, 0.5 + math.sin(a) * 0.5), (1.0, 0.0)))
        for k in range(n):
            b.tri(mid, ring[(k + 1) % n], ring[k])
    b.write("mesh", "water")
    print("water: %d triangles, river %.0f m long" % (b.triangles(), along))


if __name__ == "__main__":
    main()
