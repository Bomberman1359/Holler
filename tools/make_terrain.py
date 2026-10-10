#!/usr/bin/env python3
import json
import os
import struct

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

import maplib
from maplib import CELL, HALF, N, SIZE, catmull, fbm, grid, out_dir, polyline_distance, read_sites, sample, smoothstep

SEED = 1947
TREE_CELL = 16.0
OUT = out_dir("terrain")
S = read_sites()
rng = np.random.default_rng(SEED)

RIVER = [(-330, -1408), (-320, -1150), (-300, -900), (-235, -560), (-165, -312), (-128, -100), (-60, 150),
         (18, 400), (42, 640), (5, 900), (-55, 1150), (-90, 1408)]

PADS = [
    (S["GASTHAUS"], 80.0, 140.0),
    (S["CHURCH"], 30.0, 70.0),
    (S["SANATORIUM"], 42.0, 85.0),
    (S["RADAR"], 28.0, 60.0),
    ((S["TUNNEL"][0] + 45.0, S["TUNNEL"][1] + 5.0), 82.0, 118.0),
    (S["LOOKOUT"], 16.0, 48.0),
    (S["SPAWN"], 18.0, 55.0),
    (S["CHURCH_ROOF"], 14.0, 30.0),
]


def dist_to(x, z, p):
    return np.hypot(x - p[0], z - p[1])


