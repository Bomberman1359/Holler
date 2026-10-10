#!/usr/bin/env python3
# usage: python3 tools/make_audio.py [sound ...]
import os
import subprocess
import sys
import wave

import numpy as np
from scipy import signal

SR = 32000
OUT = os.path.join(os.path.dirname(__file__), "..", "audio")
rng = np.random.default_rng(1947)


def t(seconds):
    return np.arange(int(seconds * SR)) / SR


def norm(x, peak=0.9):
    m = np.max(np.abs(x))
    return x if m == 0 else x / m * peak


def lowpass(x, hz, order=4):
    b, a = signal.butter(order, min(hz, SR * 0.49) / (SR / 2), "low")
    return signal.lfilter(b, a, x, axis=0)


def highpass(x, hz, order=2):
    b, a = signal.butter(order, hz / (SR / 2), "high")
    return signal.lfilter(b, a, x, axis=0)


def bandpass(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), min(hi, SR * 0.49) / (SR / 2)], "band")
    return signal.lfilter(b, a, x, axis=0)


def peak(x, hz, q=8.0):
    b, a = signal.iirpeak(hz / (SR / 2), q)
    return signal.lfilter(b, a, x)


def noise(n):
    return rng.standard_normal(n)


def brown(n):
    return norm(highpass(np.cumsum(noise(n)), 12.0))


def tone(freq, n, phase=0.0):
    f = np.broadcast_to(np.asarray(freq, dtype=np.float64), (n,))
    return np.sin(2 * np.pi * np.cumsum(f) / SR + phase)


def saw(freq, n):
    f = np.broadcast_to(np.asarray(freq, dtype=np.float64), (n,))
    return signal.sawtooth(2 * np.pi * np.cumsum(f) / SR)


def pad(freq, seconds, voices=5, spread=0.006, cut=900.0):
    n = int(seconds * SR)
    x = np.zeros(n)
    for v in range(voices):
        d = 1.0 + spread * (v - (voices - 1) / 2) / max(voices - 1, 1) * 2.0 + rng.uniform(-0.0006, 0.0006)
        drift = 1.0 + 0.0015 * np.sin(2 * np.pi * rng.uniform(0.05, 0.2) * t(seconds) + rng.uniform(0, 6))
        x += signal.sawtooth(2 * np.pi * np.cumsum(freq * d * drift) / SR + rng.uniform(0, 6))
    return lowpass(x / voices, cut)


def swell(n, rise, fall, hold=0.0):
    e = np.ones(n)
    r, f = int(rise * SR), int(fall * SR)
    e[:r] = np.sin(np.linspace(0, np.pi / 2, r)) ** 2
    e[n - f:] = np.cos(np.linspace(0, np.pi / 2, f)) ** 2
    return e


def place(mix, x, at, gain=1.0, pan=0.0):
    s = int(at * SR)
    e = min(s + len(x), len(mix))
    if e <= s:
        return
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    mix[s:e, 0] += x[: e - s] * gain * l
    mix[s:e, 1] += x[: e - s] * gain * r


def loopable(x, fade=1.0):
    n = int(fade * SR)
    head, tail = x[:n], x[-n:]
    ramp = np.linspace(0.0, 1.0, n)
    if x.ndim == 2:
        ramp = ramp[:, None]
    body = x[: len(x) - n].copy()
    body[:n] = head * ramp + tail * (1.0 - ramp)
    return body


def reverb(x, seconds=2.2, wet=0.35, bright=3500.0):
    n = int(seconds * SR)
    ir = lowpass(noise(n) * np.exp(-np.linspace(0, 7, n)), bright)
    y = signal.fftconvolve(x, ir)[: len(x)]
    return x * (1 - wet) + norm(y) * wet * np.max(np.abs(x))


def reverb2(x, seconds=3.0, wet=0.4, bright=3000.0):
    out = np.zeros((len(x), 2))
    n = int(seconds * SR)
    for ch in range(2):
        ir = lowpass(noise(n) * np.exp(-np.linspace(0, 6.5, n)), bright)
        y = signal.fftconvolve(x, ir)[: len(x)]
        out[:, ch] = x * (1 - wet) + norm(y) * wet * max(np.max(np.abs(x)), 1e-9)
    return out


def save(name, x, level=0.9, ogg=False):
    x = norm(np.asarray(x, dtype=np.float64), level)
    channels = 2 if x.ndim == 2 else 1
    path = os.path.join(OUT, name + ".wav")
    with wave.open(path, "wb") as f:
        f.setnchannels(channels)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((x * 32767).astype(np.int16).tobytes())
    if ogg:
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", path, "-c:a", "libvorbis", "-q:a", "5",
                        os.path.join(OUT, name + ".ogg")], check=True)
        os.remove(path)
    print("wrote %-18s %5.1f s%s" % (name, len(x) / SR, "  stereo" if channels == 2 else ""))


def wind_bed():
    seconds = 30
    n = int(seconds * SR)
    tt = t(seconds)
    mix = np.zeros((n, 2))
    for ch in range(2):
        rush = bandpass(noise(n), 160, 700) * 0.8 + lowpass(noise(n), 260) * 0.35
        gust = 0.5 + 0.5 * np.sin(2 * np.pi * 0.061 * tt + ch * 0.9) * np.sin(2 * np.pi * 0.019 * tt + 1.0 + ch * 0.4)
        gust = 0.35 + 0.65 * gust ** 2
        needles = bandpass(noise(n), 2200, 6500) * 0.10 * (0.4 + 0.6 * gust)
        mix[:, ch] = rush * gust + needles
    center = 620 + 260 * np.sin(2 * np.pi * 0.043 * tt) + 120 * np.sin(2 * np.pi * 0.11 * tt + 2.0)
    src = noise(n)
    whistle = np.zeros(n)
    block = 2048
    for s in range(0, n, block):
        c = float(center[s])
        whistle[s:s + block] = bandpass(src[max(s - block, 0):s + block], c * 0.94, c * 1.06)[-min(block, n - s):] if s else bandpass(src[:block], c * 0.94, c * 1.06)
    place(mix, whistle * (0.3 + 0.7 * np.sin(2 * np.pi * 0.027 * tt) ** 2), 0.0, 0.32, 0.25)
    for at, pan in ((7.5, -0.6), (21.0, 0.5)):
        d = int(1.3 * SR)
        f = 74 + 30 * np.sin(np.linspace(0, 2.6, d)) + rng.uniform(-3, 3, d).cumsum() * 0.02
        creak = peak(saw(f, d) * (noise(d) * 0.3 + 0.7), 410, 5) + peak(saw(f, d), 760, 6) * 0.5
        place(mix, creak * swell(d, 0.25, 0.6), at, 0.22, pan)
    save("wind_bed", loopable(mix, 2.5), 0.62, ogg=True)


