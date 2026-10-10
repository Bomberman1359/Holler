import math

import numpy as np

from buildlib import Mat, UP, ruin_top, unit, v3


PLASTER = Mat("plaster")
OCHRE = Mat("plaster", (0.50, 0.45, 0.36))
PINK = Mat("plaster", (0.50, 0.43, 0.40))
GREY_PLASTER = Mat("plaster", (0.42, 0.43, 0.42))
BRICK = Mat("brick")
STONE = Mat("masonry")
CONCRETE = Mat("concrete")
BOARDS = Mat("planks")
DARK_BOARDS = Mat("planks", (0.30, 0.26, 0.22))
TIMBER = Mat("planks", (0.24, 0.19, 0.15))
GREEN_BOARDS = Mat("planks", (0.30, 0.40, 0.30))
SHINGLE = Mat("shingles")
FLOOR = Mat("floorboards")
RUST = Mat("rust", (0.37, 0.43, 0.47))
ALU = Mat("aluminum")
OLIVE = Mat("army_paint", (0.34, 0.42, 0.6))
CANVAS = Mat("cloth", (0.36, 0.37, 0.25))
SHEET = Mat("cloth", (0.5, 0.49, 0.45))
BLANKET = Mat("cloth", (0.30, 0.31, 0.33))
PAINT = Mat("wall_paint")
PAINT_GREEN = Mat("wall_paint", (0.36, 0.45, 0.38))
RUBBLE = Mat("rubble")
TILE = Mat("tiles")
IRON = Mat("iron")
ENAMEL = Mat("enamel")
RUBBER = Mat("iron", (0.22, 0.22, 0.22))
BRASS = Mat("iron", (0.75, 0.6, 0.3))
GLOW_WARM = Mat("enamel", (0.5, 0.36, 0.16), glow=1.0)
GLOW_RED = Mat("enamel", (0.5, 0.05, 0.03), glow=1.0)


def window_frame(k, a, T, w, h, depth=0.1, m=DARK_BOARDS, bars=True, sill=True):
    T = unit(T)
    N = np.cross(T, UP)
    a = np.asarray(a, dtype=np.float64) - N * (depth + 0.03)
    s = 0.07

    def bar(u0, v0, u1, v1):
        lo = a + T * u0 + UP * v0
        k.face([lo, lo + T * (u1 - u0), lo + T * (u1 - u0) + UP * (v1 - v0), lo + UP * (v1 - v0)], m, T=T, U=UP, solid=False)
        back = [lo - N * 0.05 + UP * (v1 - v0), lo - N * 0.05 + T * (u1 - u0) + UP * (v1 - v0), lo - N * 0.05 + T * (u1 - u0), lo - N * 0.05]
        k.face(back, m, solid=False)
    bar(0, 0, w, s)
    bar(0, h - s, w, h)
    bar(0, s, s, h - s)
    bar(w - s, s, w, h - s)
    if bars:
        bar(w / 2 - s / 2, s, w / 2 + s / 2, h - s)
        bar(s, h * 0.62, w - s, h * 0.62 + s * 0.8)
    if sill:
        k.block(a + T * (w / 2) + N * (depth + 0.08) - UP * 0.03, (w + 0.16, 0.06, 0.18), m, yaw=math.atan2(-T[2], T[0]), solid=False)


def shutter(k, a, T, w, h, open_angle=2.6, m=GREEN_BOARDS, side=-1, sag=0.0):
    T = unit(T)
    N = np.cross(T, UP)
    d = T * math.cos(open_angle) * (-side) + N * math.sin(open_angle)
    d = unit(d)
    c = np.asarray(a, dtype=np.float64) + d * (w / 2) + UP * (h / 2) + N * 0.03
    yaw = math.atan2(-d[2], d[0])
    k.block(c, (w, h, 0.035), m, yaw=yaw, roll=sag, solid=False)


def door_leaf(k, hinge, T, w, h, angle=1.2, m=DARK_BOARDS, thick=0.05):
    T = unit(T)
    N = np.cross(T, UP)
    d = unit(T * math.cos(angle) - N * math.sin(angle))
    c = np.asarray(hinge, dtype=np.float64) + d * (w / 2) + UP * (h / 2)
    k.block(c, (w, h, thick), m, yaw=math.atan2(-d[2], d[0]))


def gable_roof(k, x0, x1, z0, z1, eave, rise, top=SHINGLE, under=DARK_BOARDS, over=0.45, thick=0.1, holes_front=(), holes_back=()):
    half = (z1 - z0) / 2
    run = half + over
    drop = over * rise / half
    length = math.hypot(run, rise + drop)
    w = x1 - x0 + 2 * over
    U1 = unit(v3(0, rise + drop, -run))
    k.panel(v3(x0 - over, eave - drop, z1 + over), v3(1, 0, 0), U1, w, length, thick, top, under, holes_front, anchor="front", bottom=True)
    U2 = unit(v3(0, rise + drop, run))
    k.panel(v3(x1 + over, eave - drop, z0 - over), v3(-1, 0, 0), U2, w, length, thick, top, under, holes_back, anchor="front", bottom=True)
    k.beam(v3(x0 - over, eave + rise + 0.02, (z0 + z1) / 2), v3(x1 + over, eave + rise + 0.02, (z0 + z1) / 2), 0.16, under, solid=False)


def chimney(k, x, z, base, height, m=BRICK, size=0.6):
    k.box((x - size / 2, base, z - size / 2), (x + size / 2, base + height, z + size / 2), m, skip="y-")
    k.box((x - size / 2 - 0.06, base + height, z - size / 2 - 0.06), (x + size / 2 + 0.06, base + height + 0.12, z + size / 2 + 0.06), m)


def rubble_heap(k, x, z, radius, height, seed=0, m=RUBBLE, sky=1.0):
    rng = np.random.default_rng(seed)
    rings = []
    n = 12
    for r, h in ((1.0, 0.0), (0.75, 0.45), (0.42, 0.85), (0.12, 1.0)):
        ring = []
        for i in range(n):
            a = i / n * 2 * math.pi
            rr = radius * r * (0.75 + 0.5 * rng.random())
            ring.append((x + math.cos(a) * rr, height * h * (0.8 + 0.4 * rng.random()) - (0.05 if h == 0.0 else 0.0), z + math.sin(a) * rr))
        rings.append(ring)
    k.loft(rings, m.but(sky=sky))
    top = rings[-1]
    k.face([top[i] for i in range(n)][::-1], m.but(sky=sky))
    for _ in range(int(3 + radius * 2)):
        a, r = rng.uniform(0, 6.28), rng.uniform(0.2, 1.0) * radius
        s = rng.uniform(0.15, 0.4)
        k.block((x + math.cos(a) * r, height * (1 - r / radius) * 0.7 + s * 0.3, z + math.sin(a) * r), (s * 1.6, s, s * 1.1),
                BRICK.but(sky=sky) if rng.random() < 0.6 else PLASTER.but(sky=sky), yaw=rng.uniform(0, 3), pitch=rng.uniform(-0.5, 0.5), roll=rng.uniform(-0.4, 0.4), solid=False)
    for _ in range(int(1 + radius)):
        a = rng.uniform(0, 6.28)
        p = v3(x + math.cos(a) * radius * 0.5, height * 0.5, z + math.sin(a) * radius * 0.5)
        q = p + v3(rng.uniform(-1.5, 1.5), rng.uniform(0.1, 0.9), rng.uniform(-1.5, 1.5))
        k.beam(p - (q - p) * 0.4, q, 0.14, TIMBER.but(sky=sky), solid=False)