def build_heights(x, z):
    shape = x.shape
    river = catmull(RIVER, 4.0)
    order = np.argsort(river[:, 1])
    cx = np.interp(z, river[order, 1], river[order, 0]).astype(np.float32)
    d = x - cx
    west = smoothstep(80.0, 1000.0, -d) * 120.0
    east = smoothstep(80.0, 900.0, d) * 110.0
    base = 8.0 + (HALF - z) * 0.012
    rise = west + east
    rough = np.clip(rise / 90.0, 0.08, 1.0)
    h = base + rise
    h += fbm(shape, 260, 4, 0.5, SEED + 1, ridged=True) * 34.0 * rough
    h += fbm(shape, 70, 4, 0.5, SEED + 2) * 9.0 * rough
    h += fbm(shape, 18, 3, 0.5, SEED + 3) * 1.7 * (0.3 + 0.7 * rough)
    h += 70.0 * np.exp(-dist_to(x, z, S["LOOKOUT"]) ** 2 / (2.0 * 230.0 ** 2))
    h += 32.0 * np.exp(-dist_to(x, z, S["RADAR"]) ** 2 / (2.0 * 110.0 ** 2))
    tx, tz = S["TUNNEL"]
    wobble = fbm(shape, 40, 3, 0.5, SEED + 6)
    wx = tx + 132.0 + 16.0 * np.sin(z * 0.03) + wobble * 22.0
    wall = smoothstep(wx, wx + 30.0, x) * np.exp(-((z - tz) ** 2) / (2.0 * 150.0 ** 2)) * (1.0 - smoothstep(tx + 330.0, tx + 520.0, x))
    h += 62.0 * wall * (0.8 + 0.3 * wobble)
    edge = HALF - np.maximum(np.abs(x), np.abs(z))
    rim = 1.0 - smoothstep(25.0, 190.0 + 70.0 * fbm(shape, 130, 3, 0.5, SEED + 7), edge)
    h += rim * 105.0

    pad_heights = []
    for center, r_in, r_out in PADS:
        dd = dist_to(x, z, center)
        target = float(h[dd < r_in * 0.7].mean())
        pad_heights.append(target)
        w = 1.0 - smoothstep(r_in, r_out, dd)
        h = h * (1.0 - w) + target * w

    track = catmull(S["TRACK"], 3.0)
    th = sample(h, track[:, 0], track[:, 1])
    th = ndimage.gaussian_filter1d(th, 9.0, mode="nearest")
    tdist, talong = polyline_distance(x, z, track, 40.0)
    step_len = np.linalg.norm(np.diff(track, axis=0), axis=1)
    seg = np.concatenate([[0.0], np.cumsum(step_len)])
    for _ in range(3):
        for i in range(1, len(th)):
            th[i] = min(max(th[i], th[i - 1] - 0.24 * step_len[i - 1]), th[i - 1] + 0.24 * step_len[i - 1])
        for i in range(len(th) - 2, -1, -1):
            th[i] = min(max(th[i], th[i + 1] - 0.24 * step_len[i]), th[i + 1] + 0.24 * step_len[i])
    th = ndimage.gaussian_filter1d(th, 3.0, mode="nearest")
    graded = np.interp(talong, seg, th).astype(np.float32)
    w = 1.0 - smoothstep(3.6, 13.0, tdist)
    h = h * (1.0 - w) + graded * w

    rdist, ralong = polyline_distance(x, z, river, 60.0)
    rseg = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(river, axis=0), axis=1))])
    rh = sample(h, river[:, 0], river[:, 1])
    rh = ndimage.gaussian_filter1d(rh, 12.0, mode="nearest")
    rh = np.minimum.accumulate(rh)
    bank = np.interp(ralong, rseg, rh).astype(np.float32)
    ford = dist_to(x, z, S["FORD"])
    depth = 1.9 * (1.0 - 0.5 * (1.0 - smoothstep(6.0, 16.0, ford)))
    w = 1.0 - smoothstep(2.5, 8.0, rdist)
    meadow = 1.0 - smoothstep(8.0, 55.0, rdist)
    h = h * (1.0 - meadow * 0.6) + (bank + 0.5) * meadow * 0.6
    h -= depth * w
    water = np.stack([river[:, 0], rh - 0.75, river[:, 1]], axis=1)

    foot_e = np.full(shape, 9.0, dtype=np.float32)
    foot_water = []
    for center, heading, _side in S["FOOTPRINTS"]:
        c, s = np.cos(heading), np.sin(heading)
        rx = (x - center[0]) * c - (z - center[1]) * s
        rz = (x - center[0]) * s + (z - center[1]) * c
        e = np.hypot(rx / (S["FOOT_WIDTH"] * 0.5), rz / (S["FOOT_LENGTH"] * 0.5))
        foot_e = np.minimum(foot_e, e)
        level = float(h[e < 1.0].mean())
        foot_water.append(level - 1.5)
        inside = 1.0 - smoothstep(0.55, 1.0, e)
        h = np.where(e < 1.7, h * (1.0 - inside * 0.85) + (level - 3.2) * inside * 0.85 + 0.95 * np.exp(-((e - 1.14) / 0.13) ** 2), h)

    crater_mask = np.zeros(shape, dtype=np.float32)
    craters = []
    tries = 0
    while len(craters) < 30 and tries < 4000:
        tries += 1
        a = rng.uniform(0, 2 * np.pi)
        r = rng.uniform(14.0, 120.0)
        p = (S["FORD"][0] + np.cos(a) * r, S["FORD"][1] + np.sin(a) * r * 0.8)
        rad = rng.uniform(2.0, 5.5)
        if float(sample(tdist, p[0], p[1])) < rad + 4.0 or float(sample(rdist, p[0], p[1])) < rad + 5.0:
            continue
        if any(np.hypot(p[0] - q[0], p[1] - q[1]) < rad + q[2] + 1.5 for q in craters):
            continue
        craters.append((p[0], p[1], rad))
    for cx_, cz_, rad in craters:
        e = dist_to(x, z, (cx_, cz_)) / rad
        near = e < 2.2
        bowl = -0.38 * rad * (1.0 - smoothstep(0.0, 1.0, e)) + 0.14 * rad * np.exp(-((e - 1.15) / 0.22) ** 2)
        h = np.where(near, h + bowl, h)
        crater_mask = np.maximum(crater_mask, 1.0 - smoothstep(0.9, 1.9, e))

    bx, bz = S["BOMBER"]
    tail = np.array([bx + maplib.BOMBER_TAIL[0], bz + maplib.BOMBER_TAIL[1]])
    nose = np.array([bx + maplib.BOMBER_NOSE[0], bz + maplib.BOMBER_NOSE[1]])
    length = float(np.linalg.norm(nose - tail))
    axis = (nose - tail) / length
    along_plane = (x - tail[0]) * axis[0] + (z - tail[1]) * axis[1]
    across_plane = np.abs(-(x - tail[0]) * axis[1] + (z - tail[1]) * axis[0])
    scar = (1.0 - smoothstep(2.0, 4.5, across_plane)) * smoothstep(-58.0, -38.0, along_plane) * (1.0 - smoothstep(-6.0, 0.0, along_plane))
    h -= 0.9 * scar
    ends = sample(h, np.array([tail[0], nose[0]]), np.array([tail[1], nose[1]]))
    line = ends[0] + (ends[1] - ends[0]) * np.clip(along_plane / length, -0.15, 1.15)
    beyond = np.maximum(np.maximum(-along_plane - 1.5, along_plane - length - 1.5), 0.0)
    bed = (1.0 - smoothstep(2.6, 6.5, np.hypot(across_plane, beyond))) * smoothstep(4.0, 7.5, tdist)
    h = h * (1.0 - bed) + (line - 0.12) * bed
    trench = np.zeros(shape, dtype=np.float32)
    for i, station in enumerate(maplib.BOMBER_DENTS):
        off = np.abs(along_plane - station)
        m = (1.0 - smoothstep(1.0, 1.9, off)) * smoothstep(2.2, 4.2, across_plane) * (1.0 - smoothstep(19.0 + 3.0 * i, 24.0 + 3.0 * i, across_plane))
        trench = np.maximum(trench, m)
    trench *= smoothstep(4.0, 7.5, tdist)
    h -= 0.8 * trench

    lane = np.full(shape, 60.0, dtype=np.float32)
    for a, b in S["LANES"]:
        dd, _ = polyline_distance(x, z, [a, b], 60.0)
        lane = np.minimum(lane, dd)
    h -= 0.45 * (1.0 - smoothstep(S["LANE_HALF_WIDTH"] * 0.5, S["LANE_HALF_WIDTH"] + 2.0, lane)) * (tdist > 8.0)

    keep = smoothstep(2.5, 7.0, tdist)
    for center, r_in, _r_out in PADS:
        keep = keep * smoothstep(r_in * 0.7, r_in, dist_to(x, z, center))
    keep = keep * (1.0 - bed)
    h += (fbm(shape, 5, 3, 0.55, SEED + 4) * 0.34 + fbm(shape, 1.6, 2, 0.5, SEED + 5) * 0.07) * keep

    fields = {"tdist": tdist, "rdist": rdist, "lane": lane, "foot_e": foot_e, "crater": crater_mask, "trench": np.maximum(trench, scar),
              "rise": rise, "wall": wall}
    info = {"bomber_bed": [float(ends[0]) - 0.12, float(ends[1]) - 0.12], "pad_heights": pad_heights, "foot_water": foot_water, "craters": craters, "track": track, "water": water}
    return h.astype(np.float32), fields, info