def night_bed():
    seconds = 26
    n = int(seconds * SR)
    mix = np.zeros((n, 2))
    for at, pan in ((5.0, -0.7), (17.5, -0.6)):
        for k, f in enumerate((372, 331, 331)):
            d = int((0.42 if k < 2 else 0.7) * SR)
            hoot = tone(f * (1.0 + 0.01 * np.sin(np.linspace(0, 9, d))), d) * np.hanning(d)
            place(mix, reverb(np.pad(hoot, (0, SR)), 1.6, 0.6), at + k * 0.55, 0.3, pan)
    for at, pan in ((2.2, 0.4), (9.4, 0.7), (13.1, 0.2), (22.0, 0.6)):
        d = int(0.05 * SR)
        drip = tone(np.linspace(1500, 900, d), d) * np.exp(-np.linspace(0, 6, d))
        place(mix, reverb(np.pad(drip, (0, SR // 2)), 0.6, 0.5), at, 0.12, pan)
    for at, pan in ((11.0, -0.3), (24.0, 0.3)):
        d = int(0.5 * SR)
        rustle = bandpass(noise(d), 1800, 6000) * (np.abs(np.sin(np.linspace(0, 17, d))) ** 4) * np.hanning(d)
        place(mix, rustle, at, 0.10, pan)
    save("night_bed", loopable(mix, 1.5), 0.42, ogg=True)


def whispers():
    seconds = 14
    n = int(seconds * SR)
    tt = t(seconds)
    mix = np.zeros((n, 2))
    for ch in range(2):
        breath = noise(n)
        syll = np.zeros(n)
        at = rng.uniform(0, 0.4)
        while at < seconds - 0.4:
            d = int(rng.uniform(0.07, 0.22) * SR)
            s = int(at * SR)
            syll[s:s + d] += np.hanning(d)[: max(min(d, n - s), 0)] * rng.uniform(0.4, 1.0)
            at += d / SR + rng.uniform(0.02, 0.12) + (rng.uniform(0.4, 1.4) if rng.random() < 0.2 else 0.0)
        v = np.zeros(n)
        for f, q in ((rng.uniform(500, 800), 5), (rng.uniform(1400, 2200), 6), (rng.uniform(2800, 3600), 6)):
            v += peak(breath, f, q)
        mix[:, ch] = highpass(v, 350) * syll * (0.55 + 0.45 * np.sin(2 * np.pi * 0.09 * tt + ch * 2.0))
    save("whispers", loopable(mix, 1.0), 0.5, ogg=True)


def watcher_hum():
    seconds = 9
    n = int(seconds * SR)
    tt = t(seconds)
    x = np.zeros(n)
    for f0 in (196.0, 197.6, 293.2):
        vib = 1.0 + 0.004 * np.sin(2 * np.pi * rng.uniform(4.2, 5.4) * tt + rng.uniform(0, 6))
        src = saw(f0 * vib, n)
        x += peak(src, 420, 4) + peak(src, 880, 6) * 0.5 + peak(src, 2500, 8) * 0.12
    x *= 0.8 + 0.2 * np.sin(2 * np.pi * 0.23 * tt)
    save("watcher_hum", reverb2(loopable(x, 1.0), 2.0, 0.35), 0.5, ogg=True)


def heartbeat():
    seconds = 0.86
    n = int(seconds * SR)
    x = np.zeros(n)
    for at, f, g in ((0.0, 196, 1.0), (0.27, 228, 0.7)):
        d = int(0.2 * SR)
        k = np.arange(d) / SR
        thump = (tone(f * np.exp(-k * 5), d) + 0.7 * tone(f * 2 * np.exp(-k * 5), d)) * np.exp(-k * 20) * np.minimum(k / 0.004, 1.0)
        s = int(at * SR)
        x[s:s + d] += thump * g
    save("heartbeat", lowpass(x, 700), 0.6, ogg=True)


def breath():
    seconds = 2.2
    n = int(seconds * SR)
    x = np.zeros(n)
    for at, d_s, lo, hi, g in ((0.0, 0.75, 500, 2300, 0.7), (0.95, 1.0, 380, 1500, 1.0)):
        d = int(d_s * SR)
        b = bandpass(noise(d), lo, hi) * np.hanning(d) ** 1.4
        b = peak(b, (lo + hi) / 2, 2)
        s = int(at * SR)
        x[s:s + d] += b[: n - s] * g
    save("breath", x, 0.42, ogg=True)


def scope_hum():
    tt = t(4)
    n = len(tt)
    x = 0.5 * np.sin(2 * np.pi * 2870 * tt + 2.0 * np.sin(2 * np.pi * 6 * tt)) + 0.35 * np.sign(np.sin(2 * np.pi * 200 * tt))
    x = lowpass(x, 5000) + bandpass(noise(n), 1000, 4000) * 0.15
    save("scope_hum", loopable(x, 0.5), 0.32, ogg=True)


def film_motor():
    tt = t(3)
    n = len(tt)
    clicks = np.zeros(n)
    for i in range(0, n, SR // 18):
        d = min(120, n - i)
        clicks[i:i + d] += noise(d) * np.exp(-np.linspace(0, 7, d))
    x = bandpass(clicks, 900, 5000) + 0.25 * np.sin(2 * np.pi * 236 * tt) + lowpass(noise(n), 700) * 0.1
    save("film_motor", loopable(x, 0.4), 0.4, ogg=True)


def crank():
    tt = t(2)
    n = len(tt)
    x = np.zeros(n)
    for i in range(0, n, SR // 9):
        d = min(300, n - i)
        x[i:i + d] += noise(d) * np.exp(-np.linspace(0, 6, d))
    for i in range(0, n, SR // 18):
        d = min(90, n - i)
        x[i:i + d] += noise(d) * np.exp(-np.linspace(0, 8, d)) * 0.4
    save("crank", loopable(bandpass(x, 500, 3500), 0.3), 0.5, ogg=True)


def footfall():
    seconds = 7.0
    n = int(seconds * SR)
    tt = t(seconds)
    blow = tone(52 * np.exp(-tt * 2.2) + 30, n) * np.exp(-tt * 1.6)
    body = (tone(168 * np.exp(-tt * 1.4) + 60, n) + 0.6 * tone(246 * np.exp(-tt * 1.8) + 90, n)) * np.exp(-tt * 2.6)
    thud = bandpass(noise(n), 110, 520) * np.exp(-tt * 3.8) * 2.2
    slap = bandpass(noise(n), 500, 2600) * np.exp(-tt * 16) * 0.9
    rumble = bandpass(brown(n), 60, 260) * np.exp(-tt * 0.75) * (1 - np.exp(-tt * 6)) * 2.0
    x = blow * 0.8 + body * 1.2 + thud + slap + rumble
    for at in (0.18, 0.4, 0.75, 1.3, 2.1):
        d = int(rng.uniform(0.12, 0.3) * SR)
        crack = bandpass(noise(d), 350, 3200) * np.exp(-np.linspace(0, rng.uniform(5, 9), d))
        s = int(at * SR)
        x[s:s + d] += crack * rng.uniform(0.25, 0.5)
    mix = reverb2(x, 3.2, 0.3, 1800.0)
    save("footfall", mix, 0.97)


def colossus_voice():
    seconds = 9.5
    n = int(seconds * SR)
    tt = t(seconds)
    f0 = 58 + 9 * np.sin(2 * np.pi * 0.09 * tt) + 2.5 * np.sin(2 * np.pi * 0.7 * tt) + 26 * np.clip((tt - 6.2) / 3.0, 0, 1) ** 2
    src = saw(f0, n) * (0.7 + 0.3 * noise(n).clip(-1, 1)) + 0.5 * saw(f0 * 2.01, n)
    x = peak(src, 190, 3) * 1.2 + peak(src, 330, 4) + peak(src, 620, 5) * 0.6 + peak(src, 1150, 6) * 0.2
    x += bandpass(brown(n), 50, 160) * 0.5
    x += peak(saw(f0 * 1.488, n), 440, 4) * 0.35 * np.clip((tt - 2.5) / 2.0, 0, 1)
    env = np.minimum(tt / 1.8, 1.0) * np.minimum((seconds - tt) / 2.2, 1.0)
    save("colossus_voice", reverb2(x * env, 3.6, 0.45, 2200.0), 0.95)


def colossus_roar():
    seconds = 5.2
    n = int(seconds * SR)
    tt = t(seconds)
    f0 = 74 + 62 * np.clip(tt / 1.2, 0, 1) ** 1.5 + 5 * np.sin(2 * np.pi * 0.8 * tt) - 44 * np.clip((tt - 3.4) / 1.8, 0, 1)
    f0 = f0 * (1.0 + 0.12 * lowpass(noise(n), 40))
    src = saw(f0, n) + 0.6 * saw(f0 * 1.5, n) + 0.5 * saw(f0 * 2.02, n)
    rough = 0.5 + 0.5 * (0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(23 + 8 * np.sin(2 * np.pi * 0.7 * tt)) / SR))
    src = src * rough + noise(n) * 0.35
    x = peak(src, 240, 3) * 1.2 + peak(src, 420, 3) + peak(src, 780, 4) * 0.8 + peak(src, 1500, 5) * 0.5 + peak(src, 2600, 5) * 0.25
    x = norm(x) + norm(bandpass(brown(n), 60, 200)) * 0.3
    env = np.minimum(tt / 0.5, 1.0) ** 1.5 * np.minimum((seconds - tt) / 1.3, 1.0)
    x = np.tanh(x * env * 3.6)
    save("colossus_roar", reverb2(x, 3.0, 0.35, 2600.0), 0.98)


def colossus_breath():
    seconds = 12.0
    n = int(seconds * SR)
    x = np.zeros(n)
    for at, d_s, f1, f2, g in ((0.3, 4.3, 330, 720, 0.75), (5.4, 5.6, 230, 520, 1.0)):
        d = int(d_s * SR)
        k = np.linspace(0, 1, d)
        air = noise(d) * np.sin(k * np.pi) ** 1.3
        b = peak(air, f1, 2.5) + peak(air, f2, 3.5) * 0.6 + bandpass(air, 150, 900) * 0.4
        if f1 < 300:
            b += peak(saw(47 + 4 * np.sin(k * 5), d), 190, 3) * np.sin(k * np.pi) ** 2 * 0.5 * np.max(np.abs(b))
        s0 = int(at * SR)
        x[s0:s0 + d] += b * g
    save("colossus_breath", loopable(reverb2(x, 3.0, 0.4, 1600.0), 0.3), 0.8, ogg=True)


def cable_sing():
    tt = t(3.5)
    n = len(tt)
    x = np.zeros(n)
    glide = 1.0 + 0.06 * (1 - np.exp(-tt * 1.5))
    for f, a in [(421, 1.0), (587, 0.7), (911, 0.5), (1343, 0.35), (2017, 0.2)]:
        x += a * np.sin(2 * np.pi * np.cumsum(f * glide) / SR + 0.4 * np.sin(2 * np.pi * 7.3 * tt))
    env = np.minimum(tt / 0.6, 1.0) * np.exp(-np.maximum(tt - 1.2, 0) * 1.3)
    save("cable_sing", reverb2(x * env, 1.8, 0.35), 0.6)


def reacher_step():
    for k in range(3):
        tt = t(0.26)
        n = len(tt)
        slap = bandpass(noise(n), 300, 2400 - 250 * k) * np.exp(-tt * 38)
        squelch = bandpass(noise(n), 700, 1800) * np.exp(-((tt - 0.05) / 0.03) ** 2) * 0.6
        low = (tone(190 * np.exp(-tt * 14) + 70, n)) * np.exp(-tt * 30) * 0.9
        save("reacher_step%d" % k, slap + squelch + low, 0.8)


def reacher_click():
    tt = t(0.16)
    n = len(tt)
    x = np.zeros(n)
    for at, f in ((0.0, 1450), (0.055, 1750)):
        d = n - int(at * SR)
        k = np.arange(d) / SR
        knock = tone(f * (1.0 + 0.5 * np.exp(-k * 300)), d) * np.exp(-k * 120) + noise(d) * np.exp(-k * 600) * 0.4
        x[int(at * SR):] += peak(knock, 900, 3) + knock * 0.4
    save("reacher_click", x, 0.7)


def reacher_sniff():
    seconds = 1.5
    n = int(seconds * SR)
    x = np.zeros(n)
    for at, d_s in ((0.0, 0.22), (0.34, 0.2), (0.66, 0.48)):
        d = int(d_s * SR)
        k = np.linspace(0, 1, d)
        pull = noise(d) * np.sin(k * np.pi) ** 0.7
        pull = peak(pull, 900 + 500 * k[-1], 3) + bandpass(pull, 1500, 4200) * 0.5
        flutter = 1.0 + 0.35 * np.sin(2 * np.pi * 38 * np.arange(d) / SR)
        s = int(at * SR)
        x[s:s + d] += pull * flutter
    save("reacher_sniff", x, 0.5)


def reacher_breath():
    seconds = 3.4
    n = int(seconds * SR)
    x = np.zeros(n)
    for at, d_s, f1, f2, g, rate in ((0.0, 1.25, 620, 1500, 0.7, 34.0), (1.55, 1.7, 430, 1150, 1.0, 21.0)):
        d = int(d_s * SR)
        k = np.linspace(0, 1, d)
        air = noise(d) * np.sin(k * np.pi) ** 1.2
        b = peak(air, f1, 3) + peak(air, f2, 4) * 0.7
        flap = 0.55 + 0.45 * (np.sin(2 * np.pi * rate * np.arange(d) / SR * (1.0 + 0.3 * k)) > 0.2)
        s0 = int(at * SR)
        x[s0:s0 + d] += b * flap * g
    save("reacher_breath", loopable(x, 0.12), 0.6, ogg=True)


def reacher_alert():
    seconds = 0.95
    n = int(seconds * SR)
    x = np.zeros(n)
    at, gap, f = 0.0, 0.115, 1250.0
    while at < seconds - 0.08:
        d = int(0.05 * SR)
        k = np.arange(d) / SR
        knock = tone(f * (1.0 + 0.5 * np.exp(-k * 300)), d) * np.exp(-k * 130) + noise(d) * np.exp(-k * 600) * 0.4
        s0 = int(at * SR)
        x[s0:s0 + d] += peak(knock, 900, 3) + knock * 0.4
        gap = max(gap * 0.82, 0.027)
        f *= 1.055
        at += gap
    save("reacher_alert", x, 0.8)


def reacher_screech():
    seconds = 2.3
    n = int(seconds * SR)
    tt = t(seconds)
    f0 = 430 + 330 * (1 - np.exp(-tt * 22)) + 140 * np.exp(-((tt - 0.6) / 0.25) ** 2) - 330 * np.clip((tt - 1.5) / 0.65, 0, 1) ** 1.5
    crack = np.ones(n)
    for at, d in ((0.31, 0.07), (0.83, 0.05), (1.12, 0.11), (1.42, 0.06)):
        crack[int(at * SR):int((at + d) * SR)] = 0.5
    f = f0 * crack * (1.0 + 0.16 * lowpass(noise(n), 90) + 0.03 * np.sin(2 * np.pi * 31 * tt))
    src = saw(f, n) + 0.5 * saw(f * 1.497, n)
    rough = 0.45 + 0.55 * (signal.square(2 * np.pi * np.cumsum(58 + 30 * np.sin(2 * np.pi * 1.7 * tt)) / SR) > 0)
    src = src * rough + noise(n) * 0.1
    x = peak(src, 1250, 4) + peak(src, 2500, 5) + peak(src, 3600, 6) * 0.5 + peak(src, 5400, 6) * 0.15 + src * 0.15
    env = np.minimum(tt / 0.02, 1.0) * np.minimum((seconds - tt) / 0.55, 1.0)
    x = highpass(lowpass(np.tanh(x / np.max(np.abs(x)) * env * 2.4), 6500), 180)
    rattle = np.zeros(n)
    at, gap = 1.5, 0.03
    while at < seconds - 0.05:
        d = int(0.02 * SR)
        k = np.arange(d) / SR
        rattle[int(at * SR):int(at * SR) + d] += (tone(900, d) + noise(d)) * np.exp(-k * 240)
        gap *= 1.16
        at += gap
    x = x + norm(peak(rattle, 1100, 3)) * 0.55
    save("reacher_screech", reverb2(x, 1.4, 0.2), 0.98)


def watcher_sting():
    seconds = 2.4
    n = int(seconds * SR)
    tt = t(seconds)
    x = np.zeros(n)
    pre = int(0.32 * SR)
    x[:pre] += bandpass(noise(pre), 900, 5000) * np.linspace(0, 1, pre) ** 3 * 0.5
    hit = n - pre
    k = np.arange(hit) / SR
    cluster = np.zeros(hit)
    for f in (466.2, 493.9, 554.4, 587.3, 698.5, 740.0, 932.3):
        vib = 1.0 + 0.006 * np.sin(2 * np.pi * rng.uniform(5, 7) * k + rng.uniform(0, 6))
        cluster += signal.sawtooth(2 * np.pi * np.cumsum(f * vib) / SR + rng.uniform(0, 6))
    cluster = bandpass(cluster, 400, 5200) * np.exp(-k * 1.9) * np.minimum(k / 0.006, 1.0)
    thump = (tone(180 * np.exp(-k * 10) + 70, hit)) * np.exp(-k * 9)
    x[pre:] += cluster * 0.55 + thump * 0.9
    save("watcher_sting", reverb2(x, 1.8, 0.3), 0.92)


def branch_crack():
    seconds = 1.6
    n = int(seconds * SR)
    x = np.zeros(n)
    for at, g in ((0.0, 1.0), (0.07, 0.5), (0.19, 0.3)):
        d = int(0.12 * SR)
        k = np.arange(d) / SR
        snap = bandpass(noise(d), 700, 6000) * np.exp(-k * 60) + tone(310, d) * np.exp(-k * 45) * 0.6
        s = int(at * SR)
        x[s:s + d] += snap * g
    save("branch_crack", reverb2(x, 1.3, 0.35), 0.75)


def death_hit():
    seconds = 2.2
    n = int(seconds * SR)
    k = np.arange(n) / SR
    cluster = np.zeros(n)
    for f in (311.1, 329.6, 466.2, 493.9, 698.5, 740.0, 987.8, 1046.5):
        vib = 1.0 + 0.007 * np.sin(2 * np.pi * rng.uniform(5, 7) * k + rng.uniform(0, 6))
        cluster += signal.sawtooth(2 * np.pi * np.cumsum(f * vib) / SR + rng.uniform(0, 6))
    cluster = bandpass(cluster, 250, 6000) * np.exp(-k * 1.3) * np.minimum(k / 0.004, 1.0)
    slam = (tone(240 * np.exp(-k * 7) + 110, n) + 0.6 * tone(480 * np.exp(-k * 8) + 220, n)) * np.exp(-k * 5)
    crash = bandpass(noise(n), 300, 7000) * np.exp(-k * 4.5)
    x = np.tanh((norm(cluster) * 0.6 + slam * 1.1 + norm(crash) * 0.8) * 1.6)
    save("death_hit", reverb2(x, 1.6, 0.25), 0.98)


def knock():
    seconds = 2.2
    n = int(seconds * SR)
    x = np.zeros(n)
    for at, g in ((0.0, 1.0), (0.44, 0.85), (0.9, 0.7)):
        d = int(0.25 * SR)
        k = np.arange(d) / SR
        hit = (tone(188, d) + 0.5 * tone(412, d) + 0.25 * tone(655, d)) * np.exp(-k * 32) + bandpass(noise(d), 600, 3000) * np.exp(-k * 120) * 0.5
        x[int(at * SR):int(at * SR) + d] += hit * g
    save("knock", reverb2(x, 1.5, 0.4, 2400.0), 0.7)


def metal_groan():
    seconds = 3.4
    n = int(seconds * SR)
    tt = t(seconds)
    f = 64 - 14 * tt / seconds + 3 * np.sin(2 * np.pi * 0.9 * tt)
    src = saw(f, n) * (0.6 + 0.4 * noise(n))
    x = np.zeros(n)
    for hzr, q, g in ((238, 14, 1.0), (377, 16, 0.8), (731, 18, 0.6), (1183, 20, 0.35)):
        x += peak(src, hzr * (1.0 + 0.0), q) * g
    x *= swell(n, 0.8, 1.4) * (0.75 + 0.25 * np.sin(2 * np.pi * 2.3 * tt))
    save("metal_groan", reverb2(x, 2.4, 0.4, 2600.0), 0.7)


def footsteps():
    for k in range(4):
        tt = t(0.2)
        n = len(tt)
        heel = (tone(230 * np.exp(-tt * 14) + 110, n)) * np.exp(-tt * 38)
        earth = bandpass(noise(n), 150, 620 + 60 * k) * np.exp(-tt * 30) * 2.2
        crunch = bandpass(noise(n), 1600, 5200) * np.exp(-((tt - 0.035 - 0.01 * k) / 0.025) ** 2) * 0.1
        save("step_ground%d" % k, heel * 0.8 + earth + crunch, 0.5)
    for k in range(3):
        tt = t(0.22)
        n = len(tt)
        knock = (tone(196 + 22 * k, n) + 0.5 * tone(392 + 40 * k, n) + 0.3 * tone(610 + 30 * k, n)) * np.exp(-tt * 34)
        tap = bandpass(noise(n), 900, 3500) * np.exp(-tt * 90) * 0.5
        save("step_wood%d" % k, knock + tap, 0.5)
    for k in range(3):
        tt = t(0.2)
        n = len(tt)
        tap = bandpass(noise(n), 700, 4200) * np.exp(-tt * 85) + tone(260 + 30 * k, n) * np.exp(-tt * 60) * 0.5
        save("step_stone%d" % k, reverb(np.pad(tap, (0, int(0.12 * SR))), 0.35, 0.3), 0.5)
    for k in range(3):
        tt = t(0.3)
        n = len(tt)
        ring = (tone(430 + 50 * k, n) + 0.5 * tone(1180 + 90 * k, n) + 0.3 * tone(2140 + 60 * k, n)) * np.exp(-tt * 22)
        tap = bandpass(noise(n), 900, 5000) * np.exp(-tt * 110) * 0.6
        save("step_metal%d" % k, ring + tap, 0.5)
    for k in range(2):
        tt = t(0.34)
        n = len(tt)
        splash = bandpass(noise(n), 600, 4800) * np.exp(-((tt - 0.05) / 0.06) ** 2) + lowpass(noise(n), 500) * np.exp(-tt * 14) * 0.6
        save("step_water%d" % k, splash, 0.5)
    tt = t(0.3)
    n = len(tt)
    land = bandpass(noise(n), 140, 700) * np.exp(-tt * 20) * 2.0 + (tone(240 * np.exp(-tt * 9) + 110, n)) * np.exp(-tt * 24)
    save("land", land, 0.6)


def small():
    tt = t(0.7)
    n = len(tt)
    save("zoom_whirr", (np.sin(2 * np.pi * (380 + 240 * tt) * tt) * 0.5 + bandpass(noise(n), 800, 3000) * 0.4) * np.hanning(n), 0.4)
    tt = t(0.5)
    n = len(tt)
    save("paper", bandpass(noise(n), 1800, 7000) * (np.abs(np.sin(2 * np.pi * 9 * tt)) ** 3) * np.hanning(n), 0.5)
    tt = t(0.3)
    n = len(tt)
    save("film_click", np.sin(2 * np.pi * 1300 * tt) * np.exp(-tt * 60) + bandpass(noise(n), 2000, 6000) * np.exp(-tt * 80), 0.6)
    tt = t(0.25)
    n = len(tt)
    save("switch", np.sin(2 * np.pi * 900 * tt) * np.exp(-tt * 120) + noise(n) * np.exp(-tt * 200) * 0.5, 0.5)
    tt = t(5)
    n = len(tt)
    static = bandpass(noise(n), 600, 3200) * (0.6 + 0.4 * np.sin(2 * np.pi * 3.1 * tt) * np.sin(2 * np.pi * 0.7 * tt))
    save("radio_static", loopable(static, 0.5), 0.5, ogg=True)
    tt = t(1.6)
    n = len(tt)
    tear = bandpass(noise(n), 250, 7000) * (np.minimum(tt / 0.01, 1.0)) * np.exp(-tt * 1.6) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 50 * tt)))
    tear += tone(118, n) * np.exp(-tt * 3) * 0.6 + tone(236, n) * np.exp(-tt * 3) * 0.4
    save("film_burn", tear, 0.8)
    tt = t(0.45)
    n = len(tt)
    hit = bandpass(noise(n), 300, 7500) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 60 * tt))) * np.minimum(tt / 0.004, 1.0) * np.minimum((0.45 - tt) / 0.03, 1.0)
    save("static_hit", hit, 0.7)
    tt = t(0.3)
    n = len(tt)
    cloth = bandpass(noise(n), 700, 3200) * np.hanning(n) ** 2
    clink = (tone(2350, n) + 0.5 * tone(3710, n)) * np.exp(-np.maximum(tt - 0.16, 0) * 70) * (tt > 0.16) * 0.35
    save("pickup", cloth + clink, 0.5)
    tt = t(1.3)
    n = len(tt)
    clang = np.zeros(n)
    for f, g, dec in ((212, 1.0, 5.0), (331, 0.8, 6.0), (487, 0.7, 7.0), (793, 0.5, 9.0), (1247, 0.3, 12.0)):
        clang += tone(f, n, rng.uniform(0, 6)) * np.exp(-tt * dec) * g
    clang += bandpass(noise(n), 500, 5000) * np.exp(-tt * 45) * 1.5
    latch = np.zeros(n)
    s0 = int(0.42 * SR)
    latch[s0:] = (tone(1700, n - s0) * np.exp(-tt[: n - s0] * 90)) * 0.5
    save("locker", reverb2(clang + latch, 0.8, 0.25), 0.7)
    tt = t(1.4)
    n = len(tt)
    f = 240 + 180 * np.sin(np.linspace(0, 2.2, n)) + np.cumsum(rng.uniform(-1, 1, n)) * 0.02
    hinge = peak(saw(f, n) * (0.6 + 0.4 * noise(n)), 950, 6) + peak(saw(f, n), 1900, 8) * 0.5
    save("door_creak", reverb2(hinge * swell(n, 0.2, 0.5), 1.2, 0.35), 0.5)


