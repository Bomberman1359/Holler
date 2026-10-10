#!/usr/bin/env python3
# usage: python3 tools/make_sites.py [place ...]
import json
import math
import os
import sys

import numpy as np

import maplib
import props as P
from buildlib import Kit, Mat, UP, ruin_top, unit, v3

S = maplib.read_sites()
HALF_PI = math.pi / 2


def track_local(k, meters):
    p, d = maplib.track_at(meters)
    return (p[0] - k.ox, p[1] - k.oz), d


def spawn():
    k = Kit("spawn", S["SPAWN"])
    (tx, tz), d = track_local(k, 6.0)
    heading = math.atan2(d[0], d[1])
    with k.at(tx - 2.6, k.ground(tx - 2.6, tz + 1.0), tz + 1.0, yaw=heading + 0.35):
        P.jeep(k)
        k.mark("jeep", (0, 1.0, 0))
    with k.at(tx - 4.3, k.ground(tx - 4.3, tz - 0.6), tz - 0.6, yaw=1.0):
        P.crate(k, 0.6, P.OLIVE)
    (bx, bz), d2 = track_local(k, 21.0)
    side = (-d2[1], d2[0])
    gy = k.ground(bx, bz)
    a = v3(bx - side[0] * 3.4, gy, bz - side[1] * 3.4)
    b = v3(bx + side[0] * 3.4, gy, bz + side[1] * 3.4)
    for p in (a, b):
        k.box((p[0] - 0.09, p[1] - 0.3, p[2] - 0.09), (p[0] + 0.09, p[1] + 1.15, p[2] + 0.09), P.DARK_BOARDS)
    k.beam(a + UP * 1.05, b + UP * 0.45 + v3(0, 0, 0), 0.1, P.ENAMEL.but(tint=(0.5, 0.2, 0.18)))
    with k.at(a[0] - side[0] * 1.6, k.ground(a[0] - side[0] * 1.6, a[2] - side[1] * 1.6), a[2] - side[1] * 1.6, yaw=math.atan2(-d2[0], -d2[1]) + 0.15):
        P.signpost(k, "sign_halt", 1.5, 2.3, 1.3, lean=0.06)
        k.mark("sign_halt", (0, 1.6, 0.3))
    (sx, sz), d3 = track_local(k, 34.0)
    side3 = (-d3[1], d3[0])
    with k.at(sx + side3[0] * 3.0, k.ground(sx + side3[0] * 3.0, sz + side3[1] * 3.0), sz + side3[1] * 3.0, yaw=math.atan2(-d3[0], -d3[1]) - 0.5):
        P.signpost(k, "sign_lookout", 1.5, 2.0, 0.42, posts=1, lean=-0.08)
    for m in (12.0, 48.0):
        (px, pz), dd = track_local(k, m)
        sd = (-dd[1], dd[0])
        with k.at(px - sd[0] * 4.5, k.ground(px - sd[0] * 4.5, pz - sd[1] * 4.5), pz - sd[1] * 4.5, yaw=math.atan2(dd[0], dd[1])):
            P.pole(k)
    k.mark("start", (tx + 0.6, k.ground(tx + 0.6, tz + 4.2) + 0.5, tz + 4.2), yaw=math.atan2(-d[0], -d[1]) + 0.3)
    return k


