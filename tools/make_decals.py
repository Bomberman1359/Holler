#!/usr/bin/env python3
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import maplib
import texlib as T
from texlib import fbm, smoothstep

SHEET_W, SHEET_H = 2048, 4096
PAD = 6
FONTS = os.path.join(maplib.ROOT, "assets", "fonts")
BLOOD = (0.105, 0.028, 0.02)


def font(name, size):
    files = {"type": "SpecialElite-Regular.ttf", "courier": "CourierPrime-Regular.ttf", "courier_bold": "CourierPrime-Bold.ttf",
             "fell": "IMFePIrm28P.ttf", "fell_italic": "IMFePIit28P.ttf", "fraktur": "UnifrakturCook-Bold.ttf",
             "hand": "HomemadeApple-Regular.ttf", "scrawl": "ReenieBeanie.ttf", "paint": "RockSalt-Regular.ttf"}
    return ImageFont.truetype(os.path.join(FONTS, files[name]), size)


def rgba(rgb, alpha):
    h, w = alpha.shape
    out = np.zeros((h, w, 4), dtype=np.float32)
    out[..., :3] = np.asarray(rgb, dtype=np.float32)
    out[..., 3] = np.clip(alpha, 0.0, 1.0)
    return out


def noise(h, w, freq, seed, octaves=4, stretch=(1.0, 1.0)):
    s = max(h, w)
    return fbm(s, freq, octaves, 0.55, seed, stretch=stretch)[:h, :w]


def falloff(h, w, power=2.0, sx=1.0, sy=1.0):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx = (xx - w / 2) / (w / 2) / sx
    dy = (yy - h / 2) / (h / 2) / sy
    return np.clip(1.0 - (dx * dx + dy * dy) ** (power / 2.0), 0.0, 1.0)


def edge_fade(h, w, px=8):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy))
    return np.clip(d / px, 0.0, 1.0)


def pool(seed, size=256):
    n = noise(size, size, 3, seed) * 0.5 + noise(size, size, 9, seed + 1) * 0.2
    body = smoothstep(0.42, 0.5, falloff(size, size, 2.0, 0.8, 0.8) * 0.75 + n * 0.45)
    rim = smoothstep(0.36, 0.42, falloff(size, size, 2.0, 0.8, 0.8) * 0.75 + n * 0.45) - body
    rng = np.random.default_rng(seed)
    drops = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(drops)
    for _ in range(40):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.3, 0.48) * size
        x, y = size / 2 + math.cos(a) * r, size / 2 + math.sin(a) * r
        s = rng.uniform(1.0, 5.0)
        d.ellipse([x - s, y - s * rng.uniform(0.6, 1.4), x + s, y + s], fill=255)
    drops = np.asarray(drops.filter(ImageFilter.GaussianBlur(0.8)), dtype=np.float32) / 255.0
    alpha = np.clip(body * 0.9 + rim * 0.75 + drops * 0.8, 0, 1) * edge_fade(size, size)
    shade = 0.75 + 0.5 * noise(size, size, 14, seed + 2)
    col = np.array(BLOOD)[None, None, :] * shade[..., None] * (1.0 - 0.45 * rim[..., None])
    return rgba(col, alpha)


def smear(seed, w=512, h=160):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    lanes = fbm(max(w, h), 26, 3, 0.5, seed, stretch=(0.04, 1.0))[:h, :w]
    band = smoothstep(0.0, 0.5, falloff(h, w, 2.0, 2.0, 0.85))
    thin = 1.0 - smoothstep(0.1, 0.95, xx / w)
    alpha = smoothstep(-0.15, 0.35, lanes) * band * (0.35 + 0.65 * thin) * edge_fade(h, w, 10)
    blotch = smoothstep(0.1, 0.5, noise(h, w, 5, seed + 1)) * (1.0 - smoothstep(0.0, 0.35, xx / w)) * band
    alpha = np.clip(alpha * 0.85 + blotch * 0.6, 0, 1)
    shade = 0.7 + 0.6 * noise(h, w, 18, seed + 2, stretch=(0.2, 1.0))
    return rgba(np.array(BLOOD)[None, None, :] * shade[..., None], alpha)


