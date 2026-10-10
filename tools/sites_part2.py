import math

import numpy as np

import maplib
import props as P
from buildlib import Kit, Mat, UP, ruin_top, terrain_height, unit, v3

S = maplib.read_sites()
HALF_PI = math.pi / 2


def _fuselage_ring(z, r, dent=0.0, n=14, flat=0.0):
    pts = []
    for i in range(n):
        a = i / n * 2 * math.pi
        x, y = math.sin(a) * r, math.cos(a) * r
        if y > 0:
            y *= 1.0 - dent * (0.45 + 0.55 * math.cos(a) ** 2)
        else:
            y *= 1.0 - flat
        pts.append((x, y, z))
    return pts


def bomber():
    k = Kit("bomber", S["BOMBER"])
    skin = P.ALU
    inside = P.ALU.but(sky=0.12, tint=(0.32, 0.36, 0.30))
    dark = dict(sky=0.12)
    (tx, tz), (nx, nz) = maplib.BOMBER_TAIL, maplib.BOMBER_NOSE
    tail_at = v3(tx, k.ground(tx, tz) + maplib.BOMBER_LIFT, tz)
    nose_at = v3(nx, k.ground(nx, nz) + maplib.BOMBER_LIFT, nz)
    axis = unit(nose_at - tail_at)
    yaw = math.atan2(axis[0], axis[2])
    pitch = -math.asin(axis[1])
    floor = -0.8
    with k.at(tail_at[0], tail_at[1], tail_at[2], yaw=yaw, pitch=pitch):
        def radius(z):
            return float(np.interp(z, [0.0, 2.0, 5.0, 8.0, 16.5, 19.5, 22.5], [0.3, 0.7, 1.0, 1.15, 1.15, 1.0, 0.55]))

        def dent(z):
            return max(0.0, *(0.56 * math.exp(-((z - c) / 1.0) ** 2) for c in maplib.BOMBER_DENTS))

        zs = np.arange(7.6, 17.01, 0.4)
        outer = [_fuselage_ring(z, radius(z), dent(z)) for z in zs]
        inner = [_fuselage_ring(z, radius(z) - 0.07, dent(z) * 1.04) for z in zs]
        k.loft(outer, skin)
        k.loft(inner, inside, inward=True)
        for ring_o, ring_i, front in ((outer[0], inner[0], False), (outer[-1], inner[-1], True)):
            for i in range(len(ring_o)):
                j = (i + 1) % len(ring_o)
                quad = [ring_o[i], ring_o[j], ring_i[j], ring_i[i]]
                k.face(quad if front else quad[::-1], P.IRON.but(sky=0.3), solid=False)
        k.box((-0.7, floor - 0.06, 7.6), (0.7, floor, 17.0), P.BOARDS.but(**dark))
        for z in np.arange(8.2, 17.0, 1.2):
            r = radius(z) - 0.08
            ring = _fuselage_ring(z, r, dent(z) * 1.04, n=10)
            for i in range(10):
                if ring[i][1] > floor or ring[(i + 1) % 10][1] > floor:
                    k.beam(ring[i], ring[(i + 1) % 10], 0.07, P.IRON.but(**dark), solid=False)
        k.box((0.5, -0.24, 10.8), (1.0, -0.2, 11.7), P.DARK_BOARDS.but(**dark), solid=False)
        k.box((0.52, floor, 10.84), (0.58, -0.24, 10.9), P.IRON.but(**dark), solid=False)
        k.box((0.52, floor, 11.6), (0.58, -0.24, 11.66), P.IRON.but(**dark), solid=False)
        with k.at(0.82, -0.2, 11.38, yaw=-HALF_PI):
            P.radio_set(k, sky=0.12)
        k.decal("sheet_typed", (0.68, -0.195, 11.02), (0, 1, 0), 0.24, up=(0, 0, 1), turn=0.2, sky=0.12)
        k.mark("paper_flightlog", (0.68, -0.19, 11.02))
        k.mark("battery_bomber", (0.78, -0.2, 11.62), yaw=0.2)
        with k.at(-0.5, floor, 15.9, yaw=0.3):
            P.crate(k, 0.4, P.OLIVE.but(tint=(0.36, 0.38, 0.34)), 0.12, h=0.25)
        for z, x in ((14.4, -0.62), (9.6, 0.62)):
            k.tube([(x, floor + 0.16, z), (x, floor + 0.16, z + 0.7)], [0.11, 0.11], 8, P.ENAMEL.but(sky=0.12, tint=(0.26, 0.23, 0.1)), solid=False)
        k.decal("smear_1", (0.0, floor + 0.004, 13.4), (0, 1, 0), 1.1, up=(0, 0, 1), sky=0.12)
        k.decal("hand_drag", (-0.98, -0.15, 9.3), (1, 0.15, 0), 0.5, up=(0, 1, 0), sky=0.12)
        k.mark("crawl_in", (0, floor, 18.4), eye=0.95)
        k.mark("crawl_out", (0, floor, 6.6), math.pi, eye=0.95)
        k.mark("inside", (0, floor, 16.2), eye=0.95)
        k.mark("under_dent", (0, floor, 12.0), eye=0.95)
        def on_ground(x, z, lift):
            w = k.world((x, 0.0, z))
            need = terrain_height(w[0], w[2]) - k.oy + lift
            return v3(x, (need - k._p((x, 0.0, z))[1]) / k._R[1, 1], z)

        root = v3(-1.0, -0.2, 13.4)
        stations = [0.0, 0.3, 0.55, 0.8, 1.0]
        line = [root] + [on_ground(-1.0 - 13.5 * t, 13.4 - 1.4 * t, 0.75 - 0.6 * t) for t in stations[1:]]
        rings = []
        for p, tt in zip(line, stations):
            c, th = 5.4 - 3.0 * tt, 0.55 - 0.35 * tt
            rings.append([(p[0], p[1] + th / 2, p[2] + c * 0.35), (p[0], p[1] + th * 0.3, p[2] - c * 0.65), (p[0], p[1] - th * 0.3, p[2] - c * 0.65),
                          (p[0], p[1] - th / 2, p[2] + c * 0.35), (p[0], p[1], p[2] + c * 0.42)])
        k.loft(rings, skin)
        k.face(rings[-1][::-1], skin, solid=False)
        for t in (0.28, 0.6):
            p = on_ground(-1.0 - 13.5 * t, 13.4 - 1.4 * t + 1.4, 0.45 - 0.3 * t)
            k.tube([p + v3(0, 0, -1.6), p, p + v3(0, 0, 1.3), p + v3(0, 0, 1.7)], [0.45, 0.66, 0.62, 0.3], 12, skin)
            for a in (0.4, 2.5, 4.6):
                d = v3(math.cos(a), math.sin(a), 0.25 if a < 1 else -0.35)
                k.beam(p + v3(0, 0, 1.6), p + v3(0, 0, 1.6) + unit(d) * 1.7, 0.2, P.IRON, depth=0.04, solid=False)
        star = on_ground(-8.0, 12.2, 0.75 - 0.6 * 0.52 + 0.14)
        k.decal("star", star, (0.0, 1, 0), 2.2, 2.2, up=(0, 0, 1))
        k.loft([[(1.0, -0.1, 15.0), (1.0, -0.2, 11.5), (1.0, -0.55, 11.5), (1.0, -0.6, 15.0)],
                [(2.6, -0.15, 14.6), (2.3, -0.3, 12.0), (2.4, -0.5, 12.1), (2.7, -0.55, 14.5)]], skin)
        with k.at(0.5, -0.25, -0.9, yaw=0.16, roll=0.2):
            zt = np.arange(0.0, 7.01, 0.5)
            k.loft([_fuselage_ring(z, radius(z), dent(z - 0.9)) for z in zt], skin)
            k.loft([_fuselage_ring(z, radius(z) - 0.07, dent(z - 0.9)) for z in zt], inside, inward=True)
            k.tube([(0, 0, 0.0), (0, 0, -0.5)], [0.3, 0.05], 8, skin)
            fin = [[(0.07, 0.8, 0.6), (0.07, 0.9, 4.6), (-0.07, 0.9, 4.6), (-0.07, 0.8, 0.6)],
                   [(0.03, 4.0, 0.7), (0.03, 4.0, 2.4), (-0.03, 4.0, 2.4), (-0.03, 4.0, 0.7)]]
            k.loft(fin, skin)
            k.decal("stencil_31", (0.085, 2.2, 2.2), (1, 0, 0.02), 1.5, up=(0, 1, 0))
            for sx in (-1, 1):
                tp = [[(sx * 0.4, 0.45, 0.8), (sx * 0.4, 0.5, 3.6), (sx * 0.4, 0.38, 3.6), (sx * 0.4, 0.35, 0.8)],
                      [(sx * 4.6, 0.75, 1.3), (sx * 4.6, 0.75, 2.9), (sx * 4.6, 0.7, 2.9), (sx * 4.6, 0.7, 1.3)]]
                k.loft(tp, skin)
        with k.at(0.9, -0.35, 18.9, yaw=-0.75, pitch=0.3):
            zn = np.arange(0.0, 4.21, 0.42)
            k.loft([_fuselage_ring(z, radius(18.3 + z), max(dent(18.3 + z), 0.25 if z > 2.5 else 0.0), flat=0.3) for z in zn], skin)
            k.loft([_fuselage_ring(z, radius(18.3 + z) - 0.07, max(dent(18.3 + z), 0.25 if z > 2.5 else 0.0), flat=0.3) for z in zn], inside, inward=True)
            k.tube([(0, 0, 4.2), (0, -0.1, 4.9)], [0.52, 0.12], 10, P.IRON)
            k.decal("soot_0", (0.0, 1.02, 2.0), (0, 1, 0), 2.6, 2.6, up=(0, 0, 1))
        k.decal("soot_1", (0.0, radius(12.0) * 0.55, 16.0), (0.5, 1, 0), 2.4, 2.4, up=(0, 0, 1))
    wx, wz = -44.0, -3.0
    with k.at(wx, k.ground(wx, wz) + 0.4, wz, yaw=1.2, roll=0.12):
        rings = [[(0, 0.3, 1.8), (0, 0.2, -3.6), (0, -0.2, -3.6), (0, -0.3, 1.8), (0, 0.0, 2.2)],
                 [(13.0, 0.1, 0.9), (13.0, 0.06, -1.5), (13.0, -0.06, -1.5), (13.0, -0.1, 0.9), (13.0, 0.0, 1.1)]]
        k.loft(rings, skin)
        k.tube([(4.0, -0.3, -0.5), (4.0, -0.3, 1.2), (4.0, -0.3, 2.6)], [0.5, 0.66, 0.4], 12, skin)
        k.decal("star", (8.0, 0.25, -0.6), (0, 1, 0), 2.2, 2.2, up=(0, 0, 1))
    (cx, cz) = (15.5, 9.5)
    with k.at(cx, k.ground(cx, cz), cz, yaw=-1.98):
        P.camera_tripod(k)
        k.mark("camera", (0, 1.5, 0))
    with k.at(13.2, k.ground(13.2, -2.0), -2.0, yaw=-HALF_PI - 0.2):
        P.signpost(k, "sign_halt", 1.5, 2.2, 1.3, lean=-0.1)
    k.mark("dents_view", (14.0, k.ground(14.0, 15.0), 15.0))
    k.mark("tail_view", (-27.0, k.ground(-27.0, -9.0), -9.0))
    return k


