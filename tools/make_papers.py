#!/usr/bin/env python3
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import maplib
import texlib as T
from texlib import fbm, smoothstep

FONTS = os.path.join(maplib.ROOT, "assets", "fonts")
W, H = 768, 1024
FACES = {"type": "SpecialElite-Regular.ttf", "courier": "CourierPrime-Regular.ttf", "courier_bold": "CourierPrime-Bold.ttf",
         "fell": "IMFePIrm28P.ttf", "fell_italic": "IMFePIit28P.ttf", "fraktur": "UnifrakturCook-Bold.ttf",
         "pen": "HomemadeApple-Regular.ttf", "pencil": "ReenieBeanie.ttf", "scrawl": "RockSalt-Regular.ttf"}
BLOOD = np.array([0.20, 0.05, 0.035])
INK_TYPE = np.array([0.10, 0.09, 0.10])
INK_PENCIL = np.array([0.20, 0.20, 0.22])
INK_PEN = np.array([0.07, 0.08, 0.17])
INK_CARBON = np.array([0.20, 0.13, 0.36])


def font(face, size):
    return ImageFont.truetype(os.path.join(FONTS, FACES[face]), size)


def noise(freq, seed, octaves=4, stretch=(1.0, 1.0), h=H, w=W):
    s = max(h, w)
    return fbm(s, freq, octaves, 0.55, seed, stretch=stretch)[:h, :w]