def gasthaus():
    k = Kit("gasthaus", S["GASTHAUS"])
    street = 3.0
    w, d = 15.0, 9.5
    with k.at(street - 5.5 - d, 0.0, w / 2, yaw=HALF_PI):
        P.house(k, w, d, floors=2, storey=2.75, wall=P.OCHRE, door="open", seed=11, sign="sign_gasthaus", inside=P.PAINT.indoors(0.05))
        sky = 0.05
        k.decal("notice", (w / 2 + 1.25, 1.55, d + 0.012), (0, 0, 1), 0.42)
        k.mark("paper_notice", (w / 2 + 1.25, 1.55, d + 0.3), yaw=math.pi)
        k.box((0.9, 0.12, 2.0), (1.5, 1.2, 7.2), P.DARK_BOARDS.indoors(sky))
        k.box((0.8, 1.2, 1.9), (1.6, 1.26, 7.3), P.DARK_BOARDS.indoors(sky))
        k.box((0.42, 0.12, 2.0), (0.62, 2.1, 7.2), P.DARK_BOARDS.indoors(sky))
        for i in range(9):
            k.tube([(0.74, 1.5, 2.3 + i * 0.55), (0.74, 1.78, 2.3 + i * 0.55)], [0.04, 0.02], 6, P.BRASS.indoors(sky).but(tint=(0.2, 0.3, 0.2)), solid=False)
        k.mark("battery_bar", (1.2, 1.26, 3.4), yaw=0.5)
        with k.at(w - 1.2, 0.12, 4.7, yaw=-HALF_PI):
            P.stove(k, sky)
        spots = [(4.6, 3.1, 0.05), (4.4, 6.7, -0.08), (9.6, 6.9, 0.1), (10.8, 3.3, 1.57)]
        rng = np.random.default_rng(5)
        for (x, z, yaw) in spots:
            with k.at(x, 0.12, z, yaw=yaw):
                P.table(k, 1.7, 0.85, sky=sky)
                for sx in (-0.45, 0.45):
                    for sz in (-0.22, 0.22):
                        with k.at(sx, 0.76, sz, yaw=rng.uniform(-0.3, 0.3)):
                            P.place_setting(k, sky)
                with k.at(0, 0, -0.75):
                    P.bench(k, 1.6, sky=sky)
                if rng.random() < 0.6:
                    with k.at(0, 0, 0.75):
                        P.bench(k, 1.6, sky=sky)
                else:
                    with k.at(0.5, 0, 1.0, yaw=rng.uniform(0, 3)):
                        P.chair(k, sky=sky, fallen=True)
                    with k.at(-0.5, 0, 0.8, yaw=math.pi + 0.2):
                        P.chair(k, sky=sky)
        with k.at(13.4, 0.12, 8.6, yaw=math.pi):
            P.cupboard(k, sky=sky)
        with k.at(5.63, 0.12, 1.9, yaw=math.pi):
            P.camera_tripod(k, sky)
            k.mark("camera", (0, 1.5, 0))
            k.mark("camera_view", (0, 1.5, 6.0))
        with k.at(6.6, 0.12, 1.2, yaw=0.4):
            P.tripod_trunk(k, sky)
        k.mark("inn_door", (w / 2, 0.2, d + 1.0))
        k.mark("inn_room", (w / 2, 0.2, d / 2))
        k.mark("watcher_spot", (5.63, 0.0, -38.0))
    plan = [
        (8.5, -24.0, -13.5, 7.5, "east", 2, "gable", 0.0, P.PLASTER, "shut", 21),
        (8.5, -7.0, 5.5, 8.0, "east", 1, "none", 0.55, P.PINK, "open", 22),
        (9.5, 12.0, 21.5, 7.0, "east", 1, "holes", 0.0, P.BOARDS, "shut", 23),
        (-2.5, -30.0, -19.0, 8.0, "west", 1, "none", 0.85, P.GREY_PLASTER, "none", 24),
        (-2.5, 15.5, 26.0, 7.5, "west", 2, "holes", 0.0, P.PLASTER, "shut", 25),
        (8.5, 30.0, 40.5, 7.5, "east", 1, "none", 0.3, P.OCHRE, "open", 26),
        (-3.5, 33.0, 42.0, 7.0, "west", 1, "gable", 0.0, P.BOARDS, "shut", 27),
        (8.5, -44.0, -33.0, 7.5, "east", 1, "gable", 0.0, P.PINK, "shut", 28),
    ]
    for (front, z0, z1, depth, side, floors, roof, ruin, wall, door, seed) in plan:
        width = z1 - z0
        if side == "east":
            ctx = k.at(front + depth, 0.0, z0, yaw=-HALF_PI)
        else:
            ctx = k.at(front - depth, 0.0, z1, yaw=HALF_PI)
        with ctx:
            P.house(k, width, depth, floors=floors, wall=wall, roof=roof, ruin=ruin, door=door, seed=seed)
    with k.at(14.0, 0.0, -10.0):
        pass
    with k.at(-1.0, 0.0, -13.5):
        P.well(k)
    with k.at(5.5, 0.0, 9.5, yaw=0.5):
        P.cart(k)
    P.fence(k, (9.0, 6.5), (9.0, 11.5), seed=3)
    P.fence(k, (-3.0, 27.0), (-3.0, 32.5), seed=4, broken=0.5)
    P.fence(k, (9.0, 22.0), (9.0, 29.5), seed=5, broken=0.4)
    for z in (-36.0, -6.0, 24.0, 52.0):
        with k.at(7.2, 0.0, z):
            P.pole(k)
    k.decal("leaves", (3.0, 0.02, 2.0), (0, 1, 0), 3.5, 3.5)
    k.decal("leaves", (2.0, 0.02, -9.0), (0, 1, 0), 3.5, 3.5, turn=1.0)
    k.mark("street_south", (street, 0.2, 48.0))
    k.mark("street_north", (street, 0.2, -40.0))
    return k


