import os
import re

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GEN = os.path.join(ROOT, "assets", "gen")

SIZE = 2816.0
CELL = 2.0
N = int(SIZE / CELL)
HALF = SIZE / 2.0

BOMBER_TAIL = (-19.0, -1.5)
BOMBER_NOSE = (3.5, 0.5)
BOMBER_DENTS = (4.0, 8.85, 13.7, 18.55)
BOMBER_LIFT = 0.9


def out_dir(*parts):
    path = os.path.join(GEN, *parts)
    os.makedirs(path, exist_ok=True)
    return path


def read_sites():
    text = open(os.path.join(ROOT, "scripts", "sites.gd")).read()
    text = re.sub(r"#.*", "", text)
    sites = {}
    for m in re.finditer(r"const\s+(\w+)\s*:=\s*(.*?)(?=\n(?:const|static|func|var)\b|\Z)", text, re.S):
        name, body = m.group(1), m.group(2).strip()
        body = re.sub(r"Vector2\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)", r"(\1, \2)", body)
        try:
            sites[name] = eval(body, {"__builtins__": {}})
        except Exception:
            pass
    return sites


def grid():
    axis = np.linspace(-HALF, HALF, N + 1, dtype=np.float32)
    x, z = np.meshgrid(axis, axis)
    return x, z


def smoothstep(a, b, v):
    t = np.clip((v - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def catmull(points, step=3.0):
    pts = np.array(points, dtype=np.float64)
    ext = np.vstack([pts[0] * 2 - pts[1], pts, pts[-1] * 2 - pts[-2]])
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        n = max(int(np.linalg.norm(p2 - p1) / step), 1)
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1])
    return np.array(out)


def polyline_distance(x, z, pts, margin=60.0):
    dist = np.full(x.shape, margin, dtype=np.float32)
    along = np.zeros(x.shape, dtype=np.float32)
    pts = np.asarray(pts, dtype=np.float64)
    seg_len = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    start = np.concatenate([[0.0], np.cumsum(seg_len)])
    x0, z0 = x[0, 0], z[0, 0]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        lo_x, hi_x = min(a[0], b[0]) - margin, max(a[0], b[0]) + margin
        lo_z, hi_z = min(a[1], b[1]) - margin, max(a[1], b[1]) + margin
        c0 = max(int((lo_x - x0) / CELL), 0)
        c1 = min(int((hi_x - x0) / CELL) + 2, x.shape[1])
        r0 = max(int((lo_z - z0) / CELL), 0)
        r1 = min(int((hi_z - z0) / CELL) + 2, x.shape[0])
        if c0 >= c1 or r0 >= r1:
            continue
        sx = x[r0:r1, c0:c1]
        sz = z[r0:r1, c0:c1]
        d = b - a
        L2 = max(float(d @ d), 1e-9)
        t = np.clip(((sx - a[0]) * d[0] + (sz - a[1]) * d[1]) / L2, 0.0, 1.0)
        dd = np.hypot(sx - (a[0] + t * d[0]), sz - (a[1] + t * d[1])).astype(np.float32)
        cur = dist[r0:r1, c0:c1]
        better = dd < cur
        cur[better] = dd[better]
        al = along[r0:r1, c0:c1]
        al[better] = (start[i] + t * seg_len[i])[better]
    return dist, along


def sample(grid_values, px, pz):
    fx = np.clip((np.asarray(px) + HALF) / CELL, 0, N - 1e-3)
    fz = np.clip((np.asarray(pz) + HALF) / CELL, 0, N - 1e-3)
    i = fx.astype(int)
    j = fz.astype(int)
    tx = fx - i
    tz = fz - j
    a = grid_values[j, i] * (1 - tx) + grid_values[j, i + 1] * tx
    b = grid_values[j + 1, i] * (1 - tx) + grid_values[j + 1, i + 1] * tx
    return a * (1 - tz) + b * tz


def fbm(shape, wavelength_cells, octaves=5, gain=0.5, seed=0, ridged=False):
    rng = np.random.default_rng(seed)
    h, w = shape
    out = np.zeros(shape, dtype=np.float32)
    amp = 1.0
    total = 0.0
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    f = np.sqrt(fx * fx + fy * fy)
    for o in range(octaves):
        center = (2.0 ** o) / wavelength_cells
        band = np.exp(-((f - center) ** 2) / (2.0 * (center * 0.45) ** 2))
        spec = band * np.exp(2j * np.pi * rng.random(band.shape))
        layer = np.fft.irfft2(spec, s=shape).astype(np.float32)
        layer /= max(float(np.abs(layer).max()), 1e-9)
        if ridged:
            layer = 1.0 - 2.0 * np.abs(layer)
        out += layer * amp
        total += amp
        amp *= gain
    return out / total


_track = None


def track():
    global _track
    if _track is None:
        import numpy as np
        pts = np.fromfile(os.path.join(GEN, "terrain", "track.bin"), dtype=np.float32).reshape(-1, 3).astype(np.float64)
        seg = np.hypot(np.diff(pts[:, 0]), np.diff(pts[:, 2]))
        _track = (pts, np.concatenate([[0.0], np.cumsum(seg)]))
    return _track


def track_at(meters):
    import numpy as np
    pts, at = track()
    meters = float(np.clip(meters, 0.0, at[-1]))
    i = int(np.clip(np.searchsorted(at, meters) - 1, 0, len(pts) - 2))
    t = (meters - at[i]) / max(at[i + 1] - at[i], 1e-6)
    p = pts[i] + (pts[i + 1] - pts[i]) * t
    j0, j1 = max(i - 1, 0), min(i + 2, len(pts) - 1)
    d = pts[j1] - pts[j0]
    n = np.hypot(d[0], d[2])
    return (p[0], p[2]), (d[0] / n, d[2] / n)


def track_nearest(x, z):
    import numpy as np
    pts, at = track()
    d = np.hypot(pts[:, 0] - x, pts[:, 2] - z)
    i = int(np.argmin(d))
    return float(at[i]), float(d[i])