def house(k, w, d, floors=1, storey=2.7, wall=PLASTER, roof="gable", ruin=0.0, seed=0, door="shut", rise=None, inside=None,
          shutters=True, stone_base=True, windows_front=None, sign=None):
    rng = np.random.default_rng(seed)
    H = floors * storey + 0.2
    t = 0.38
    inner = inside or PAINT.indoors(0.05 if roof == "gable" else 0.45)
    rise = rise if rise is not None else d * 0.42
    win_w, win_h, sill = 0.95, 1.3, 0.95

    def windows(length, count, skip_door=None):
        out = []
        for f in range(floors):
            for i in range(count):
                u = (i + 0.5) / count * length
                if skip_door is not None and f == 0 and abs(u - skip_door) < 1.1:
                    continue
                out.append((u - win_w / 2, u + win_w / 2, f * storey + sill, f * storey + sill + win_h))
        return out

    def top(length, s):
        if ruin <= 0.0:
            return None
        return ruin_top(length, H, seed * 7 + s, low=max(1.0 - ruin * 1.15, 0.12), rough=0.6 + ruin)

    n_front = windows_front or max(int(w / 2.6), 2)
    door_u = w / 2 if door != "none" else None
    front = windows(w, n_front, door_u)
    if door != "none":
        front.append((door_u - 0.55, door_u + 0.55, 0.0, 2.1))
    back = windows(w, max(n_front - 1, 1))
    side_n = max(int(d / 3.2), 1)
    gable = (lambda u: H - 0.14 + rise * (1.0 - abs(2.0 * u / d - 1.0))) if (roof != "none" and ruin <= 0.0) else None
    walls = [
        ((0, d), (w, d), w, front, top(w, 1)),
        ((w, 0), (0, 0), w, back, top(w, 2)),
        ((w, d), (w, 0), d, windows(d, side_n), gable or top(d, 3)),
        ((0, 0), (0, d), d, windows(d, side_n), gable or top(d, 4)),
    ]
    for (a, b, length, holes, tp) in walls:
        k.wall(a, b, H + (rise if tp is gable and gable else 0.0), t, wall, inner, holes, top=tp, edge=BRICK if ruin > 0 else None)
        T = unit(v3(b[0] - a[0], 0, b[1] - a[1]))
        N = np.cross(T, UP)
        for (u0, u1, v0, v1) in holes:
            if v0 < 0.01:
                continue
            height_here = H
            if tp is not None and not callable(tp):
                height_here = min(_top_at(tp, u0), _top_at(tp, (u0 + u1) / 2), _top_at(tp, u1))
            if v1 > height_here - 0.05:
                continue
            p = v3(a[0], v0, a[1]) + T * u0
            window_frame(k, p, T, u1 - u0, v1 - v0)
            if shutters and rng.random() < (0.75 - ruin * 0.6):
                ang = rng.choice([2.9, 2.9, 2.5, 0.25])
                shutter(k, p, T, (u1 - u0) / 2, v1 - v0, ang, side=-1, sag=rng.uniform(-0.03, 0.03))
                if rng.random() < 0.8:
                    shutter(k, p + T * (u1 - u0), -T, (u1 - u0) / 2, v1 - v0, -ang, side=-1, sag=rng.uniform(-0.12, 0.03))
            elif rng.random() < 0.5:
                k.decal("glass_broken_%d" % rng.integers(0, 2), p + T * ((u1 - u0) / 2) + UP * ((v1 - v0) / 2) - N * 0.08, N, u1 - u0, v1 - v0, alpha=0.9)
    if stone_base and ruin < 0.6:
        s = 0.07
        for (a, b, length, holes, _tp) in walls:
            T = unit(v3(b[0] - a[0], 0, b[1] - a[1]))
            N = np.cross(T, UP)
            foot = v3(a[0], -0.3, a[1]) + N * s - T * s
            doors = [(u0 + s, u1 + s, 0.0, 9.0) for (u0, u1, v0, v1) in holes if v0 < 0.01]
            k.panel(foot, T, UP, length + 2 * s, 0.72, s, STONE, STONE, doors, anchor="front", solid=False)
    k.floor((t, t), (w - t, d - t), 0.12, 0.3, FLOOR.indoors(inner.sky))
    for f in range(1, floors):
        if ruin < 0.3:
            k.floor((t, t), (w - t, d - t), f * storey, 0.16, FLOOR.indoors(inner.sky), DARK_BOARDS.indoors(inner.sky))
    if ruin <= 0.0 and roof != "none":
        holes_f, holes_b = [], []
        if roof == "holes":
            for _ in range(rng.integers(1, 4)):
                hx, hl = rng.uniform(0.5, w - 2.5), rng.uniform(1.2, 3.0)
                hole = (hx, hx + hl, rng.uniform(0.6, 1.5), rng.uniform(2.2, 4.0))
                (holes_f if rng.random() < 0.5 else holes_b).append(hole)
        gable_roof(k, 0, w, 0, d, H, rise, holes_front=holes_f, holes_back=holes_b)
        chimney(k, w * rng.uniform(0.25, 0.75), d / 2 + rng.uniform(-0.8, 0.8), H + rise - 0.9, 1.7)
    elif ruin > 0.0:
        rubble_heap(k, w * rng.uniform(0.3, 0.7), d * rng.uniform(0.3, 0.7), min(w, d) * 0.33, 0.5 + ruin * 0.8, seed + 3, sky=0.6)
        if rng.random() < 0.7:
            rubble_heap(k, w * rng.uniform(0.1, 0.9), d + rng.uniform(0.5, 1.5), 1.6, 0.6, seed + 4)
    if door == "shut":
        k.box((door_u - 0.55, 0.0, d - 0.2), (door_u + 0.55, 2.1, d - 0.13), DARK_BOARDS)
    elif door == "open":
        door_leaf(k, v3(door_u - 0.55, 0.12, d - 0.1), v3(1, 0, 0), 1.08, 2.0, angle=rng.uniform(1.0, 1.9))
    if door != "none":
        k.box((door_u - 0.8, -0.1, d), (door_u + 0.8, 0.16, d + 0.7), STONE)
    if sign:
        k.block((door_u, 2.75, d + 0.07), (3.4, 0.62, 0.05), DARK_BOARDS, solid=False)
        k.decal(sign, (door_u, 2.75, d + 0.1), (0, 0, 1), 3.3)
    return H


def _top_at(steps, u):
    h = steps[0][1]
    for (su, sh) in sorted(steps):
        if su <= u:
            h = sh
    return h