def spatter(seed, size=256):
    rng = np.random.default_rng(seed)
    img = Image.new("L", (size * 2, size * 2), 0)
    d = ImageDraw.Draw(img)
    cx, cy = size * 0.6, size * 1.0
    for _ in range(170):
        a = rng.normal(0.0, 0.5)
        r = abs(rng.normal(0, 0.45)) * size * 1.6
        x, y = cx + math.cos(a) * r, cy + math.sin(a) * r
        s = max(rng.uniform(1.5, 9.0) * (1.0 - r / (size * 1.7)), 1.0)
        L = s * rng.uniform(1.0, 3.5)
        d.ellipse([x - L, y - s, x + L, y + s], fill=255)
    for _ in range(8):
        x, y = cx + rng.uniform(-30, 60), cy + rng.uniform(-50, 50)
        s = rng.uniform(10, 28)
        d.ellipse([x - s, y - s * 0.8, x + s, y + s * 0.8], fill=255)
    a = np.asarray(img.resize((size, size), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.6)), dtype=np.float32) / 255.0
    shade = 0.75 + 0.5 * noise(size, size, 12, seed + 1)
    return rgba(np.array(BLOOD)[None, None, :] * shade[..., None], a * 0.92 * edge_fade(size, size))


def handprint(seed, w=256, h=400, dragged=False):
    rng = np.random.default_rng(seed)
    s = 3
    img = Image.new("L", (w * s, h * s), 0)
    d = ImageDraw.Draw(img)
    px, py = w * s * 0.5, h * s * (0.78 if not dragged else 0.4)
    pr = w * s * 0.2
    d.ellipse([px - pr, py - pr * 0.9, px + pr, py + pr * 1.1], fill=255)
    for k, ang in enumerate((-0.42, -0.16, 0.06, 0.28)):
        L = h * s * (0.55 if not dragged else 0.3) * (0.82 + 0.18 * math.sin((k + 0.6) * 1.1))
        x0, y0 = px + math.sin(ang) * pr * 0.9, py - pr * 0.7
        segs = 3
        for j in range(segs):
            t0, t1 = j / segs, (j + 0.86) / segs
            a0 = (x0 + math.sin(ang) * L * t0, y0 - math.cos(ang) * L * t0)
            a1 = (x0 + math.sin(ang) * L * t1, y0 - math.cos(ang) * L * t1)
            d.line([a0, a1], fill=255, width=int(pr * (0.42 - 0.07 * j)))
            d.ellipse([a1[0] - pr * 0.2, a1[1] - pr * 0.2, a1[0] + pr * 0.2, a1[1] + pr * 0.2], fill=255)
    tx, ty = px + pr * 0.9, py + pr * 0.2
    d.line([(tx, ty), (tx + pr * 1.3, ty - pr * 1.0)], fill=255, width=int(pr * 0.42))
    if dragged:
        for k in range(5):
            x = px + (k - 2) * pr * 0.42 + rng.uniform(-6, 6)
            d.line([(x, py), (x + rng.uniform(-20, 20), h * s - 20)], fill=int(rng.uniform(120, 230)), width=int(pr * rng.uniform(0.18, 0.34)))
    a = np.asarray(img.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.0)), dtype=np.float32) / 255.0
    lines = smoothstep(-0.3, 0.2, noise(h, w, 40, seed + 1, stretch=(1.0, 0.3)))
    patchy = smoothstep(-0.4, 0.2, noise(h, w, 7, seed + 2))
    if dragged:
        yy = np.mgrid[0:h, 0:w][0] / h
        patchy = patchy * (1.0 - 0.75 * smoothstep(0.45, 1.0, yy))
    shade = 0.8 + 0.4 * noise(h, w, 10, seed + 3)
    return rgba(np.array(BLOOD)[None, None, :] * shade[..., None], a * (0.35 + 0.65 * lines) * (0.4 + 0.6 * patchy) * edge_fade(h, w))


