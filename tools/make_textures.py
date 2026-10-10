#!/usr/bin/env python3
# usage: python3 tools/make_textures.py [set ...]
import sys

import numpy as np
from PIL import Image

import texlib as T
from texlib import Layer, blur, cells, fbm, ramp, remap, smoothstep, stamp_blobs, stamp_strokes, white

SIZE = 1024


def mix(a, b, t):
    t = t[..., None] if t.ndim == 2 and a.ndim == 3 else t
    return a * (1.0 - t) + b * t


def col(r, g, b):
    return np.array([r, g, b], dtype=np.float32)


def flat(c):
    return np.broadcast_to(np.array(c, dtype=np.float32), (SIZE, SIZE, 3)).copy()


def forest_floor():
    big = fbm(SIZE, 4, 4, 0.5, 11)
    mid = fbm(SIZE, 14, 4, 0.55, 12)
    height = big * 6.0 + mid * 2.0 + fbm(SIZE, 110, 3, 0.6, 13) * 0.9
    color = ramp(remap(big * 0.6 + mid * 0.4 + fbm(SIZE, 40, 3, 0.5, 14) * 0.5), [
        (0.0, (0.10, 0.075, 0.05)), (0.45, (0.19, 0.135, 0.085)), (0.8, (0.27, 0.185, 0.105)), (1.0, (0.33, 0.23, 0.13))])
    def needle(rng):
        k = rng.random()
        if k < 0.12:
            return (0.46, 0.38, 0.24)
        if k < 0.5:
            return (0.30, 0.20, 0.11)
        return (0.17, 0.115, 0.07)
    rgb, cov = stamp_strokes(SIZE, 70000, (4, 10), (0.8, 1.2), 15, needle)
    color = mix(color, rgb / np.maximum(cov, 1e-3)[..., None], np.clip(cov * 1.3, 0, 1) * 0.75)
    height += cov * 0.9
    def twig(rng):
        return (0.33, 0.33, 0.30) if rng.random() < 0.25 else (0.12, 0.09, 0.07)
    rgb, cov = stamp_strokes(SIZE, 520, (24, 120), (1.4, 3.2), 16, twig, curve=0.9)
    color = mix(color, rgb / np.maximum(cov, 1e-3)[..., None], np.clip(cov * 1.5, 0, 1))
    height += blur(cov, 0.8) * 3.5
    moss = smoothstep(0.02, 0.3, fbm(SIZE, 3, 4, 0.55, 17) + fbm(SIZE, 22, 2, 0.5, 18) * 0.3)
    moss_c = ramp(remap(fbm(SIZE, 60, 3, 0.6, 19)), [(0.0, (0.055, 0.10, 0.035)), (0.6, (0.11, 0.17, 0.055)), (1.0, (0.20, 0.25, 0.09))])
    color = mix(color, moss_c, moss * 0.92)
    height += moss * (3.5 + fbm(SIZE, 70, 3, 0.6, 20) * 2.2)
    rough = 0.9 + moss * 0.08
    stamp_blobs(height, color, 46, (9, 15), 21, bump=0.7, tint=lambda r: (0.25, 0.16, 0.09), squash=(0.34, 0.45))
    T.stamp_stones(height, color, 16, (6, 30), 22, lift=0.45, grey=(0.22, 0.34), sink=0.5)
    return Layer("forest_floor", color, height, rough, normal_strength=0.8)


def grass():
    clump = smoothstep(-0.25, 0.35, fbm(SIZE, 7, 3, 0.5, 31))
    height = fbm(SIZE, 5, 4, 0.5, 32) * 5.0 + clump * 5.0
    color = ramp(remap(fbm(SIZE, 20, 4, 0.5, 33)), [(0.0, (0.07, 0.065, 0.04)), (1.0, (0.15, 0.13, 0.075))])

    def blade(rng):
        k = rng.random()
        if k < 0.4:
            return (0.50 + rng.random() * 0.08, 0.46, 0.27)
        if k < 0.75:
            return (0.30, 0.33, 0.15)
        return (0.13, 0.20, 0.07)
    for seed, count, length in ((34, 26000, (14, 34)), (35, 22000, (22, 54)), (36, 16000, (10, 22))):
        rgb, cov = stamp_strokes(SIZE, count, length, (0.9, 1.8), seed, blade, curve=1.4, mask=0.3 + 0.7 * clump)
        color = mix(color, rgb / np.maximum(cov, 1e-3)[..., None], np.clip(cov * 1.6, 0, 1) * 0.9)
        height += blur(cov, 0.7) * 2.6
    stamp_blobs(height, color, 30, (5, 11), 37, bump=0.25, tint=lambda r: (0.34, 0.20, 0.08), squash=(0.5, 0.8))
    return Layer("grass", color, height, 0.93, normal_strength=0.7)