def sanatorium():
    site = S["SANATORIUM"]
    m_near, _ = maplib.track_nearest(*site)
    (px, pz), dr = maplib.track_at(m_near)
    k = Kit("sanatorium", site, yaw=math.atan2(-dr[0], -dr[1]))
    tx, tz = k.local(px, pz)
    front = tx - 13.0
    L, D = 46.0, 12.0
    g_h, u_h = 3.4, 3.9
    H = g_h + u_h
    t = 0.45
    out = P.GREY_PLASTER
    dark = 0.05
    with k.at(front - D, 0.0, 20.0, yaw=HALF_PI):
        def openings(count, v0, v1, w, x_from=1.6, x_to=L - 1.0, skip=()):
            out_ = []
            for i in range(count):
                u = x_from + (x_to - x_from) * (i + 0.5) / count
                if any(abs(u - s) < 1.3 for s in skip):
                    continue
                out_.append((u - w / 2, u + w / 2, v0, v1))
            return out_
        door_u = 8.0
        low_f = openings(14, 1.2, 2.7, 1.0, skip=(door_u,))
        high_f = openings(14, g_h + 1.0, g_h + 3.0, 1.1)
        fall = [(0.0, H), (33.0, H), (34.2, H - 1.2), (35.5, g_h + 2.0), (37.0, g_h + 2.6), (38.2, g_h + 0.9), (40.0, g_h - 0.2),
                (42.0, 2.2), (44.0, 2.6), (45.2, 1.1)]
        k.wall((0, D), (L, D), H, t, out, P.PAINT_GREEN.indoors(dark), low_f + high_f + [(door_u - 0.75, door_u + 0.75, 0.0, 2.5)], top=fall, edge=P.BRICK)
        back_fall = [(0.0, 1.4), (1.6, 0.8), (3.5, 2.3), (5.0, g_h + 0.4), (6.5, g_h + 1.8), (9.0, g_h + 2.2), (11.0, H - 0.6), (13.0, H)]
        low_b = [(L - u1, L - u0, v0, v1) for (u0, u1, v0, v1) in openings(14, 1.5, 2.6, 0.9)]
        high_b = [(L - u1, L - u0, v0, v1) for (u0, u1, v0, v1) in openings(14, g_h + 1.0, g_h + 3.0, 1.1)]
        k.wall((L, 0), (0, 0), H, t, out, P.PAINT_GREEN.indoors(dark), low_b + high_b, top=back_fall, edge=P.BRICK)
        k.wall((0, 0), (0, D), H + 3.6, t, out, P.PAINT_GREEN.indoors(dark), [(D / 2 - 0.55, D / 2 + 0.55, g_h + 1.0, g_h + 3.0)],
               top=lambda u: H - 0.14 + 3.6 * (1.0 - abs(2.0 * u / D - 1.0)))
        for n, (u0, u1, v0, v1) in enumerate(low_f):
            P.window_frame(k, v3(u0, v0, D), v3(1, 0, 0), u1 - u0, v1 - v0)
            P.window_bars(k, v3(u0, v0, D), v3(1, 0, 0), u1 - u0, v1 - v0, bent=(n in (5, 9)), seed=n)
        for (u0, u1, v0, v1) in high_f:
            if u1 < 34:
                P.window_frame(k, v3(u0, v0, D), v3(1, 0, 0), u1 - u0, v1 - v0)
        P.gable_roof(k, 0.0, 33.5, 0.0, D, H, 3.6, holes_front=[(20.0, 24.0, 1.0, 4.5), (29.5, 34.5, 0.0, 7.5)],
                     holes_back=[(3.0, 8.0, 0.5, 6.5), (17.0, 19.5, 2.0, 5.0)])
        P.chimney(k, 12.0, D / 2 + 1.0, H + 2.4, 2.4)
        floor_g = P.TILE.indoors(dark).but(tint=(0.42, 0.42, 0.4))
        k.floor((t, t), (L - 0.3, D - t), 0.12, 0.3, floor_g)
        wall_g = P.TILE.indoors(dark)
        cz = 9.0
        doors = [(1.0, 2.2, 0.0, 2.2)] + [(x + 1.6, x + 2.6, 0.0, 2.05) for x in (6.0, 10.5, 15.0, 19.5)] + [(27.0, 28.4, 0.0, 2.3)]
        k.wall((t, cz), (40.0, cz), g_h - 0.25, 0.22, P.PAINT_GREEN.indoors(dark), wall_g, [(u0 - t, u1 - t, v0, v1) for (u0, u1, v0, v1) in doors])
        for x in (6.0, 10.5, 15.0, 19.5, 24.0, 34.0):
            k.wall((x, t), (x, cz), g_h - 0.25, 0.2, wall_g, wall_g)
        for n, (x, ceil) in enumerate(((6.0, 2.0), (10.5, 2.8))):
            k.floor((x + 0.2, t), (x + 4.5, cz), ceil + 0.1, 0.1, P.PAINT.indoors(dark), P.PAINT.indoors(dark))
        for n, x in enumerate((6.0, 10.5, 15.0, 19.5)):
            P.cell_door(k, v3(x + 1.6, 0.12, cz + 0.22), v3(1, 0, 0), sky=dark, burst=0.5 + 0.35 * n, seed=n)
            k.box((x + 0.5, 0.12, t + 0.2), (x + 2.4, 0.5, t + 1.0), P.IRON.indoors(dark))
            k.decal("stencil_%s" % ("7", "12", "B", "31")[n], (x + 3.3, 1.5, cz + 0.225), (0, 0, 1), 0.45, sky=dark)
        k.decal("tally", (12.6, 1.3, t + 0.012), (0, 0, 1), 1.6, sky=dark)
        k.decal("wall_hoert_alles", (12.7, 1.95, t + 0.012), (0, 0, 1), 2.4, sky=dark)
        k.mark("cell_scratch", (12.7, 1.5, t + 1.0))
        k.decal("hand_drag", (21.5, 2.0, t + 0.012), (0, 0, 1), 1.5, sky=dark)
        k.decal("pool_0", (17.0, 0.135, 4.0), (0, 1, 0), 1.7, sky=dark)
        with k.at(29.0, 0.12, 4.2, yaw=0.5):
            P.clamp_chair(k, dark)
        with k.at(26.2, 0.12, 6.5, yaw=0.3):
            P.trolley(k, dark, tipped=True)
        with k.at(31.5, 0.12, 2.0):
            P.trolley(k, dark)
            with k.at(0, 0.82, 0):
                P.basin(k, dark)
            k.mark("battery_treatment", (0.1, 0.27, 0.0), yaw=0.3)
        with k.at(25.2, 0.12, 1.0):
            P.cupboard(k, 1.4, 2.0, 0.5, P.ENAMEL, dark)
        k.decal("spatter_0", (29.6, 0.135, 5.6), (0, 1, 0), 2.2, sky=dark)
        k.decal("smear_1", (30.5, 0.135, 8.0), (0, 1, 0), 4.5, 1.4, up=(1, 0, 0), turn=0.4, sky=dark)
        with k.at(23.0, 0.12, D - t - 0.35, yaw=math.pi):
            P.locker(k, dark)
            k.mark("hide_ground", (0, 0.2, 0))
        k.decal("drag_long", (16.0, 0.135, 10.3), (0, 1, 0), 9.0, 1.3, up=(0, 0, 1), turn=HALF_PI, sky=dark)
        k.decal("chalk_dont_run", (door_u + 2.2, 1.7, D - t - 0.012), (0, 0, -1), 1.5, sky=dark)
        P.rubble_heap(k, 40.0, 5.5, 5.0, 1.9, 71, sky=0.6)
        P.rubble_heap(k, 44.5, 9.0, 3.2, 1.2, 72, sky=0.8)
        k.stairs((1.0, 0.12, 6.5), (1, 0), g_h - 0.12, 4.6, 1.9, P.CONCRETE.indoors(dark))
        ward_floor = P.FLOOR.indoors(0.09).but(turn=True)
        k.floor((t, t), (39.0, D - t), g_h, 0.25, ward_floor, P.PAINT.indoors(dark),
                holes=[(1.0, 5.6, 5.5, 7.5), (20.0, 23.4, 1.6, 7.0)])
        wsky = 0.09
        rng = np.random.default_rng(77)
        x = 7.5
        for n, length in enumerate((2.0, 2.0, 2.0, 2.4, 3.0)):
            for side in (0, 1):
                z = (t + length / 2 + 0.15) if side == 0 else (D - t - length / 2 - 0.15)
                if side == 1 and n == 0:
                    continue
                with k.at(x, g_h, z, yaw=0.0 if side == 0 else math.pi):
                    P.bed(k, length, 0.9 + 0.12 * (length - 2.0), wsky, made=(rng.random() < 0.4), seed=n * 2 + side)
            x += 2.3 + 0.2 * n
        for (bx, length, wd) in ((24.6, 5.0, 1.5), (31.0, 6.5, 1.9)):
            with k.at(bx, g_h, t + wd / 2 + 0.2, yaw=HALF_PI):
                P.bed(k, length, wd, wsky, made=False, seed=int(bx))
        with k.at(33.0, g_h, D - t - 1.4, yaw=HALF_PI):
            P.bed(k, 9.0, 2.4, wsky, made=False, mattress=True, seed=9)
        k.mark("paper_journal2", (9.9, g_h + 0.7, 2.0))
        k.decal("sheet_hand", (9.9, g_h + 0.69, 2.0), (0, 1, 0), 0.24, up=(1, 0, 0), turn=0.4, sky=wsky)
        for (wx, wy, ww) in ((8.6, g_h + 1.35, 0.9), (16.4, g_h + 2.0, 1.7), (25.0, g_h + 2.9, 3.0)):
            k.decal("wall_noch_da", (wx, wy, t + 0.012), (0, 0, 1), ww, sky=wsky)
        k.decal("wall_noch_da", (30.0, H - 0.02, 6.0), (0, -1, 0), 6.5, up=(0, 0, -1), sky=wsky)
        k.floor((t, t), (33.5, D - t), H + 0.02, 0.12, P.PAINT.indoors(wsky), P.PAINT.indoors(wsky),
                holes=[(20.5, 24.0, 6.0, 11.0), (29.5, 33.5, 5.5, 11.6), (3.0, 8.0, 0.4, 6.0)])
        with k.at(6.4, g_h, D - t - 0.35, yaw=math.pi):
            P.locker(k, wsky, P.ENAMEL)
            k.mark("hide_ward_south", (0, 0.2, 0))
        with k.at(27.8, g_h, D - t - 0.35, yaw=math.pi):
            P.locker(k, wsky, P.ENAMEL)
            k.mark("hide_ward_north", (0, 0.2, 0))
        with k.at(19.0, g_h, 8.6, yaw=-HALF_PI):
            P.camera_tripod(k, wsky)
            k.mark("camera", (0, 1.5, 0))
        k.decal("sheet_bloody", (37.2, g_h + 0.012, 4.2), (0, 1, 0), 0.24, up=(1, 0, 0), turn=-0.5, sky=0.5)
        k.mark("paper_journal3", (37.2, g_h + 0.2, 4.2))
        k.decal("hand_big", (38.4, g_h + 1.6, D - t - 0.012), (0, 0, -1), 2.0, sky=0.5)
        k.decal("smear_2", (36.5, g_h + 0.012, 7.0), (0, 1, 0), 5.0, 1.6, up=(1, 0, 0), sky=0.5)
        for bx in (12.0, 22.0):
            with k.at(bx, g_h, 6.0, yaw=rng.uniform(0, 3)):
                P.trolley(k, wsky, tipped=(bx > 15))
        for z in np.arange(1.5, 11.0, 1.6):
            k.beam((38.2, g_h - 0.12, z), (40.6 + rng.uniform(-0.6, 1.2), g_h - 0.3 - rng.uniform(0.0, 0.6), z + rng.uniform(-0.3, 0.3)),
                   0.18, P.TIMBER.but(sky=0.6), solid=False)
        k.mark("entrance", (door_u, 0.2, D + 2.0))
        k.mark("corridor", (door_u, 0.2, 10.3))
        k.mark("stairs_foot", (0.9, 0.2, 10.3))
        k.mark("ward_south", (6.5, g_h + 0.2, 6.5))
        k.mark("ward_north", (36.5, g_h + 0.2, 6.0))
        k.mark("last_room_view", (39.0, g_h + 1.6, 6.0))
        k.mark("reacher_home", (30.0, 0.2, 10.3))
        k.mark("reacher_ward", (34.0, g_h + 0.2, 6.0))
        k.box((door_u - 1.3, -0.2, D), (door_u + 1.3, 0.12, D + 1.4), P.CONCRETE)
        P.door_leaf(k, v3(door_u - 0.75, 0.12, D - 0.1), v3(1, 0, 0), 0.72, 2.35, angle=1.9, m=P.GREEN_BOARDS)
        k.box((door_u + 1.2, 1.5, D + 0.01), (door_u + 3.0, 2.2, D + 0.04), P.ENAMEL, solid=False)
        k.decal("sign_lazarett", (door_u + 2.1, 1.85, D + 0.045), (0, 0, 1), 1.7)
    return k