def build_maps(x, z, h, f):
    gz, gx = np.gradient(h, CELL)
    ny = 1.0 / np.sqrt(1.0 + gx * gx + gz * gz)
    nx = -gx * ny
    nz = -gz * ny
    slope = np.degrees(np.arccos(np.clip(ny, 0.0, 1.0)))
    shape = h.shape
    scree = 1.0 - smoothstep(70.0, 115.0, dist_to(x, z, S["BOMBER"]))
    pad_in = np.zeros(shape, dtype=np.float32)
    pad_any = np.zeros(shape, dtype=np.float32)
    for center, r_in, r_out in PADS:
        dd = dist_to(x, z, center)
        pad_in = np.maximum(pad_in, 1.0 - smoothstep(r_in * 0.8, r_in, dd))
        pad_any = np.maximum(pad_any, 1.0 - smoothstep(r_in, r_out, dd))
    patch = fbm(shape, 60, 3, 0.5, SEED + 10)
    fine = fbm(shape, 9, 3, 0.5, SEED + 11)

    rock = np.maximum(smoothstep(30.0, 42.0, slope + fine * 6.0), scree * (0.55 + 0.45 * smoothstep(-0.2, 0.3, fine)))
    rock = np.maximum(rock, smoothstep(196.0, 214.0, h + fine * 6.0) * 0.85)
    rock = np.maximum(rock, smoothstep(0.3, 0.8, f["wall"]))
    dirt = np.maximum(1.0 - smoothstep(S["TRACK_HALF_WIDTH"] - 0.4, S["TRACK_HALF_WIDTH"] + 1.6, f["tdist"] + fine * 0.5), f["crater"])
    dirt = np.maximum(dirt, (1.0 - smoothstep(S["LANE_HALF_WIDTH"] - 1.0, S["LANE_HALF_WIDTH"] + 2.5, f["lane"] + fine * 2.0)) * 0.9)
    dirt = np.maximum(dirt, (1.0 - smoothstep(0.9, 1.35, f["foot_e"])))
    dirt = np.maximum(dirt, f["trench"])
    dirt = np.maximum(dirt, pad_in * 0.5 * smoothstep(-0.3, 0.2, fine))
    dirt = np.maximum(dirt, 1.0 - smoothstep(2.0, 6.5, f["rdist"]))
    meadow = (1.0 - smoothstep(25.0, 85.0, f["rdist"] + patch * 25.0)) * (1.0 - smoothstep(18.0, 28.0, slope))
    grass = np.maximum(meadow, pad_any * 0.9)
    grass = np.maximum(grass, smoothstep(0.25, 0.45, patch) * (1.0 - smoothstep(14.0, 24.0, slope)) * 0.8)
    grass = np.maximum(grass, (1.0 - smoothstep(3.0, 9.0, f["tdist"])) * 0.5)
    grass = np.maximum(grass, smoothstep(2.0, 6.0, f["lane"]) * (1.0 - smoothstep(6.0, 12.0, f["lane"])) * 0.7)

    weights = np.stack([np.ones(shape, dtype=np.float32), grass, rock, dirt], axis=2)
    weights[..., 0] *= (1.0 - grass) * (1.0 - rock) * (1.0 - dirt)
    weights[..., 1] *= (1.0 - rock) * (1.0 - dirt)
    weights[..., 2] *= (1.0 - dirt * 0.8)
    weights /= weights.sum(axis=2, keepdims=True)

    dens = np.ones(shape, dtype=np.float32)
    dens *= smoothstep(4.2, 6.5, f["tdist"])
    dens *= smoothstep(S["LANE_HALF_WIDTH"], S["LANE_HALF_WIDTH"] + 2.0, f["lane"])
    dens *= smoothstep(6.0, 11.0, f["rdist"])
    dens *= 1.0 - pad_in
    dens *= smoothstep(1.2, 1.5, f["foot_e"])
    dens *= 1.0 - f["crater"]
    dens *= 1.0 - smoothstep(34.0, 40.0, slope)
    dens *= 1.0 - scree
    dens *= 1.0 - smoothstep(186.0, 204.0, h)
    dens *= 1.0 - 0.9 * (1.0 - smoothstep(45.0, 90.0, dist_to(x, z, S["FORD"])))
    dens *= 1.0 - 0.75 * meadow
    dens *= 1.0 - smoothstep(0.3, 0.42, patch)
    dens *= 1.0 - smoothstep(0.2, 0.6, f["wall"])
    vx, vz = S["VIADUCT"]
    dens *= np.where((np.abs(z - vz) < 7.0) & (np.abs(x - vx) < 190.0), 0.0, 1.0)
    dens *= np.where(dist_to(x, z, S["CHURCH_ROOF"]) < 13.0, 0.0, 1.0)

    macro = 1.0 + fbm(shape, 110, 3, 0.5, SEED + 12) * 0.16 + fine * 0.05
    burnt = np.maximum(f["crater"], (1.0 - smoothstep(20.0, 70.0, dist_to(x, z, S["FORD"]))) * 0.5 * smoothstep(-0.1, 0.4, fine))
    tint = np.stack([macro, macro, macro], axis=2)
    tint *= (1.0 - 0.5 * burnt)[..., None]
    tint[..., 0] *= 1.0 + 0.10 * meadow
    tint[..., 2] *= 1.0 - 0.12 * meadow
    tint *= (1.0 - 0.18 * dens)[..., None]
    wet = np.maximum(1.0 - smoothstep(3.0, 14.0, f["rdist"]), 1.0 - smoothstep(0.7, 1.1, f["foot_e"]))
    wet = np.maximum(wet, (1.0 - smoothstep(0.0, 1.6, f["tdist"])) * smoothstep(0.0, 0.5, fine) * 0.7)
    wet = np.maximum(wet, f["crater"] * 0.8)

    blur = ndimage.gaussian_filter(h, 6.0)
    shelter = np.clip(0.5 + (h - blur) * 0.22, 0.0, 1.0)

    return {"weights": weights, "dens": dens, "tint": tint, "wet": wet, "nx": nx, "nz": nz, "shelter": shelter, "slope": slope,
            "meadow": meadow, "pad_in": pad_in}