def soot(seed, size=256):
    a = smoothstep(0.1, 0.75, falloff(size, size, 1.6) * 0.9 + noise(size, size, 4, seed) * 0.35)
    return rgba((0.012, 0.011, 0.01), a * 0.85 * edge_fade(size, size, 12))


def damp(seed, size=256):
    n = falloff(size, size, 1.8, 1.0, 0.9) * 0.8 + noise(size, size, 4, seed) * 0.4
    body = smoothstep(0.3, 0.5, n)
    line = smoothstep(0.26, 0.3, n) - smoothstep(0.3, 0.34, n)
    return rgba((0.05, 0.05, 0.035), (body * 0.45 + line * 0.5) * edge_fade(size, size, 10))


def rust_run(seed, w=96, h=384):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    lanes = fbm(max(w, h), 14, 3, 0.5, seed, stretch=(1.0, 0.03))[:h, :w]
    a = smoothstep(-0.1, 0.4, lanes) * (1.0 - smoothstep(0.2, 1.0, yy / h)) * smoothstep(0.0, 0.4, falloff(h, w, 2.0, 0.9, 4.0))
    return rgba((0.25, 0.10, 0.04), a * 0.75 * edge_fade(h, w, 6))


def crack(seed, size=384):
    c = T.cracks(size, 7, seed, 1.6, 0.75)
    a = c * edge_fade(size, size, 16) * smoothstep(0.0, 0.5, falloff(size, size, 2.0))
    return rgba((0.02, 0.018, 0.016), a * 0.9)


def bullet_holes(seed, w=384, h=256):
    rng = np.random.default_rng(seed)
    img = Image.new("L", (w, h), 0)
    ring = Image.new("L", (w, h), 0)
    d, dr = ImageDraw.Draw(img), ImageDraw.Draw(ring)
    for _ in range(11):
        x, y = rng.uniform(30, w - 30), rng.normal(h * 0.5, h * 0.14)
        s = rng.uniform(3.5, 8.0)
        dr.ellipse([x - s * 2.3, y - s * 2.0, x + s * 2.3, y + s * 2.0], fill=255)
        d.ellipse([x - s, y - s, x + s, y + s], fill=255)
    hole = np.asarray(img.filter(ImageFilter.GaussianBlur(0.8)), dtype=np.float32) / 255.0
    chip = np.asarray(ring.filter(ImageFilter.GaussianBlur(2.0)), dtype=np.float32) / 255.0
    chip = chip * smoothstep(-0.3, 0.3, noise(h, w, 30, seed + 1))
    col = np.zeros((h, w, 3), dtype=np.float32)
    col[:] = (0.34, 0.32, 0.29)
    col = col * (1.0 - hole[..., None]) + np.array([0.01, 0.01, 0.01]) * hole[..., None]
    return rgba(col, np.clip(chip * 0.8 + hole, 0, 1))