class Sheet:

    def __init__(self, seed, color=(0.86, 0.81, 0.66), stain=0.35, w=W, h=H, margin=70):
        self.seed = seed
        self.w, self.h = w, h
        self.rng = np.random.default_rng(seed)
        tone = 0.80 + 0.09 * noise(4, seed, h=h, w=w) + 0.035 * noise(70, seed + 1, h=h, w=w)
        self.rgb = np.zeros((h, w, 3), dtype=np.float32)
        self.rgb[:] = color
        self.rgb *= tone[..., None]
        fox = smoothstep(0.2, 0.75, noise(7, seed + 2, h=h, w=w)) * stain
        self.rgb = self.rgb * (1 - fox[..., None]) + np.array([0.45, 0.33, 0.18]) * fox[..., None]
        self.alpha = np.ones((h, w), dtype=np.float32)
        self.ink = np.zeros((h, w), dtype=np.float32)
        self.ink_rgb = np.zeros((h, w, 3), dtype=np.float32)
        self.y = margin + 10
        self.margin = margin


    def _wrap(self, text, f, width):
        out = []
        for para in text.split("\n"):
            words = para.split(" ")
            line = ""
            for word in words:
                trial = (line + " " + word) if line else word
                if f.getlength(trial) <= width or not line:
                    line = trial
                else:
                    out.append(line)
                    line = word
            out.append(line)
        return out

    def write(self, text, face="type", size=30, color=INK_TYPE, gap=1.0, indent=0, align="left", wobble=0.0, strength=0.9, spacing=1.32, x=None, width=None,
              slant=0.0, bold=0, shaky=0.0):
        f = font(face, size)
        width = width or (self.w - self.margin * 2 - indent)
        ascent, descent = f.getmetrics()
        lh = int((ascent + descent) * spacing * (0.62 if face in ("scrawl", "pen") else 0.86))
        for line in self._wrap(text, f, width):
            if line:
                room = int(size * 0.8)
                img = Image.new("L", (self.w, ascent + descent + room * 2), 0)
                lx = (x if x is not None else self.margin + indent)
                if align == "center":
                    lx = (self.w - f.getlength(line)) / 2
                elif align == "right":
                    lx = self.w - self.margin - f.getlength(line)
                draw = ImageDraw.Draw(img)
                if shaky:
                    cx = lx + self.rng.uniform(-1.5, 1.5)
                    for ch in line:
                        draw.text((cx + self.rng.normal(0, shaky * 0.5), room + self.rng.normal(0, shaky)), ch, font=f, fill=255)
                        cx += f.getlength(ch)
                else:
                    draw.text((lx + self.rng.uniform(-1.5, 1.5) * (wobble > 0), room), line, font=f, fill=255)
                if bold:
                    img = img.filter(ImageFilter.MaxFilter(bold * 2 + 1))
                if slant:
                    base = room + ascent
                    img = img.transform(img.size, Image.AFFINE, (1.0, slant, -slant * base, 0.0, 1.0, 0.0), resample=Image.BICUBIC)
                if wobble:
                    img = img.rotate(self.rng.uniform(-wobble, wobble), resample=Image.BICUBIC, center=(lx, room + ascent))
                part = np.asarray(img, dtype=np.float32) / 255.0 * strength
                y0 = self.y - room
                ys = max(y0, 0)
                ye = min(y0 + part.shape[0], self.h)
                if ye > ys:
                    seg = part[ys - y0:ye - y0]
                    old = self.ink[ys:ye]
                    take = seg > old
                    self.ink[ys:ye] = np.maximum(old, seg)
                    self.ink_rgb[ys:ye][take] = color
            self.y += lh
        self.y += int(lh * (gap - 1.0) + lh * 0.45)

    def typed(self, text, face="type", size=30, color=INK_TYPE, gap=1.0, indent=0, strength=0.95, spacing=1.32, x=None, width=None, align="left",
              blur=0.0, pressure=0.45):
        f = font(face, size)
        adv = f.getlength("abcdefghijklmnopqrstuvwxyz") / 26.0 * 1.08
        width = width or (self.w - self.margin * 2 - indent)
        ascent, descent = f.getmetrics()
        lh = int((ascent + descent) * spacing * 0.86)
        tall = ascent + descent + 8
        cw = int(adv * 1.6) + 8
        ribbon = noise(18, self.seed + 70, stretch=(0.25, 1.0)) * 0.5 + 0.5

        class Mono:
            @staticmethod
            def getlength(t):
                return len(t) * adv

        for line in self._wrap(text, Mono, width):
            if line:
                lx = x if x is not None else self.margin + indent
                if align == "center":
                    lx = (self.w - adv * len(line)) / 2
                elif align == "right":
                    lx = self.w - self.margin - adv * len(line)
                tilt = self.rng.uniform(-1.2, 1.2)
                for i, ch in enumerate(line):
                    if ch == " ":
                        continue
                    hit = self.rng.uniform(1.0 - pressure, 1.0)
                    if self.rng.random() < 0.07:
                        hit *= 0.55
                    g = Image.new("L", (cw, tall), 0)
                    gd = ImageDraw.Draw(g)
                    gd.text((4, 4), ch, font=f, fill=255)
                    if self.rng.random() < 0.05:
                        gd.text((4 + self.rng.uniform(1.0, 2.0), 4 + self.rng.uniform(-1.0, 1.0)), ch, font=f, fill=110)
                    if blur:
                        g = g.filter(ImageFilter.GaussianBlur(blur))
                    a = np.asarray(g, dtype=np.float32) / 255.0
                    yy = np.linspace(-1.0, 1.0, tall)[:, None]
                    xx = np.linspace(-1.0, 1.0, cw)[None, :]
                    a = a * np.clip(hit + yy * self.rng.uniform(-0.45, 0.45) + xx * self.rng.uniform(-0.25, 0.25), 0.12, 1.0)
                    px = int(round(lx + i * adv + (adv - f.getlength(ch)) * 0.5 + self.rng.normal(0.0, 0.6))) - 4
                    py = int(round(self.y + self.rng.normal(0.0, 0.7) + tilt * i / max(len(line), 1))) - 4
                    ys, ye = max(py, 0), min(py + tall, self.h)
                    xs, xe = max(px, 0), min(px + cw, self.w)
                    if ye <= ys or xe <= xs:
                        continue
                    seg = a[ys - py:ye - py, xs - px:xe - px] * strength * (0.72 + 0.28 * ribbon[ys:ye, xs:xe])
                    old = self.ink[ys:ye, xs:xe]
                    take = seg > old
                    self.ink[ys:ye, xs:xe] = np.maximum(old, seg)
                    self.ink_rgb[ys:ye, xs:xe][take] = color
            self.y += lh
        self.y += int(lh * (gap - 1.0) + lh * 0.45)

    def stamp(self, text, cx, cy, size=40, color=(0.50, 0.10, 0.12), angle=-6.0, face="courier_bold", box=True, strength=0.85, seed=0, lines=None):
        f = font(face, size)
        rows = lines or [text]
        asc, desc = f.getmetrics()
        tw = max(f.getlength(r) for r in rows)
        pad = int(size * 0.4)
        bw, bh = int(tw + pad * 2), int((asc + desc) * len(rows) + pad * 2)
        img = Image.new("L", (bw + 24, bh + 24), 0)
        d = ImageDraw.Draw(img)
        for k, r in enumerate(rows):
            d.text((12 + pad + (tw - f.getlength(r)) / 2, 12 + pad + k * (asc + desc) - desc * 0.4), r, font=f, fill=255)
        if box:
            d.rectangle([14, 14, 10 + bw, 10 + bh], outline=255, width=max(3, size // 9))
        img = img.rotate(angle, resample=Image.BICUBIC, expand=True)
        a = np.asarray(img, dtype=np.float32) / 255.0
        h, w = a.shape
        n = noise(14, self.seed + 80 + seed, h=h, w=w) * 0.6 + noise(60, self.seed + 81 + seed, h=h, w=w) * 0.4
        a = a * smoothstep(-0.55, 0.15, n) * strength
        x0, y0 = int(cx - w / 2), int(cy - h / 2)
        ys, ye = max(y0, 0), min(y0 + h, self.h)
        xs, xe = max(x0, 0), min(x0 + w, self.w)
        seg = a[ys - y0:ye - y0, xs - x0:xe - x0]
        old = self.ink[ys:ye, xs:xe]
        take = seg > old * 0.8
        self.ink[ys:ye, xs:xe] = np.maximum(old, seg)
        self.ink_rgb[ys:ye, xs:xe][take] = color

    def pen_line(self, pts, color, width=3, strength=0.85):
        img = Image.new("L", (self.w, self.h), 0)
        ImageDraw.Draw(img).line(pts, fill=255, width=width, joint="curve")
        a = np.asarray(img.filter(ImageFilter.GaussianBlur(0.7)), dtype=np.float32) / 255.0 * strength
        take = a > self.ink
        self.ink = np.maximum(self.ink, a)
        self.ink_rgb[take] = color

    def skip(self, lines=1.0, size=30):
        self.y += int(size * 1.3 * lines)

    def rule(self, y=None, x0=None, x1=None, strength=0.5, color=INK_TYPE, thick=2):
        y = self.y if y is None else y
        x0 = self.margin if x0 is None else x0
        x1 = self.w - self.margin if x1 is None else x1
        self.ink[y:y + thick, x0:x1] = np.maximum(self.ink[y:y + thick, x0:x1], strength)
        self.ink_rgb[y:y + thick, x0:x1] = color

    def bar(self, x0, y0, x1, y1):
        n = noise(40, self.seed + 30, h=self.h, w=self.w)[y0:y1, x0:x1]
        self.ink[y0:y1, x0:x1] = 0.93 + 0.07 * n
        self.ink_rgb[y0:y1, x0:x1] = (0.03, 0.03, 0.04)

    def typed_wear(self, amount=0.35):
        n = noise(26, self.seed + 5, h=self.h, w=self.w) * 0.5 + 0.5 + noise(5, self.seed + 6, h=self.h, w=self.w) * 0.25
        self.ink *= smoothstep(amount - 0.55, amount + 0.05, n) * 0.5 + 0.5


    def water(self, y0, y1, strength=1.0):
        yy = np.arange(self.h, dtype=np.float32)[:, None]
        edge = noise(3, self.seed + 11, h=self.h, w=self.w) * 60.0
        band = smoothstep(y0 - 30, y0 + 30, yy + edge) * (1.0 - smoothstep(y1 - 30, y1 + 30, yy + edge))
        blurred = np.asarray(Image.fromarray((self.ink * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(7)), dtype=np.float32) / 255.0
        run = np.roll(blurred, 9, axis=0) * 0.5 + blurred * 0.5
        self.ink = self.ink * (1 - band * strength) + run * 0.55 * band * strength
        tide = np.abs(band - 0.5) < 0.12
        self.rgb *= (1.0 - 0.10 * band)[..., None]
        self.rgb[tide] *= 0.86

    def smear(self, y0, y1, x0=0, x1=None, color=(0.33, 0.22, 0.12), strength=0.9, drag=40):
        x1 = self.w if x1 is None else x1
        yy, xx = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
        n = noise(5, self.seed + 13, h=self.h, w=self.w, stretch=(0.35, 1.0))
        m = smoothstep(y0 - 20, y0 + 25, yy + n * 50) * (1.0 - smoothstep(y1 - 25, y1 + 20, yy + n * 50))
        m *= smoothstep(x0 - 30, x0 + 30, xx + n * 40) * (1.0 - smoothstep(x1 - 30, x1 + 30, xx + n * 40))
        streak = 0.55 + 0.45 * smoothstep(-0.3, 0.4, noise(30, self.seed + 14, h=self.h, w=self.w, stretch=(0.08, 1.0)))
        m = m * streak * strength
        dragged = np.asarray(Image.fromarray((self.ink * 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(drag)), dtype=np.float32) / 255.0
        self.ink = self.ink * (1 - m) + dragged * m * 0.6
        self.rgb = self.rgb * (1 - m[..., None] * 0.85) + np.array(color) * m[..., None] * 0.85

    def blood(self, cx, cy, radius, seed=0, strength=0.95):
        yy, xx = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
        d = np.hypot(xx - cx, yy - cy) / radius
        n = noise(5, self.seed + 20 + seed, h=self.h, w=self.w) * 0.45 + noise(24, self.seed + 21 + seed, h=self.h, w=self.w) * 0.12
        m = smoothstep(1.0, 0.75, d + n) * strength
        ring = smoothstep(0.75, 0.95, d + n) * smoothstep(1.05, 0.95, d + n)
        shade = 0.7 + 0.5 * noise(14, self.seed + 22 + seed, h=self.h, w=self.w)
        self.rgb = self.rgb * (1 - m[..., None]) + (BLOOD * shade[..., None]) * m[..., None]
        self.rgb *= (1.0 - 0.35 * ring)[..., None]
        self.ink *= 1.0 - m * 0.8
        for _ in range(int(radius / 12)):
            a = self.rng.uniform(0, 6.28)
            r = radius * self.rng.uniform(1.05, 1.9)
            px, py, pr = cx + np.cos(a) * r, cy + np.sin(a) * r, self.rng.uniform(1.5, 6.0)
            dm = smoothstep(pr, pr - 1.5, np.hypot(xx - px, yy - py))
            self.rgb = self.rgb * (1 - dm[..., None]) + BLOOD * 0.9 * dm[..., None]

    def burn(self, line, reach=90.0, holes=()):
        yy, xx = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
        xs, ys = zip(*line)
        edge = np.interp(np.arange(self.w), xs, ys)[None, :]
        n = noise(9, self.seed + 40, h=self.h, w=self.w) * 46.0 + noise(40, self.seed + 41, h=self.h, w=self.w) * 9.0
        d = edge - yy + n
        for (hx, hy, hr) in holes:
            d = np.minimum(d, (np.hypot(xx - hx, yy - hy) - hr) + n * 0.5)
        self.alpha *= smoothstep(0.0, 2.5, d)
        char = 1.0 - smoothstep(0.0, reach, d)
        self.rgb = self.rgb * (1 - char[..., None] * 0.93) + np.array([0.06, 0.045, 0.035]) * char[..., None] * 0.93
        brown = (1.0 - smoothstep(0.0, reach * 2.4, d)) * 0.5
        self.rgb = self.rgb * (1 - brown[..., None]) + np.array([0.34, 0.2, 0.09]) * brown[..., None]
        self.ink *= smoothstep(reach * 0.2, reach * 1.2, d) * 0.9 + 0.1

    def tear(self, line, below=True):
        yy = np.arange(self.h, dtype=np.float32)[:, None]
        xs, ys = zip(*line)
        edge = np.interp(np.arange(self.w), xs, ys)[None, :]
        n = noise(18, self.seed + 50, h=self.h, w=self.w) * 9.0 + noise(90, self.seed + 51, h=self.h, w=self.w) * 2.5
        d = (edge - yy + n) if below else (yy - edge + n)
        self.alpha *= smoothstep(0.0, 1.6, d)
        fibre = (1.0 - smoothstep(0.0, 7.0, d)) * 0.5
        self.rgb = self.rgb * (1 - fibre[..., None]) + np.array([0.93, 0.9, 0.82]) * fibre[..., None]
        self.ink *= smoothstep(1.0, 6.0, d)

    def folds(self, across=True, down=True):
        yy, xx = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
        f = np.zeros((self.h, self.w), dtype=np.float32)
        if across:
            f += np.exp(-((yy - self.h * 0.5) / 2.0) ** 2) * 0.2 + np.exp(-((yy - self.h * 0.5 - 4) / 9.0) ** 2) * 0.05
        if down:
            f += np.exp(-((xx - self.w * 0.5) / 2.0) ** 2) * 0.14
        self.rgb *= (1.0 - f)[..., None]

    def edges(self, rough=1.0, corner=None):
        yy, xx = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
        n1 = noise(30, self.seed + 3, h=self.h, w=self.w)
        n2 = noise(5, self.seed + 4, h=self.h, w=self.w)
        d = np.minimum(np.minimum(xx, self.w - 1 - xx), np.minimum(yy, self.h - 1 - yy))
        self.alpha *= smoothstep(0.0, 1.5, d - 5.0 - n1 * 3.0 * rough - np.maximum(n2, 0.0) * 14.0 * rough)
        dark = 1.0 - smoothstep(0.0, 46.0, d + n2 * 20.0)
        self.rgb *= (1.0 - 0.22 * dark)[..., None]
        if corner:
            cx, cy, size = corner
            c = np.abs(xx - cx) + np.abs(yy - cy) * 0.8 - size
            self.alpha *= smoothstep(-2.0, 2.0, c + n1 * 8.0)

    def ring(self, cx, cy, r):
        yy, xx = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
        d = np.abs(np.hypot(xx - cx, yy - cy) - r + noise(6, self.seed + 60, h=self.h, w=self.w) * 3.0)
        m = smoothstep(5.0, 1.0, d) * (0.5 + 0.5 * smoothstep(-0.4, 0.4, noise(4, self.seed + 61, h=self.h, w=self.w))) * 0.45
        self.rgb = self.rgb * (1 - m[..., None]) + np.array([0.36, 0.24, 0.11]) * m[..., None]

    def hole(self, cx, cy, r=7):
        yy, xx = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
        d = np.hypot(xx - cx, yy - cy)
        self.alpha *= smoothstep(r - 1.0, r + 0.5, d)
        rust = smoothstep(r + 14.0, r, d) * 0.6
        self.rgb = self.rgb * (1 - rust[..., None]) + np.array([0.36, 0.17, 0.07]) * rust[..., None]


    def image(self):
        a = self.ink[..., None]
        rgb = self.rgb * (1 - a) + self.ink_rgb * a
        out = np.concatenate([np.clip(rgb, 0, 1), self.alpha[..., None]], axis=2)
        return Image.fromarray((out * 255.0 + 0.5).astype(np.uint8), "RGBA")


def notice():
    s = Sheet(11, color=(0.84, 0.79, 0.63), stain=0.45)
    s.write("Bekanntmachung", "fraktur", 76, align="center", gap=1.0)
    s.rule(strength=0.7, thick=3)
    s.skip(0.5)
    ink = np.array([0.05, 0.05, 0.07])
    hand = dict(face="pencil", size=50, color=ink, wobble=0.6, bold=1, spacing=1.1, slant=-0.05)
    s.write("2 March 1945", **dict(hand, size=44), align="right")
    s.write("By order of the site commandant, all residents of Kaltenholz will leave the village by 18:00 today.", **hand)
    s.write("Livestock stays. Take one bag.", **hand)
    f = font("pencil", 50)
    line = "Do not look toward the site after dark."
    y0 = s.y
    s.write(line, **hand)
    if f.getlength(line) < W - s.margin * 2:
        yb = y0 + f.getmetrics()[0] * 0.92
        x1 = s.margin + f.getlength(line)
        s.pen_line([(s.margin - 6, yb + 3), ((s.margin + x1) / 2, yb + 7), (x1 + 8, yb + 1)], ink, width=4)
    s.write("Whoever is found in the village after the hour named will be", **hand)
    s.stamp("KOMMANDANTUR", 190, 196, size=24, color=(0.30, 0.15, 0.40), angle=7.0, strength=0.7)
    s.folds()
    s.edges(1.2)
    s.hole(W / 2, 34)
    s.tear([(0, 850), (150, 790), (330, 838), (520, 770), (768, 812)])
    return s, "A notice, nailed to the door"


def journal1():
    s = Sheet(12, color=(0.88, 0.85, 0.74), stain=0.25)
    for y in range(150, H - 60, 44):
        s.rule(y, 40, W - 40, 0.16, (0.35, 0.45, 0.6), 1)
    s.y = 118
    s.write("11 Nov.", "pencil", 50, INK_PENCIL, wobble=0.7)
    s.write("They measured me again this morning. 1.94. Dr. H. smiled and wrote it twice.", "pencil", 46, INK_PENCIL, wobble=0.7)
    s.write("The food is good here. Meat every day. Mother thinks I am with the mountain troops and I have not told her different.", "pencil", 46, INK_PENCIL, wobble=0.7)
    s.write("I have asked for longer trousers.", "pencil", 46, INK_PENCIL, wobble=0.7)
    wet_from = s.y - 10
    s.write("We are thirty-one in the intake. They keep us apart from", "pencil", 46, INK_PENCIL, wobble=0.7)
    s.write("the others from our intake. Franz says his knees ache at night. Mine too.", "pencil", 46, INK_PENCIL, wobble=0.7)
    s.water(wet_from, wet_from + 125)
    s.edges(0.8, corner=(W, 0, 60))
    return s, "A page from a notebook, in pencil"


def flightlog():
    s = Sheet(13, color=(0.83, 0.79, 0.66), stain=0.5)
    printed = np.array([0.16, 0.15, 0.19])
    s.typed("PILOT'S FLIGHT LOG", "courier_bold", 30, printed, gap=0.5, pressure=0.25)
    top = s.y - 12
    s.rule(top, strength=0.55, color=printed)
    col = s.margin + 112
    s.y = top + 10
    s.typed("TIME", "courier_bold", 15, printed, x=s.margin + 4, pressure=0.2)
    s.y = top + 10
    s.typed("REMARKS", "courier_bold", 15, printed, x=col, pressure=0.2)
    s.y = top + 40
    rows = [("0412", "Released on the valley. No structure seen at the given position.", 0.4, 0.0, 0),
            ("0415", "Nav. insists position correct.", 0.5, 0.0, 0),
            ("0419", "Second pass at 900 ft below cloud.", 0.7, 0.4, 0),
            ("0421", "Target is not a structure.", 1.0, 0.8, 0),
            ("0422", "Target is walking.", 1.6, 1.4, 1),
            ("", "Turning for a third", 2.4, 2.0, 0)]
    for time, text, wob, shake, heavy in rows:
        y = s.y
        if time:
            s.write(time, "pen", 30, INK_PENCIL, x=s.margin + 4, wobble=0.4, slant=0.12)
        s.y = y
        s.write(text, "pen", 32 + 4 * heavy, INK_PENCIL, x=col, width=W - col - s.margin + 10, wobble=wob, shaky=shake, slant=0.12, bold=heavy,
                spacing=1.25)
        s.rule(s.y - 16, strength=0.22, color=printed, thick=1)
        s.y += 4
    s.ink[top:s.y - 16, col - 16:col - 15] = np.maximum(s.ink[top:s.y - 16, col - 16:col - 15], 0.4)
    s.ink_rgb[top:s.y - 16, col - 16:col - 15] = printed
    s.burn([(0, 880), (140, 800), (300, 838), (470, 730), (620, 760), (768, 640)], reach=85, holes=[(668, 128, 30)])
    s.edges(1.0)
    return s, "A flight log, the last page, scorched"


def journal2():
    s = Sheet(14, color=(0.88, 0.85, 0.74), stain=0.3)
    for y in range(150, H - 60, 52):
        s.rule(y, 40, W - 40, 0.16, (0.35, 0.45, 0.6), 1)
    s.y = 112
    s.write("3 Jan.", "pencil", 58, INK_PENCIL, wobble=1.0)
    s.write("2.60.", "pencil", 66, INK_PENCIL, wobble=1.0)
    s.write("The new bed came in two pieces and they bolted it together in the ward. I watched them do it. Nobody looked at me.", "pencil", 54, INK_PENCIL, wobble=1.0, spacing=1.2)
    s.write("The others have stopped talking. They stand at the windows all day. At night too I think. Franz stands at the one by my bed. He does not answer to Franz.", "pencil", 54, INK_PENCIL, wobble=1.0, spacing=1.2)
    smear_at = s.y
    s.write("My knees are the worst of it now, and my hands will not", "pencil", 54, INK_PENCIL, wobble=1.0, spacing=1.2)
    s.smear(smear_at - 30, smear_at + 70, 150)
    s.write("I have not had a letter since Christmas.", "pencil", 54, INK_PENCIL, wobble=1.0, spacing=1.2)
    s.edges(0.9, corner=(0, H, 70))
    return s, "A page from a notebook, in pencil, in a large hand"


def journal3():
    s = Sheet(15, color=(0.87, 0.84, 0.73), stain=0.4)
    s.y = 110
    s.write("they dont tell me the number now", "scrawl", 36, INK_PENCIL, wobble=2.5, spacing=1.45)
    s.write("i cant hold the pencil it is like holding a pin", "scrawl", 36, INK_PENCIL, wobble=2.5, spacing=1.45)
    s.write("number 12 screams at night. they said the light hurt him so they", "scrawl", 36, INK_PENCIL, wobble=2.5, spacing=1.45)
    cut = s.y - 30
    s.smear(cut, H + 40, color=(0.30, 0.13, 0.07), strength=0.95, drag=60)
    s.blood(230, 760, 120, 1)
    s.y = 900
    s.write("he can hear me writing this", "scrawl", 30, np.array([0.08, 0.07, 0.07]), wobble=3.0, align="right")
    s.edges(1.3)
    return s, "A page, the letters three fingers high"


def cellwall():
    s = Sheet(16, color=(0.52, 0.55, 0.50), stain=0.0)
    damp = smoothstep(-0.2, 0.5, noise(4, 160)) * 0.25
    s.rgb *= (1.0 - damp)[..., None]
    cracks = T.cracks(1024, 9, 161, 1.2)[:H, :W]
    s.rgb *= (1.0 - 0.5 * cracks)[..., None]
    scratch = np.array([0.80, 0.80, 0.74])
    rng = np.random.default_rng(162)
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    y = 150
    for row, groups in enumerate((6, 6, 3)):
        for g in range(groups):
            x0 = 90 + g * 100
            for k in range(4 if not (row == 2 and g == 2) else 3):
                x = x0 + k * 13 + rng.uniform(-2, 2)
                d.line([(x, y + rng.uniform(-4, 4)), (x + rng.uniform(-3, 3), y + 60 + rng.uniform(-5, 5))], fill=255, width=3)
            if not (row == 2 and g == 2):
                d.line([(x0 - 8, y + 44 + rng.uniform(-6, 6)), (x0 + 50, y + 12 + rng.uniform(-6, 6))], fill=255, width=3)
        y += 92
    s.ink = np.maximum(s.ink, np.asarray(img, dtype=np.float32) / 255.0 * 0.85)
    s.ink_rgb[:] = scratch
    s.y = 480
    s.write("12 HEARS", "scrawl", 60, scratch, wobble=2.0, align="center", strength=0.85, gap=0.4)
    s.write("EVERYTHING", "scrawl", 60, scratch, wobble=2.0, align="center", strength=0.85, gap=0.4)
    s.y += 50
    s.write("dont run", "scrawl", 38, scratch, wobble=3.0, align="center", strength=0.7)
    s.ink *= smoothstep(-0.5, 0.1, noise(60, 163)) * 0.6 + 0.4
    return s, "Scratched into the plaster"


def teamnote():
    s = Sheet(17, color=(0.90, 0.88, 0.78), stain=0.12)
    printed = np.array([0.14, 0.18, 0.16])
    s.typed("MESSAGE FORM", "courier_bold", 30, printed, align="center", gap=0.4, pressure=0.2)
    y = s.y + 18
    for label, value, at, room in (("FROM", "Survey pty, Hochwald", 0, 58), ("DATE", "5 Oct 47", 318, 58), ("TIME", "2140", 506, 58)):
        s.y = y
        s.typed(label, "courier_bold", 17, printed, x=s.margin + at, pressure=0.2)
        s.y = y - 24
        s.write(value, "pencil", 38, INK_PENCIL, x=s.margin + at + room, wobble=0.5)
    s.y = y + 46
    s.rule(strength=0.55, color=printed)
    for yy in range(s.y + 60, H - 80, 50):
        s.rule(yy, 60, W - 60, 0.14, (0.3, 0.4, 0.55), 1)
    s.skip(0.9)
    s.write("Set camera 5 on the mast. Good line of sight up the valley.", "pencil", 50, INK_PENCIL, wobble=0.6, spacing=1.16)
    s.write("Wilson says it turned when we keyed the radio. I say coincidence. It is two miles off and it has no ears I can see.", "pencil", 50, INK_PENCIL, wobble=0.6, spacing=1.16)
    s.write("We try again from the fire lookout tomorrow, better height.", "pencil", 50, INK_PENCIL, wobble=0.6, spacing=1.16)
    s.write("Morale poor. Kowalski will not stop counting the ones in the trees. He says there is one more each time.", "pencil", 50, INK_PENCIL, wobble=0.6, spacing=1.16)
    s.write("Lt. R. Abbott", "pen", 34, INK_PEN, align="right")
    s.ring(590, 830, 78)
    s.edges(0.5)
    return s, "A field message pad, nine days old"


def armyorder():
    s = Sheet(18, color=(0.82, 0.78, 0.64), stain=0.55)
    s.typed("KAMPFGRUPPE HOCHWALD", "courier_bold", 34, gap=0.5)
    s.typed("Gefechtsstand, 19 April 1945", "type", 28)
    s.rule(strength=0.6)
    s.skip(0.8)
    s.typed("All batteries will fire on the figure at first light.", "type", 31)
    s.typed("Aircraft have been requested.", "type", 31)
    y1 = s.y
    s.typed("It must not reach the valley mouth before", "type", 31)
    f = font("type", 31)
    y_fire = s.y
    s.typed("It does not respond to fire.", "type", 31)
    y2 = s.y
    s.typed("It does not respond to its name.", "type", 31)
    s.typed("The men are not to be told what it was.", "type", 31)
    s.typed_wear(0.35)
    red = np.array([0.60, 0.11, 0.09])
    x1 = min(s.margin + f.getlength("abcdefghijklmnopqrstuvwxyz") / 26.0 * 1.08 * len("It does not respond to fire."), W - s.margin)
    yb = y_fire + f.getmetrics()[0] + 4
    s.pen_line([(s.margin - 4, yb + 2), ((s.margin + x1) / 2, yb + 5), (x1 + 6, yb)], red, width=4, strength=0.8)
    s.pen_line([(s.margin - 4, yb + 11), ((s.margin + x1) / 2, yb + 13), (x1 - 40, yb + 10)], red, width=3, strength=0.7)
    s.stamp("GEHEIME KOMMANDOSACHE", 450, 868, size=24, color=(0.58, 0.10, 0.10), angle=-6.0, strength=0.75)
    s.burn([(0, 1100), (768, 1100)], reach=10, holes=[(520, y1 + 12, 120), (610, y2 + 14, 96), (60, 960, 150), (700, 80, 90)])
    s.edges(1.4)
    return s, "An army order, half burned"


def memo():
    s = Sheet(19, color=(0.88, 0.86, 0.78), stain=0.2)
    c = INK_CARBON
    t = dict(face="courier", size=29, color=c, blur=0.7, pressure=0.45, strength=1.0)
    s.typed("VORHABEN HOCHWUCHS", **dict(t, face="courier_bold", size=32), gap=0.5)
    s.typed("To: site commandant", **dict(t, size=24))
    s.rule(strength=0.5, color=c)
    s.skip(0.7)
    s.typed("Subjects 1 to 30 stopped between 2 and 4 m. Quiet. They take no food. They stand for hours.", **t)
    s.typed("They watch 31 at all times. Moved to the far ward, they turn to face the wall he is behind. We do not know why.", **t)
    s.typed("Subject 12 is the exception. Growth in the arms only. Extremely sensitive to light, then, after the procedure, to sound.", **t)
    f = font("courier", 29)
    y = s.y
    s.typed("Recommend he is", **t)
    x = s.margin + int(f.getlength("abcdefghijklmnopqrstuvwxyz") / 26.0 * 1.08 * len("Recommend he is ")) + 6
    s.bar(x, y + 24, W - s.margin - 30, y + 60)
    y = s.y
    s.typed(" ", **t)
    s.bar(s.margin - 4, y + 24, s.margin + 430, y + 60)
    s.skip(0.5)
    s.typed("Subject 31 continues.", **t)
    s.ink = np.maximum(s.ink * 0.85, np.roll(s.ink, 2, axis=1) * 0.3)
    s.stamp("DURCHSCHLAG", 560, 92, size=22, color=(0.55, 0.14, 0.12), angle=4.0, strength=0.6)
    s.y = 900
    s.write("he hears the typewriter", "pencil", 44, INK_PENCIL, wobble=2.0, align="right", slant=0.06)
    s.folds(down=False)
    s.edges(0.6)
    return s, "A staff memo, typed, the carbon copy"


def measlog():
    s = Sheet(20, color=(0.86, 0.83, 0.70), stain=0.3)
    s.typed("MESSPROTOKOLL", "courier_bold", 34, gap=0.2, pressure=0.3)
    s.write("Proband 31", "pen", 40, INK_PEN, wobble=0.6, slant=0.1, gap=0.6)
    top = s.y
    s.rule(strength=0.6)
    rows = [("1.94 m", "Nov 43", ""), ("2.60 m", "Jan 44", ""), ("6.1 m", "Apr 44", "moved to cell 4"), ("38 m", "Aug 44", "moved to the hall"),
            ("61 m", "Oct 44", "hall roof removed"), ("110 m", "Dec 44", "moved outside, braced"), ("180 m", "Feb 45", "second bracing"), ("240 m", "Mar 45", "")]
    s.skip(0.5)
    for height, date, note in rows:
        y = s.y
        s.write(height, "pen", 30, INK_PEN, x=s.margin + 12)
        s.y = y
        s.write(date, "pen", 30, INK_PEN, x=s.margin + 190)
        if note:
            s.y = y
            s.write(note, "pen", 30, INK_PEN, x=s.margin + 340)
        s.y = y + 62
        s.rule(s.y - 14, strength=0.3, thick=1)
    for x in (s.margin + 170, s.margin + 320):
        s.ink[top:s.y - 14, x:x + 1] = np.maximum(s.ink[top:s.y - 14, x:x + 1], 0.3)
    s.skip(0.6)
    s.write("Measurement stopped.", "pen", 34, INK_PEN, wobble=0.8, slant=0.1)
    s.write("He no longer answers to his name.", "pen", 34, INK_PEN, wobble=1.0, slant=0.1)
    s.skip(0.4)
    s.write("what is he eating", "pencil", 54, INK_PENCIL, wobble=2.0, align="right")
    s.edges(0.7)
    return s, "A measuring log, ruled in columns"


def doctor():
    s = Sheet(21, color=(0.89, 0.87, 0.78), stain=0.22)
    s.y = 110
    s.write("20 April", "pen", 34, INK_PEN, wobble=0.5)
    s.write("I have read the theory again and I can find no error in it. That is the worst of it.", "pen", 34, INK_PEN, wobble=0.5)
    s.write("We did not make them grow.", "pen", 34, INK_PEN, wobble=0.5)
    s.write("We only took away what stops it.", "pen", 34, INK_PEN, wobble=0.5)
    s.write("Every one of us carries the same instruction. In us something says enough. In him nothing does, and nothing will, and he is still", "pen", 34, INK_PEN, wobble=0.5)
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    f = font("pen", 34)
    x0 = s.margin + f.getlength("and he is still ") + 30
    y0 = s.y - 62
    pts = [(x0 + t * (W - x0 + 40), y0 + 10 * np.sin(t * 5) + t * t * 260) for t in np.linspace(0, 1, 40)]
    d.line(pts, fill=255, width=3)
    trail = np.asarray(img.filter(ImageFilter.GaussianBlur(0.8)), dtype=np.float32) / 255.0
    take = trail > s.ink
    s.ink = np.maximum(s.ink, trail * 0.85)
    s.ink_rgb[take] = INK_PEN
    s.edges(0.6, corner=(W, H, 50))
    return s, "A doctor's diary, the last entry"


def lookoutnote():
    s = Sheet(22, color=(0.62, 0.50, 0.34), stain=0.25)
    flute = 0.94 + 0.06 * np.sin(np.arange(W) * 0.9)[None, :]
    s.rgb *= flute[..., None]
    s.y = 140
    ink = np.array([0.10, 0.10, 0.11])
    s.write("6 Oct", "pencil", 60, ink, wobble=1.5)
    s.write("Abbott keyed the set at 0600.", "pencil", 60, ink, wobble=1.5)
    s.write("It answered.", "pencil", 60, ink, wobble=1.5)
    s.write("Not words. But it answered, and then it turned round", "pencil", 60, ink, wobble=1.5)
    s.skip(2.0)
    s.write("do not transmit", "pencil", 72, ink, wobble=3.0)
    s.write("do NOT", "scrawl", 64, ink, wobble=4.0)
    s.edges(1.5, corner=(W, 0, 90))
    s.tear([(0, 990), (200, 1004), (420, 968), (768, 996)])
    return s, "Pencil, on the back of a ration box"


PAPERS = {"notice": notice, "journal1": journal1, "flightlog": flightlog, "journal2": journal2, "journal3": journal3, "cellwall": cellwall,
          "teamnote": teamnote, "armyorder": armyorder, "memo": memo, "measlog": measlog, "doctor": doctor, "lookoutnote": lookoutnote}


def main():
    out = maplib.out_dir("papers")
    info = {}
    for key, make in PAPERS.items():
        sheet, caption = make()
        img = sheet.image()
        path = os.path.join(out, key + ".png")
        img.save(path)
        info[key] = {"caption": caption, "wall": key == "cellwall"}
        print(key)
    with open(os.path.join(out, "papers.json"), "w") as f:
        json.dump(info, f, indent=1)


if __name__ == "__main__":
    main()