def rock():
    warp = fbm(SIZE, 3, 3, 0.5, 40)
    n1 = fbm(SIZE, 4, 5, 0.55, 41, stretch=(1.0, 1.7))
    n2 = fbm(SIZE, 9, 4, 0.5, 42)
    ridge = 1.0 - np.abs(n1 * 0.75 + n2 * 0.25 + warp * 0.2) * 2.2
    crease = smoothstep(0.78, 1.0, ridge)
    height = ridge * 9.0 + fbm(SIZE, 30, 4, 0.6, 43) * 2.4 + fbm(SIZE, 140, 3, 0.6, 44) * 0.7 - crease * 6.0
    grey = 0.31 + fbm(SIZE, 7, 4, 0.5, 45) * 0.07 + fbm(SIZE, 60, 3, 0.5, 46) * 0.035
    color = np.stack([grey * 1.03, grey, grey * 0.95], axis=2)
    color = mix(color, color * col(1.12, 0.98, 0.82), smoothstep(0.1, 0.5, fbm(SIZE, 5, 3, 0.5, 47)) * 0.6)
    color *= (1.0 - 0.55 * crease)[..., None]
    lichen = smoothstep(0.32, 0.5, fbm(SIZE, 11, 4, 0.6, 48)) * smoothstep(-0.1, 0.25, fbm(SIZE, 80, 2, 0.5, 49)) * (1.0 - crease)
    color = mix(color, flat((0.45, 0.48, 0.40)), lichen * 0.55)
    moss = smoothstep(0.4, 0.6, fbm(SIZE, 6, 3, 0.55, 50)) * crease
    color = mix(color, flat((0.10, 0.15, 0.06)), np.clip(moss * 2.0, 0, 1))
    loose = 0.25 + 0.75 * smoothstep(-0.2, 0.3, fbm(SIZE, 3, 2, 0.5, 51))
    T.stamp_stones(height, color, 2600, (2, 9), 53, lift=0.5, mask=loose, sink=0.1)
    T.stamp_stones(height, color, 230, (9, 56), 52, lift=0.55, mask=loose, sink=0.15)
    return Layer("rock", color, height, 0.84, normal_strength=0.75)


def dirt():
    big = fbm(SIZE, 3, 4, 0.5, 61)
    height = big * 5.0 + fbm(SIZE, 16, 4, 0.55, 62) * 2.2 + fbm(SIZE, 130, 3, 0.6, 63) * 0.7
    wet = smoothstep(0.15, 0.5, -big + fbm(SIZE, 9, 2, 0.5, 64) * 0.2)
    color = ramp(remap(fbm(SIZE, 6, 5, 0.55, 65)), [(0.0, (0.15, 0.115, 0.08)), (0.5, (0.23, 0.175, 0.12)), (1.0, (0.31, 0.245, 0.17))])
    color *= (0.9 + 0.2 * white(SIZE, 66))[..., None]
    color = mix(color, color * col(0.5, 0.48, 0.46), wet)
    height = mix(height, blur(height, 3.0) - 1.5, wet)
    crack = (1.0 - smoothstep(0.0, 1.0, np.abs(fbm(SIZE, 5, 3, 0.5, 70)) * 60.0)) * smoothstep(0.0, 0.4, fbm(SIZE, 4, 2, 0.5, 71))
    height -= crack * 1.2 * (1.0 - wet)
    color *= (1.0 - 0.18 * crack * (1.0 - wet))[..., None]
    T.stamp_stones(height, color, 1500, (1.5, 6.0), 67, lift=0.45, grey=(0.24, 0.40), warm=0.5, sink=0.3)
    T.stamp_stones(height, color, 60, (7, 24), 68, lift=0.4, grey=(0.24, 0.38), warm=0.4, sink=0.4)

    def straw(rng):
        return (0.42, 0.37, 0.22) if rng.random() < 0.5 else (0.14, 0.10, 0.07)
    rgb, cov = stamp_strokes(SIZE, 900, (10, 46), (0.9, 1.8), 69, straw, curve=1.0)
    color = mix(color, rgb / np.maximum(cov, 1e-3)[..., None], np.clip(cov * 1.4, 0, 1) * 0.8)
    height += cov * 1.2
    rough = 0.88 - wet * 0.5
    return Layer("dirt", color, height, rough, normal_strength=0.7)