def church():
    k = Kit("church", S["CHURCH"])
    stone = P.STONE
    inner = P.PLASTER.but(sky=0.55, tint=(0.46, 0.45, 0.42))
    H, t = 7.5, 0.8
    x0, x1, z0, z1 = 2.0, 22.0, -4.6, 4.6
    tall = [(u - 0.55, u + 0.55, 2.2, 5.8) for u in (3.0, 7.7, 12.3, 17.0)]
    k.wall((x0, z1), (x1, z1), H, t, stone, inner, tall, top=ruin_top(x1 - x0, H, 31, low=0.86, step=0.7, rough=0.35), edge=P.STONE)
    k.wall((x1, z0), (x0, z0), H, t, stone, inner, tall, top=ruin_top(x1 - x0, H, 32, low=0.84, step=0.7, rough=0.35), edge=P.STONE)
    k.wall((x1, z1), (x1, z0), H + 2.0, t, stone, inner, [((z1 - z0) / 2 - 1.0, (z1 - z0) / 2 + 1.0, 2.4, 6.6)],
           top=ruin_top(z1 - z0, H + 2.0, 33, low=0.8, step=0.6, rough=0.5), edge=P.STONE)
    k.wall((x0, z0), (x0, -2.5), H, t, stone, inner, top=ruin_top(2.1, H, 34, low=0.85, rough=0.3), edge=P.STONE)
    k.wall((x0, 2.5), (x0, z1), H, t, stone, inner, top=ruin_top(2.1, H, 35, low=0.85, rough=0.3), edge=P.STONE)
    k.floor((x0 - 0.2, z0 + t), (x1 - t, z1 - t), 0.1, 0.4, P.STONE.but(sky=0.6, scale=4.0, tint=(0.42, 0.42, 0.42)))
    rng = np.random.default_rng(36)
    for i in range(9):
        x = x0 + 1.2 + i * 2.2
        if rng.random() < 0.6:
            side = 1 if rng.random() < 0.5 else -1
            zb = z1 - 0.4 if side > 0 else z0 + 0.4
            k.beam((x, H - 0.3, zb), (x + rng.uniform(-0.4, 0.4), H + rng.uniform(0.6, 2.4), zb - side * rng.uniform(0.8, 2.6)), 0.16, P.TIMBER, solid=False)
    tw, th, tt = 5.0, 15.0, 0.9
    ax0, ax1, az0, az1 = -3.0, 2.0, -2.5, 2.5
    belfry = [(tw / 2 - 0.6, tw / 2 + 0.6, 10.6, 13.2)]
    k.wall((ax0, az0), (ax0, az1), th, tt, stone, inner.but(sky=0.2), [(tw / 2 - 0.85, tw / 2 + 0.85, 0.0, 2.7)] + belfry,
           top=ruin_top(tw, th, 37, low=0.82, rough=0.5), edge=P.STONE)
    k.wall((ax0, az1), (ax1, az1), th, tt, stone, inner.but(sky=0.2), belfry, top=ruin_top(tw, th, 38, low=0.8, rough=0.5), edge=P.STONE)
    k.wall((ax1, az0), (ax0, az0), th, tt, stone, inner.but(sky=0.2), belfry, top=ruin_top(tw, th, 39, low=0.8, rough=0.5), edge=P.STONE)
    k.wall((ax1, az1), (ax1, az0), th, tt, stone, inner.but(sky=0.2), [(tw / 2 - 1.2, tw / 2 + 1.2, 0.0, 3.6)] + belfry,
           top=ruin_top(tw, th, 40, low=0.85, rough=0.4), edge=P.STONE)
    k.floor((ax0 + tt, az0 + tt), (ax1 - tt + 0.9, az1 - tt), 0.1, 0.4, P.STONE.but(sky=0.2, scale=4.0, tint=(0.42, 0.42, 0.42)))
    k.box((ax0 - 1.2, -0.2, -1.4), (ax0, 0.1, 1.4), stone)
    P.door_leaf(k, v3(ax0 + 0.2, 0.1, -0.85), v3(0, 0, 1), 0.85, 2.6, angle=2.1)
    k.decal("chalk_look_up", (ax0 + tt + 0.02, 1.7, 1.45), (1, 0, 0), 1.3, sky=0.2)
    for row in range(7):
        for side in (-1, 1):
            x = x0 + 3.2 + row * 1.5
            z = side * 2.3
            if rng.random() < 0.25:
                with k.at(x + rng.uniform(-0.6, 0.6), 0.5, z + rng.uniform(-0.4, 0.4), yaw=-HALF_PI + rng.uniform(-0.9, 0.9), roll=1.4):
                    P.bench(k, 2.6, sky=0.55, back=True)
            else:
                with k.at(x, 0.1, z, yaw=-HALF_PI + rng.uniform(-0.06, 0.06)):
                    P.bench(k, 2.6, sky=0.55, back=True)
    k.box((x1 - 3.4, 0.1, -1.3), (x1 - 2.4, 1.15, 1.3), stone.but(sky=0.55))
    k.box((x1 - 3.5, 1.15, -1.45), (x1 - 2.3, 1.19, 1.45), P.SHEET.but(sky=0.55))
    k.beam((x1 - 1.0, 1.5, 3.2), (x1 - 1.0, 4.6, 3.2), 0.16, P.TIMBER.but(sky=0.55), solid=False)
    k.beam((x1 - 1.0, 3.7, 2.4), (x1 - 1.0, 3.7, 4.0), 0.16, P.TIMBER.but(sky=0.55), solid=False)
    k.decal("sheet_hand", (x1 - 2.9, 1.2, 0.5), (0, 1, 0), 0.24, up=(-1, 0, 0), turn=0.3, sky=0.55)
    k.mark("paper_journal1", (x1 - 2.9, 1.25, 0.5))
    k.mark("battery_altar", (x1 - 2.85, 1.19, -0.7), yaw=1.1)
    with k.at(8.5, 0.1, z0 + t + 0.42, yaw=0.0):
        P.locker(k, sky=0.3, m=P.DARK_BOARDS)
        k.mark("hide", (0, 0.2, 0.0), yaw=0.0)
    k.decal("hand_big", (14.0, 5.1, z1 - t - 0.02), (0, 0, -1), 2.4, sky=0.55)
    k.decal("hand_drag", (9.5, 4.2, z0 + t + 0.02), (0, 0, 1), 2.2, sky=0.55)
    k.decal("smear_0", (12.0, 0.12, 0.6), (0, 1, 0), 5.0, 1.6, up=(1, 0, 0), sky=0.55)
    k.decal("pool_1", (15.2, 0.12, 0.3), (0, 1, 0), 1.6, sky=0.55)
    with k.at(6.0, 0.1, 0.4, yaw=HALF_PI):
        P.camera_tripod(k, 0.55)
        k.mark("camera", (0, 1.5, 0))
    with k.at(-4.6, 0.0, 4.2, roll=1.2):
        k.tube([(0, 0, 0), (0, 0.5, 0), (0, 0.95, 0), (0, 1.15, 0)], [0.75, 0.6, 0.42, 0.18], 14, P.BRASS.but(tint=(0.32, 0.34, 0.26)), cap_start=False)
    yard = [(-4.0, 6.5), (26.0, 6.5), (26.0, 22.0), (-4.0, 22.0)]
    for i in range(4):
        a, b = yard[i], yard[(i + 1) % 4]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        gate = [(L / 2 - 1.0, L / 2 + 1.0, 0.0, 3.0)] if i == 0 else []
        k.wall(a, b, 1.0, 0.45, stone, stone, gate, top=ruin_top(L, 1.0, 41 + i, low=0.5, step=1.2, rough=0.8), base=-0.2)
    for i in range(11):
        x, z = rng.uniform(-1.5, 24.0), rng.uniform(9.0, 20.0)
        with k.at(x, k.ground(x, z), z, yaw=rng.uniform(-0.3, 0.3), roll=rng.uniform(-0.25, 0.25), pitch=rng.uniform(-0.2, 0.2)):
            if rng.random() < 0.5:
                k.box((-0.05, -0.2, -0.04), (0.05, 1.2, 0.04), P.IRON)
                k.box((-0.32, 0.75, -0.035), (0.32, 0.85, 0.035), P.IRON, solid=False)
            else:
                k.box((-0.3, -0.2, -0.07), (0.3, 0.85, 0.07), stone)
    k.mark("door", (ax0 - 2.0, 0.2, 0.0))
    k.mark("nave", (10.0, 0.2, 0.0))
    k.mark("reacher_home", (17.0, 0.2, -1.0))
    return k


