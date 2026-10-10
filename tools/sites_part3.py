import math

import numpy as np

import maplib
import props as P
from buildlib import Kit, Mat, UP, ruin_top, unit, v3
from sites_part2 import _fuselage_ring

S = maplib.read_sites()
HALF_PI = math.pi / 2


def ford():
    k = Kit("ford", S["FORD"])
    rng = np.random.default_rng(91)
    target = v3(70.0, 300.0, -230.0)

    def aim(x, z):
        d = target - v3(x, k.ground(x, z), z)
        return math.atan2(d[0], d[2]), math.atan2(d[1], math.hypot(d[0], d[2]))

    for (x, z, blown, seed) in ((-23.0, -10.0, False, 1), (9.0, 7.5, True, 2), (31.0, -13.0, False, 3)):
        yaw, pitch = aim(x, z)
        with k.at(x, k.ground(x, z) - 0.15, z, yaw=yaw + rng.uniform(-0.5, 0.5), roll=rng.uniform(-0.08, 0.08), pitch=rng.uniform(-0.06, 0.06)):
            P.tank(k, gun_pitch=min(pitch, 0.5), turret_yaw=rng.uniform(-0.3, 0.3), blown=blown)
        k.decal("soot_%d" % (seed % 2), (x, k.ground(x, z) + 0.05, z), (0, 1, 0), 9.0, 9.0)
    for n, (x, z) in enumerate(((-31.0, 21.0), (-12.0, -27.0), (21.0, 13.0))):
        yaw, pitch = aim(x, z)
        with k.at(x, k.ground(x, z), z, yaw=yaw):
            P.field_gun(k, pitch=pitch)
            for i in range(4):
                a0, a1 = math.pi * 0.72 + i * 0.42, math.pi * 0.72 + (i + 1) * 0.42
                P.sandbag_wall(k, (math.cos(a0) * 3.7, math.sin(a0) * 3.7 - 0.5), (math.cos(a1) * 3.7, math.sin(a1) * 3.7 - 0.5), layers=3 if i in (1, 2) else 2, seed=n * 7 + i)
            for i in range(9):
                with k.at(rng.uniform(-2.5, 2.5), 0.0, rng.uniform(-3.0, -0.6), yaw=rng.uniform(0, 3.1)):
                    P.shell_case(k)
            if n == 1:
                with k.at(2.4, 0.0, -1.6, yaw=0.3):
                    P.crate(k, 0.7, P.OLIVE, h=0.4)
                    k.decal("sheet_typed", (0.0, 0.41, 0.0), (0, 1, 0), 0.24, up=(0, 0, -1), turn=0.3)
                    k.mark("paper_army_order", (0.0, 0.5, 0.0))
    with k.at(-37.0, k.ground(-37.0, -5.0), -5.0, yaw=1.9, roll=0.05):
        P.truck(k, burned=True)
    tx, tz = -4.0, 24.0
    with k.at(tx, k.ground(tx, tz) - 1.2, tz, yaw=0.7, pitch=-1.25):
        zt = np.arange(0.0, 6.01, 0.5)

        def radius(z):
            return float(np.interp(z, [0.0, 2.0, 5.0, 8.0], [0.3, 0.7, 1.0, 1.15]))
        k.loft([_fuselage_ring(z, radius(z)) for z in zt], P.ALU)
        fin = [[(0.07, 0.8, 0.6), (0.07, 0.9, 4.6), (-0.07, 0.9, 4.6), (-0.07, 0.8, 0.6)],
               [(0.03, 4.0, 0.7), (0.03, 4.0, 2.4), (-0.03, 4.0, 2.4), (-0.03, 4.0, 0.7)]]
        k.loft(fin, P.ALU)
        k.decal("soot_0", (0.0, 1.0, 3.0), (0, 1, 0), 3.0, 3.0, up=(0, 0, 1))
    (fx, fz), d = (lambda p: ((p[0][0] - k.ox, p[0][1] - k.oz), p[1]))(maplib.track_at(maplib.track_nearest(*S["FORD"])[0]))
    side = (-d[1], d[0])
    for along in (-9.0, 9.0):
        for s in (-3.2, 3.2):
            x, z = fx + d[0] * along + side[0] * s, fz + d[1] * along + side[1] * s
            k.tube([(x, k.ground(x, z) - 0.4, z), (x + rng.uniform(-0.15, 0.15), k.ground(x, z) + 1.7, z)], [0.06, 0.05], 6, P.ENAMEL.but(tint=(0.5, 0.5, 0.46)))
    cx, cz = fx - d[0] * 16.0 + side[0] * 5.0, fz - d[1] * 16.0 + side[1] * 5.0
    with k.at(cx, k.ground(cx, cz), cz, yaw=math.atan2(d[0], d[1]) + 0.5):
        P.camera_tripod(k, fallen=True)
    k.mark("battle", (0.0, k.ground(0.0, 0.0) + 0.2, 0.0))
    k.mark("guns_aim", tuple(target))
    return k