def table(k, w=1.6, d=0.8, h=0.76, m=DARK_BOARDS, sky=0.06):
    m = m.but(sky=sky)
    k.box((-w / 2, h - 0.05, -d / 2), (w / 2, h, d / 2), m)
    for sx in (-1, 1):
        for sz in (-1, 1):
            k.box((sx * (w / 2 - 0.1) - 0.035, 0, sz * (d / 2 - 0.1) - 0.035), (sx * (w / 2 - 0.1) + 0.035, h - 0.05, sz * (d / 2 - 0.1) + 0.035), m, skip="y- y+", solid=False)


def bench(k, w=1.5, h=0.45, m=DARK_BOARDS, sky=0.06, back=False):
    m = m.but(sky=sky)
    k.box((-w / 2, h - 0.04, -0.16), (w / 2, h, 0.16), m)
    for sx in (-1, 1):
        k.box((sx * (w / 2 - 0.12) - 0.03, 0, -0.14), (sx * (w / 2 - 0.12) + 0.03, h - 0.04, 0.14), m, skip="y- y+", solid=False)
    if back:
        k.box((-w / 2, h + 0.25, -0.2), (w / 2, h + 0.5, -0.16), m, solid=False)
        for sx in (-1, 1):
            k.box((sx * (w / 2 - 0.05) - 0.025, h, -0.2), (sx * (w / 2 - 0.05) + 0.025, h + 0.5, -0.16), m, solid=False)


def chair(k, m=DARK_BOARDS, sky=0.06, fallen=False):
    m = m.but(sky=sky)
    if fallen:
        with k.at(0, 0.22, 0, pitch=-1.45):
            chair(k, m, sky)
        return
    k.box((-0.2, 0.43, -0.2), (0.2, 0.46, 0.2), m)
    for sx in (-1, 1):
        for sz in (-1, 1):
            k.box((sx * 0.17 - 0.018, 0, sz * 0.17 - 0.018), (sx * 0.17 + 0.018, 0.43 if sz > 0 else 0.92, sz * 0.17 + 0.018), m, skip="y-", solid=False)
    k.box((-0.2, 0.7, -0.19), (0.2, 0.9, -0.165), m, solid=False)


def place_setting(k, sky=0.06):
    k.tube([(0, 0.0, 0), (0, 0.012, 0)], [0.11, 0.12], 10, ENAMEL.but(sky=sky), solid=False, cap_start=False)
    k.tube([(0.2, 0.0, -0.06), (0.2, 0.09, -0.06)], [0.04, 0.042], 8, BRASS.but(sky=sky, tint=(0.4, 0.38, 0.34)), solid=False, cap_start=False)
    k.box((-0.2, 0.0, -0.01), (-0.06, 0.006, 0.012), IRON.but(sky=sky, tint=(0.8, 0.8, 0.8)), solid=False)


def bed(k, length=2.0, width=0.9, sky=0.06, made=True, mattress=True, seed=0):
    rng = np.random.default_rng(seed)
    fr = ENAMEL.but(sky=sky)
    h = 0.5
    for sz, top in ((-length / 2, 1.05), (length / 2, 0.8)):
        for sx in (-1, 1):
            k.tube([(sx * width / 2, 0, sz), (sx * width / 2, top, sz)], [0.02, 0.02], 6, fr, solid=False)
        k.tube([(-width / 2, top, sz), (width / 2, top, sz)], [0.02, 0.02], 6, fr, solid=False)
        k.tube([(-width / 2, h + 0.12, sz), (width / 2, h + 0.12, sz)], [0.014, 0.014], 5, fr, solid=False)
        n = max(int(width / 0.16), 3)
        for i in range(1, n):
            x = -width / 2 + width * i / n
            k.tube([(x, h + 0.12, sz), (x, top, sz)], [0.008, 0.008], 4, fr, solid=False, cap_start=False, cap_end=False)
    k.box((-width / 2, h - 0.04, -length / 2), (width / 2, h, length / 2), IRON.but(sky=sky))
    if mattress:
        k.box((-width / 2 + 0.03, h, -length / 2 + 0.04), (width / 2 - 0.03, h + 0.13, length / 2 - 0.04), SHEET.but(sky=sky, tint=(0.46, 0.44, 0.38)))
        if made:
            k.box((-width / 2 + 0.01, h + 0.13, -length / 2 + 0.55), (width / 2 - 0.01, h + 0.17, length / 2 - 0.05), BLANKET.but(sky=sky))
            k.box((-width / 2 + 0.12, h + 0.13, -length / 2 + 0.1), (width / 2 - 0.12, h + 0.22, -length / 2 + 0.45), SHEET.but(sky=sky), solid=False)
        else:
            k.block((rng.uniform(-0.1, 0.1), h + 0.17, rng.uniform(0.0, 0.4)), (width * 0.9, 0.08, length * 0.5), BLANKET.but(sky=sky), yaw=rng.uniform(-0.4, 0.4), solid=False)


def locker(k, sky=0.06, m=None):
    m = (m or OLIVE).but(sky=sky)
    w, h, d, t = 0.9, 2.0, 0.6, 0.03
    k.box((-w / 2, 0, -d / 2), (-w / 2 + t, h, d / 2), m)
    k.box((w / 2 - t, 0, -d / 2), (w / 2, h, d / 2), m)
    k.box((-w / 2, 0, -d / 2), (w / 2, h, -d / 2 + t), m)
    k.box((-w / 2, h - t, -d / 2), (w / 2, h, d / 2), m)
    k.box((-w / 2, 0, -d / 2), (w / 2, 0.06, d / 2), m)
    k.box((-w / 2 + t, 1.68, -d / 2 + t), (w / 2 - t, 1.7, d / 2 - 0.05), m, solid=False)
    k.block((0.2, 0.05, d / 2 + 0.8), (w, 0.03, h * 0.95), m, yaw=0.5, pitch=0.06, solid=False)


def crate(k, s=0.7, m=BOARDS, sky=1.0, h=None):
    m = m.but(sky=sky)
    h = h or s
    k.box((-s / 2, 0, -s / 2), (s / 2, h, s / 2), m, skip="y-")
    for sx in (-1, 1):
        k.box((sx * (s / 2 + 0.012) - 0.012, 0.05, -s / 2), (sx * (s / 2 + 0.012) + 0.012, 0.13, s / 2), DARK_BOARDS.but(sky=sky), solid=False)
        k.box((sx * (s / 2 + 0.012) - 0.012, h - 0.13, -s / 2), (sx * (s / 2 + 0.012) + 0.012, h - 0.05, s / 2), DARK_BOARDS.but(sky=sky), solid=False)


def barrel(k, m=RUST, sky=1.0, r=0.29, h=0.88, fallen=False):
    m = m.but(sky=sky)
    if fallen:
        k.tube([(-h / 2, r, 0), (-h / 4, r, 0), (h / 4, r, 0), (h / 2, r, 0)], [r, r * 1.03, r * 1.03, r], 12, m)
    else:
        k.tube([(0, 0, 0), (0, h * 0.3, 0), (0, h * 0.7, 0), (0, h, 0)], [r, r * 1.03, r * 1.03, r], 12, m)