def place_trees(h, m, f):
    spacing = 5.2
    n = int(SIZE / spacing)
    gi, gj = np.meshgrid(np.arange(n), np.arange(n))
    px = -HALF + (gi + rng.random((n, n)) * 0.86 + 0.07) * spacing
    pz = -HALF + (gj + rng.random((n, n)) * 0.86 + 0.07) * spacing
    dens = sample(m["dens"], px, pz)
    keep = rng.random((n, n)) < dens * 0.74
    built = os.path.join(maplib.GEN, "sites", "keepout.npy")
    if os.path.exists(built):
        mask = np.unpackbits(np.load(built), axis=1)[:, :int(SIZE)].astype(bool)
        keep &= ~mask[np.clip((pz + HALF).astype(int), 0, int(SIZE) - 1), np.clip((px + HALF).astype(int), 0, int(SIZE) - 1)]
    edge = (dens > 0.05) & (dens < 0.75)
    px, pz, dens, edge = px[keep], pz[keep], dens[keep], edge[keep]
    count = len(px)
    py = sample(h, px, pz) - 0.35
    yaw = rng.random(count) * 2 * np.pi
    height = rng.uniform(17.0, 30.0, count) * (0.85 + 0.15 * dens)
    kind = rng.integers(0, 2, count).astype(np.float32)
    dead = rng.random(count) < 0.07
    kind[dead] = 2.0
    height[dead] *= rng.uniform(0.45, 0.9, int(dead.sum()))
    young = edge & (rng.random(count) < 0.45) & ~dead
    kind[young] = 3.0
    height[young] = rng.uniform(2.5, 8.0, int(young.sum()))
    rows = np.stack([px, py, pz, yaw, height, kind, rng.random(count), rng.uniform(0.75, 1.1, count)], axis=1).astype(np.float32)
    return rows