def radio_tune():
    seconds = 32
    tt = t(seconds)
    n = len(tt)
    x = np.zeros(n)
    tune = ["A", "F", "D", "E", "G", "F", "E", "C#", "D", "F", "A", "Bb", "A", "G", "F", "E"]
    beat = 0.95
    wow = 1.0 + 0.012 * np.sin(2 * np.pi * 0.6 * tt) + 0.004 * np.sin(2 * np.pi * 6.3 * tt)
    for i, name in enumerate(tune * 2):
        s = int(i * beat * SR)
        d = int(beat * 0.95 * SR)
        if s + d > n:
            break
        f = hz(name, 2) * 0.97
        phase = 2 * np.pi * np.cumsum(f * wow[s:s + d]) / SR
        reed = np.sign(np.sin(phase)) * 0.5 + np.sin(phase * 2) * 0.3 + np.sin(phase) * 0.6
        env = np.minimum(np.arange(d) / (0.06 * SR), 1.0) * np.minimum((d - np.arange(d)) / (0.12 * SR), 1.0)
        x[s:s + d] += reed * env
        if i % 3 == 0:
            x[s:s + d] += np.sin(2 * np.pi * hz("D", 1) * 0.97 * np.arange(d) / SR) * env * 0.8
    x = bandpass(x, 350, 2400)
    crackle = (rng.random(n) > 0.9994).astype(float) * rng.uniform(-1, 1, n) * 2.0
    hiss = bandpass(noise(n), 800, 3000) * 0.12
    fade = 0.65 + 0.35 * np.sin(2 * np.pi * 0.13 * tt)
    save("radio_tune", loopable(norm(x) * fade + hiss + crackle, 1.0), 0.6, ogg=True)