def stove(k, sky=0.06):
    m = TILE.but(sky=sky, tint=(0.30, 0.42, 0.32))
    k.box((-0.7, 0.0, -0.55), (0.7, 0.45, 0.55), m)
    k.box((-0.55, 0.45, -0.45), (0.55, 1.5, 0.45), m, skip="y-")
    k.box((-0.6, 1.5, -0.5), (0.6, 1.6, 0.5), m)
    k.box((-0.4, 1.6, -0.3), (0.4, 2.1, 0.3), m, skip="y-")
    k.box((-0.18, 0.55, 0.45), (0.18, 0.9, 0.47), IRON.but(sky=sky), solid=False)


def cupboard(k, w=1.2, h=1.9, d=0.45, m=DARK_BOARDS, sky=0.06, open_door=True):
    m = m.but(sky=sky)
    k.box((-w / 2, 0, -d / 2), (w / 2, h, d / 2 - 0.04), m)
    k.box((-w / 2 - 0.03, h, -d / 2 - 0.03), (w / 2 + 0.03, h + 0.06, d / 2), m, solid=False)
    if open_door:
        door_leaf(k, v3(-w / 2, 0.08, d / 2 - 0.02), v3(1, 0, 0), w / 2 - 0.02, h - 0.16, angle=-1.9, m=m, thick=0.03)
        k.box((0.0, 0.08, d / 2 - 0.04), (w / 2, h - 0.08, d / 2 - 0.01), m, solid=False)
    else:
        k.box((-w / 2, 0.08, d / 2 - 0.04), (w / 2, h - 0.08, d / 2 - 0.01), m, solid=False)


def desk(k, w=1.5, d=0.75, sky=0.06, m=DARK_BOARDS):
    m = m.but(sky=sky)
    k.box((-w / 2, 0.72, -d / 2), (w / 2, 0.77, d / 2), m)
    k.box((-w / 2, 0.0, -d / 2), (-w / 2 + 0.42, 0.72, d / 2 - 0.03), m, skip="y+")
    k.box((w / 2 - 0.42, 0.0, -d / 2), (w / 2, 0.72, d / 2 - 0.03), m, skip="y+")
    k.box((-w / 2 + 0.42, 0.25, -d / 2), (w / 2 - 0.42, 0.72, -d / 2 + 0.03), m, solid=False)


def radio_set(k, sky=0.06, lit=False):
    m = OLIVE.but(sky=sky)
    k.box((-0.3, 0, -0.18), (0.3, 0.36, 0.18), m)
    for i, x in enumerate((-0.18, -0.02, 0.14)):
        k.tube([(x, 0.22, 0.18), (x, 0.22, 0.2)], [0.045, 0.04], 10, IRON.but(sky=sky), solid=False, cap_start=False)
    k.box((-0.24, 0.07, 0.18), (0.2, 0.13, 0.185), GLOW_WARM.but(glow=0.9 if lit else 0.0, sky=sky), solid=False)
    k.box((0.34, 0.0, -0.1), (0.42, 0.05, 0.14), IRON.but(sky=sky), solid=False)
    k.tube([(-0.25, 0.36, -0.1), (-0.25, 1.5, -0.1)], [0.006, 0.003], 4, IRON.but(sky=sky), solid=False)


def camera_tripod(k, sky=1.0, fallen=False):
    wood = BOARDS.but(sky=sky, tint=(0.5, 0.42, 0.3))
    body = IRON.but(sky=sky, tint=(0.34, 0.34, 0.36))
    if fallen:
        with k.at(0, 0.25, 0, roll=1.45):
            camera_tripod(k, sky)
        return
    top = v3(0, 1.35, 0)
    for a in (0.5, 2.6, 4.7):
        foot = v3(math.cos(a) * 0.55, 0, math.sin(a) * 0.55)
        k.beam(foot, top, 0.045, wood, solid=False)
    k.tube([(0, 1.33, 0), (0, 1.42, 0)], [0.07, 0.06], 8, body, solid=False)
    k.box((-0.1, 1.42, -0.17), (0.1, 1.66, 0.14), body)
    k.tube([(0, 1.54, 0.14), (0, 1.54, 0.26)], [0.045, 0.055], 10, body, solid=False)
    k.tube([(0.1, 1.5, -0.02), (0.14, 1.5, -0.02)], [0.03, 0.03], 8, body, solid=False)
    for z in (-0.08, 0.06):
        k.tube([(-0.035, 1.75, z), (0.035, 1.75, z)], [0.1, 0.1], 12, body, solid=False)


def tripod_trunk(k, sky=1.0):
    crate(k, 0.5, OLIVE, sky, h=0.3)


def signpost(k, decal, width=1.5, height=2.2, board_h=0.5, posts=2, m=BOARDS, lean=0.0):
    with k.at(0, 0, 0, roll=lean):
        if posts == 2:
            for sx in (-1, 1):
                k.box((sx * (width / 2 - 0.08) - 0.05, -0.4, -0.05), (sx * (width / 2 - 0.08) + 0.05, height, 0.05), DARK_BOARDS)
        else:
            k.box((-0.06, -0.4, -0.06), (0.06, height, 0.06), DARK_BOARDS)
        k.box((-width / 2, height - board_h - 0.1, 0.05), (width / 2, height - 0.1, 0.09), m, solid=False)
        k.decal(decal, (0, height - board_h / 2 - 0.1, 0.09), (0, 0, 1), width * 0.96, board_h * 0.94)


def fence(k, a, b, height=1.0, m=BOARDS, gap=2.2, broken=0.25, seed=0):
    rng = np.random.default_rng(seed)
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    L = np.linalg.norm(b - a)
    n = max(int(L / gap), 1)
    pts = []
    for i in range(n + 1):
        p = a + (b - a) * i / n
        pts.append(v3(p[0], k.ground(p[0], p[1]), p[1]))
    for i, p in enumerate(pts):
        lean = rng.uniform(-0.12, 0.12)
        k.beam(p - UP * 0.3, p + v3(lean, height, lean * 0.5), 0.1, DARK_BOARDS, solid=False)
        if i < n and rng.random() > broken:
            for hgt in (0.45, 0.85):
                k.beam(p + UP * hgt * height, pts[i + 1] + UP * (hgt * height + rng.uniform(-0.05, 0.05)), 0.07, m, depth=0.03, solid=False)


def pole(k, height=7.5, arm=True, wire_to=None):
    k.tube([(0, -0.5, 0), (0, height, 0)], [0.11, 0.08], 7, TIMBER)
    if arm:
        k.box((-0.7, height - 0.7, -0.05), (0.7, height - 0.6, 0.05), TIMBER, solid=False)
        for x in (-0.6, 0.6):
            k.tube([(x, height - 0.6, 0), (x, height - 0.48, 0)], [0.035, 0.03], 6, ENAMEL, solid=False)