def leaves(seed, size=384):
    rng = np.random.default_rng(seed)
    img = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for _ in range(95):
        x, y = rng.uniform(40, size * 2 - 40), rng.uniform(40, size * 2 - 40)
        a = rng.uniform(0, 2 * math.pi)
        L, wd = rng.uniform(12, 30), rng.uniform(5, 12)
        k = rng.random()
        col = (int(60 + k * 50), int(38 + k * 30), int(16 + k * 12), 255)
        pts = [(x + math.cos(a) * L, y + math.sin(a) * L), (x + math.cos(a + 1.57) * wd, y + math.sin(a + 1.57) * wd),
               (x - math.cos(a) * L, y - math.sin(a) * L), (x - math.cos(a + 1.57) * wd, y - math.sin(a + 1.57) * wd)]
        d.polygon(pts, fill=col)
        d.line([pts[0], pts[2]], fill=(col[0] // 2, col[1] // 2, col[2] // 2, 255), width=1)
    out = np.asarray(img.resize((size, size), Image.LANCZOS), dtype=np.float32) / 255.0
    out[..., 3] *= edge_fade(size, size, 20)
    return out


def glass(seed, w=256, h=256, broken=False):
    n = noise(h, w, 5, seed) * 0.5 + 0.5
    streak = smoothstep(0.2, 0.8, fbm(max(w, h), 22, 3, 0.5, seed + 1, stretch=(1.0, 0.1))[:h, :w] * 0.5 + 0.5)
    alpha = 0.22 + 0.3 * n * streak
    col = np.zeros((h, w, 3), dtype=np.float32)
    col[:] = (0.20, 0.22, 0.21)
    if broken:
        rng = np.random.default_rng(seed)
        img = Image.new("L", (w, h), 255)
        d = ImageDraw.Draw(img)
        cx, cy = w * rng.uniform(0.35, 0.65), h * rng.uniform(0.35, 0.65)
        pts = []
        for k in range(14):
            a = k / 14 * 2 * math.pi + rng.uniform(-0.1, 0.1)
            r = rng.uniform(0.28, 0.62) * min(w, h) * (1.25 if k % 2 == 0 else 0.7)
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
        d.polygon(pts, fill=0)
        keep = np.asarray(img, dtype=np.float32) / 255.0
        edge = np.asarray(img.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(0.7)), dtype=np.float32) / 255.0
        alpha = alpha * keep + edge * 0.6
        col = col + edge[..., None] * 0.35
    return rgba(col, alpha)


def text_block(lines, face, size, color=(0, 0, 0), spacing=1.25, wear=0.0, seed=0, pad=10, align="left", wobble=0.0):
    f = font(face, size)
    ascent, descent = f.getmetrics()
    boxes = [f.getbbox(t) if t else (0, 0, 0, 0) for t in lines]
    widths = [b[2] - min(b[0], 0) for b in boxes]
    lh = int((ascent + descent) * spacing * 0.8) if face in ("paint", "hand") else int(size * spacing)
    room = int(size * 0.5) + (int(size * 0.5) if wobble else 0)
    w = max(widths) + pad * 2 + room
    h = lh * (len(lines) - 1) + ascent + descent + pad * 2 + room
    img = np.zeros((h, w), dtype=np.float32)
    rng = np.random.default_rng(seed)
    for k, t in enumerate(lines):
        if not t:
            continue
        line = Image.new("L", (w, ascent + descent + room), 0)
        x = pad + room // 2 if align == "left" else (w - widths[k]) // 2
        ImageDraw.Draw(line).text((x - min(boxes[k][0], 0), room // 2), t, font=f, fill=255)
        if wobble:
            line = line.rotate(rng.uniform(-wobble, wobble), resample=Image.BICUBIC)
        y = pad + k * lh
        part = np.asarray(line, dtype=np.float32) / 255.0
        hh = min(part.shape[0], h - y)
        img[y:y + hh] = np.maximum(img[y:y + hh], part[:hh])
    a = img
    if wear > 0.0:
        a = a * smoothstep(wear - 0.75, wear - 0.25, noise(h, w, 22, seed + 5) * 0.5 + 0.5 + noise(h, w, 4, seed + 6) * 0.25)
    ys, xs = np.where(a > 0.02)
    if len(ys):
        y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, h)
        x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, w)
        a = a[y0:y1, x0:x1]
    return rgba(np.array(color, dtype=np.float32), a)


def board(tex, ground, border=None, pad=14, wear=0.25, seed=0):
    h, w = tex.shape[0] + pad * 2, tex.shape[1] + pad * 2
    out = np.zeros((h, w, 4), dtype=np.float32)
    shade = 0.82 + 0.3 * noise(h, w, 6, seed) + 0.1 * noise(h, w, 40, seed + 1)
    out[..., :3] = np.array(ground, dtype=np.float32) * shade[..., None]
    out[..., 3] = 1.0
    if border is not None:
        b = 5
        for sl in (np.s_[:b, :], np.s_[-b:, :], np.s_[:, :b], np.s_[:, -b:]):
            out[sl + (slice(0, 3),)] = np.array(border, dtype=np.float32)
    a = tex[..., 3:4]
    out[pad:-pad, pad:-pad, :3] = out[pad:-pad, pad:-pad, :3] * (1 - a) + tex[..., :3] * a
    chip = smoothstep(0.80 - wear * 0.25, 0.86 - wear * 0.25, noise(h, w, 16, seed + 2) * 0.5 + 0.5 + noise(h, w, 3, seed + 3) * 0.2)
    out[..., :3] = out[..., :3] * (1 - chip[..., None]) + np.array([0.16, 0.12, 0.09]) * chip[..., None]
    return out


def paper(w, h, seed, lines=None, face="type", size=13, stain=0.4, blood=0.0, torn=True, heading=None, stamp=None):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    base = np.zeros((h, w, 3), dtype=np.float32)
    tone = 0.78 + 0.08 * noise(h, w, 4, seed) + 0.03 * noise(h, w, 60, seed + 1)
    base[:] = (0.86, 0.80, 0.64)
    base *= tone[..., None]
    fox = smoothstep(0.25, 0.7, noise(h, w, 7, seed + 2)) * stain
    base = base * (1 - fox[..., None]) + np.array([0.42, 0.31, 0.17]) * fox[..., None]
    fold = np.exp(-((yy - h * 0.5) / 1.5) ** 2) * 0.18 + np.exp(-((xx - w * 0.5) / 1.5) ** 2) * 0.12
    base *= (1.0 - fold)[..., None]
    y = int(h * 0.09)
    if heading:
        t = text_block([heading], "fell", int(size * 1.5), pad=0)
        th, tw = t.shape[:2]
        x = max((w - tw) // 2, 2)
        tw = min(tw, w - x)
        a = t[:th, :tw, 3:4] * 0.85
        base[y:y + th, x:x + tw] = base[y:y + th, x:x + tw] * (1 - a) + np.array([0.08, 0.07, 0.06]) * a
        y += th + 2
    if lines:
        t = text_block(lines, face, size, pad=0, spacing=1.35, wobble=0.6 if face in ("hand", "scrawl") else 0.0, seed=seed)
        th, tw = min(t.shape[0], h - y - 4), min(t.shape[1], w - int(w * 0.09) - 2)
        x = int(w * 0.09)
        a = t[:th, :tw, 3:4] * (0.8 if face in ("type", "courier") else 0.88)
        ink = np.array([0.10, 0.09, 0.10]) if face in ("type", "courier") else np.array([0.08, 0.09, 0.16])
        base[y:y + th, x:x + tw] = base[y:y + th, x:x + tw] * (1 - a) + ink * a
    if stamp:
        t = text_block([stamp], "courier_bold", int(size * 1.3), pad=6)
        im = Image.fromarray((t[..., 3] * 255).astype(np.uint8))
        d = ImageDraw.Draw(im)
        d.rectangle([1, 1, im.width - 2, im.height - 2], outline=255, width=2)
        im = im.rotate(rng.uniform(-14, -6), expand=True, resample=Image.BICUBIC)
        sa = np.asarray(im, dtype=np.float32) / 255.0
        sh, sw = min(sa.shape[0], h - 8), min(sa.shape[1], w - 8)
        x, yy0 = w - sw - 6, h - sh - int(h * 0.12)
        a = (sa[:sh, :sw] * smoothstep(-0.3, 0.3, noise(sh, sw, 20, seed + 7)))[..., None] * 0.7
        base[yy0:yy0 + sh, x:x + sw] = base[yy0:yy0 + sh, x:x + sw] * (1 - a) + np.array([0.45, 0.08, 0.07]) * a
    alpha = np.ones((h, w), dtype=np.float32)
    if torn:
        n1 = noise(h, w, 30, seed + 3)
        n2 = noise(h, w, 5, seed + 4)
        d = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy))
        alpha = smoothstep(0.0, 1.5, d - 2.5 - n1 * 2.0 - np.maximum(n2, 0.0) * 9.0 * (rng.random() < 0.7))
        corner = (xx + yy * 0.8) - rng.uniform(10, 34)
        alpha *= smoothstep(-2.0, 2.0, corner + n1 * 6.0)
    if blood > 0.0:
        b = smoothstep(0.78 - blood * 0.4, 0.86 - blood * 0.4, noise(h, w, 3, seed + 8) * 0.5 + 0.5 + noise(h, w, 20, seed + 9) * 0.06)
        base = base * (1 - b[..., None] * 0.92) + np.array(BLOOD) * 1.6 * b[..., None] * 0.92
    return rgba(base, alpha)