def church_roof():
    k = Kit("church_roof", S["CHURCH_ROOF"], yaw=0.5)
    w, d, rise = 21.0, 10.2, 5.2
    P.gable_roof(k, -w / 2, w / 2, -d / 2, d / 2, 0.35, rise, over=0.5, thick=0.16)
    for sx in (-1, 1):
        x = sx * w / 2
        pts = [v3(x, 0.35, -d / 2), v3(x, 0.35, d / 2), v3(x, 0.35 + rise - 0.1, 0.0)]
        k.face(pts if sx > 0 else pts[::-1], P.BOARDS)
        k.face(pts[::-1] if sx > 0 else pts, P.DARK_BOARDS.indoors(0.2))
    rng = np.random.default_rng(51)
    for i in range(14):
        x = -w / 2 + 0.8 + i * 1.5
        for sz in (-1, 1):
            k.beam((x, 0.6, sz * (d / 2 - 0.2)), (x + rng.uniform(-0.2, 0.2), -0.1, sz * (d / 2 + rng.uniform(0.1, 0.8))), 0.15, P.TIMBER, solid=False)
    k.box((-0.7, rise + 0.2, -0.7), (0.7, rise + 2.2, 0.7), P.DARK_BOARDS)
    k.tube([(0, rise + 2.2, 0), (0, rise + 4.4, 0)], [1.0, 0.03], 4, P.SHINGLE)
    k.beam((0, rise + 4.3, 0), (0, rise + 5.3, 0), 0.06, P.IRON, solid=False)
    k.beam((-0.3, rise + 5.0, 0), (0.3, rise + 5.0, 0), 0.06, P.IRON, solid=False)
    k.mark("roof", (0, 1.0, d / 2 + 4.0))
    return k