def well(k):
    k.tube([(0, -0.2, 0), (0, 0.85, 0)], [0.95, 0.95], 14, STONE, cap_start=False)
    k.tube([(0, 0.85, 0), (0, 0.3, 0)], [0.7, 0.7], 14, STONE, cap_start=False, cap_end=True)
    for sx in (-1, 1):
        k.box((sx * 0.85 - 0.06, 0.8, -0.06), (sx * 0.85 + 0.06, 2.2, 0.06), TIMBER)
    k.tube([(-0.9, 1.9, 0), (0.9, 1.9, 0)], [0.07, 0.07], 8, TIMBER, solid=False)
    k.box((-1.1, 2.2, -0.7), (1.1, 2.26, 0.7), SHINGLE)


def cart(k, broken=True):
    k.box((-1.4, 0.75, -0.6), (1.4, 0.85, 0.6), BOARDS)
    for sz in (-0.6, 0.6):
        k.box((-1.4, 0.85, sz - 0.03), (1.4, 1.25, sz + 0.03), BOARDS, solid=False)
    k.beam((1.4, 0.8, 0), (3.2, 0.35, 0), 0.08, TIMBER, solid=False)
    wheel(k, (-0.8, 0.55, 0.72), 0.55, axis=(0, 0, 1), m=TIMBER, tyre=RUST)
    if not broken:
        wheel(k, (-0.8, 0.55, -0.72), 0.55, axis=(0, 0, 1), m=TIMBER, tyre=RUST)
    else:
        with k.at(-1.8, 0.06, -1.5, pitch=1.5):
            wheel(k, (0, 0, 0), 0.55, axis=(0, 0, 1), m=TIMBER, tyre=RUST)


def wheel(k, c, r, axis=(1, 0, 0), width=0.1, m=RUBBER, tyre=None, spokes=8, solid=False):
    c = np.asarray(c, dtype=np.float64)
    ax = unit(axis)
    if tyre is None:
        k.tube([c - ax * width / 2, c - ax * width * 0.3, c + ax * width * 0.3, c + ax * width / 2], [r * 0.82, r, r, r * 0.82], 14, m, solid=solid)
        k.tube([c - ax * (width / 2 + 0.01), c + ax * (width / 2 + 0.01)], [r * 0.45, r * 0.45], 10, OLIVE, solid=False)
        return
    side = unit(np.cross(ax, UP)) if abs(ax[1]) < 0.9 else v3(1, 0, 0)
    up = np.cross(side, ax)
    n = 14
    ring_o = [c + (side * math.cos(i / n * 6.2832) + up * math.sin(i / n * 6.2832)) * r for i in range(n)]
    ring_i = [c + (side * math.cos(i / n * 6.2832) + up * math.sin(i / n * 6.2832)) * (r - 0.07) for i in range(n)]
    for i in range(n):
        j = (i + 1) % n
        for sgn in (-1, 1):
            off = ax * (width / 2 * sgn)
            quad = [ring_i[i] + off, ring_i[j] + off, ring_o[j] + off, ring_o[i] + off]
            k.face(quad if sgn > 0 else quad[::-1], tyre, solid=False)
        k.face([ring_o[i] - ax * width / 2, ring_o[i] + ax * width / 2, ring_o[j] + ax * width / 2, ring_o[j] - ax * width / 2][::-1], tyre, solid=False)
    for i in range(spokes):
        a = i / spokes * 6.2832
        k.beam(c, c + (side * math.cos(a) + up * math.sin(a)) * (r - 0.05), 0.045, m, solid=False)
    k.tube([c - ax * (width / 2 + 0.04), c + ax * (width / 2 + 0.04)], [0.09, 0.09], 8, m, solid=False)


def jeep(k, sky=1.0, doors_decal=True):
    body = OLIVE.but(sky=sky)
    dark = IRON.but(sky=sky)
    seat = CANVAS.but(sky=sky)
    r = 0.37
    k.box((-0.72, 0.42, -1.55), (0.72, 0.5, 0.45), body)
    for sx in (-1, 1):
        x0, x1 = (sx * 0.78, sx * 0.72) if sx < 0 else (sx * 0.72, sx * 0.78)
        k.box((x0, 0.5, -1.55), (x1, 1.02, -0.62), body)
        k.box((x0, 0.5, -0.62), (x1, 0.74, 0.0), body)
        k.box((x0, 0.5, 0.0), (x1, 1.02, 0.45), body)
    k.box((-0.78, 0.5, -1.6), (0.78, 1.02, -1.55), body)
    k.box((-0.78, 0.5, 0.4), (0.78, 1.04, 0.5), body)
    hood = [[(-0.55, 0.62, 0.5), (0.55, 0.62, 0.5), (0.55, 1.05, 0.5), (-0.55, 1.05, 0.5)],
            [(-0.5, 0.62, 1.45), (0.5, 0.62, 1.45), (0.5, 1.0, 1.45), (-0.5, 1.0, 1.45)]]
    k.loft(hood, body, close=True)
    k.face([hood[1][0], hood[1][1], hood[1][2], hood[1][3]], body)
    k.decal("star", (0, 1.035, 0.95), (0, 1, 0.05), 0.62, 0.62, up=(0, 0, 1), sky=sky)
    k.box((-0.5, 0.55, 1.45), (0.5, 1.0, 1.48), body)
    for i in range(9):
        x = -0.24 + i * 0.06
        k.box((x - 0.014, 0.62, 1.48), (x + 0.014, 0.93, 1.485), dark, solid=False)
    for sx in (-1, 1):
        k.tube([(sx * 0.38, 0.82, 1.47), (sx * 0.38, 0.82, 1.5)], [0.085, 0.08], 12, ENAMEL.but(sky=sky, tint=(0.4, 0.42, 0.4)), solid=False, cap_start=False)
    k.box((-0.82, 0.5, 1.52), (0.82, 0.6, 1.6), dark)
    for sx in (-1, 1):
        x0, x1 = sorted((sx * 0.5, sx * 0.84))
        k.box((x0, 0.8, 0.5), (x1, 0.84, 1.45), body)
        k.block((sx * 0.67, 0.72, 1.5), (0.34, 0.04, 0.22), body, pitch=0.9, solid=False)
    for sx in (-1, 1):
        for z in (-1.0, 0.98):
            wheel(k, (sx * 0.7, r, z), r, axis=(1, 0, 0), width=0.2, m=RUBBER.but(sky=sky), solid=True)
    wheel(k, (0.3, 0.86, -1.72), r, axis=(0, 0, 1), width=0.2, m=RUBBER.but(sky=sky))
    k.box((-0.55, 0.6, -1.78), (-0.2, 1.05, -1.6), body)
    for sx in (-1, 1):
        k.beam((sx * 0.72, 1.04, 0.45), (sx * 0.72, 1.72, 0.36), 0.045, body, solid=False)
    k.beam((-0.72, 1.72, 0.36), (0.72, 1.72, 0.36), 0.045, body, solid=False)
    k.beam((0.0, 1.04, 0.45), (0.0, 1.72, 0.36), 0.03, body, solid=False)
    k.decal("glass", (0.0, 1.38, 0.42), (0, 0.13, 1), 1.4, 0.66, sky=sky, alpha=0.9)
    k.decal("glass", (0.0, 1.38, 0.39), (0, -0.13, -1), 1.4, 0.66, sky=sky, alpha=0.9)
    k.tube([(-0.36, 1.12, 0.12), (-0.36, 1.16, 0.08)], [0.19, 0.19], 12, dark, solid=False)
    k.beam((-0.36, 0.9, 0.42), (-0.36, 1.13, 0.1), 0.03, dark, solid=False)
    for sx in (-1, 1):
        k.box((sx * 0.36 - 0.24, 0.5, -0.5), (sx * 0.36 + 0.24, 0.78, -0.05), seat)
        k.block((sx * 0.36, 1.0, -0.55), (0.46, 0.5, 0.07), seat, pitch=-0.15, solid=False)
    k.box((-0.66, 0.5, -1.5), (0.66, 0.8, -1.05), seat)