def pack_trees(rows):
    cells = int(SIZE / TREE_CELL)
    ci = np.clip(((rows[:, 0] + HALF) / TREE_CELL).astype(int), 0, cells - 1)
    cj = np.clip(((rows[:, 2] + HALF) / TREE_CELL).astype(int), 0, cells - 1)
    key = cj * cells + ci
    order = np.lexsort((rows[:, 5], key))
    rows = rows[order]
    key = key[order]
    kinds = np.zeros((cells * cells, 4), dtype=np.uint32)
    np.add.at(kinds, (key, np.clip(np.round(rows[:, 5]).astype(int), 0, 3)), 1)
    counts = np.bincount(key, minlength=cells * cells).astype(np.uint32)
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]]).astype(np.uint32)
    yaw = rows[:, 3]
    s = rows[:, 4]
    lean_a = rng.random(len(rows)) * 2 * np.pi
    lean = rng.uniform(0.0, 0.045, len(rows))
    c, sn = np.cos(yaw) * s, np.sin(yaw) * s
    buf = np.zeros((len(rows), 20), dtype=np.float32)
    buf[:, 0] = c
    buf[:, 1] = np.cos(lean_a) * lean * s
    buf[:, 2] = sn
    buf[:, 3] = rows[:, 0]
    buf[:, 4] = 0.0
    buf[:, 5] = s
    buf[:, 6] = 0.0
    buf[:, 7] = rows[:, 1]
    buf[:, 8] = -sn
    buf[:, 9] = np.sin(lean_a) * lean * s
    buf[:, 10] = c
    buf[:, 11] = rows[:, 2]
    buf[:, 12] = rows[:, 7]
    buf[:, 13] = rows[:, 7]
    buf[:, 14] = rows[:, 7]
    buf[:, 15] = 1.0
    buf[:, 16] = rows[:, 5]
    buf[:, 17] = rows[:, 6]
    tops = np.full(cells * cells, -1000.0, dtype=np.float32)
    np.maximum.at(tops, key, (rows[:, 1] + rows[:, 4]).astype(np.float32))
    with open(os.path.join(OUT, "trees.bin"), "wb") as fh:
        fh.write(struct.pack("<4sIIf", b"TREE", cells, len(rows), TREE_CELL))
        fh.write(starts.tobytes())
        fh.write(counts.tobytes())
        fh.write(tops.tobytes())
        fh.write(kinds.tobytes())
        fh.write(buf.tobytes())
    return len(rows)