import sites_part2
import sites_part3

def prop_battery():
    k = Kit("prop_battery", (0.0, 0.0), base=0.0)
    k.box((-0.08, 0.0, -0.045), (0.08, 0.12, 0.045), P.OLIVE.but(tint=(0.5, 0.42, 0.2)), solid=False)
    k.box((-0.082, 0.03, -0.047), (0.082, 0.085, 0.047), P.ENAMEL.but(tint=(0.42, 0.4, 0.33)), solid=False, skip="y+ y-")
    for x in (-0.045, 0.045):
        k.tube([(x, 0.12, 0.0), (x, 0.15, 0.0)], [0.012, 0.012], 6, P.BRASS, solid=False)
    return k


SITES = {"prop_battery": prop_battery, "spawn": spawn, "gasthaus": gasthaus, "church": church, "church_roof": church_roof,
         "bomber": sites_part2.bomber, "sanatorium": sites_part2.sanatorium, "radar": sites_part2.radar,
         "ford": sites_part3.ford, "tunnel": sites_part3.tunnel, "lookout": sites_part3.lookout, "lookout_roof": sites_part3.lookout_roof}


def main():
    want = sys.argv[1:] or list(SITES)
    out = maplib.out_dir("sites")
    for name in want:
        info = SITES[name]().write()
        print("%-12s %6d triangles, %d marks, %d lamps" % (name, info["triangles"], len(info["marks"]), len(info["glows"])))
    with open(os.path.join(out, "index.json"), "w") as f:
        json.dump(sorted(n[:-5] for n in os.listdir(out) if n.endswith(".json") and n != "index.json" and not n.startswith("prop_")), f)
    keep_out(out)


def keep_out(out, margin=3):
    from scipy import ndimage
    size = int(maplib.SIZE)
    mask = np.zeros((size, size), dtype=bool)
    for n in sorted(os.listdir(out)):
        if n.endswith("_foot.npy") and not n.startswith("prop_"):
            cells = np.load(os.path.join(out, n))
            cells = cells[(cells[:, 0] >= 0) & (cells[:, 0] < size) & (cells[:, 1] >= 0) & (cells[:, 1] < size)]
            mask[cells[:, 1], cells[:, 0]] = True
    yy, xx = np.mgrid[-margin:margin + 1, -margin:margin + 1]
    mask = ndimage.binary_dilation(mask, structure=(xx * xx + yy * yy) <= margin * margin)
    np.save(os.path.join(out, "keepout.npy"), np.packbits(mask, axis=1))
    print("no trees on %d square meters" % int(mask.sum()))


if __name__ == "__main__":
    main()