def tunnel():
    k = Kit("tunnel", S["TUNNEL"])
    conc = P.CONCRETE
    dark = 0.05
    ins = P.PAINT_GREEN.indoors(dark)
    rng = np.random.default_rng(101)
    for z in (-3.5, 3.5):
        k.box((-6.4, -0.3, z - 0.3), (-5.8, 3.0, z + 0.3), conc)
    k.beam((-6.1, 1.1, -3.2), (-4.9, 1.0, 2.6), 0.12, P.ENAMEL.but(tint=(0.5, 0.2, 0.18)))
    with k.at(-6.9, 0.0, 5.6, yaw=-HALF_PI):
        P.signpost(k, "sign_halt", 1.5, 2.3, 1.3)
    k.decal("sign_danger", (-6.42, 1.9, -3.5), (-1, 0, 0), 1.0)
    P.fence(k, (-6.0, -4.0), (-6.0, -40.0), height=2.2, gap=4.0, broken=0.5, seed=102)
    P.fence(k, (-6.0, 4.0), (-6.0, 44.0), height=2.2, gap=4.0, broken=0.5, seed=103)
    k.mark("gate", (-8.0, 0.2, 0.0))

    ox0, ox1, oz0, oz1, oh = 18.0, 50.0, 6.0, 15.5, 3.2
    t = 0.4
    cz = 8.6
    rooms = [(18.0, 26.0), (26.0, 34.0), (34.0, 42.0), (42.0, 46.0), (46.0, 50.0)]
    south = [(x0 + (x1 - x0) / 2 - 0.6 - ox0, x0 + (x1 - x0) / 2 + 0.6 - ox0, 1.3, 2.3) for (x0, x1) in rooms[:3]]
    k.wall((ox0, oz1), (ox1, oz1), oh, t, conc, ins, south)
    for (u0, u1, v0, v1) in south:
        P.window_bars(k, v3(ox0 + u0, v0, oz1), v3(1, 0, 0), u1 - u0, v1 - v0)
    k.wall((ox1, oz0), (ox0, oz0), oh, t, conc, ins, [(3.0, 4.0, 1.5, 2.2), (12.0, 13.0, 1.5, 2.2), (21.0, 22.0, 1.5, 2.2)])
    k.wall((ox1, oz1), (ox1, oz0), oh, t, conc, ins)
    k.wall((ox0, oz0), (ox0, oz1), oh, t, conc, ins, [(0.7, 1.9, 0.0, 2.2)])
    k.floor((ox0 + t, oz0 + t), (ox1 - t, oz1 - t), 0.1, 0.4, conc.indoors(dark))
    k.floor((ox0 - 0.3, oz0 - 0.3), (ox1 + 0.3, oz1 + 0.3), oh + 0.25, 0.25, conc, conc.indoors(dark), holes=[(46.6, 49.4, 9.4, 14.6)])
    room_doors = [(x0 + 0.8 - ox0 - t, x0 + 1.8 - ox0 - t, 0.0, 2.05) for (x0, x1) in rooms]
    k.wall((ox0 + t, cz), (ox1 - t, cz), oh - 0.02, 0.22, ins, ins, room_doors)
    for (x0, x1) in rooms[1:]:
        k.wall((x0, cz + 0.22), (x0, oz1 - t), oh - 0.02, 0.2, ins, ins)
    P.door_leaf(k, v3(ox0 + 0.05, 0.1, oz0 + 0.7), v3(0, 0, 1), 1.18, 2.1, angle=2.2, m=P.RUST)
    k.mark("office_door", (ox0 - 1.5, 0.2, oz0 + 1.3))
    with k.at(22.5, 0.1, 13.6, yaw=math.pi):
        P.desk(k, 1.6, 0.8, dark)
        k.decal("sheet_typed", (0.3, 0.775, 0.0), (0, 1, 0), 0.24, up=(0, 0, -1), turn=-0.15, sky=dark)
        k.mark("paper_staff_memo", (0.3, 0.85, 0.0))
        k.mark("battery_office", (-0.45, 0.77, 0.1), yaw=0.8)
    with k.at(22.4, 0.1, 12.3, yaw=0.5):
        P.chair(k, P.DARK_BOARDS, dark, fallen=True)
    with k.at(19.2, 0.1, 12.5, yaw=HALF_PI):
        P.cupboard(k, 1.4, 2.0, 0.5, P.DARK_BOARDS, dark)
    for i in range(7):
        k.decal("sheet_%s" % ("typed", "blank", "hand")[i % 3], (20.0 + rng.uniform(0, 5), 0.115, 9.6 + rng.uniform(0, 4.5)), (0, 1, 0), 0.24, turn=rng.uniform(0, 6), sky=dark)
    with k.at(30.0, 0.1, 12.0):
        k.box((-0.3, 0.0, -0.3), (0.3, 1.0, 0.3), P.DARK_BOARDS.indoors(dark))
        k.box((-0.2, 1.0, -0.35), (0.2, 1.4, 0.3), P.IRON.indoors(dark))
        k.tube([(0, 1.2, 0.3), (0, 1.2, 0.5)], [0.07, 0.08], 10, P.IRON.indoors(dark), solid=False)
        for y in (1.5, 1.2):
            k.tube([(-0.26, y, -0.2), (-0.2, y, -0.2)], [0.16, 0.16], 12, P.IRON.indoors(dark), solid=False)
    k.box((26.4, 0.1, 14.2), (33.6, 2.0, 14.7), P.DARK_BOARDS.indoors(dark))
    for i in range(16):
        k.tube([(26.8 + i * 0.42, 0.9 + (i % 3) * 0.45, 14.15), (26.8 + i * 0.42, 0.9 + (i % 3) * 0.45, 14.2)], [0.16, 0.16], 10, P.IRON.indoors(dark).but(tint=(0.4, 0.4, 0.42)), solid=False)
    with k.at(32.6, 0.1, 10.2, yaw=-HALF_PI):
        P.table(k, 1.3, 0.7, sky=dark)
        k.decal("sheet_typed", (0.0, 0.765, 0.0), (0, 1, 0), 0.24, up=(0, 0, -1), turn=0.1, sky=dark)
        k.mark("paper_measuring_log", (0.0, 0.85, 0.0))
    k.box((26.3, 0.9, 9.4), (26.34, 2.5, 13.0), P.SHEET.indoors(dark), solid=False)
    with k.at(38.0, 0.1, 13.5, yaw=math.pi):
        P.desk(k, 1.7, 0.85, dark)
        k.box((0.45, 0.45, 0.3), (0.82, 0.6, 0.8), P.DARK_BOARDS.indoors(dark), solid=False)
        k.decal("sheet_hand", (0.63, 0.61, 0.6), (0, 1, 0), 0.22, up=(0, 0, -1), sky=dark)
        k.mark("paper_doctor", (0.63, 0.7, 0.6))
    with k.at(35.0, 0.1, 10.0, yaw=0.8):
        P.clamp_chair(k, dark)
    with k.at(40.8, 0.1, 9.6, yaw=-HALF_PI):
        P.locker(k, dark)
        k.mark("hide_office", (0, 0.2, 0))
    k.decal("ruler", (41.75, 1.6, 12.0), (-1, 0, 0), 0.3, 3.0, sky=dark)
    for n, (x0, x1) in enumerate(rooms[3:]):
        P.cell_door(k, v3(x0 + 0.8, 0.1, cz - 0.02), v3(1, 0, 0), sky=dark, burst=-0.9 - 0.3 * n, seed=5 + n)
        k.box((x0 + 0.5, 0.1, oz1 - t - 0.9), (x0 + 2.6, 0.45, oz1 - t - 0.15), P.IRON.indoors(dark))
    k.decal("tally", (44.0, 1.4, oz1 - t - 0.012), (0, 0, -1), 1.5, sky=dark)
    k.decal("hand_drag", (47.9, 2.0, oz1 - t - 0.012), (0, 0, -1), 1.3, sky=0.4)
    P.rubble_heap(k, 48.0, 12.0, 1.5, 0.5, 104, sky=0.5)
    k.decal("drag_long", (33.0, 0.115, 7.4), (0, 1, 0), 11.0, 1.2, sky=dark)
    k.decal("chalk_six", (ox0 + t + 0.012, 1.6, 7.3), (1, 0, 0), 0.9, sky=dark)

    hx0, hx1, hz0, hz1, hh = 58.0, 82.0, -46.0, -10.0, 18.5
    ht = 0.9
    hin = conc.but(sky=0.6)
    door_w = 10.0
    k.wall((hx0, hz1), (hx1, hz1), hh, ht, conc, hin, [((hx1 - hx0) / 2 - door_w / 2, (hx1 - hx0) / 2 + door_w / 2, 0.0, 14.0)],
           top=ruin_top(hx1 - hx0, hh, 105, low=0.9, step=1.6, rough=0.3))
    k.wall((hx1, hz0), (hx0, hz0), hh, ht, conc, hin, top=ruin_top(hx1 - hx0, hh, 106, low=0.88, step=1.6, rough=0.3))
    k.wall((hx1, hz1), (hx1, hz0), hh, ht, conc, hin, top=ruin_top(hz1 - hz0, hh, 107, low=0.86, step=1.6, rough=0.35))
    k.wall((hx0, hz0), (hx0, hz1), hh, ht, conc, hin, top=ruin_top(hz1 - hz0, hh, 108, low=0.9, step=1.6, rough=0.3))
    k.floor((hx0 + ht, hz0 + ht), (hx1 - ht, hz1 - ht), 0.08, 0.4, conc.but(sky=0.6, scale=6.0))
    for i in range(6):
        z = hz0 + 3.5 + i * 5.8
        k.beam((hx0 + 0.4, hh - 0.6, z), (hx0 + rng.uniform(2.5, 6.0), hh + rng.uniform(1.0, 4.0), z + rng.uniform(-0.8, 0.8)), 0.35, P.RUST, solid=False)
        k.beam((hx1 - 0.4, hh - 0.6, z), (hx1 - rng.uniform(2.5, 6.0), hh + rng.uniform(1.0, 4.0), z + rng.uniform(-0.8, 0.8)), 0.35, P.RUST, solid=False)
    k.decal("ruler_tall", (hx0 + 7.0, 9.0, hz0 + ht + 0.02), (0, 0, 1), 1.7, 18.0, sky=0.6)
    k.decal("ruler_tall", (hx1 - 7.0, 9.0, hz0 + ht + 0.02), (0, 0, 1), 1.7, 18.0, sky=0.6)
    k.decal("wall_nicht_auf", ((hx0 + hx1) / 2, 8.5, hz0 + ht + 0.02), (0, 0, 1), 9.0, sky=0.6)
    k.decal("hand_big", (hx1 - ht - 0.02, 12.5, -30.0), (-1, 0, 0), 4.2, sky=0.6)
    for (rx, rz) in ((64.0, -38.0), (76.0, -38.0), (64.0, -20.0), (76.0, -20.0)):
        k.box((rx - 1.0, 0.08, rz - 1.0), (rx + 1.0, 0.7, rz + 1.0), conc.but(sky=0.6))
        ring = [(rx + math.cos(a) * 0.9, 0.7 + abs(math.sin(a)) * 1.5, rz) for a in np.linspace(0, math.pi, 9)]
        k.tube(ring, [0.11] * 9, 7, P.IRON.but(sky=0.6), cap_start=False, cap_end=False)
        for j in range(4):
            k.tube([(rx + 0.6 + j * 0.55, 0.78, rz + 0.5 + j * 0.2), (rx + 1.05 + j * 0.55, 0.78, rz + 0.62 + j * 0.2)], [0.13, 0.13], 6, P.IRON.but(sky=0.6), solid=False)
    k.mark("hall_door", ((hx0 + hx1) / 2, 0.2, hz1 + 3.0))
    k.mark("hall_center", ((hx0 + hx1) / 2, 0.2, (hz0 + hz1) / 2))
    with k.at((hx0 + hx1) / 2 - 7.0, 0.0, hz1 + 9.0, yaw=math.pi - 0.65):
        P.camera_tripod(k)
        k.mark("camera", (0, 1.5, 0))

    gx0, gx1, gz0, gz1, gh = 106.0, 114.0, -36.0, 44.0, 5.6
    gbase = k.ground(110.0, 0.0)
    with k.at(0.0, gbase, 0.0):
        k.wall((gx1, gz1), (gx1, gz0), gh, 0.8, conc, conc.indoors(0.25))
        k.floor((gx0 - 0.6, gz0), (gx1 + 0.6, gz1), gh + 0.5, 0.5, conc, conc.indoors(0.25))
        k.floor((gx0 - 0.6, gz0), (gx1, gz1), 0.06, 0.4, conc.indoors(0.3))
        for z in np.arange(gz0 + 0.5, gz1, 6.0):
            k.box((gx0 - 0.4, 0.0, z - 0.4), (gx0 + 0.4, gh, z + 0.4), conc)
        P.rails(k, (110.0, 0.06, gz0 + 1.0), (110.0, 0.06, gz1 + 14.0), sky=0.3)
        with k.at(110.0, 0.06, 12.0):
            P.flatcar(k, sky=0.3)
        with k.at(110.0, 0.06, 50.0):
            P.flatcar(k, cradle=False)
        with k.at(gx1 - 1.3, 0.06, -8.0, yaw=-HALF_PI):
            P.locker(k, 0.25)
            k.mark("hide_gallery", (0, 0.2, 0))
        k.decal("stencil_31", (gx1 - 0.82, 2.6, 12.0), (-1, 0, 0), 2.2, sky=0.25)
        k.mark("gallery", (110.0, 0.3, 30.0))
        mz0, mz1 = gz0 - 12.0, gz0
        k.wall((gx0, mz0), (gx0, mz1), 11.0, 2.5, conc, conc.indoors(0.2), [(2.0, 10.0, 0.0, 9.0)])
        k.floor((gx0 - 2.5, mz0), (gx1 + 6.0, mz1), 11.4, 1.4, conc, conc.indoors(0.1))
        k.wall((gx0, mz1), (gx1 + 6.0, mz1), 11.0, 0.9, conc, conc.indoors(0.1))
        k.wall((gx1 + 6.0, mz0), (gx0, mz0), 11.0, 0.9, conc, conc.indoors(0.1))
        P.rubble_heap(k, gx0 + 4.5, (mz0 + mz1) / 2, 5.0, 5.5, 109, sky=0.15)
        P.rubble_heap(k, gx0 + 9.0, (mz0 + mz1) / 2 + 1.0, 4.5, 8.0, 110, sky=0.1)
        k.decal("stencil_B", (gx0 - 2.52, 9.9, (mz0 + mz1) / 2), (-1, 0, 0), 1.6)
        k.mark("mouth", (gx0 - 6.0, 0.3, (mz0 + mz1) / 2))
    bx, bz = 30.0, -52.0
    with k.at(bx, k.ground(bx, bz) + 1.6, bz, yaw=0.5, roll=1.05, pitch=0.12):
        k.block((0, 0, 0), (8.0, 0.7, 9.0), P.RUST)
        for i in range(4):
            k.tube([(-3.2 + i * 2.1, 0.36, -4.0), (-3.2 + i * 2.1, 0.36, 4.0)], [0.12, 0.12], 6, P.IRON, solid=False)
    k.decal("soot_0", (bx + 2.0, k.ground(bx + 2.0, bz) + 0.04, bz), (0, 1, 0), 10.0, 10.0)
    k.mark("blast_door", (bx - 6.0, k.ground(bx - 6.0, bz) + 0.2, bz))

    wx, wz = 44.0, 30.0
    with k.at(wx, 0.0, wz, yaw=0.4):
        k.box((-1.2, 0.0, -1.0), (1.2, 0.5, 1.0), conc)
        k.tube([(-0.9, 1.1, 0), (0.9, 1.1, 0)], [0.55, 0.55], 12, P.RUST)
        for sx in (-1, 1):
            k.box((sx * 1.0 - 0.08, 0.5, -0.5), (sx * 1.0 + 0.08, 1.7, 0.5), P.RUST)
        top = v3(26.0, 250.0, -14.0)
        k.tube([v3(0, 1.6, 0), top * 0.25, top * 0.6, top], [0.05, 0.05, 0.05, 0.05], 4, P.IRON, solid=False, cap_start=False, cap_end=False)
        for (hgt, name) in ((38.0, "mark_38"), (61.0, "mark_61"), (110.0, "mark_110"), (240.0, "mark_240")):
            p = top * (hgt / 250.0)
            k.block(p + v3(1.6, 0, 0), (3.2, 1.3, 0.06), P.ENAMEL.but(tint=(0.12, 0.12, 0.12)), solid=False)
            k.decal(name, p + v3(1.6, 0, 0.04), (0, 0, 1), 3.0)
            k.decal(name, p + v3(1.6, 0, -0.04), (0, 0, -1), 3.0)
    k.mark("winch", (wx - 3.0, 0.2, wz + 2.0))
    with k.at(8.0, 0.0, -14.0, yaw=-1.1):
        P.truck(k, burned=False)
    for i, (x, z) in enumerate(((12.0, 20.0), (13.2, 20.6), (12.4, 21.6), (52.0, 2.0), (53.0, 3.2), (16.0, -6.0))):
        with k.at(x, 0.0, z, yaw=rng.uniform(0, 3)):
            if i % 2:
                P.barrel(k, fallen=(i == 3))
            else:
                P.crate(k, rng.uniform(0.6, 1.0))
    k.mark("yard", (30.0, 0.2, 0.0))
    k.mark("reacher_home", (56.0, 0.2, 2.0))
    k.mark("chase_start", (40.0, 0.2, 7.3))
    return k


