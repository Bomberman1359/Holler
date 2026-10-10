import os

import numpy as np
from PIL import Image
from scipy import ndimage

from maplib import ROOT, out_dir


def rng_for(*key):
    seed = 0
    for part in key:
        for ch in str(part):
            seed = (seed * 131 + ord(ch)) % (2 ** 31 - 1)
    return np.random.default_rng(seed)


def fbm(size, base_freq, octaves=5, gain=0.5, seed=0, lacunarity=2.0, stretch=(1.0, 1.0)):
    h, w = (size, size) if isinstance(size, int) else size
    rng = np.random.default_rng(seed)
    fy = np.fft.fftfreq(h)[:, None] * h / stretch[1]
    fx = np.fft.rfftfreq(w)[None, :] * w / stretch[0]
    f = np.sqrt(fx * fx + fy * fy)
    out = np.zeros((h, w), dtype=np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        center = base_freq * (lacunarity ** o)
        band = np.exp(-((f - center) ** 2) / (2.0 * (center * 0.4) ** 2))
        spec = band * np.exp(2j * np.pi * rng.random(band.shape))
        layer = np.fft.irfft2(spec, s=(h, w)).astype(np.float32)
        layer /= max(float(layer.std()) * 2.5, 1e-9)
        out += layer * amp
        total += amp
        amp *= gain
    return np.clip(out / total, -1.5, 1.5) / 1.5


def white(size, seed=0):
    h, w = (size, size) if isinstance(size, int) else size
    return np.random.default_rng(seed).random((h, w)).astype(np.float32)


def cells(size, count, seed=0, stretch=(1.0, 1.0), jitter=1.0):
    h, w = (size, size) if isinstance(size, int) else size
    rng = np.random.default_rng(seed)
    n = int(np.sqrt(count))
    gx, gy = np.meshgrid(np.arange(n), np.arange(n))
    px = ((gx + 0.5 + (rng.random((n, n)) - 0.5) * jitter) / n * w).ravel()
    py = ((gy + 0.5 + (rng.random((n, n)) - 0.5) * jitter) / n * h).ravel()
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d1 = np.full((h, w), 1e9, dtype=np.float32)
    d2 = np.full((h, w), 1e9, dtype=np.float32)
    ident = np.zeros((h, w), dtype=np.int32)
    for k in range(len(px)):
        dx = np.abs(xx - px[k])
        dx = np.minimum(dx, w - dx) * stretch[0]
        dy = np.abs(yy - py[k])
        dy = np.minimum(dy, h - dy) * stretch[1]
        d = np.sqrt(dx * dx + dy * dy)
        closer = d < d1
        d2 = np.where(closer, d1, np.minimum(d2, d))
        ident = np.where(closer, k, ident)
        d1 = np.where(closer, d, d1)
    return d1, (d2 - d1) * 0.5, ident


def bricks(size, courses, per_row, mortar, seed=0, jitter=0.0, bond=0.5):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    ch = size / courses
    row = np.floor(yy / ch).astype(np.int32)
    v = yy / ch - row
    bw = size / per_row
    shift = (row % 2) * bond * bw + rng.uniform(0, 1, courses)[row % courses] * jitter * bw
    x = np.mod(xx + shift, size)
    colm = np.floor(x / bw).astype(np.int32)
    u = x / bw - colm
    edge = np.minimum(np.minimum(u, 1.0 - u) * bw, np.minimum(v, 1.0 - v) * ch) - mortar * 0.5
    ident = row * per_row + (colm % per_row)
    return edge, ident, u, v


def boards(size, count, seed=0, vertical=True, gap=2.0, lengths=0):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    across, along = (xx, yy) if vertical else (yy, xx)
    w = size / count
    idx = np.floor(across / w).astype(np.int32)
    u = across / w - idx
    edge = np.minimum(u, 1.0 - u) * w - gap * 0.5
    ident = idx.copy()
    if lengths > 0:
        offs = rng.uniform(0, lengths, count)[idx % count]
        piece = np.floor((along + offs) / lengths).astype(np.int32)
        t = (along + offs) / lengths - piece
        edge = np.minimum(edge, np.minimum(t, 1.0 - t) * lengths - gap * 0.5)
        ident = idx * 97 + piece
    return edge, ident, u, along


def per_id(ident, seed=0):
    rng = np.random.default_rng(seed)
    table = rng.random(int(ident.max()) + 1).astype(np.float32)
    return table[ident]


def dots(size, points, radius):
    out = np.zeros((size, size), dtype=np.float32)
    R = int(radius) + 2
    ys, xs = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
    shape = np.clip(1.0 - (np.sqrt(xs * xs + ys * ys) / radius) ** 2, 0.0, 1.0)
    for (cx, cy) in points:
        yi = (int(cy) + np.arange(-R, R + 1)) % size
        xi = (int(cx) + np.arange(-R, R + 1)) % size
        ix = np.ix_(yi, xi)
        out[ix] = np.maximum(out[ix], shape)
    return out


def cracks(size, count, seed, width=1.6, part=0.5):
    _d, edge, _ident = cells(size, count, seed, jitter=1.0)
    wx = fbm(size, 9, 3, 0.5, seed + 1) * 9.0
    wy = fbm(size, 9, 3, 0.5, seed + 2) * 9.0
    yy, xx = np.mgrid[0:size, 0:size]
    edge = edge[np.mod(yy + wy, size).astype(np.int32), np.mod(xx + wx, size).astype(np.int32)]
    line = 1.0 - smoothstep(0.0, width, edge)
    shown = smoothstep(-0.15, 0.15, fbm(size, 3, 3, 0.5, seed + 3) + (part - 0.5) * 1.2)
    return line * shown


def streaks(size, seed, freq=18, length=0.25):
    return np.clip(fbm(size, freq, 3, 0.5, seed, stretch=(1.0, length)) * 0.5 + 0.5, 0, 1)


def blur(a, sigma):
    return ndimage.gaussian_filter(a, sigma, mode="wrap")


def smoothstep(lo, hi, v):
    t = np.clip((v - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def remap(a, lo=0.0, hi=1.0):
    mn, mx = float(a.min()), float(a.max())
    return lo + (a - mn) / max(mx - mn, 1e-9) * (hi - lo)


def ramp(v, stops):
    v = np.clip(v, 0.0, 1.0)
    pos = [s[0] for s in stops]
    out = np.zeros(v.shape + (3,), dtype=np.float32)
    for c in range(3):
        out[..., c] = np.interp(v, pos, [s[1][c] for s in stops])
    return out


def stamp_blobs(height, color, count, radius, seed, bump=1.0, tint=None, squash=(0.6, 1.0), mask=None, profile=1.6):
    h, w = height.shape
    rng = np.random.default_rng(seed)
    for _ in range(count):
        r = rng.uniform(*radius)
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        if mask is not None and rng.random() > mask[int(cy) % h, int(cx) % w]:
            continue
        sq = rng.uniform(*squash)
        ang = rng.uniform(0, np.pi)
        R = int(r) + 2
        ys, xs = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
        ca, sa = np.cos(ang), np.sin(ang)
        u = (xs * ca + ys * sa) / r
        v = (-xs * sa + ys * ca) / (r * sq)
        d = np.sqrt(u * u + v * v)
        shape = np.clip(1.0 - d ** profile, 0.0, 1.0)
        yi = (int(cy) + np.arange(-R, R + 1)) % h
        xi = (int(cx) + np.arange(-R, R + 1)) % w
        ix = np.ix_(yi, xi)
        cur = height[ix]
        ground = float(cur[R, R])
        height[ix] = np.where(shape > 0.0, np.maximum(cur, ground + shape * bump * r), cur)
        if color is not None and tint is not None:
            col = np.array(tint(rng), dtype=np.float32)
            a = smoothstep(0.0, 0.35, shape)[..., None]
            shade = (0.75 + 0.25 * shape)[..., None]
            color[ix] = color[ix] * (1.0 - a) + col * shade * a


def stamp_stones(height, color, count, radius, seed, lift=0.5, grey=(0.26, 0.42), warm=0.25, mask=None, bevel=1.3, sink=0.25, rgb=None):
    from PIL import ImageDraw
    h, w = height.shape
    rng = np.random.default_rng(seed)
    for _ in range(count):
        r = radius[0] + (radius[1] - radius[0]) * rng.random() ** 2.2
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        if mask is not None and rng.random() > mask[int(cy) % h, int(cx) % w]:
            continue
        R = int(r * 1.15) + 3
        n = rng.integers(5, 9)
        ang = np.sort(rng.uniform(0, 2 * np.pi, n))
        rad = r * rng.uniform(0.62, 1.0, n)
        sq = rng.uniform(0.6, 1.0)
        rot = rng.uniform(0, np.pi)
        px = np.cos(ang) * rad
        py = np.sin(ang) * rad * sq
        qx = px * np.cos(rot) - py * np.sin(rot)
        qy = px * np.sin(rot) + py * np.cos(rot)
        ss = 3
        m = Image.new("L", ((2 * R + 1) * ss, (2 * R + 1) * ss), 0)
        ImageDraw.Draw(m).polygon([((x + R + 0.5) * ss, (y + R + 0.5) * ss) for x, y in zip(qx, qy)], fill=255)
        inside = np.asarray(m.resize((2 * R + 1, 2 * R + 1), Image.BOX), dtype=np.float32) / 255.0
        if inside.max() <= 0.0:
            continue
        dist = ndimage.distance_transform_edt(inside > 0.5)
        ys, xs = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
        ta = rng.uniform(0, 2 * np.pi)
        tilt = (np.cos(ta) * xs + np.sin(ta) * ys) / max(r, 1.0) * rng.uniform(0.0, 0.35)
        cap = r * lift * (0.8 + tilt)
        top = np.minimum(dist * bevel, cap) + inside * 0.4
        fa = rng.uniform(0, 2 * np.pi)
        facet = np.clip((np.cos(fa) * xs + np.sin(fa) * ys) / max(r, 1.0) * 1.5 + rng.uniform(-0.2, 0.5), 0.0, 1.0)
        top -= facet * r * lift * 0.3 * (dist > 0)
        top = np.maximum(top, 0.3) * inside
        yi = (int(cy) + np.arange(-R, R + 1)) % h
        xi = (int(cx) + np.arange(-R, R + 1)) % w
        ix = np.ix_(yi, xi)
        cur = height[ix]
        under = cur[inside > 0.5]
        ground = (float(under.mean()) if under.size else float(cur[R, R])) - r * lift * sink
        new = np.where(inside > 0.5, ground + top, cur)
        covered = (new > cur + 1e-4).astype(np.float32) * inside
        height[ix] = new
        if color is not None:
            g = rng.uniform(*grey)
            tint = np.array([1.0, 1.0, 1.0])
            k = rng.random()
            if k < warm:
                tint = np.array([1.10, 0.98, 0.84])
            elif k < warm + 0.15:
                tint = np.array([0.93, 0.98, 1.06])
            shade = 0.82 + 0.3 * (0.5 - facet) + 0.12 * np.clip(dist / max(r * 0.5, 1.0), 0, 1)
            speck = 0.92 + 0.16 * rng.random(inside.shape)
            stone = (g * shade * speck)[..., None] * tint
            if rgb is not None:
                stone = (shade * speck)[..., None] * np.array(rgb(rng), dtype=np.float32)
            a = covered[..., None]
            color[ix] = color[ix] * (1.0 - a) + stone * a


def stamp_strokes(size, count, length, width, seed, color_fn, supersample=2, curve=0.0, mask=None):
    from PIL import ImageDraw
    s = size * supersample
    img = Image.new("RGB", (s, s), (0, 0, 0))
    cov = Image.new("L", (s, s), 0)
    d = ImageDraw.Draw(img)
    dc = ImageDraw.Draw(cov)
    rng = np.random.default_rng(seed)
    for _ in range(count):
        cx, cy = rng.uniform(0, s), rng.uniform(0, s)
        if mask is not None and rng.random() > mask[int(cy / supersample) % size, int(cx / supersample) % size]:
            continue
        L = rng.uniform(*length) * supersample
        a = rng.uniform(0, 2 * np.pi)
        wd = max(int(round(rng.uniform(*width) * supersample)), 1)
        col = tuple(int(np.clip(c, 0, 1) * 255) for c in color_fn(rng))
        pts = []
        bend = rng.uniform(-curve, curve)
        for k in range(4):
            t = k / 3.0 - 0.5
            pts.append((cx + np.cos(a + bend * t) * L * t, cy + np.sin(a + bend * t) * L * t))
        for ox in (-s, 0, s):
            for oy in (-s, 0, s):
                if ox == 0 and oy == 0 or (cx + ox > -L and cx + ox < s + L and cy + oy > -L and cy + oy < s + L):
                    moved = [(p[0] + ox, p[1] + oy) for p in pts]
                    d.line(moved, fill=col, width=wd)
                    dc.line(moved, fill=255, width=wd)
    img = img.resize((size, size), Image.LANCZOS)
    cov = cov.resize((size, size), Image.LANCZOS)
    return np.asarray(img, dtype=np.float32) / 255.0, np.asarray(cov, dtype=np.float32) / 255.0


def normals(height, strength=1.0):
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * 0.5 * strength
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * 0.5 * strength
    nz = 1.0 / np.sqrt(dx * dx + dy * dy + 1.0)
    return np.stack([-dx * nz, dy * nz, nz], axis=2)


def occlusion(height, radius=6.0, strength=1.0):
    return np.clip(1.0 - (blur(height, radius) - height) * strength, 0.0, 1.0)


def to_srgb8(rgb):
    return (np.clip(rgb, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


class Layer:

    def __init__(self, name, color, height, rough, normal_strength=4.0, alpha=None, ao=0.6):
        self.name = name
        self.color = color.astype(np.float32)
        self.height = height.astype(np.float32)
        self.rough = rough.astype(np.float32) if isinstance(rough, np.ndarray) else np.full(height.shape, rough, dtype=np.float32)
        self.normal_strength = normal_strength
        self.alpha = alpha
        self.ao = ao

    def albedo_image(self):
        shade = 1.0 - self.ao * (1.0 - occlusion(self.height, 5.0, 2.0))
        rgb = to_srgb8(self.color * shade[..., None])
        if self.alpha is not None:
            return Image.fromarray(np.dstack([rgb, to_srgb8(self.alpha)]), "RGBA")
        return Image.fromarray(np.dstack([rgb, np.full(rgb.shape[:2], 255, np.uint8)]), "RGBA")

    def nrh_image(self):
        n = normals(self.height, self.normal_strength)
        hh = remap(self.height)
        data = np.dstack([self.rough, n[..., 1] * 0.5 + 0.5, hh, n[..., 0] * 0.5 + 0.5])
        return Image.fromarray(to_srgb8(data), "RGBA")


IMPORT_ARRAY = """[remap]

importer="2d_array_texture"
type="CompressedTexture2DArray"

[deps]

source_file="res://{path}"

[params]

compress/mode={mode}
compress/high_quality=false
compress/lossy_quality=0.7
compress/hdr_compression=1
compress/channel_pack={pack}
mipmaps/generate=true
mipmaps/limit=-1
slices/horizontal={cols}
slices/vertical={rows}
"""

IMPORT_TEXTURE = """[remap]

importer="texture"
type="CompressedTexture2D"

[deps]

source_file="res://{path}"

[params]

compress/mode={mode}
compress/high_quality=false
compress/lossy_quality=0.7
compress/hdr_compression=1
compress/normal_map=0
compress/channel_pack=0
mipmaps/generate={mips}
mipmaps/limit=-1
roughness/mode=0
roughness/src_normal=""
process/fix_alpha_border={fix}
process/premult_alpha=false
process/normal_map_invert_y=false
process/hdr_as_srgb=false
process/hdr_clamp_exposure=false
process/size_limit=0
detect_3d/compress_to=0
"""


def edge_alpha(mask, spread):
    from scipy import ndimage
    mask = np.asarray(mask, dtype=bool)
    if not mask.any():
        return np.zeros(mask.shape, dtype=np.float32)
    inside = ndimage.distance_transform_edt(mask)
    outside = ndimage.distance_transform_edt(~mask)
    return np.clip(0.5 + (inside - outside) / (2.0 * spread), 0.0, 1.0).astype(np.float32)


def bleed(rgb, mask):
    from scipy import ndimage
    mask = np.asarray(mask, dtype=bool)
    if not mask.any() or mask.all():
        return rgb
    idx = ndimage.distance_transform_edt(~mask, return_distances=False, return_indices=True)
    return rgb[idx[0], idx[1]]


def write_import(rel_path, text):
    full = os.path.join(ROOT, rel_path + ".import")
    if os.path.exists(full):
        uid = [line for line in open(full).read().splitlines() if line.startswith("uid=")]
        if uid:
            out = []
            for line in text.splitlines():
                out.append(line)
                if line.startswith("type="):
                    out.append(uid[0])
            text = "\n".join(out) + "\n"
    with open(full, "w") as f:
        f.write(text)


def write_array(folder, name, layers, cols=None):
    n = len(layers)
    cols = cols or int(np.ceil(np.sqrt(n)))
    rows = int(np.ceil(n / cols))
    size = layers[0].height.shape[0]
    out = out_dir(folder)
    for kind in ("albedo", "nrh"):
        sheet = Image.new("RGBA", (cols * size, rows * size))
        for i, layer in enumerate(layers):
            img = layer.albedo_image() if kind == "albedo" else layer.nrh_image()
            sheet.paste(img, ((i % cols) * size, (i // cols) * size))
        file = "%s_%s.png" % (name, kind)
        sheet.save(os.path.join(out, file))
        rel = os.path.join("assets", "gen", folder, file)
        write_import(rel, IMPORT_ARRAY.format(path=rel, mode=2, pack=0 if kind == "albedo" else 1, cols=cols, rows=rows))
    with open(os.path.join(out, name + "_layers.txt"), "w") as f:
        f.write("\n".join(layer.name for layer in layers) + "\n")
    return [layer.name for layer in layers]


def write_texture(folder, file, image, compressed=True, mips=True, fix_alpha=True):
    out = out_dir(folder)
    image.save(os.path.join(out, file))
    rel = os.path.join("assets", "gen", folder, file)
    write_import(rel, IMPORT_TEXTURE.format(path=rel, mode=2 if compressed else 0, mips="true" if mips else "false", fix="true" if fix_alpha else "false"))