def radar():
    k = Kit("radar", S["RADAR"])
    with k.at(-13.0, k.ground(-13.0, -9.0), -9.0, yaw=0.3):
        P.lattice_mast(k, 60.0)
        P.ladder(k, (0.9, 0.3, 3.0), (0.25, 60.0, 0.7), P.RUST)
        k.box((-0.25, 60.1, -0.25), (0.25, 60.5, 0.25), P.GLOW_RED, solid=False)
        k.glow((0, 60.6, 0), 34.0, (1.0, 0.1, 0.06), 2.2, name="mast_lamp")
        k.mark("mast_top", (0, 60.0, 0))
        k.mark("mast_foot", (0, 0.5, 4.5))
    with k.at(-12.0, k.ground(-12.0, 12.0), 12.0, yaw=2.2):
        k.tube([(0, -0.4, 0), (0, 0.5, 0)], [2.6, 2.6], 16, P.CONCRETE)
        k.box((-1.6, 0.5, -1.2), (1.6, 2.9, 1.2), P.RUST)
        k.beam((-1.2, 2.9, 0.2), (-1.2, 5.6, 0.9), 0.3, P.RUST)
        k.beam((1.2, 2.9, 0.2), (1.2, 5.6, 0.9), 0.3, P.RUST)
        with k.at(0, 5.6, 1.6, pitch=-0.55):
            P.dish(k, 7.5)
        k.decal("sign_danger", (0, 1.9, 1.215), (0, 0, 1), 1.0)
    hx, hz = -1.5, 4.5
    with k.at(hx - 3.0, k.ground(hx, hz), hz + 2.5, yaw=HALF_PI):
        w, d, h = 5.0, 6.0, 2.6
        ins = P.PAINT.indoors(0.05)
        k.wall((0, d), (w, d), h, 0.3, P.CONCRETE, ins, [(w / 2 - 0.5, w / 2 + 0.5, 0.0, 2.1)])
        k.wall((w, 0), (0, 0), h, 0.3, P.CONCRETE, ins, [(1.6, 2.6, 1.1, 1.9)])
        k.wall((w, d), (w, 0), h, 0.3, P.CONCRETE, ins, [(2.2, 3.4, 1.1, 1.9)])
        k.wall((0, 0), (0, d), h, 0.3, P.CONCRETE, ins)
        k.floor((0.3, 0.3), (w - 0.3, d - 0.3), 0.1, 0.4, P.CONCRETE.indoors(0.05))
        k.floor((-0.25, -0.25), (w + 0.25, d + 0.25), h + 0.22, 0.22, P.CONCRETE, P.CONCRETE.indoors(0.05))
        P.door_leaf(k, v3(w / 2 - 0.5, 0.1, d - 0.05), v3(1, 0, 0), 0.98, 2.0, angle=2.0, m=P.RUST)
        with k.at(1.0, 0.1, 0.9):
            P.desk(k, 1.4, 0.7, 0.05)
            with k.at(-0.2, 0.77, 0.0):
                P.radio_set(k, 0.05)
            k.decal("sheet_typed", (0.45, 0.775, 0.1), (0, 1, 0), 0.22, up=(0, 0, -1), turn=0.2, sky=0.05)
            k.mark("paper_survey_note", (0.45, 0.85, 0.1))
            k.mark("battery_hut", (0.3, 0.77, -0.2), yaw=-0.4)
        with k.at(w - 0.65, 0.1, 1.0, yaw=-HALF_PI):
            P.locker(k, 0.05)
            k.mark("hide", (0, 0.2, 0))
        with k.at(1.0, 0.1, 4.6, yaw=0.4):
            P.chair(k, P.DARK_BOARDS, 0.05, fallen=True)
        k.decal("chalk_radio", (0.31, 1.6, 3.4), (1, 0, 0), 1.4, sky=0.05)
        k.mark("hut_door", (w / 2, 0.2, d + 1.2))
        k.mark("hut", (w / 2, 0.2, d / 2))
    with k.at(4.5, k.ground(4.5, -1.0), -1.0, yaw=-2.0):
        P.camera_tripod(k)
        k.mark("camera", (0, 1.5, 0))
    post = [(-26, -22), (8, -22), (8, 22), (-26, 22)]
    for i in range(4):
        P.fence(k, post[i], post[(i + 1) % 4], height=1.8, gap=3.4, broken=0.7, seed=80 + i)
    k.mark("knee_view", (2.0, k.ground(2.0, 10.0) + 0.2, 10.0))
    return k