LOOKOUT_FLOOR = 12.0
CABIN = 2.3
DECK = 3.5


def lookout():
    k = Kit("lookout", S["LOOKOUT"])
    k.see_from = 0.0
    wood = P.TIMBER
    boards = P.BOARDS
    F = LOOKOUT_FLOOR
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]

    def leg(c, y):
        w = 3.9 - 0.7 * (y / F)
        return v3(c[0] * w, y, c[1] * w)
    for j, c in enumerate(corners):
        c2 = corners[(j + 1) % 4]
        k.beam(leg(c, -0.6), leg(c, F), 0.3, wood)
        for (y0, y1) in ((0.3, 4.0), (4.0, 8.0), (8.0, F - 0.3)):
            k.beam(leg(c, y0), leg(c2, y1), 0.14, wood, solid=False)
            k.beam(leg(c2, y0), leg(c, y1), 0.14, wood, solid=False)
            k.beam(leg(c, y1), leg(c2, y1), 0.16, wood, solid=False)
        p = leg(c, 0.0)
        k.box((p[0] - 0.5, -0.5, p[2] - 0.5), (p[0] + 0.5, 0.25, p[2] + 0.5), P.CONCRETE)
    pts = [(-2.9, -2.9), (2.9, -2.9), (2.9, 2.9), (-2.9, 2.9)]
    for i in range(4):
        a, b = pts[i], pts[(i + 1) % 4]
        d = (b[0] - a[0], b[1] - a[1])
        n = math.hypot(*d)
        d = (d[0] / n, d[1] / n)
        foot = v3(a[0] + d[0] * 0.6, i * 3.0, a[1] + d[1] * 0.6)
        k.stairs(foot, d, 3.0, n - 1.2, 1.05, boards, steps=17)
        side = v3(-d[1], 0, d[0])
        for s in (-1, 1):
            p0 = foot + side * (0.56 * s) + UP * 0.95
            p1 = foot + v3(d[0], 0, d[1]) * (n - 1.2) + side * (0.56 * s) + UP * 3.95
            k.beam(p0, p1, 0.06, wood, solid=False)
            k.beam(p0 - UP * 0.95, p0, 0.06, wood, solid=False)
            k.beam(p1 - UP * 0.95, p1, 0.06, wood, solid=False)
        if i < 3:
            k.box((b[0] - 0.62, (i + 1) * 3.0 - 0.1, b[1] - 0.62), (b[0] + 0.62, (i + 1) * 3.0, b[1] + 0.62), boards)
    k.floor((-DECK, -DECK), (DECK, DECK), F, 0.14, boards, wood, holes=[(-3.45, -2.35, -1.2, 2.2)])
    for j, c in enumerate(corners):
        c2 = corners[(j + 1) % 4]
        a, b = v3(c[0] * DECK, F, c[1] * DECK), v3(c2[0] * DECK, F, c2[1] * DECK)
        k.beam(a + UP * 1.0, b + UP * 1.0, 0.08, wood)
        k.beam(a + UP * 0.5, b + UP * 0.5, 0.06, wood, solid=False)
        for q in np.linspace(0, 1, 6):
            p = a + (b - a) * q
            k.beam(p, p + UP * 1.0, 0.07, wood, solid=False)
    for j, c in enumerate(corners):
        c2 = corners[(j + 1) % 4]
        a, b = v3(c[0] * DECK, F, c[1] * DECK), v3(c2[0] * DECK, F, c2[1] * DECK)
        k.unseen([a, b, b + UP * 1.4, a + UP * 1.4])
        k.unseen([a, b, b + UP * 1.4, a + UP * 1.4][::-1])
    ch = 2.35
    ins = P.BOARDS.but(sky=0.08, tint=(0.5, 0.46, 0.4))
    out = P.GREEN_BOARDS
    sides = [((-CABIN, CABIN), (CABIN, CABIN)), ((CABIN, CABIN), (CABIN, -CABIN)), ((CABIN, -CABIN), (-CABIN, -CABIN)), ((-CABIN, -CABIN), (-CABIN, CABIN))]
    for n, (a, b) in enumerate(sides):
        holes = [(0.35, 2 * CABIN - 0.35, 0.95, 2.05)]
        if n == 2:
            holes = [(0.35, 2.9, 0.95, 2.05), (3.3, 4.2, 0.0, 2.05)]
        k.wall(a, b, ch, 0.12, out, ins, holes, base=F)
        T = unit(v3(b[0] - a[0], 0, b[1] - a[1]))
        N = np.cross(T, UP)
        for (u0, u1, v0, v1) in holes:
            if v0 < 0.1:
                continue
            for u in np.arange(u0, u1 + 0.01, (u1 - u0) / round((u1 - u0) / 0.95)):
                p = v3(a[0], F + v0, a[1]) + T * u - N * 0.06
                k.beam(p, p + UP * (v1 - v0), 0.05, wood, solid=False)
            c = v3(a[0], F + (v0 + v1) / 2, a[1]) + T * ((u0 + u1) / 2)
            k.decal("glass", c - N * 0.05, N, u1 - u0, v1 - v0, alpha=0.8, tint=(1.0, 0.63, 0.3), glow=0.8)
            k.decal("glass", c - N * 0.07, -N, u1 - u0, v1 - v0, alpha=0.75, sky=0.08)
    k.floor((-CABIN, -CABIN), (CABIN, CABIN), F + 0.02, 0.05, P.FLOOR.but(sky=0.08))
    P.door_leaf(k, v3(-CABIN + 0.4, F, -CABIN + 0.02), v3(1, 0, 0), 0.88, 2.0, angle=-1.9, m=out)
    with k.at(1.55, F + 0.02, 1.5, yaw=math.pi):
        P.table(k, 1.2, 0.6, sky=0.08)
        with k.at(0.1, 0.76, 0.0):
            P.radio_set(k, 0.08, lit=True)
        k.mark("radio", (0.1, 0.95, 0.0), yaw=0.0)
        k.mark("battery_lookout", (-0.42, 0.76, 0.12), yaw=0.6)
    with k.at(0.0, F + 0.02, 0.0):
        k.tube([(0, 0, 0), (0, 0.95, 0)], [0.09, 0.09], 8, wood.but(sky=0.08))
        k.tube([(0, 0.95, 0), (0, 1.0, 0)], [0.55, 0.55], 16, P.BRASS.but(sky=0.08, tint=(0.4, 0.38, 0.3)))
        k.beam((-0.5, 1.03, 0), (0.5, 1.03, 0), 0.03, P.IRON.but(sky=0.08), solid=False)
        k.decal("sheet_hand", (0.22, 1.012, 0.2), (0, 1, 0), 0.26, up=(0, 0, -1), turn=0.5, sky=0.08, tint=(0.75, 0.6, 0.42))
        k.mark("paper_lookout_note", (0.22, 1.06, 0.2))
    k.box((-CABIN + 0.15, F + 0.02, 0.6), (-CABIN + 1.0, F + 0.5, CABIN - 0.15), P.DARK_BOARDS.but(sky=0.08))
    k.box((-CABIN + 0.15, F + 0.5, 0.6), (-CABIN + 1.0, F + 0.62, CABIN - 0.15), P.BLANKET.but(sky=0.08))
    with k.at(1.7, F + 0.02, -1.7):
        k.tube([(0, 0, 0), (0, 0.7, 0)], [0.26, 0.26], 10, P.IRON.but(sky=0.08))
        k.tube([(0, 0.7, 0), (0, 2.3, 0)], [0.07, 0.07], 8, P.IRON.but(sky=0.08), solid=False)
    rng = np.random.default_rng(121)
    for i in range(6):
        with k.at(-0.9 + (i % 3) * 0.75, F + 0.17, -1.6 + (i // 3) * 0.7, yaw=rng.uniform(-0.3, 0.3)):
            k.tube([(-0.3, 0, 0), (0.3, 0, 0)], [0.14, 0.14], 9, P.CANVAS.but(sky=0.08), solid=False)
    k.box((0.2, F + 0.02, -0.9), (0.31, F + 0.2, -0.62), P.IRON.but(sky=0.08, tint=(0.3, 0.22, 0.16)), solid=False)
    k.box((1.15, F + 0.8, 1.35), (1.27, F + 1.0, 1.47), P.GLOW_WARM, solid=False)
    k.glow((0.0, F + 1.7, 0.0), 17.0, (1.0, 0.62, 0.3), 2.6, name="cabin_lamp")
    k.mark("cabin", (0.0, F + 0.3, 0.0))
    k.mark("deck", (-2.9, F + 0.3, -2.9))
    k.mark("stair_foot", (-2.3, 0.3, -4.2))
    with k.at(7.5, k.ground(7.5, -4.0), -4.0, yaw=0.3):
        k.box((-1.2, 0.0, -0.8), (1.2, 1.5, 0.8), P.DARK_BOARDS, skip="z+")
        k.box((-1.35, 1.5, -0.95), (1.35, 1.58, 1.0), P.SHINGLE)
        for i in range(5):
            k.tube([(-1.0, 0.15 + (i // 3) * 0.24, -0.4 + (i % 3) * 0.3), (0.6, 0.15 + (i // 3) * 0.24, -0.4 + (i % 3) * 0.3)], [0.11, 0.11], 7, wood, solid=False)
    k.tube([(-7.0, k.ground(-7.0, 5.0) - 0.4, 5.0), (-7.0, k.ground(-7.0, 5.0) + 9.0, 5.0)], [0.07, 0.04], 6, P.ENAMEL)
    return k


def lookout_roof():
    k = Kit("lookout_roof", S["LOOKOUT"])
    k.see_from = 0.0
    F = LOOKOUT_FLOOR + 2.35
    r = CABIN + 0.75
    top = v3(0, F + 1.7, 0)
    c = [v3(-r, F, -r), v3(r, F, -r), v3(r, F, r), v3(-r, F, r)]
    for i in range(4):
        a, b = c[i], c[(i + 1) % 4]
        k.face([b, a, top], P.SHINGLE)
        k.face([a, b, top], P.DARK_BOARDS.but(sky=0.08))
    k.face([c[0], c[1], c[2], c[3]], P.DARK_BOARDS.but(sky=0.08))
    k.tube([top, top + UP * 2.6], [0.03, 0.015], 5, P.IRON, solid=False)
    return k
