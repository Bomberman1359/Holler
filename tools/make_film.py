#!/usr/bin/env python3
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import texlib as T
from texlib import fbm

GRAIN = 256
DIRT = 512


def band(size, lo, hi, seed):
    rng = np.random.default_rng(seed)
    fy = np.fft.fftfreq(size)[:, None]
    fx = np.fft.rfftfreq(size)[None, :]
    f = np.sqrt(fx * fx + fy * fy) + 1e-9
    keep = np.exp(-((1.0 / f - (lo + hi) * 0.5) ** 2) / (2.0 * ((hi - lo) * 0.5 + 0.3) ** 2))
    spec = keep * np.exp(2j * np.pi * rng.random(keep.shape))
    out = np.fft.irfft2(spec, s=(size, size))
    out /= max(float(out.std()) * 3.0, 1e-9)
    return np.clip(out, -1.0, 1.0)


def grain():
    fine = band(GRAIN, 1.6, 3.2, 11)
    clump = band(GRAIN, 4.0, 9.0, 12)
    blotch = fbm(GRAIN, 3, 3, 0.5, 13)
    data = np.stack([fine, clump, blotch], axis=2) * 0.5 + 0.5
    return Image.fromarray((np.clip(data, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB")


def wrapped(draw_fn, size):
    big = Image.new("L", (size * 3, size * 3), 0)
    draw_fn(ImageDraw.Draw(big), size)
    a = np.asarray(big, dtype=np.float32)
    out = np.zeros((size, size), dtype=np.float32)
    for j in range(3):
        for i in range(3):
            out = np.maximum(out, a[j * size:(j + 1) * size, i * size:(i + 1) * size])
    return out / 255.0


def dirt():
    rng = np.random.default_rng(21)

    def dark(d, size):
        for _ in range(46):
            x, y = rng.uniform(size, size * 2, 2)
            r = rng.uniform(0.7, 2.4)
            d.ellipse([x - r, y - r, x + r, y + r], fill=int(rng.uniform(120, 255)))
        for _ in range(7):
            x, y = rng.uniform(size, size * 2, 2)
            pts = []
            r = rng.uniform(2.5, 6.0)
            for k in range(7):
                a = k / 7.0 * 2 * math.pi
                rr = r * rng.uniform(0.4, 1.0)
                pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
            d.polygon(pts, fill=int(rng.uniform(150, 240)))
        for _ in range(5):
            x, y = rng.uniform(size, size * 2, 2)
            ang = rng.uniform(0, 2 * math.pi)
            curl = rng.uniform(-0.12, 0.12)
            pts = [(x, y)]
            for k in range(int(rng.uniform(18, 60))):
                ang += curl + rng.uniform(-0.08, 0.08)
                pts.append((pts[-1][0] + math.cos(ang) * 2.0, pts[-1][1] + math.sin(ang) * 2.0))
            d.line(pts, fill=int(rng.uniform(130, 220)), width=1)

    def bright(d, size):
        for _ in range(26):
            x, y = rng.uniform(size, size * 2, 2)
            r = rng.uniform(0.6, 1.5)
            d.ellipse([x - r, y - r, x + r, y + r], fill=int(rng.uniform(140, 255)))

    r = wrapped(dark, DIRT)
    g = wrapped(bright, DIRT)
    r = np.asarray(Image.fromarray((r * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)), dtype=np.float32) / 255.0
    g = np.asarray(Image.fromarray((g * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.5)), dtype=np.float32) / 255.0
    b = fbm(DIRT, 4, 4, 0.55, 23) * 0.5 + 0.5
    data = np.stack([r, g, b], axis=2)
    return Image.fromarray((np.clip(data, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB")


def main():
    T.write_texture("tex", "film_grain.png", grain(), compressed=False, mips=False, fix_alpha=False)
    T.write_texture("tex", "film_dirt.png", dirt(), compressed=False, mips=False, fix_alpha=False)
    print("film grain %d px, dirt %d px" % (GRAIN, DIRT))


if __name__ == "__main__":
    main()