NOTE = {"D": 0, "Eb": 1, "E": 2, "F": 3, "F#": 4, "G": 5, "Ab": 6, "A": 7, "Bb": 8, "B": 9, "C": 10, "C#": 11}


def hz(name, octave):
    return 73.416 * (2 ** octave) * 2 ** (NOTE[name] / 12)


def bell(freq, seconds, wow=0.0):
    n = int(seconds * SR)
    k = np.arange(n) / SR
    w = 1.0 + wow * np.sin(2 * np.pi * 0.9 * k + rng.uniform(0, 6)) + wow * 0.4 * np.sin(2 * np.pi * 5.1 * k)
    x = np.zeros(n)
    for ratio, a, decay in ((1.0, 1.0, 1.6), (2.76, 0.45, 3.2), (5.4, 0.22, 6.0), (8.9, 0.1, 9.0)):
        x += a * tone(freq * ratio * w, n, rng.uniform(0, 6)) * np.exp(-k * decay)
    return x * np.minimum(k / 0.002, 1.0)


def scrape(base, seconds):
    n = int(seconds * SR)
    k = np.arange(n) / SR
    x = np.zeros(n)
    for ratio in (1.0, 1.48, 2.11, 2.9, 3.67, 4.6, 5.83):
        beat = 1.0 + 0.003 * np.sin(2 * np.pi * rng.uniform(0.2, 1.1) * k + rng.uniform(0, 6))
        x += tone(base * ratio * beat, n, rng.uniform(0, 6)) * rng.uniform(0.3, 1.0) / ratio ** 0.6
    x *= (0.7 + 0.3 * lowpass(noise(n), 30) * 6.0)
    return x * swell(n, seconds * 0.45, seconds * 0.4)