def truck(k, sky=1.0, burned=True):
    body = (RUST.but(tint=(0.24, 0.24, 0.24)) if burned else OLIVE).but(sky=sky)
    dark = IRON.but(sky=sky)
    r = 0.5
    k.box((-0.5, 0.75, -3.2), (0.5, 0.95, 2.6), dark)
    k.box((-1.1, 0.95, 0.4), (1.1, 2.35, 1.5), body)
    k.box((-0.8, 0.95, 1.5), (0.8, 1.75, 2.75), body)
    k.box((-0.8, 0.9, 2.75), (0.8, 1.7, 2.8), dark)
    for i in range(7):
        x = -0.6 + i * 0.2
        k.box((x - 0.03, 1.0, 2.8), (x + 0.03, 1.62, 2.81), body, solid=False)
    k.box((-1.2, 0.95, -3.3), (1.2, 1.1, 0.3), body)
    for sx in (-1, 1):
        x0, x1 = sorted((sx * 1.2, sx * 1.14))
        k.box((x0, 1.1, -3.3), (x1, 1.75, 0.3), body)
    k.box((-1.2, 1.1, 0.24), (1.2, 1.75, 0.3), body)
    for z in (-3.1, -2.0, -0.9, 0.1):
        for sx in (-1, 1):
            k.beam((sx * 1.17, 1.75, z), (sx * 1.0, 2.7, z), 0.04, dark, solid=False)
        k.beam((-1.0, 2.7, z), (1.0, 2.7, z), 0.04, dark, solid=False)
    for sx in (-1, 1):
        for z in (-2.4, -1.3, 2.1):
            if burned:
                k.tube([(sx * 1.0 - 0.12, r * 0.55, z), (sx * 1.0 + 0.12, r * 0.55, z)], [r * 0.55, r * 0.55], 10, dark)
            else:
                wheel(k, (sx * 1.0, r, z), r, axis=(1, 0, 0), width=0.26, m=RUBBER.but(sky=sky), solid=True)
    if burned:
        k.decal("soot_0", (0, 0.02, 1.0), (0, 1, 0), 6.5, 6.5, sky=sky)


def tank(k, sky=1.0, gun_pitch=0.9, turret_yaw=0.4, blown=False):
    paint = (RUST.but(tint=(0.2, 0.2, 0.2)) if blown else OLIVE.but(tint=(0.3, 0.37, 0.5))).but(sky=sky)
    worn = RUST.but(sky=sky, tint=(0.17, 0.19, 0.21))
    dark = IRON.but(sky=sky)
    for sx in (-1, 1):
        x0, x1 = sorted((sx * 1.45, sx * 0.95))
        outline = [(-2.95, 0.55), (-2.75, 0.12), (-2.2, 0.0), (2.0, 0.0), (2.75, 0.25), (3.0, 0.7), (2.7, 0.92), (-2.7, 0.92)]
        k.loft([[(x0, y, z) for z, y in outline], [(x1, y, z) for z, y in outline]], dark)
        k.face([(x0, y, z) for z, y in outline], dark, solid=False)
        k.face([(x1, y, z) for z, y in outline][::-1], dark, solid=False)
        for z in np.linspace(-2.1, 2.1, 5):
            k.tube([(sx * 1.455, 0.42, z), (sx * 1.5, 0.42, z)], [0.4, 0.36], 10, worn, solid=False)
            k.tube([(sx * 1.5, 0.42, z), (sx * 1.53, 0.42, z)], [0.13, 0.1], 6, dark, solid=False)
        k.tube([(sx * 1.455, 0.62, 2.62), (sx * 1.5, 0.62, 2.62)], [0.3, 0.27], 10, worn, solid=False)
        k.tube([(sx * 1.455, 0.55, -2.6), (sx * 1.5, 0.55, -2.6)], [0.34, 0.3], 10, worn, solid=False)
    def ring(z, y0, y1, w0=0.95, w1=0.95):
        return [(-w0, y0, z), (w0, y0, z), (w1, y1, z), (-w1, y1, z)]
    rings = [ring(-2.95, 0.75, 1.15, 0.95, 0.9), ring(-2.3, 0.45, 1.5, 0.95, 0.9), ring(1.1, 0.45, 1.55, 0.95, 0.86), ring(2.2, 0.45, 1.25, 0.95, 0.9), ring(3.0, 0.62, 0.9)]
    k.loft(rings, paint)
    k.face(rings[0][::-1], paint)
    k.face(rings[-1], paint)
    for sx in (-1, 1):
        x0, x1 = sorted((sx * 1.52, sx * 0.9))
        k.box((x0, 0.92, -2.9), (x1, 0.97, 2.75), paint)
        k.box((sx * 1.2 - 0.26, 0.97, -1.9), (sx * 1.2 + 0.26, 1.27, -0.9), paint, solid=False)
    k.tube([(-0.7, 1.72, -2.35), (0.7, 1.72, -2.35)], [0.26, 0.26], 10, worn, solid=False)
    k.box((-0.8, 1.5, -2.3), (0.8, 1.56, -1.0), dark, solid=False)
    k.tube([(-0.3, 1.1, 2.72), (-0.3, 1.1, 2.8)], [0.1, 0.09], 8, dark, solid=False)
    for i in range(4):
        k.box((0.2 + i * 0.17, 0.95, 2.74 - i * 0.0), (0.34 + i * 0.17, 1.2, 2.82), dark, solid=False)

    def turret():
        prof = [(0.0, 1.22, 1.18), (0.25, 1.26, 1.2), (0.55, 1.1, 1.1), (0.78, 0.8, 0.8)]
        rs = []
        for h, w, l in prof:
            rs.append([(math.cos(a) * w, h, math.sin(a) * l - 0.1 * (h > 0.3)) for a in np.linspace(0, 2 * math.pi, 14, endpoint=False)])
        k.loft(rs, paint)
        k.face(rs[-1], paint)
        k.tube([(0.3, 0.78, -0.35), (0.3, 0.92, -0.35)], [0.3, 0.28], 10, paint, solid=False)
        k.block((0.3, 1.15, -0.62), (0.56, 0.04, 0.56), paint, pitch=1.25, solid=False)
        k.box((-0.42, 0.18, 0.95), (0.42, 0.62, 1.42), paint)
    if blown:
        with k.at(3.6, 0.82, -1.0, yaw=1.1, roll=2.95):
            turret()
            k.tube([(0, 0.4, 1.3), (0, 0.52, 4.3)], [0.1, 0.075], 8, dark)
        k.tube([(0, 1.5, 0.2), (0, 1.56, 0.2)], [1.02, 1.02], 14, dark, solid=False)
        k.decal("soot_1", (0, 1.585, 0.2), (0, 1, 0), 3.0, 3.0, sky=sky)
        k.decal("soot_0", (0.96, 1.1, -0.6), (1, 0.1, 0), 2.6, 1.3, sky=sky)
    else:
        with k.at(0, 1.5, 0.2, yaw=turret_yaw):
            turret()
            d = v3(0, math.sin(gun_pitch), math.cos(gun_pitch))
            at = v3(0, 0.4, 1.2)
            k.tube([at, at + d * 3.2, at + d * 3.25, at + d * 3.6], [0.1, 0.078, 0.11, 0.1], 8, dark)
        k.decal("rust_run_0", (0.955, 1.1, 0.2), (1, 0.05, 0), 1.0, 0.9, sky=sky)
        k.decal("rust_run_1", (-0.955, 1.1, -1.0), (-1, 0.05, 0), 1.0, 0.9, sky=sky)
        k.decal("star", (0.9, 1.12, -1.75), (1, 0.06, 0), 0.6, 0.6, sky=sky, alpha=0.7)