def preview(x, z, h, m, info, rows):
    gz, gx = np.gradient(h, CELL)
    shade = np.clip(0.55 + (gx * 0.6 + gz * 0.6) * 0.9, 0.15, 1.0)
    w = m["weights"]
    col = (w[..., 0:1] * np.array([0.16, 0.24, 0.13]) + w[..., 1:2] * np.array([0.38, 0.42, 0.20]) +
           w[..., 2:3] * np.array([0.45, 0.44, 0.42]) + w[..., 3:4] * np.array([0.42, 0.33, 0.22]))
    col = col * m["tint"] * shade[..., None] * 2.2
    img = Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).resize((1408, 1408))
    d = ImageDraw.Draw(img)

    def px(p):
        return ((p[0] + HALF) / SIZE * 1408, (p[1] + HALF) / SIZE * 1408)
    step = max(len(rows) // 30000, 1)
    for r in rows[::step]:
        q = px((r[0], r[2]))
        d.point(q, fill=(10, 40, 18) if r[5] < 2 else (120, 110, 90) if r[5] == 2 else (40, 90, 40))
    d.line([px(p) for p in info["track"]], fill=(255, 220, 120), width=2)
    d.line([px((p[0], p[2])) for p in info["water"]], fill=(90, 150, 255), width=2)
    for name in ("SPAWN", "GASTHAUS", "CHURCH", "CHURCH_ROOF", "BOMBER", "VIADUCT", "SANATORIUM", "FORD", "RADAR", "TUNNEL", "LOOKOUT"):
        q = px(S[name])
        d.ellipse([q[0] - 5, q[1] - 5, q[0] + 5, q[1] + 5], outline=(255, 60, 60), width=2)
        d.text((q[0] + 8, q[1] - 6), "%s %.0f m" % (name.lower(), float(sample(h, S[name][0], S[name][1]))), fill=(255, 255, 255))
    os.makedirs(os.path.join(os.path.dirname(OUT), "..", "..", "test_out"), exist_ok=True)
    img.save(os.path.join(os.path.dirname(OUT), "..", "..", "test_out", "map_preview.jpg"), quality=88)


def main():
    x, z = grid()
    h, f, info = build_heights(x, z)
    m = build_maps(x, z, h, f)
    rows = place_trees(h, m, f)
    count = pack_trees(rows)

    h.astype("<f4").tofile(os.path.join(OUT, "height.bin"))
    import texlib
    texlib.write_texture("terrain", "control.png", Image.fromarray((np.clip(m["weights"], 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA"), compressed=False, mips=False, fix_alpha=False)
    tint = np.concatenate([np.clip(m["tint"] * 128.0, 0, 255), (m["wet"] * 255.0)[..., None]], axis=2)
    texlib.write_texture("terrain", "tint.png", Image.fromarray(tint.astype(np.uint8), "RGBA"), compressed=False, mips=False, fix_alpha=False)
    nrm = np.stack([m["nx"] * 0.5 + 0.5, m["nz"] * 0.5 + 0.5, m["shelter"]], axis=2)
    texlib.write_texture("terrain", "normal.png", Image.fromarray((np.clip(nrm, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB"), compressed=False, mips=False, fix_alpha=False)

    track = info["track"]
    ty = sample(h, track[:, 0], track[:, 1])
    np.stack([track[:, 0], ty, track[:, 1]], axis=1).astype("<f4").tofile(os.path.join(OUT, "track.bin"))
    info["water"].astype("<f4").tofile(os.path.join(OUT, "river.bin"))
    seg = np.linalg.norm(np.diff(track, axis=0), axis=1)
    grade = np.abs(np.diff(ty)) / np.maximum(seg, 1e-6)
    grade = ndimage.uniform_filter1d(grade, 5)
    worst = int(np.argmax(grade))
    print("steepest stretch of track at (%.0f, %.0f), %.0f m along" % (track[worst, 0], track[worst, 1], float(seg[:worst].sum())))
    steep = np.where(grade > 0.3)[0]
    if len(steep):
        print("over 30%%: %d stretches of 3 m, between %.0f and %.0f m along" % (len(steep), float(seg[:steep[0]].sum()), float(seg[:steep[-1]].sum())))
    stops = {}
    for name in ("SPAWN", "GASTHAUS", "CHURCH", "BOMBER", "SANATORIUM", "FORD", "RADAR", "TUNNEL", "LOOKOUT"):
        stops[name.lower()] = round(float(sample(h, S[name][0], S[name][1])), 1)
    meta = {
        "size": SIZE, "cell": CELL, "samples": N + 1, "tree_cell": TREE_CELL, "trees": count,
        "track_length": round(float(seg.sum()), 1), "track_points": len(track), "track_steepest_percent": round(float(grade.max() * 100.0), 1),
        "height_min": round(float(h.min()), 1), "height_max": round(float(h.max()), 1),
        "foot_water": [round(v, 2) for v in info["foot_water"]],
        "craters": [[round(float(c[0]), 1), round(float(c[1]), 1), round(float(c[2]), 2)] for c in info["craters"]],
        "ground": stops,
    }
    with open(os.path.join(OUT, "meta.json"), "w") as fh:
        json.dump(meta, fh, indent=1)
    preview(x, z, h, m, info, rows)
    print(json.dumps({k: v for k, v in meta.items() if k != "craters"}, indent=1))


if __name__ == "__main__":
    main()