def music():
    seconds = 168
    n = int(seconds * SR)
    tt = t(seconds)
    mix = np.zeros((n, 2))
    for name, octave, gain, rate, pan in (("D", 1, 0.9, 0.031, -0.2), ("A", 1, 0.7, 0.023, 0.25), ("D", 2, 0.5, 0.041, 0.0), ("F", 2, 0.34, 0.017, -0.4), ("Eb", 2, 0.2, 0.011, 0.5)):
        v = pad(hz(name, octave), seconds, 5, 0.009, 700.0)
        breathe = 0.35 + 0.65 * (0.5 + 0.5 * np.sin(2 * np.pi * rate * tt + rng.uniform(0, 6))) ** 2
        place(mix, v * breathe, 0.0, gain * 0.5, pan)
    place(mix, bandpass(noise(n), 180, 420) * (0.3 + 0.7 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.013 * tt)) ** 2), 0.0, 0.05, 0.0)
    tune = [("A", 3), ("F", 3), ("D", 3), ("Eb", 3), ("A", 2)]
    at = 14.0
    while at < seconds - 30.0:
        for i, (name, octave) in enumerate(tune):
            if i >= 3 and rng.random() < 0.3:
                break
            note = bell(hz(name, octave) * 2 ** (rng.uniform(-14, 14) / 1200), 5.0, 0.004)
            place(mix, reverb(np.pad(note, (0, SR)), 3.0, 0.55, 2600.0), at + i * rng.choice([1.25, 1.3, 1.9]) , 0.2, 0.35)
        at += rng.uniform(26.0, 40.0)
    for at2, base, pan in ((32.0, 233.0, -0.6), (71.0, 311.0, 0.6), (118.0, 207.0, -0.3), (147.0, 277.0, 0.4)):
        s = scrape(base, rng.uniform(7.0, 10.0))
        place(mix, reverb(s, 3.5, 0.5, 3000.0), at2, 0.11, pan)
    for at3, f in ((52.0, 1244.5), (96.0, 1174.7), (133.0, 1318.5)):
        d = int(9.0 * SR)
        k = np.arange(d) / SR
        line = tone(f * (1.0 + 0.003 * np.sin(2 * np.pi * 4.6 * k)), d) + 0.4 * tone(f * 1.0595 * (1.0 + 0.003 * np.sin(2 * np.pi * 5.3 * k)), d)
        place(mix, reverb(line * swell(d, 4.0, 3.5), 3.0, 0.5), at3, 0.035, rng.uniform(-0.5, 0.5))
    for at4 in (61.0, 139.0):
        d = int(5.0 * SR)
        k = np.arange(d) / SR
        boom = (tone(150 * np.exp(-k * 2) + 55, d) + bandpass(noise(d), 90, 300) * 1.5) * np.exp(-k * 1.4)
        place(mix, reverb(boom, 3.5, 0.5, 900.0), at4, 0.3, 0.0)
    save("music", loopable(mix, 5.0), 0.82, ogg=True)