def plaster():
    big = fbm(SIZE, 3, 4, 0.5, 101)
    height = big * 2.0 + fbm(SIZE, 24, 4, 0.6, 102) * 0.9 + fbm(SIZE, 160, 3, 0.6, 103) * 0.35
    v = remap(big * 0.6 + fbm(SIZE, 9, 4, 0.5, 104) * 0.4)
    color = ramp(v, [(0.0, (0.50, 0.47, 0.41)), (0.5, (0.64, 0.61, 0.54)), (1.0, (0.74, 0.71, 0.63))])
    crack = T.cracks(SIZE, 30, 105, 1.5, 0.45)
    height -= crack * 2.5
    color *= (1.0 - 0.5 * crack)[..., None]
    damp = smoothstep(0.1, 0.6, fbm(SIZE, 4, 4, 0.55, 107)) * T.streaks(SIZE, 108)
    color = mix(color, color * col(0.62, 0.60, 0.52), damp * 0.8)
    gone = smoothstep(0.36, 0.42, fbm(SIZE, 2, 4, 0.6, 109) + fbm(SIZE, 30, 2, 0.5, 110) * 0.1)
    edge, ident, _u, _v = T.bricks(SIZE, 32, 9, 5.0, 111, jitter=0.3)
    brick = ramp(T.per_id(ident, 112), [(0.0, (0.24, 0.15, 0.12)), (0.6, (0.32, 0.19, 0.14)), (1.0, (0.38, 0.25, 0.19))])
    brick = mix(flat((0.45, 0.43, 0.39)), brick, smoothstep(-0.5, 1.5, edge))
    color = mix(color, brick, gone)
    height = mix(height, smoothstep(-0.5, 2.0, edge) * 2.0 - 5.0, gone)
    rim = smoothstep(0.27, 0.36, fbm(SIZE, 2, 4, 0.6, 109) + fbm(SIZE, 30, 2, 0.5, 110) * 0.1) * (1.0 - gone)
    color *= (1.0 - 0.25 * rim)[..., None]
    return Layer("plaster", color, height, 0.92, normal_strength=1.1)


def brick():
    edge, ident, u, v = T.bricks(SIZE, 32, 9, 6.0, 121, jitter=0.25)
    per = T.per_id(ident, 122)
    face = smoothstep(-0.5, 2.5, edge)
    color = ramp(remap(per + fbm(SIZE, 30, 3, 0.5, 123) * 0.25), [(0.0, (0.22, 0.10, 0.075)), (0.4, (0.36, 0.165, 0.11)), (0.8, (0.47, 0.24, 0.15)), (1.0, (0.52, 0.34, 0.24))])
    mortar = ramp(remap(fbm(SIZE, 40, 3, 0.5, 124)), [(0.0, (0.30, 0.29, 0.26)), (1.0, (0.50, 0.48, 0.43))])
    color = mix(mortar, color, face)
    spall = (per > 0.9).astype(np.float32) * smoothstep(-0.2, 0.3, fbm(SIZE, 40, 2, 0.5, 125))
    height = face * (4.0 + per * 1.5) - spall * 2.5 + fbm(SIZE, 90, 3, 0.6, 126) * 0.6 * face
    color *= (1.0 - 0.3 * spall)[..., None]
    bloom = smoothstep(0.25, 0.6, fbm(SIZE, 5, 4, 0.55, 127)) * 0.35
    color = mix(color, flat((0.62, 0.60, 0.56)), bloom * face)
    soot = smoothstep(0.2, 0.7, fbm(SIZE, 3, 3, 0.5, 128)) * T.streaks(SIZE, 129) * 0.6
    color *= (1.0 - soot)[..., None]
    return Layer("brick", color, height, 0.9, normal_strength=1.0)