def ruler(w=96, h=1024, top=9, every=1):
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    f = font("courier_bold", 24)
    d.line([(8, 0), (8, h)], fill=255, width=3)
    n = top // every * 2
    for k in range(n + 1):
        y = h - 4 - k * (h - 8) / float(n)
        d.line([(8, y), (40 if k % 2 == 0 else 24, y)], fill=255, width=3)
        if k % 2 == 0 and k > 0:
            d.text((44, y - 15), "%d" % (k // 2 * every), font=f, fill=255)
    a = np.asarray(img, dtype=np.float32) / 255.0
    a *= smoothstep(-0.55, -0.1, noise(h, w, 20, 77, stretch=(1.0, 0.3)))
    return rgba((0.05, 0.05, 0.05), a)


def star(size=256):
    s = 3
    img = Image.new("L", (size * s, size * s), 0)
    d = ImageDraw.Draw(img)
    c, r = size * s / 2, size * s * 0.46
    d.ellipse([c - r, c - r, c + r, c + r], outline=255, width=int(size * s * 0.035))
    pts = []
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        rr = r * (0.84 if k % 2 == 0 else 0.33)
        pts.append((c + math.cos(a) * rr, c + math.sin(a) * rr))
    d.polygon(pts, fill=255)
    a = np.asarray(img.resize((size, size), Image.LANCZOS), dtype=np.float32) / 255.0
    a *= smoothstep(-0.6, -0.15, noise(size, size, 14, 91))
    return rgba((0.78, 0.77, 0.72), a)


def tally(seed=5, w=512, h=200):
    rng = np.random.default_rng(seed)
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    x = 14
    while x < w - 60:
        for k in range(4):
            d.line([(x + k * 9 + rng.uniform(-2, 2), 30 + rng.uniform(-6, 6)), (x + k * 9 + rng.uniform(-3, 3), h - 30 + rng.uniform(-8, 8))], fill=255, width=2)
        d.line([(x - 5, h - 44 + rng.uniform(-10, 10)), (x + 36, 44 + rng.uniform(-10, 10))], fill=255, width=2)
        x += 58 + rng.uniform(-4, 8)
    a = np.asarray(img.filter(ImageFilter.GaussianBlur(0.5)), dtype=np.float32) / 255.0
    return rgba((0.72, 0.70, 0.66), a * 0.9)


def arrow(w=256, h=128):
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    d.line([(16, h / 2), (w - 40, h / 2 + 4)], fill=255, width=9)
    d.line([(w - 70, h / 2 - 34), (w - 20, h / 2 + 4), (w - 76, h / 2 + 40)], fill=255, width=9)
    a = np.asarray(img.filter(ImageFilter.GaussianBlur(0.8)), dtype=np.float32) / 255.0
    a *= smoothstep(-0.35, 0.25, noise(h, w, 30, 3))
    return rgba((0.80, 0.79, 0.74), a * 0.9)


CHALK = (0.80, 0.79, 0.74)
PAINT_BLACK = (0.03, 0.03, 0.03)
PAINT_RED = (0.33, 0.045, 0.035)


def pictures():
    p = {}
    for k in range(3):
        p["pool_%d" % k] = pool(300 + k * 7)
    for k in range(3):
        p["smear_%d" % k] = smear(330 + k * 7)
    p["drag_long"] = smear(351, 1024, 150)
    for k in range(2):
        p["spatter_%d" % k] = spatter(360 + k * 7)
    p["hand_big"] = handprint(371)
    p["hand_drag"] = handprint(372, 256, 512, dragged=True)
    for k in range(2):
        p["soot_%d" % k] = soot(380 + k)
        p["damp_%d" % k] = damp(384 + k)
        p["rust_run_%d" % k] = rust_run(388 + k)
        p["crack_%d" % k] = crack(392 + k)
    p["bullet_holes"] = bullet_holes(396)
    p["leaves"] = leaves(398)
    p["glass"] = glass(401)
    p["glass_broken_0"] = glass(402, broken=True)
    p["glass_broken_1"] = glass(403, broken=True)
    p["ruler"] = ruler()
    p["ruler_tall"] = ruler(top=18, every=2)
    p["star"] = star()
    p["tally"] = tally()
    p["chalk_arrow"] = arrow()

    halt = text_block(["HALT!"], "fraktur", 92, PAINT_BLACK, pad=4, align="center")
    sub = text_block(["Sperrgebiet", "Betreten verboten"], "fraktur", 38, PAINT_BLACK, pad=4, align="center", spacing=1.15)
    w = max(halt.shape[1], sub.shape[1])
    both = np.zeros((halt.shape[0] + sub.shape[0], w, 4), dtype=np.float32)
    both[:halt.shape[0], (w - halt.shape[1]) // 2:(w - halt.shape[1]) // 2 + halt.shape[1]] = halt
    both[halt.shape[0]:, (w - sub.shape[1]) // 2:(w - sub.shape[1]) // 2 + sub.shape[1]] = sub
    p["sign_halt"] = board(both, (0.74, 0.72, 0.64), border=PAINT_BLACK, wear=0.3, seed=411)
    p["sign_gasthaus"] = board(text_block(["Gasthaus zum Hirschen"], "fraktur", 64, (0.62, 0.52, 0.22), pad=6), (0.10, 0.13, 0.10), border=(0.5, 0.42, 0.18), wear=0.35, seed=412)
    p["sign_lookout"] = board(text_block(["Aussichtsturm  3 km"], "fell", 46, (0.9, 0.88, 0.8), pad=4), (0.16, 0.12, 0.08), wear=0.4, seed=413)
    p["sign_lazarett"] = board(text_block(["Heilstätte Hochwald", "Station B"], "fell", 44, PAINT_BLACK, pad=6, spacing=1.2), (0.72, 0.70, 0.62), border=PAINT_BLACK, wear=0.35, seed=414)
    p["sign_danger"] = board(text_block(["Lebensgefahr", "Hochspannung"], "fraktur", 50, (0.62, 0.08, 0.06), pad=6, spacing=1.15, align="center"), (0.76, 0.72, 0.5), border=(0.62, 0.08, 0.06), wear=0.3, seed=415)
    for n in ("12", "31", "7", "B"):
        p["stencil_" + n] = text_block([n], "courier_bold", 150, PAINT_BLACK, wear=0.35, seed=420 + len(n))
    for n in ("38 m", "61 m", "110 m", "240 m"):
        p["mark_" + n.split()[0]] = text_block(["— " + n], "courier_bold", 90, (0.82, 0.80, 0.74), wear=0.3, seed=430 + len(n), pad=6)

    p["wall_noch_da"] = text_block(["ICH BIN NOCH DA"], "paint", 70, (0.045, 0.04, 0.04), wear=0.2, seed=441, wobble=1.5)
    p["wall_hoert_alles"] = text_block(["12 HÖRT ALLES"], "scrawl", 96, (0.75, 0.73, 0.69), wear=0.15, seed=442, wobble=2.0)
    p["wall_nicht_auf"] = text_block(["ES HÖRT", "NICHT AUF"], "paint", 80, PAINT_RED, wear=0.25, seed=443, wobble=2.0, spacing=1.5)
    p["wall_nicht_hinsehen"] = text_block(["NICHT HINSEHEN"], "paint", 64, (0.045, 0.04, 0.04), wear=0.3, seed=444, wobble=1.5)
    p["chalk_dont_run"] = text_block(["DON'T RUN", "it hears"], "scrawl", 84, CHALK, wear=0.3, seed=451, wobble=2.5, spacing=1.0)
    p["chalk_radio"] = text_block(["DO NOT KEY", "THE RADIO"], "scrawl", 84, CHALK, wear=0.3, seed=452, wobble=2.0, spacing=1.0)
    p["chalk_six"] = text_block(["6 went up", "5", "4", "3"], "scrawl", 70, CHALK, wear=0.25, seed=453, wobble=3.0, spacing=1.0)
    p["chalk_count"] = text_block(["count the trees", "one of them", "is not a tree"], "scrawl", 66, CHALK, wear=0.3, seed=454, wobble=2.0, spacing=1.0)
    p["chalk_look_up"] = text_block(["don't look up"], "scrawl", 84, CHALK, wear=0.3, seed=455, wobble=2.0)

    p["notice"] = paper(200, 270, 461, ["Alle Bewohner verlassen", "den Ort bis 18 Uhr.", "Das Vieh bleibt.", "", "Nach Einbruch der", "Dunkelheit nicht zum", "Gelände hinsehen."],
                        "type", 13, heading="Räumungsbefehl", stamp="2. MÄRZ 1945", stain=0.35)
    p["sheet_typed"] = paper(150, 205, 462, ["xxxxxxx xxxx xxxxx", "xxx xxxxxxx xx xxx", "xxxxx xxxxxxx xxxx", "xx xxxxx xxx xxxxx", "xxxxxxxx xxx xxxx", "xxx xxxxx xxxxxxx"], "courier", 11, stain=0.5)
    p["sheet_hand"] = paper(150, 205, 463, ["mmm mmmmm mm", "mmmm mm mmmm", "mm mmmmm mmm", "mmmmm mm mm"], "hand", 11, stain=0.6)
    p["sheet_bloody"] = paper(150, 205, 464, ["mmm mmmm mm", "mmmm mm mmm", "mm mmmmm"], "hand", 11, stain=0.7, blood=0.55)
    p["sheet_blank"] = paper(150, 205, 465, None, stain=0.8)
    return p


def pack(pics):
    sheet = np.zeros((SHEET_H, SHEET_W, 4), dtype=np.float32)
    regions = {}
    x, y, row = PAD, PAD, 0
    for name in sorted(pics, key=lambda n: -pics[n].shape[0]):
        im = pics[name]
        h, w = im.shape[:2]
        if x + w + PAD > SHEET_W:
            x, y, row = PAD, y + row + PAD, 0
        if y + h + PAD > SHEET_H:
            raise SystemExit("the decal sheet is full at " + name)
        sheet[y:y + h, x:x + w] = im
        regions[name] = [x / SHEET_W, y / SHEET_H, (x + w) / SHEET_W, (y + h) / SHEET_H]
        x += w + PAD
        row = max(row, h)
    return sheet, regions, y + row


def main():
    pics = pictures()
    sheet, regions, used = pack(pics)
    rgb = T.bleed(sheet[..., :3], sheet[..., 3] > 0.02)
    out = np.dstack([rgb, sheet[..., 3]])
    img = Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")
    T.write_texture("tex", "decals.png", img, compressed=True, mips=True, fix_alpha=False)
    with open(os.path.join(maplib.out_dir("tex"), "decals.json"), "w") as f:
        json.dump(regions, f, indent=0)
    print("%d pictures on the sheet, %d of %d rows of pixels used" % (len(pics), used, SHEET_H))
    bg = Image.new("RGBA", img.size, (120, 124, 130, 255))
    bg.alpha_composite(img)
    bg.convert("RGB").crop((0, 0, SHEET_W, min(used + 8, SHEET_H))).save("/tmp/decals.jpg", quality=88)


if __name__ == "__main__":
    main()