def tension():
    seconds = 24
    n = int(seconds * SR)
    tt = t(seconds)
    mix = np.zeros((n, 2))
    for i, f in enumerate((415.3, 440.0, 587.3, 622.3, 880.0, 932.3, 1244.5)):
        vib = 1.0 + 0.004 * np.sin(2 * np.pi * rng.uniform(5, 6.5) * tt + rng.uniform(0, 6))
        v = signal.sawtooth(2 * np.pi * np.cumsum(f * vib) / SR + rng.uniform(0, 6))
        trem = 0.45 + 0.55 * (0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(10.5, 13.5) * tt + rng.uniform(0, 6))) ** 2
        breathe = 0.3 + 0.7 * (0.5 + 0.5 * np.sin(2 * np.pi * (i % 3 + 1) / seconds * tt + rng.uniform(0, 6)))
        v = bandpass(v, 350, 5200) * trem * breathe
        place(mix, v, 0.0, 0.16, (i - 3) / 3.5)
    bridge = bandpass(noise(n), 2800, 7000) * (0.5 + 0.5 * np.sin(2 * np.pi * 12.0 * tt)) ** 2
    place(mix, bridge, 0.0, 0.05, 0.0)
    for at in np.arange(0.0, seconds - 1.0, 2.0):
        d = int(0.9 * SR)
        k = np.arange(d) / SR
        thud = (tone(165 * np.exp(-k * 6) + 70, d) + 0.5 * tone(330 * np.exp(-k * 6) + 140, d)) * np.exp(-k * 7) * np.minimum(k / 0.006, 1.0)
        place(mix, thud, at, 0.5, 0.0)
    save("tension", loopable(mix, 2.0), 0.8, ogg=True)