def concrete():
    edge, ident, u, along = T.boards(SIZE, 14, 131, vertical=False, gap=2.5, lengths=420)
    per = T.per_id(ident, 132)
    height = (per - 0.5) * 0.9 + smoothstep(-1.0, 1.5, edge) * 0.5 + fbm(SIZE, 50, 3, 0.6, 133, stretch=(0.3, 2.0)) * 0.5 + fbm(SIZE, 5, 3, 0.5, 134) * 1.5
    pores = (white(SIZE, 135) > 0.99965).astype(np.float32) * smoothstep(-0.2, 0.3, fbm(SIZE, 6, 3, 0.5, 142))
    pores = np.clip(blur(pores, 1.3) * 11.0, 0, 1)
    height -= pores * 2.0
    g = 0.40 + fbm(SIZE, 4, 4, 0.5, 136) * 0.07 + (per - 0.5) * 0.05 + fbm(SIZE, 60, 2, 0.5, 137) * 0.03
    color = np.stack([g * 1.0, g * 0.99, g * 0.95], axis=2)
    color *= (1.0 - 0.35 * pores)[..., None] * (0.9 + 0.1 * smoothstep(-1.0, 2.0, edge))[..., None]
    crack = T.cracks(SIZE, 9, 143, 1.4, 0.4)
    color *= (1.0 - 0.5 * crack)[..., None]
    height -= crack * 2.0
    run = smoothstep(0.35, 0.8, fbm(SIZE, 22, 3, 0.5, 138, stretch=(1.0, 0.12))) * smoothstep(0.0, 0.5, fbm(SIZE, 3, 2, 0.5, 139))
    color = mix(color, color * col(1.0, 0.72, 0.5), run * 0.7)
    dirt_ = T.streaks(SIZE, 140, 26, 0.15) * smoothstep(0.1, 0.7, fbm(SIZE, 2, 3, 0.5, 141))
    color *= (1.0 - 0.45 * dirt_)[..., None]
    return Layer("concrete", color, height, 0.88, normal_strength=1.0)


def planks():
    edge, ident, u, along = T.boards(SIZE, 14, 151, vertical=True, gap=3.0, lengths=0)
    per = T.per_id(ident, 152)
    grain = fbm(SIZE, 60, 4, 0.55, 153, stretch=(1.0, 0.045))
    wave = fbm(SIZE, 5, 3, 0.5, 154, stretch=(1.0, 0.3))
    height = smoothstep(-1.5, 2.0, edge) * 3.0 + grain * 1.0 + (per - 0.5) * 1.5 + wave * 1.0
    v = remap(per * 0.5 + grain * 0.35 + wave * 0.3)
    color = ramp(v, [(0.0, (0.13, 0.11, 0.09)), (0.4, (0.25, 0.21, 0.17)), (0.8, (0.36, 0.31, 0.26)), (1.0, (0.45, 0.41, 0.36))])
    split = (1.0 - smoothstep(0.0, 0.02, np.abs(fbm(SIZE, 30, 2, 0.5, 155, stretch=(1.0, 0.03))))) * smoothstep(0.0, 0.4, fbm(SIZE, 6, 2, 0.5, 156, stretch=(1.0, 0.1)))
    splits = np.clip(blur(split, 0.6) * (fbm(SIZE, 40, 2, 0.5, 157, stretch=(1.0, 0.05)) > 0.1), 0, 1)
    height -= splits * 2.0
    color *= (1.0 - 0.5 * splits)[..., None] * (0.45 + 0.55 * smoothstep(-1.5, 1.0, edge))[..., None]
    rng = np.random.default_rng(158)
    pts = []
    w = SIZE / 14
    for b in range(14):
        for y in (SIZE * 0.12, SIZE * 0.62):
            pts.append(((b + 0.5) * w + rng.uniform(-6, 6), y + rng.uniform(-10, 10)))
    nails = T.dots(SIZE, pts, 3.0)
    color = mix(color, flat((0.10, 0.07, 0.06)), nails)
    rust = np.clip(blur(nails, 4.0) * 5.0, 0, 1) * T.streaks(SIZE, 159, 30, 0.1)
    color = mix(color, color * col(0.9, 0.6, 0.42), rust)
    height += nails * 1.0
    green = smoothstep(0.3, 0.7, fbm(SIZE, 3, 4, 0.55, 160)) * 0.4
    color = mix(color, color * col(0.72, 0.95, 0.62), green)
    return Layer("planks", color, height, 0.9, normal_strength=1.0)


def shingles():
    edge, ident, u, v = T.bricks(SIZE, 16, 12, 2.0, 171, jitter=0.6)
    per = T.per_id(ident, 172)
    height = (1.0 - v) * 5.0 + per * 1.5 + smoothstep(-0.5, 1.5, edge) * 1.0 + fbm(SIZE, 70, 3, 0.6, 173, stretch=(1.0, 0.1)) * 0.6
    color = ramp(remap(per * 0.7 + fbm(SIZE, 50, 3, 0.5, 174, stretch=(1.0, 0.1)) * 0.4), [(0.0, (0.10, 0.09, 0.08)), (0.5, (0.20, 0.17, 0.14)), (1.0, (0.31, 0.27, 0.22))])
    color *= (0.5 + 0.5 * smoothstep(-0.5, 2.0, edge))[..., None] * (0.7 + 0.3 * (1.0 - v))[..., None]
    moss = smoothstep(0.2, 0.6, fbm(SIZE, 5, 4, 0.55, 175)) * smoothstep(0.55, 1.0, v)
    color = mix(color, flat((0.11, 0.17, 0.06)), moss * 0.85)
    height += moss * 1.5
    return Layer("shingles", color, height, 0.93, normal_strength=1.0)