def sandbag(k, at, yaw=0.0, m=None, sky=1.0, sag=0.0):
    m = (m or CANVAS.but(tint=(0.25, 0.23, 0.17))).but(sky=sky)
    with k.at(at[0], at[1], at[2], yaw=yaw):
        rs = []
        for z, w, h in ((-0.36, 0.1, 0.05), (-0.27, 0.17, 0.1), (0.0, 0.18, 0.105), (0.27, 0.17, 0.1), (0.36, 0.1, 0.05)):
            rs.append([(math.cos(a) * w, 0.1 + math.sin(a) * h - sag * (1 - abs(z) / 0.36) * 0.4, z) for a in np.linspace(0, 2 * math.pi, 7, endpoint=False)])
        k.loft(rs, m, solid=False)
        k.face(rs[0][::-1], m, solid=False)
        k.face(rs[-1], m, solid=False)


def sandbag_wall(k, a, b, layers=3, seed=0, sky=1.0):
    rng = np.random.default_rng(seed)
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    L = float(np.linalg.norm(b - a))
    d = (b - a) / max(L, 1e-6)
    yaw = math.atan2(d[0], d[1])
    y0 = k.ground((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    for layer in range(layers):
        n = max(int(L / 0.68) - (layer % 2), 1)
        off = 0.34 if layer % 2 else 0.0
        for i in range(n):
            if layer == layers - 1 and rng.random() < 0.3:
                continue
            p = a + d * (off + 0.35 + i * (L - 0.7 - off) / max(n - 1, 1))
            sandbag(k, (p[0] + rng.uniform(-0.03, 0.03), y0 + layer * 0.19, p[1] + rng.uniform(-0.03, 0.03)), yaw + rng.uniform(-0.12, 0.12), sky=sky)
    mid = (a + b) / 2
    k.unseen_block((mid[0], y0 + layers * 0.095, mid[1]), (0.36, layers * 0.19, L), yaw)


def field_gun(k, sky=1.0, pitch=1.05):
    m = OLIVE.but(sky=sky, tint=(0.3, 0.36, 0.48))
    dark = IRON.but(sky=sky)
    for a in (0.0, 1.5708):
        with k.at(0, 0, 0, yaw=a):
            k.box((-2.3, 0.0, -0.15), (2.3, 0.3, 0.15), m)
    k.tube([(0, 0.3, 0), (0, 1.2, 0)], [0.45, 0.35], 10, m)
    k.box((-0.6, 1.0, -0.5), (0.6, 1.9, 0.3), m)
    d = v3(0, math.sin(pitch), math.cos(pitch))
    base = v3(0, 1.6, 0.1)
    k.tube([base - d * 0.8, base + d * 1.0, base + d * 4.6], [0.16, 0.13, 0.07], 9, dark)
    k.box((-1.1, 0.9, 0.35), (1.1, 2.3, 0.4), m)
    for sx in (-1, 1):
        k.box((sx * 0.9 - 0.2, 0.9, -0.5), (sx * 0.9 + 0.2, 1.3, -0.1), CANVAS.but(sky=sky))


def shell_case(k, sky=1.0):
    k.tube([(0, 0.05, -0.3), (0, 0.05, 0.3)], [0.05, 0.05], 7, BRASS.but(sky=sky), solid=False)


def flatcar(k, sky=1.0, cradle=True, length=13.0):
    m = RUST.but(sky=sky)
    k.box((-1.4, 0.95, -length / 2), (1.4, 1.2, length / 2), DARK_BOARDS.but(sky=sky))
    k.box((-1.2, 0.75, -length / 2), (1.2, 0.95, length / 2), IRON.but(sky=sky))
    for z in (-length / 2 + 1.6, -length / 2 + 3.2, length / 2 - 3.2, length / 2 - 1.6):
        for sx in (-1, 1):
            k.tube([(sx * 0.72 - 0.06, 0.46, z), (sx * 0.72 + 0.06, 0.46, z)], [0.46, 0.46], 12, IRON.but(sky=sky))
    if cradle:
        for z in np.linspace(-length / 2 + 1.0, length / 2 - 1.0, 5):
            k.box((-1.3, 1.2, z - 0.12), (1.3, 1.45, z + 0.12), m)
            for sx in (-1, 1):
                k.beam((sx * 1.25, 1.45, z), (sx * 1.45, 2.9, z), 0.16, m)
            k.beam((-1.45, 2.9, z), (-0.5, 2.0, z), 0.1, m, solid=False)
            k.beam((1.45, 2.9, z), (0.5, 2.0, z), 0.1, m, solid=False)
        for sx in (-1, 1):
            k.beam((sx * 1.45, 2.9, -length / 2 + 1.0), (sx * 1.45, 2.9, length / 2 - 1.0), 0.12, m, solid=False)


def rails(k, a, b, sky=1.0, sleepers=True):
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    d = unit(b - a)
    side = unit(np.cross(UP, d))
    for s in (-0.72, 0.72):
        k.beam(a + side * s + UP * 0.2, b + side * s + UP * 0.2, 0.07, RUST.but(sky=sky), depth=0.13, solid=False)
    if sleepers:
        L = np.linalg.norm(b - a)
        n = int(L / 0.7)
        for i in range(n + 1):
            p = a + d * (L * i / max(n, 1))
            k.beam(p - side * 1.25 + UP * 0.07, p + side * 1.25 + UP * 0.07, 0.24, TIMBER.but(sky=sky), depth=0.14, solid=False)


def trolley(k, sky=0.06, tipped=False):
    m = P_ENAMEL(sky)
    if tipped:
        with k.at(0, 0.3, 0, roll=1.45):
            trolley(k, sky)
        return
    for y in (0.25, 0.8):
        k.box((-0.4, y, -0.25), (0.4, y + 0.02, 0.25), m, solid=False)
    for sx in (-1, 1):
        for sz in (-1, 1):
            k.tube([(sx * 0.38, 0.05, sz * 0.23), (sx * 0.38, 0.82, sz * 0.23)], [0.012, 0.012], 5, m, solid=False)
            k.tube([(sx * 0.38 - 0.02, 0.05, sz * 0.23), (sx * 0.38 + 0.02, 0.05, sz * 0.23)], [0.05, 0.05], 8, RUBBER.but(sky=sky), solid=False)


def P_ENAMEL(sky):
    return ENAMEL.but(sky=sky)


def basin(k, sky=0.06):
    k.tube([(0, 0.0, 0), (0, 0.09, 0)], [0.12, 0.19], 10, ENAMEL.but(sky=sky), solid=False, cap_start=True, cap_end=False)


def clamp_chair(k, sky=0.06):
    m = ENAMEL.but(sky=sky)
    pad = CANVAS.but(sky=sky, tint=(0.34, 0.2, 0.16))
    k.tube([(0, 0, 0), (0, 0.5, 0)], [0.28, 0.1], 10, IRON.but(sky=sky))
    k.box((-0.3, 0.5, -0.3), (0.3, 0.6, 0.35), pad)
    k.block((0, 1.05, -0.38), (0.6, 1.0, 0.1), pad, pitch=-0.25)
    k.block((0, 1.68, -0.5), (0.3, 0.22, 0.1), pad, pitch=-0.25, solid=False)
    k.block((0, 0.35, 0.6), (0.5, 0.06, 0.5), m, pitch=0.5, solid=False)
    for sx in (-1, 1):
        k.box((sx * 0.38 - 0.05, 0.78, -0.3), (sx * 0.38 + 0.05, 0.84, 0.3), m, solid=False)
        k.beam((sx * 0.38, 0.5, -0.2), (sx * 0.38, 0.8, -0.2), 0.04, m, solid=False)
        k.beam((sx * 0.38 - 0.05, 0.84, 0.2), (sx * 0.38 - 0.2, 1.02, 0.25), 0.03, IRON.but(sky=sky), solid=False)
        k.beam((sx * 0.38 + 0.05, 0.84, 0.2), (sx * 0.38 + 0.16, 1.05, 0.14), 0.03, IRON.but(sky=sky), solid=False)


def window_bars(k, a, T, w, h, sky=1.0, depth=0.2, bent=False, seed=0):
    rng = np.random.default_rng(seed)
    T = unit(T)
    N = np.cross(T, UP)
    a = np.asarray(a, dtype=np.float64) - N * depth
    n = max(int(w / 0.16), 2)
    for i in range(1, n):
        x = w * i / n
        p0, p1 = a + T * x, a + T * x + UP * h
        if bent and abs(i - n / 2) < 2.5:
            mid = (p0 + p1) * 0.5 + N * rng.uniform(0.25, 0.5) + T * (0.25 * (1 if i >= n / 2 else -1))
            k.tube([p0, mid, p1], [0.011, 0.011, 0.011], 4, IRON.but(sky=sky), solid=False, cap_start=False, cap_end=False)
        else:
            k.tube([p0, p1], [0.011, 0.011], 4, IRON.but(sky=sky), solid=False, cap_start=False, cap_end=False)


def cell_door(k, hinge, T, w=1.0, h=2.0, sky=0.06, burst=0.8, seed=0):
    rng = np.random.default_rng(seed)
    T = unit(T)
    N = np.cross(T, UP)
    d = unit(T * math.cos(burst) + N * math.sin(burst))
    c = np.asarray(hinge, dtype=np.float64) + d * (w / 2) + UP * (h / 2 - 0.08)
    k.block(c, (w, h, 0.06), RUST.but(sky=sky), yaw=math.atan2(-d[2], d[0]), roll=rng.uniform(0.05, 0.16), pitch=rng.uniform(-0.1, 0.1))


def lattice_mast(k, height=60.0, base=6.0, top=1.4, bay=4.0, m=RUST, leg=0.22, brace=0.1):
    levels = int(height / bay)
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]

    def at(level, c):
        y = level * bay
        w = (base + (top - base) * (y / height)) / 2
        return v3(c[0] * w, y, c[1] * w)
    for i in range(levels):
        for j, c in enumerate(corners):
            c2 = corners[(j + 1) % 4]
            k.beam(at(i, c), at(i + 1, c), leg, m, solid=(i < 2))
            k.beam(at(i + 1, c), at(i + 1, c2), brace, m, solid=False)
            if i % 2 == 0:
                k.beam(at(i, c), at(i + 1, c2), brace, m, solid=False)
            else:
                k.beam(at(i, c2), at(i + 1, c), brace, m, solid=False)
    for c in corners:
        p = at(0, c)
        k.box((p[0] - 0.7, -0.6, p[2] - 0.7), (p[0] + 0.7, 0.35, p[2] + 0.7), CONCRETE)
    w = top / 2 + 0.5
    k.box((-w, height, -w), (w, height + 0.12, w), m)
    return height


def ladder(k, a, b, m=RUST, width=0.45, sky=1.0):
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    d = unit(b - a)
    side = unit(np.cross(d, v3(0, 0, 1))) if abs(d[2]) < 0.9 else v3(1, 0, 0)
    for s in (-1, 1):
        k.beam(a + side * s * width / 2, b + side * s * width / 2, 0.045, m.but(sky=sky), solid=False)
    L = np.linalg.norm(b - a)
    n = int(L / 0.32)
    for i in range(1, n):
        p = a + d * (L * i / n)
        k.beam(p - side * width / 2, p + side * width / 2, 0.03, m.but(sky=sky), solid=False)


def dish(k, diameter=7.5, depth=1.3, m=RUST, back=IRON, segments=20, rings=5):
    R = diameter / 2
    rs = []
    for i in range(rings + 1):
        r = R * i / rings
        z = -depth * (1.0 - (r / R) ** 2)
        rs.append([(math.cos(a) * max(r, 0.05), math.sin(a) * max(r, 0.05), z) for a in np.linspace(0, 2 * math.pi, segments, endpoint=False)])
    k.loft(rs, m, inward=True)
    k.loft(rs, back)
    for a in np.linspace(0, 2 * math.pi, 8, endpoint=False):
        k.beam((math.cos(a) * R, math.sin(a) * R, 0.0), (math.cos(a) * 0.5, math.sin(a) * 0.5, -depth - 1.2), 0.07, back, solid=False)
    k.beam((0, 0, -depth), (0, 0, 1.6), 0.08, back, solid=False)
    k.box((-0.5, -0.04, 1.55), (0.5, 0.04, 1.63), back, solid=False)