def chase():
    beat = 0.375
    beats = 32
    seconds = beat * beats + 2.0
    n = int(seconds * SR)
    tt = t(seconds)
    mix = np.zeros((n, 2))
    for i in range(beats + 5):
        at = i * beat
        hard = i % 4 == 0
        d = int(0.3 * SR)
        k = np.arange(d) / SR
        drum = (tone((175 if hard else 150) * np.exp(-k * 9) + 68, d) + 0.5 * tone(330 * np.exp(-k * 12) + 140, d)) * np.exp(-k * 13)
        drum += bandpass(noise(d), 120, 900) * np.exp(-k * 40) * 0.7
        place(mix, drum, at, 0.75 if hard else 0.45, 0.0)
        if i % 4 == 2:
            place(mix, drum, at + beat * 0.5, 0.3, 0.0)
        note = hz("D", 1) if (i // 2) % 2 == 0 else hz("Eb", 1)
        d2 = int(beat * 0.92 * SR)
        k2 = np.arange(d2) / SR
        bow = lowpass(saw(note, d2) + saw(note * 1.006, d2) + 0.6 * saw(note * 2.0, d2), 1300) * np.minimum(k2 / 0.012, 1.0) * np.exp(-k2 * 5.5)
        place(mix, bow, at, 0.3, -0.25 if i % 2 else 0.25)
    wail_f = 1108.7 * (1.0 + 0.045 * np.sin(2 * np.pi * tt / (beat * 16)) + 0.004 * np.sin(2 * np.pi * 5.6 * tt))
    wail = tone(wail_f, n) + 0.6 * tone(wail_f * 1.0595, n) + 0.3 * tone(wail_f * 2.0, n)
    place(mix, reverb(wail * (0.5 + 0.5 * np.sin(2 * np.pi * tt / (beat * 32)) ** 2), 2.0, 0.4), 0.0, 0.07, 0.0)
    save("chase", loopable(mix, 2.0), 0.85, ogg=True)


def theme():
    seconds = 76
    n = int(seconds * SR)
    tt = t(seconds)
    mix = np.zeros((n, 2))
    for name, octave, gain, rate, pan in (("D", 1, 1.0, 0.045, 0.0), ("A", 1, 0.6, 0.031, 0.3), ("Eb", 2, 0.34, 0.021, -0.4), ("D", 2, 0.5, 0.06, -0.1), ("Ab", 2, 0.22, 0.027, 0.45)):
        v = pad(hz(name, octave), seconds, 5, 0.01, 760.0)
        breathe = 0.4 + 0.6 * (0.5 + 0.5 * np.sin(2 * np.pi * rate * tt + rng.uniform(0, 6))) ** 2
        place(mix, v * breathe, 0.0, gain * 0.5, pan)
    for at in np.arange(3.0, seconds - 4.0, 3.8):
        d = int(1.6 * SR)
        k = np.arange(d) / SR
        step = (tone(150 * np.exp(-k * 5) + 62, d) + 0.5 * tone(300 * np.exp(-k * 6) + 124, d)) * np.exp(-k * 3.4) * np.minimum(k / 0.01, 1.0)
        place(mix, step, at, 0.34, 0.0)
    tune = [("A", 3), ("F", 3), ("D", 3), ("Eb", 3), ("A", 2), ("Bb", 2), ("A", 2), ("F#", 2)]
    at = 6.0
    beat = 0.92
    wow = 0.004
    for round_ in range(5):
        for i, (name, octave) in enumerate(tune):
            if at > seconds - 9.0:
                break
            note = bell(hz(name, octave) * 2 ** (rng.uniform(-9, 9) / 1200), 4.5, wow)
            place(mix, reverb(np.pad(note, (0, SR)), 2.6, 0.45, 3000.0), at, 0.36, 0.15 * (-1) ** i)
            at += beat * (2.0 if i == len(tune) - 1 else 1.0)
        beat *= 1.14
        wow *= 1.5
        at += 1.5
    for at2 in (27.0, 58.0):
        d = int(9.0 * SR)
        k = np.arange(d) / SR
        rise = np.zeros(d)
        for f in (233.1, 246.9, 277.2, 293.7, 349.2):
            glide = 1.0 + 0.06 * (k / 9.0) ** 2
            rise += signal.sawtooth(2 * np.pi * np.cumsum(f * glide * (1.0 + 0.005 * np.sin(2 * np.pi * rng.uniform(5, 7) * k))) / SR + rng.uniform(0, 6))
        rise = bandpass(rise, 200, 4200) * (k / 9.0) ** 2.2
        rise[-int(0.05 * SR):] *= np.linspace(1, 0, int(0.05 * SR))
        place(mix, reverb(np.pad(rise, (0, 2 * SR)), 2.5, 0.4), at2, 0.12, 0.0)
    for at3, pan in ((36.5, -0.5), (66.0, 0.4)):
        d = int(6.5 * SR)
        k = np.arange(d) / SR
        f0 = 58 + 7 * np.sin(2 * np.pi * 0.11 * k) + 22 * np.clip((k - 4.0) / 2.5, 0, 1) ** 2
        src = saw(f0, d)
        call = (peak(src, 190, 3) + peak(src, 330, 4) + peak(src, 620, 5) * 0.5) * swell(d, 1.5, 2.0)
        place(mix, reverb(call, 3.5, 0.6, 1500.0), at3, 0.22, pan)
    ticks = (rng.random(n) > 0.99975).astype(float) * rng.uniform(-1, 1, n)
    place(mix, bandpass(ticks, 800, 6000) * 3.0 + bandpass(noise(n), 2000, 6000) * 0.02, 0.0, 0.16, 0.0)
    save("theme", loopable(mix, 4.0), 0.85, ogg=True)


ALL = {
    "wind_bed": wind_bed, "night_bed": night_bed, "whispers": whispers, "watcher_hum": watcher_hum, "heartbeat": heartbeat, "breath": breath,
    "scope_hum": scope_hum, "film_motor": film_motor, "crank": crank, "footfall": footfall, "colossus_voice": colossus_voice,
    "colossus_roar": colossus_roar, "colossus_breath": colossus_breath, "cable_sing": cable_sing, "reacher_step": reacher_step,
    "reacher_click": reacher_click, "reacher_sniff": reacher_sniff, "reacher_breath": reacher_breath, "reacher_alert": reacher_alert,
    "reacher_screech": reacher_screech,
    "watcher_sting": watcher_sting, "branch_crack": branch_crack, "death_hit": death_hit, "knock": knock, "metal_groan": metal_groan,
    "footsteps": footsteps, "small": small, "radio_tune": radio_tune, "music": music, "tension": tension, "chase": chase, "theme": theme,
}

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for key in (sys.argv[1:] or list(ALL)):
        ALL[key]()