def rust():
    big = fbm(SIZE, 4, 5, 0.55, 181)
    flake = smoothstep(-0.1, 0.25, fbm(SIZE, 18, 4, 0.6, 182) + big * 0.4)
    height = flake * 1.6 + fbm(SIZE, 120, 3, 0.6, 183) * 0.7 + big * 0.8
    color = ramp(remap(big * 0.5 + fbm(SIZE, 30, 4, 0.55, 184) * 0.5), [(0.0, (0.10, 0.055, 0.04)), (0.35, (0.24, 0.11, 0.06)), (0.7, (0.38, 0.19, 0.09)), (1.0, (0.50, 0.30, 0.14))])
    paint = smoothstep(0.35, 0.5, fbm(SIZE, 6, 4, 0.6, 185)) * (1.0 - flake)
    color = mix(color, flat((0.20, 0.22, 0.20)), paint * 0.8)
    rng = np.random.default_rng(186)
    pts = [(x, y) for y in (40, SIZE // 2 + 40) for x in range(32, SIZE, 64)] + [(x, y) for x in (40, SIZE // 2 + 40) for y in range(32, SIZE, 64)]
    riv = T.dots(SIZE, pts, 7.0)
    seam = np.zeros((SIZE, SIZE), dtype=np.float32)
    seam[18:22, :] = 1.0
    seam[SIZE // 2 + 18:SIZE // 2 + 22, :] = 1.0
    seam[:, 18:22] = 1.0
    seam[:, SIZE // 2 + 18:SIZE // 2 + 22] = 1.0
    height += riv * 3.0 - blur(seam, 1.0) * 2.5
    color *= (1.0 - 0.5 * blur(seam, 1.5))[..., None]
    run = T.streaks(SIZE, 187, 24, 0.1) * np.clip(blur(riv, 6.0) * 6.0, 0, 1)
    color = mix(color, color * col(1.15, 0.8, 0.55), run * 0.6)
    return Layer("rust", color, height, 0.8, normal_strength=1.0)


def aluminum():
    g = 0.42 + fbm(SIZE, 3, 4, 0.5, 191) * 0.05 + fbm(SIZE, 90, 2, 0.5, 192, stretch=(0.2, 3.0)) * 0.025
    color = np.stack([g * 0.98, g * 1.0, g * 1.03], axis=2)
    height = fbm(SIZE, 4, 3, 0.5, 193) * 1.2
    seam = np.zeros((SIZE, SIZE), dtype=np.float32)
    pts = []
    for k in range(4):
        y = k * SIZE // 4 + 20
        seam[y:y + 3, :] = 1.0
        pts += [(x, y - 9) for x in range(12, SIZE, 24)] + [(x, y + 12) for x in range(12, SIZE, 24)]
    for k in range(2):
        x = k * SIZE // 2 + 50
        seam[:, x:x + 3] = 1.0
        pts += [(x - 9, y) for y in range(12, SIZE, 24)] + [(x + 12, y) for y in range(12, SIZE, 24)]
    riv = T.dots(SIZE, pts, 3.2)
    height += riv * 1.2 - blur(seam, 0.8) * 2.0
    color *= (1.0 - 0.45 * blur(seam, 1.2))[..., None] * (1.0 - 0.25 * riv)[..., None]
    per_panel = T.per_id((np.mgrid[0:SIZE, 0:SIZE][0] // (SIZE // 4)) * 2 + (np.mgrid[0:SIZE, 0:SIZE][1] // (SIZE // 2)), 194)
    color *= (0.9 + 0.2 * per_panel)[..., None]
    oil = T.streaks(SIZE, 195, 14, 0.08) * smoothstep(0.2, 0.7, fbm(SIZE, 3, 3, 0.5, 196))
    color *= (1.0 - 0.5 * oil)[..., None]
    scorch = smoothstep(0.3, 0.75, fbm(SIZE, 2, 4, 0.6, 197))
    color = mix(color, color * col(0.35, 0.32, 0.30), scorch * 0.8)
    rough = 0.45 + scorch * 0.4 + oil * 0.2
    return Layer("aluminum", color, height, np.clip(rough, 0, 1), normal_strength=0.9)


def masonry():
    warp_x = fbm(SIZE, 6, 3, 0.5, 201) * 18.0
    warp_y = fbm(SIZE, 6, 3, 0.5, 202) * 12.0
    _d, edge, ident = cells(SIZE, 150, 203, stretch=(0.75, 1.15), jitter=1.0)
    yy, xx = np.mgrid[0:SIZE, 0:SIZE]
    sx = np.mod(xx + warp_x, SIZE).astype(np.int32)
    sy = np.mod(yy + warp_y, SIZE).astype(np.int32)
    edge, ident = edge[sy, sx], ident[sy, sx]
    per = T.per_id(ident, 204)
    face = smoothstep(2.0, 9.0, edge)
    height = face * (7.0 + per * 5.0) + fbm(SIZE, 40, 4, 0.6, 205) * 1.6 * face + fbm(SIZE, 150, 2, 0.5, 206) * 0.5
    g = 0.27 + per * 0.16 + fbm(SIZE, 50, 3, 0.5, 207) * 0.05
    stone = np.stack([g * 1.04, g, g * 0.94], axis=2)
    stone = mix(stone, stone * col(1.15, 0.95, 0.78), (T.per_id(ident, 208) > 0.6).astype(np.float32) * 0.6)
    mortar = ramp(remap(fbm(SIZE, 50, 3, 0.5, 209)), [(0.0, (0.26, 0.25, 0.22)), (1.0, (0.44, 0.42, 0.37))])
    color = mix(mortar, stone, face)
    moss = (1.0 - face) * smoothstep(0.0, 0.5, fbm(SIZE, 4, 3, 0.5, 210))
    color = mix(color, flat((0.10, 0.15, 0.06)), moss * 0.7)
    lichen = smoothstep(0.35, 0.55, fbm(SIZE, 14, 4, 0.6, 211)) * face
    color = mix(color, flat((0.47, 0.50, 0.42)), lichen * 0.4)
    return Layer("masonry", color, height, 0.9, normal_strength=0.8)


def floorboards():
    edge, ident, u, along = T.boards(SIZE, 9, 221, vertical=False, gap=2.5, lengths=700)
    per = T.per_id(ident, 222)
    grain = fbm(SIZE, 50, 4, 0.55, 223, stretch=(0.05, 1.0))
    height = smoothstep(-1.0, 2.0, edge) * 2.0 + grain * 0.6 + (per - 0.5) * 0.8
    color = ramp(remap(per * 0.5 + grain * 0.5), [(0.0, (0.09, 0.065, 0.045)), (0.5, (0.17, 0.12, 0.08)), (1.0, (0.27, 0.20, 0.13))])
    color *= (0.4 + 0.6 * smoothstep(-1.0, 1.5, edge))[..., None]
    dust = smoothstep(0.0, 0.6, fbm(SIZE, 4, 4, 0.55, 224))
    color = mix(color, flat((0.33, 0.31, 0.27)), dust * 0.35)
    scuff = smoothstep(0.3, 0.6, fbm(SIZE, 9, 3, 0.5, 225, stretch=(0.3, 1.0))) * 0.25
    color = mix(color, color * 1.5, scuff)
    return Layer("floorboards", color, height, 0.75 - scuff * 0.3 + dust * 0.15, normal_strength=0.9)


def army_paint():
    big = fbm(SIZE, 3, 4, 0.5, 231)
    g = 0.5 + big * 0.08 + fbm(SIZE, 40, 3, 0.5, 232) * 0.04
    color = np.stack([g * 0.36, g * 0.38, g * 0.22], axis=2)
    height = fbm(SIZE, 6, 3, 0.5, 233) * 0.8 + fbm(SIZE, 100, 2, 0.5, 234) * 0.2
    chip = smoothstep(0.26, 0.33, fbm(SIZE, 26, 4, 0.65, 235) * 0.7 + fbm(SIZE, 5, 2, 0.5, 236) * 0.5)
    rust_c = ramp(remap(fbm(SIZE, 40, 3, 0.5, 237)), [(0.0, (0.16, 0.08, 0.05)), (1.0, (0.40, 0.21, 0.10))])
    color = mix(color, rust_c, chip)
    height -= chip * 0.8
    run = T.streaks(SIZE, 238, 20, 0.1) * np.clip(blur(chip, 5.0) * 3.0, 0, 1)
    color = mix(color, color * col(1.2, 0.85, 0.6), run * 0.5)
    dust = smoothstep(0.2, 0.8, fbm(SIZE, 3, 3, 0.5, 239))
    color = mix(color, flat((0.30, 0.27, 0.21)), dust * 0.3)
    return Layer("army_paint", color, height, 0.7 + chip * 0.2, normal_strength=0.8)


def cloth():
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
    weave = (np.sin(xx * np.pi / 2.0) * 0.5 + 0.5) * (np.sin(yy * np.pi / 2.0 + np.pi * (np.floor(xx / 2.0) % 2)) * 0.5 + 0.5)
    crease = fbm(SIZE, 5, 4, 0.55, 241, stretch=(1.0, 0.5))
    height = weave * 0.8 + crease * 4.0 + fbm(SIZE, 14, 3, 0.5, 242) * 1.5
    g = 0.62 + weave * 0.08 + crease * 0.08 + fbm(SIZE, 60, 2, 0.5, 243) * 0.03
    color = np.stack([g, g * 0.985, g * 0.95], axis=2)
    stain = smoothstep(0.25, 0.6, fbm(SIZE, 4, 4, 0.6, 244))
    color = mix(color, color * col(0.72, 0.64, 0.5), stain * 0.6)
    return Layer("cloth", color, height, 0.95, normal_strength=0.9)


def wall_paint():
    big = fbm(SIZE, 3, 4, 0.5, 251)
    height = big * 1.0 + fbm(SIZE, 30, 3, 0.5, 252) * 0.4
    g = 0.66 + big * 0.05 + fbm(SIZE, 50, 2, 0.5, 253) * 0.02
    color = np.stack([g, g * 0.99, g * 0.95], axis=2)
    peel_n = fbm(SIZE, 9, 5, 0.62, 254) * 0.7 + fbm(SIZE, 2, 2, 0.5, 255) * 0.5
    peel = smoothstep(0.3, 0.34, peel_n)
    under = ramp(remap(fbm(SIZE, 30, 3, 0.5, 256)), [(0.0, (0.36, 0.34, 0.30)), (1.0, (0.52, 0.50, 0.45))])
    color = mix(color, under, peel)
    lip = smoothstep(0.23, 0.3, peel_n) * (1.0 - peel)
    height += lip * 2.2 - peel * 1.2
    color *= (1.0 - 0.18 * lip)[..., None]
    mould = smoothstep(0.3, 0.7, fbm(SIZE, 5, 4, 0.6, 257)) * smoothstep(0.0, 0.5, fbm(SIZE, 2, 2, 0.5, 258))
    spots = smoothstep(0.1, 0.4, fbm(SIZE, 70, 3, 0.6, 259))
    color = mix(color, flat((0.10, 0.12, 0.09)), mould * spots * 0.75)
    crack = T.cracks(SIZE, 14, 260, 1.3, 0.4)
    color *= (1.0 - 0.45 * crack)[..., None]
    height -= crack * 1.5
    return Layer("wall_paint", color, height, 0.8, normal_strength=1.0)


def rubble():
    height = fbm(SIZE, 5, 4, 0.5, 261) * 5.0 + fbm(SIZE, 40, 4, 0.6, 262) * 2.0
    color = ramp(remap(fbm(SIZE, 8, 5, 0.55, 263)), [(0.0, (0.20, 0.185, 0.165)), (0.5, (0.31, 0.29, 0.26)), (1.0, (0.43, 0.41, 0.37))])
    T.stamp_stones(height, color, 900, (3, 14), 264, lift=0.55, grey=(0.30, 0.55), warm=0.0, sink=0.2)

    def red(rng):
        k = rng.random()
        return (0.26 + k * 0.14, 0.12 + k * 0.05, 0.085 + k * 0.03)
    T.stamp_stones(height, color, 260, (4, 17), 265, lift=0.5, sink=0.3, rgb=red)
    T.stamp_stones(height, color, 40, (14, 46), 266, lift=0.5, grey=(0.42, 0.62), warm=0.0, sink=0.3)

    def splinter(rng):
        return (0.26, 0.21, 0.16) if rng.random() < 0.7 else (0.12, 0.10, 0.08)
    rgb, cov = stamp_strokes(SIZE, 70, (20, 110), (2.0, 5.0), 267, splinter, curve=0.2)
    color = mix(color, rgb / np.maximum(cov, 1e-3)[..., None], np.clip(cov * 1.5, 0, 1))
    height += blur(cov, 0.8) * 3.0
    return Layer("rubble", color, height, 0.93, normal_strength=0.8)


def tiles():
    edge, ident, u, v = T.bricks(SIZE, 10, 10, 3.0, 271, bond=0.0)
    per = T.per_id(ident, 272)
    face = smoothstep(-0.5, 2.0, edge)
    gone = (per > 0.93).astype(np.float32)
    g = 0.72 + (per - 0.5) * 0.08 + fbm(SIZE, 5, 3, 0.5, 273) * 0.04
    color = np.stack([g, g * 0.99, g * 0.94], axis=2)
    grout = flat((0.20, 0.19, 0.17))
    color = mix(grout, color, face)
    under = ramp(remap(fbm(SIZE, 40, 3, 0.5, 274)), [(0.0, (0.25, 0.23, 0.20)), (1.0, (0.40, 0.37, 0.32))])
    color = mix(color, under, gone * face)
    height = face * (2.0 - gone * 2.5) + fbm(SIZE, 4, 2, 0.5, 275) * 0.6
    crack = T.cracks(SIZE, 40, 276, 1.0, 0.6) * (T.per_id(ident, 277) > 0.6)
    color *= (1.0 - 0.6 * crack * face)[..., None]
    grime = T.streaks(SIZE, 278, 18, 0.12) * smoothstep(0.1, 0.7, fbm(SIZE, 3, 3, 0.5, 279))
    color = mix(color, color * col(0.55, 0.50, 0.38), grime * 0.75)
    rough = 0.25 + (1.0 - face) * 0.6 + gone * 0.6 + grime * 0.3
    return Layer("tiles", color, height, np.clip(rough, 0, 1), normal_strength=0.9)


def iron():
    height = fbm(SIZE, 30, 4, 0.6, 281) * 1.0 + fbm(SIZE, 4, 3, 0.5, 282) * 1.0
    pits = np.clip(blur((white(SIZE, 283) > 0.9993).astype(np.float32) * smoothstep(-0.1, 0.4, fbm(SIZE, 5, 3, 0.5, 288)), 1.2) * 12.0, 0, 1)
    height -= pits * 1.5
    g = 0.11 + fbm(SIZE, 6, 4, 0.5, 284) * 0.03 + fbm(SIZE, 80, 2, 0.5, 285) * 0.015
    color = np.stack([g, g * 1.02, g * 1.06], axis=2)
    bloom = smoothstep(0.25, 0.6, fbm(SIZE, 10, 5, 0.6, 286))
    color = mix(color, flat((0.26, 0.13, 0.07)), bloom * 0.6)
    worn = smoothstep(0.3, 0.6, fbm(SIZE, 14, 3, 0.5, 287)) * 0.3
    color = mix(color, color * 2.2, worn)
    return Layer("iron", color, height, 0.55 + bloom * 0.3 - worn * 0.2, normal_strength=0.9)


def enamel():
    g = 0.74 + fbm(SIZE, 3, 3, 0.5, 291) * 0.04
    color = np.stack([g, g * 0.995, g * 0.96], axis=2)
    height = fbm(SIZE, 5, 3, 0.5, 292) * 0.5
    chip = smoothstep(0.27, 0.31, fbm(SIZE, 20, 4, 0.65, 293) * 0.6 + fbm(SIZE, 4, 2, 0.5, 294) * 0.45)
    color = mix(color, flat((0.07, 0.06, 0.06)), chip)
    height -= chip * 1.0
    halo = np.clip(blur(chip, 5.0) * 3.0, 0, 1) * (1.0 - chip)
    color = mix(color, color * col(1.0, 0.72, 0.48), halo * 0.7)
    run = T.streaks(SIZE, 295, 22, 0.1) * np.clip(blur(chip, 9.0) * 4.0, 0, 1)
    color = mix(color, color * col(0.95, 0.68, 0.45), run * 0.5)
    grime = smoothstep(0.2, 0.8, fbm(SIZE, 2, 4, 0.55, 296))
    color = mix(color, color * col(0.7, 0.66, 0.56), grime * 0.5)
    return Layer("enamel", color, height, 0.3 + chip * 0.5 + grime * 0.2, normal_strength=0.8)


STRUCTURE = [plaster, brick, concrete, planks, shingles, rust, aluminum, masonry, floorboards, army_paint, cloth, wall_paint, rubble, tiles, iron, enamel]
STRUCTURE_SCALE = {"plaster": 2.4, "brick": 2.4, "concrete": 3.0, "planks": 2.0, "shingles": 2.4, "rust": 2.0, "aluminum": 2.4,
                   "masonry": 2.6, "floorboards": 1.8, "army_paint": 2.0, "cloth": 1.0, "wall_paint": 2.4, "rubble": 2.0,
                   "tiles": 1.5, "iron": 1.0, "enamel": 1.2}


GROUND = [forest_floor, grass, rock, dirt]

SETS = {"ground": ("ground", GROUND), "structure": ("structure", STRUCTURE)}


def main():
    want = sys.argv[1:] or list(SETS)
    for key in want:
        name, makers = SETS[key]
        layers = [m() for m in makers]
        names = T.write_array("tex", name, layers)
        print(key, "->", ", ".join(names))


if __name__ == "__main__":
    main()
