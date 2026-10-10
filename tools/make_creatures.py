#!/usr/bin/env python3
# usage: python3 tools/make_creatures.py [watchers|reacher|colossus|name ...]
import json
import math
import os
import sys

import numpy as np

import maplib
from sculpt import Body

PALE = (0.50, 0.485, 0.45)
DARK = (0.035, 0.025, 0.025)
GRIME = (0.36, 0.35, 0.32)
BRUISE = (0.40, 0.36, 0.40)
OLD_BLOOD = (0.22, 0.07, 0.05)
TOOTH = (0.66, 0.62, 0.50)


def watcher(name, face="smile", arms="shin", neck=0.18, missing_arm=False, seed=0):
    b = Body(name)
    b.base = PALE
    hip_y = 1.32
    chest_y = 1.80
    sh_y = 2.08
    neck_y = 2.13
    head_y = neck_y + neck + 0.13
    b.bone("hips", None, (0, hip_y, 0))
    b.bone("spine", "hips", (0, 1.52, 0.01))
    b.bone("chest", "spine", (0, chest_y, 0.0))
    b.bone("neck", "chest", (0, neck_y, 0.0))
    b.bone("head", "neck", (0, neck_y + neck, -0.015))
    b.bone("jaw", "head", (0, head_y - 0.045, -0.02))
    for side, sx in (("l", -1.0), ("r", 1.0)):
        b.bone("arm_" + side, "chest", (sx * 0.2, sh_y, 0.0))
        b.bone("fore_" + side, "arm_" + side, (sx * 0.245, 1.56, 0.03))
        b.bone("hand_" + side, "fore_" + side, (sx * 0.255, 1.04 if arms == "shin" else 0.62, -0.02))
        b.bone("thigh_" + side, "hips", (sx * 0.105, hip_y - 0.03, 0.0))
        b.bone("shin_" + side, "thigh_" + side, (sx * 0.115, 0.70, -0.035))
        b.bone("foot_" + side, "shin_" + side, (sx * 0.115, 0.075, 0.02))
    b.ball("hips", (0, hip_y, 0.0), 0.135, (1.25, 0.82, 0.8), k=0.05)
    for sx in (-1, 1):
        b.ball("hips", (sx * 0.115, hip_y + 0.065, -0.05), 0.04, k=0.03)
    b.chain("spine", [(0, hip_y + 0.05, 0.02), (0, 1.5, 0.035), (0, 1.66, 0.03)], [0.085, 0.07, 0.085], k=0.06)
    b.ball("chest", (0, 1.86, 0.0), 0.185, (1.0, 1.22, 0.7), k=0.07)
    for i in range(6):
        y = 1.72 + i * 0.05
        w = 0.165 - abs(i - 2.5) * 0.012
        for sx in (-1, 1):
            b.chain("chest", [(sx * 0.03, y + 0.02, -0.125), (sx * w * 0.75, y, -0.105), (sx * w, y - 0.02, -0.03), (sx * w * 0.8, y, 0.07)], [0.012, 0.014, 0.014, 0.012], k=0.014)
    b.chain("chest", [(0, 1.70, 0.105), (0, 1.86, 0.125), (0, 2.02, 0.11), (0, neck_y, 0.06)], [0.02, 0.022, 0.022, 0.02], k=0.03)
    for y in np.arange(1.40, 2.06, 0.055):
        b.ball("chest" if y > 1.68 else "spine", (0, y, 0.13 if y > 1.68 else 0.095), 0.016, k=0.012)
    for sx in (-1, 1):
        b.capsule("chest", (sx * 0.02, sh_y - 0.035, -0.092), (sx * 0.18, sh_y + 0.0, -0.035), 0.011, 0.013, k=0.016)
        b.ball("chest", (sx * 0.12, 1.98, 0.09), 0.06, (1.0, 1.3, 0.5), k=0.04)
    b.chain("neck", [(0, neck_y - 0.02, 0.01), (0, neck_y + neck * 0.5, 0.0), (0, neck_y + neck + 0.02, -0.01)], [0.048, 0.037, 0.04], k=0.04)
    for sx in (-1, 1):
        b.capsule("neck", (sx * 0.03, neck_y, -0.04), (sx * 0.05, neck_y + neck, 0.025), 0.011, k=0.018)
    b.ball("neck", (0, neck_y + neck * 0.55, -0.038), 0.014, k=0.012)
    hy = head_y
    b.ball("head", (0, hy + 0.02, 0.0), 0.1, (0.82, 1.0, 1.1), k=0.03)
    b.ball("head", (0, hy - 0.035, -0.045), 0.078, (0.86, 1.1, 0.95), k=0.04)
    b.ball("jaw", (0, hy - 0.098, -0.05), 0.058, (0.9, 0.8, 0.95), k=0.03)
    for sx in (-1, 1):
        b.ball("head", (sx * 0.058, hy - 0.03, -0.082), 0.026, (0.8, 0.9, 1.0), k=0.025)
        b.capsule("jaw", (sx * 0.064, hy - 0.06, -0.01), (sx * 0.035, hy - 0.125, -0.085), 0.013, k=0.02)
    b.capsule("head", (-0.055, hy + 0.028, -0.107), (0.055, hy + 0.028, -0.107), 0.015, k=0.02)
    if face != "none":
        b.capsule("head", (0, hy + 0.02, -0.118), (0, hy - 0.022, -0.128), 0.0085, k=0.012)
        for sx in (-1, 1):
            b.cut_ball((sx * 0.04, hy + 0.002, -0.113), 0.027, (1.15, 0.92, 1.0), k=0.01)
            b.paint_ball((sx * 0.04, hy + 0.002, -0.104), 0.029, DARK, 0.25, (1.15, 0.92, 1.0))
            b.extra_ball("head", (sx * 0.04, hy + 0.001, -0.094), 0.0115)
            b.paint_ball((sx * 0.04, hy + 0.001, -0.097), 0.0105, (0.32, 0.31, 0.27), 0.3, shine=1.0)
            b.cut_capsule((sx * 0.008, hy - 0.03, -0.134), (sx * 0.013, hy - 0.046, -0.13), 0.0038, k=0.003)
    else:
        for sx in (-1, 1):
            b.cut_ball((sx * 0.04, hy + 0.002, -0.128), 0.02, (1.2, 0.9, 0.6), k=0.02)
    my = hy - 0.078
    if face == "smile":
        def arc(t):
            return np.array([t * 0.082, my - 0.014 + 0.062 * t * t, -0.127 + 0.05 * t * t * abs(t)])
        ts = np.linspace(-1.0, 1.0, 13)
        for sx in (-1, 1):
            b.paint_ball((sx * 0.082, my + 0.04, -0.075), 0.034, OLD_BLOOD, 0.9)
        for i in range(len(ts) - 1):
            r = 0.0165 - 0.006 * abs(ts[i])
            b.cut_capsule(tuple(arc(ts[i])), tuple(arc(ts[i + 1])), r, k=0.005)
            b.paint_capsule(tuple(arc(ts[i]) + np.array([0, 0, 0.012])), tuple(arc(ts[i + 1]) + np.array([0, 0, 0.012])), r + 0.002, DARK, 0.25)
        for i, t in enumerate(np.linspace(-0.9, 0.9, 15)):
            c = arc(t) + np.array([0, 0, 0.004])
            h = 0.0125 - 0.004 * abs(t)
            b.extra_capsule("head", tuple(c + np.array([0, 0.011, 0])), tuple(c + np.array([0, 0.011 - h, -0.0008])), 0.0047, 0.0036)
            b.extra_capsule("jaw", tuple(c + np.array([0.003, -0.012, 0.001])), tuple(c + np.array([0.003, -0.012 + h * 0.85, 0.0])), 0.0044, 0.0034)
            b.paint_ball(tuple(c), 0.0125, TOOTH, 0.25, shine=0.6)
    elif face == "frown":
        def arc(t):
            return np.array([t * 0.07, my + 0.012 - 0.075 * t * t, -0.127 + 0.045 * t * t * abs(t)])
        ts = np.linspace(-1.0, 1.0, 13)
        for i in range(len(ts) - 1):
            b.cut_capsule(tuple(arc(ts[i])), tuple(arc(ts[i + 1])), 0.0075, k=0.005)
        for t in ts:
            b.paint_ball(tuple(arc(t)), 0.014, DARK, 0.3)
        for sx in (-1, 1):
            b.cut_capsule(tuple(arc(sx)), (sx * 0.072, my - 0.12, -0.05), 0.0045, k=0.008)
            b.cut_ball((sx * 0.06, hy - 0.06, -0.09), 0.022, (0.8, 1.3, 0.6), k=0.025)
    elif face == "open":
        b.ball("jaw", (0, hy - 0.165, -0.045), 0.05, (0.85, 1.0, 0.9), k=0.035)
        for sx in (-1, 1):
            b.capsule("jaw", (sx * 0.06, hy - 0.06, -0.01), (sx * 0.03, hy - 0.185, -0.07), 0.013, k=0.02)
        b.cut_ball((0, my - 0.045, -0.105), 0.044, (0.7, 1.75, 1.3), k=0.008)
        b.paint_ball((0, my - 0.045, -0.085), 0.07, DARK, 0.15, (0.75, 1.5, 1.0))
        for i in range(-3, 4):
            x = i * 0.0082
            top = my + 0.03 - abs(i) * 0.0035
            b.extra_capsule("head", (x, top, -0.127 + abs(i) * 0.002), (x, top - 0.012, -0.127 + abs(i) * 0.002), 0.0044, 0.0034)
            b.paint_ball((x, top - 0.006, -0.128), 0.009, TOOTH, 0.3, shine=0.6)
            bot = my - 0.118 + abs(i) * 0.004
            b.extra_capsule("jaw", (x, bot, -0.118 + abs(i) * 0.002), (x, bot + 0.011, -0.118 + abs(i) * 0.002), 0.0042, 0.0033)
            b.paint_ball((x, bot + 0.006, -0.119), 0.009, TOOTH, 0.3, shine=0.6)
    for side, sx in (("l", -1.0), ("r", 1.0)):
        sh = (sx * 0.2, sh_y, 0.0)
        b.ball("chest", sh, 0.042, k=0.035)
        if missing_arm and side == "r":
            b.capsule("arm_r", sh, (sx * 0.235, sh_y - 0.26, 0.02), 0.042, 0.03, k=0.03)
            b.ball("arm_r", (sx * 0.238, sh_y - 0.28, 0.02), 0.034, k=0.02)
            b.paint_ball((sx * 0.24, sh_y - 0.3, 0.02), 0.07, OLD_BLOOD, 0.8)
            continue
        elbow = (sx * 0.245, 1.56, 0.03)
        wrist = (sx * 0.255, 1.04 if arms == "shin" else 0.62, -0.02)
        b.capsule("arm_" + side, sh, elbow, 0.04, 0.03, k=0.03)
        b.ball("fore_" + side, elbow, 0.036, k=0.02)
        b.capsule("fore_" + side, elbow, wrist, 0.031, 0.021, k=0.025)
        b.ball("hand_" + side, (wrist[0], wrist[1] - 0.05, wrist[2] - 0.004), 0.034, (0.5, 1.3, 1.0), k=0.02)
        reach = 0.2 if arms == "shin" else 0.56
        for f in range(4):
            fz = wrist[2] - 0.034 + f * 0.022
            knuckle = (wrist[0] + sx * 0.002, wrist[1] - 0.095, fz)
            mid = (wrist[0] + sx * 0.008, wrist[1] - 0.095 - reach * 0.5, fz + (0.02 if arms == "ground" else 0.0))
            tip = (wrist[0] + sx * 0.004, max(wrist[1] - 0.095 - reach * (1.0 - 0.07 * abs(f - 1.5)), 0.012), fz - (0.015 if arms == "shin" else -0.12 - 0.03 * f))
            b.chain("hand_" + side, [knuckle, mid, tip], [0.0095, 0.0085, 0.006], k=0.008)
        b.chain("hand_" + side, [(wrist[0] - sx * 0.012, wrist[1] - 0.04, wrist[2] - 0.04), (wrist[0] - sx * 0.02, wrist[1] - 0.13, wrist[2] - 0.06)], [0.011, 0.007], k=0.01)
        b.paint_capsule((wrist[0], wrist[1] - 0.05, wrist[2]), (wrist[0], wrist[1] - 0.6, wrist[2]), 0.09, GRIME, 1.2)
        b.paint_ball(elbow, 0.06, BRUISE, 1.0)
    for side, sx in (("l", -1.0), ("r", 1.0)):
        hip = (sx * 0.105, hip_y - 0.03, 0.0)
        knee = (sx * 0.115, 0.70, -0.035)
        ankle = (sx * 0.115, 0.075, 0.02)
        b.capsule("thigh_" + side, hip, knee, 0.066, 0.042, k=0.045)
        b.ball("shin_" + side, (knee[0], knee[1], knee[2] - 0.012), 0.047, k=0.02)
        b.capsule("shin_" + side, knee, ankle, 0.04, 0.026, k=0.03)
        b.capsule("shin_" + side, (knee[0], knee[1] - 0.06, knee[2] - 0.03), (ankle[0], ankle[1] + 0.1, ankle[2] - 0.022), 0.012, k=0.012)
        b.ball("foot_" + side, (ankle[0], ankle[1] - 0.005, ankle[2] + 0.02), 0.036, k=0.02)
        b.capsule("foot_" + side, (ankle[0], 0.04, ankle[2]), (ankle[0] + sx * 0.012, 0.022, ankle[2] - 0.2), 0.035, 0.022, k=0.03)
        for t in range(4):
            b.capsule("foot_" + side, (ankle[0] + sx * (0.03 - t * 0.016), 0.02, ankle[2] - 0.2), (ankle[0] + sx * (0.036 - t * 0.02), 0.012, ankle[2] - 0.265 + t * 0.008), 0.0105, 0.0085, k=0.008)
        b.paint_capsule((ankle[0], 0.0, ankle[2] + 0.05), (ankle[0], 0.0, ankle[2] - 0.3), 0.14, GRIME, 1.2)
        b.paint_ball(knee, 0.075, BRUISE, 1.0)
    b.cuts.append((lambda P: P[:, 1] + 0.0, 0.004))
    b.lumpy(7.0, 0.006, seed)
    b.lumpy(31.0, 0.0016, seed + 1)
    return b


RAW = (0.46, 0.33, 0.31)
RAW_DARK = (0.27, 0.16, 0.16)


def reacher(name="reacher"):
    b = Body(name)
    b.base = RAW
    S = {s: np.array([sx * 0.36, 1.42, -0.5]) for s, sx in (("l", -1.0), ("r", 1.0))}
    E = {s: S[s] + np.array([sx * 0.58, 0.9, 0.72]) for s, sx in (("l", -1.0), ("r", 1.0))}
    H = {s: np.array([sx * 0.92, 0.0, -1.05]) for s, sx in (("l", -1.0), ("r", 1.0))}
    hip = {s: np.array([sx * 0.19, 0.84, 0.72]) for s, sx in (("l", -1.0), ("r", 1.0))}
    knee = {s: np.array([sx * 0.34, 0.5, 0.24]) for s, sx in (("l", -1.0), ("r", 1.0))}
    ankle = {s: np.array([sx * 0.3, 0.17, 0.8]) for s, sx in (("l", -1.0), ("r", 1.0))}
    toe = {s: np.array([sx * 0.31, 0.0, 0.52]) for s, sx in (("l", -1.0), ("r", 1.0))}
    b.bone("hips", None, (0, 0.88, 0.72))
    b.bone("spine", "hips", (0, 1.08, 0.3))
    b.bone("chest", "spine", (0, 1.3, -0.18))
    b.bone("neck", "chest", (0, 1.4, -0.66))
    b.bone("head", "neck", (0, 1.3, -1.0))
    b.bone("jaw", "head", (0, 1.25, -1.03))
    for s in ("l", "r"):
        b.bone("arm_" + s, "chest", S[s])
        b.bone("fore_" + s, "arm_" + s, E[s])
        b.bone("hand_" + s, "fore_" + s, H[s] + np.array([0, 0.06, 0.1]))
        b.bone("thigh_" + s, "hips", hip[s])
        b.bone("shin_" + s, "thigh_" + s, knee[s])
        b.bone("foot_" + s, "shin_" + s, ankle[s])
    b.ball("hips", (0, 0.86, 0.72), 0.17, (1.2, 0.85, 1.0), k=0.06)
    b.chain("spine", [(0, 0.92, 0.6), (0, 1.1, 0.25), (0, 1.26, -0.1)], [0.13, 0.115, 0.15], k=0.08)
    b.ball("chest", (0, 1.3, -0.36), 0.25, (0.95, 0.9, 1.25), k=0.09)
    for i in range(7):
        z = -0.6 + i * 0.085
        w = 0.235 - abs(i - 2.5) * 0.014
        for sx in (-1, 1):
            b.chain("chest", [(sx * 0.05, 1.5 - i * 0.012, z), (sx * w * 0.8, 1.42 - i * 0.01, z + 0.02), (sx * w, 1.26, z + 0.04), (sx * w * 0.7, 1.1, z + 0.02)], [0.016, 0.02, 0.02, 0.014], k=0.02)
    for i, t in enumerate(np.linspace(0.0, 1.0, 13)):
        p = np.array([0, 0.98, 0.7]) * (1 - t) + np.array([0, 1.52, -0.62]) * t + np.array([0, 0.09 * math.sin(t * math.pi), 0])
        b.ball("chest" if t > 0.55 else ("spine" if t > 0.18 else "hips"), tuple(p), 0.03, k=0.02)
    for sx in (-1, 1):
        b.ball("chest", (sx * 0.2, 1.5, -0.38), 0.11, (0.8, 0.6, 1.2), k=0.06)
    b.chain("neck", [(0, 1.42, -0.6), (0, 1.38, -0.82), (0, 1.32, -0.98)], [0.085, 0.066, 0.07], k=0.06)
    for sx in (-1, 1):
        b.capsule("neck", (sx * 0.06, 1.45, -0.6), (sx * 0.075, 1.36, -0.98), 0.018, k=0.025)
    hy, hz = 1.3, -1.1
    b.ball("head", (0, hy + 0.02, hz + 0.02), 0.125, (0.86, 0.95, 1.2), k=0.04)
    b.ball("head", (0, hy - 0.03, hz - 0.1), 0.085, (0.9, 0.8, 1.1), k=0.05)
    b.capsule("head", (-0.07, hy + 0.035, hz - 0.085), (0.07, hy + 0.035, hz - 0.085), 0.022, k=0.03)
    b.ball("jaw", (0, hy - 0.1, hz - 0.075), 0.078, (0.92, 0.6, 1.25), k=0.035)
    for sx in (-1, 1):
        b.capsule("jaw", (sx * 0.085, hy - 0.04, hz + 0.05), (sx * 0.05, hy - 0.12, hz - 0.13), 0.018, k=0.025)
        b.cut_ball((sx * 0.112, hy + 0.0, hz + 0.045), 0.03, (0.5, 1.0, 0.8), k=0.012)
        b.paint_ball((sx * 0.1, hy + 0.0, hz + 0.045), 0.034, DARK, 0.3)
        b.cut_capsule((sx * 0.012, hy - 0.012, hz - 0.185), (sx * 0.026, hy - 0.035, hz - 0.17), 0.007, k=0.004)
        b.cut_ball((sx * 0.05, hy + 0.01, hz - 0.105), 0.022, (1.2, 0.8, 0.6), k=0.025)
    my = hy - 0.07

    def arc(t):
        return np.array([t * 0.085, my + 0.035 * t * t, hz - 0.175 + 0.14 * t * t])
    ts = np.linspace(-1.0, 1.0, 13)
    for i in range(len(ts) - 1):
        r = 0.02 - 0.006 * abs(ts[i])
        b.cut_capsule(tuple(arc(ts[i])), tuple(arc(ts[i + 1])), r, k=0.006)
        b.paint_capsule(tuple(arc(ts[i]) + np.array([0, 0, 0.02])), tuple(arc(ts[i + 1]) + np.array([0, 0, 0.02])), r + 0.004, (0.1, 0.02, 0.02), 0.25)
    for i, t in enumerate(np.linspace(-0.92, 0.92, 17)):
        c = arc(t) + np.array([0, 0, 0.006])
        h = (0.022 if i % 3 else 0.031) - 0.008 * abs(t)
        b.extra_capsule("head", tuple(c + np.array([0, 0.015, 0])), tuple(c + np.array([0, 0.015 - h, -0.002])), 0.0058, 0.0028)
        b.extra_capsule("jaw", tuple(c + np.array([0.004, -0.017, 0.002])), tuple(c + np.array([0.004, -0.017 + h * 0.8, 0.0])), 0.0054, 0.0026)
        b.paint_ball(tuple(c), 0.02, TOOTH, 0.25, shine=0.6)
    for s, sx in (("l", -1.0), ("r", 1.0)):
        b.ball("chest", tuple(S[s]), 0.105, k=0.07)
        b.capsule("arm_" + s, tuple(S[s]), tuple(E[s]), 0.085, 0.06, k=0.05)
        b.ball("fore_" + s, tuple(E[s]), 0.072, k=0.03)
        b.ball("fore_" + s, tuple(E[s] + np.array([sx * 0.02, 0.05, 0.05])), 0.04, k=0.03)
        wrist = H[s] + np.array([0, 0.14, 0.2])
        b.capsule("fore_" + s, tuple(E[s]), tuple(wrist), 0.06, 0.04, k=0.04)
        b.capsule("fore_" + s, tuple(E[s] + np.array([sx * 0.03, -0.3, 0.0])), tuple(wrist + np.array([sx * 0.02, 0.3, 0.05])), 0.022, k=0.02)
        b.ball("hand_" + s, tuple(H[s] + np.array([0, 0.07, 0.08])), 0.085, (1.15, 0.5, 1.2), k=0.035)
        for f in range(5):
            a = (f - 2) * 0.32 * sx
            reach = 0.44 - 0.05 * abs(f - 2) - (0.1 if f == 0 else 0.0)
            k0 = H[s] + np.array([math.sin(a) * 0.09, 0.07, -0.02 - math.cos(a) * 0.07])
            k1 = H[s] + np.array([math.sin(a) * (0.09 + reach * 0.55), 0.085, -0.02 - math.cos(a) * (0.07 + reach * 0.55)])
            k2 = H[s] + np.array([math.sin(a) * (0.09 + reach), 0.012, -0.02 - math.cos(a) * (0.07 + reach)])
            b.chain("hand_" + s, [tuple(k0), tuple(k1), tuple(k2)], [0.024, 0.02, 0.012], k=0.015)
        b.paint_capsule(tuple(H[s] + np.array([0, 0.0, 0.2])), tuple(H[s] + np.array([0, 0.0, -0.5])), 0.34, RAW_DARK, 1.0)
        b.paint_ball(tuple(E[s]), 0.13, RAW_DARK, 1.0)
    for s, sx in (("l", -1.0), ("r", 1.0)):
        b.capsule("thigh_" + s, tuple(hip[s]), tuple(knee[s]), 0.092, 0.058, k=0.05)
        b.ball("shin_" + s, tuple(knee[s] + np.array([0, 0, -0.02])), 0.062, k=0.025)
        b.capsule("shin_" + s, tuple(knee[s]), tuple(ankle[s]), 0.052, 0.034, k=0.035)
        b.ball("foot_" + s, tuple(ankle[s]), 0.04, k=0.02)
        b.capsule("foot_" + s, tuple(ankle[s]), tuple(toe[s] + np.array([0, 0.03, 0.0])), 0.036, 0.03, k=0.03)
        for t in range(4):
            b.capsule("foot_" + s, tuple(toe[s] + np.array([sx * (0.04 - t * 0.026), 0.03, 0.0])), tuple(toe[s] + np.array([sx * (0.05 - t * 0.03), 0.014, -0.09])), 0.014, 0.011, k=0.01)
        b.paint_ball(tuple(toe[s]), 0.2, RAW_DARK, 1.0)
        b.paint_ball(tuple(knee[s]), 0.1, RAW_DARK, 1.0)
    b.cuts.append((lambda P: P[:, 1] + 0.0, 0.006))
    b.lumpy(5.0, 0.012, 21)
    b.lumpy(22.0, 0.003, 22)
    return b


SLATE = (0.30, 0.31, 0.34)
SLATE_DARK = (0.12, 0.12, 0.14)
BONE = (0.52, 0.49, 0.42)
SPLIT = (0.30, 0.07, 0.05)
CHAR = (0.05, 0.045, 0.045)


def colossus(name="colossus", tall=340.0):
    b = Body(name)
    b.base = SLATE
    u = tall / 340.0

    def P(x, y, z):
        return (x * u, y * u, z * u)
    hip_y, knee_y, ankle_y = 172.0, 92.0, 9.0
    chest_y, sh_y, neck_y, head_y = 250.0, 272.0, 282.0, 312.0
    b.bone("hips", None, P(0, hip_y + 4, 0))
    b.bone("spine", "hips", P(0, 204, 2))
    b.bone("chest", "spine", P(0, 236, 1))
    b.bone("neck", "chest", P(0, neck_y, -2))
    b.bone("head", "neck", P(0, 298, -5))
    b.bone("mouth_l", "head", P(-3, 300, -8))
    b.bone("mouth_r", "head", P(3, 300, -8))
    b.bone("arm_l", "chest", P(-30, sh_y, 0))
    b.bone("fore_l", "arm_l", P(-36, 172, 3))
    b.bone("hand_l", "fore_l", P(-38, 70, -2))
    b.bone("arm_r", "chest", P(30, sh_y, 0))
    b.bone("arm3", "chest", P(-17, 262, 15))
    b.bone("fore3", "arm3", P(-25, 208, 30))
    b.bone("hand3", "fore3", P(-27, 150, 26))
    for side, sx in (("l", -1.0), ("r", 1.0)):
        b.bone("thigh_" + side, "hips", P(sx * 14, hip_y, 0))
        b.bone("shin_" + side, "thigh_" + side, P(sx * 15, knee_y, -3))
        b.bone("foot_" + side, "shin_" + side, P(sx * 15, ankle_y, 2))
    for side, sx in (("l", -1.0), ("r", 1.0)):
        hip, knee, ankle = P(sx * 14, hip_y, 0), P(sx * 15, knee_y, -3), P(sx * 15, ankle_y, 2)
        b.capsule("thigh_" + side, hip, knee, 8.2 * u, 5.6 * u, k=5 * u)
        b.ball("shin_" + side, P(sx * 15, knee_y, -5), 7.0 * u, (1.0, 1.15, 1.0), k=3 * u)
        b.capsule("shin_" + side, knee, ankle, 5.6 * u, 3.6 * u, k=3.5 * u)
        b.capsule("shin_" + side, P(sx * 15, knee_y - 8, -7), P(sx * 15, ankle_y + 14, -1.5), 1.8 * u, k=1.6 * u)
        b.ball("foot_" + side, P(sx * 15, ankle_y, 3), 5.0 * u, k=2.5 * u)
        b.capsule("foot_" + side, P(sx * 15, 5, 7), P(sx * 16, 3.2, -30), 6.2 * u, 4.6 * u, k=4 * u)
        for t in range(4):
            b.capsule("foot_" + side, P(sx * (20.5 - t * 3.2) if sx > 0 else sx * (20.5 - t * 3.2), 3.0, -30), P(sx * (22 - t * 3.6), 1.8, -39 + t * 1.2), 1.9 * u, 1.4 * u, k=1.2 * u)
        b.paint_capsule(P(sx * 15, 0, 10), P(sx * 16, 0, -40), 22 * u, SLATE_DARK, 1.0)
        b.paint_ball(knee, 12 * u, SLATE_DARK, 1.0)
    b.ball("hips", P(0, hip_y + 5, 0), 17 * u, (1.25, 0.8, 0.75), k=7 * u)
    for sx in (-1, 1):
        b.ball("hips", P(sx * 15, hip_y + 11, -6), 5.0 * u, k=3.5 * u)
    b.chain("spine", [P(0, hip_y + 10, 2), P(0, 205, 4), P(0, 228, 3)], [10.5 * u, 8.2 * u, 10.5 * u], k=8 * u)
    b.ball("chest", P(0, 252, 0), 25 * u, (1.0, 1.25, 0.66), k=9 * u)
    for i in range(7):
        y = 232 + i * 6.2
        w = 22.5 - abs(i - 3) * 1.6
        for sx in (-1, 1):
            b.chain("chest", [P(sx * 4, y + 2.5, -15.5), P(sx * w * 0.75, y, -13), P(sx * w, y - 2.5, -3), P(sx * w * 0.8, y, 9)], [1.5 * u, 1.9 * u, 1.9 * u, 1.5 * u], k=1.9 * u)
    for y in np.arange(184, 284, 7.0):
        z = 14.5 if y > 228 else 11.0
        b.ball("chest" if y > 222 else ("spine" if y > 190 else "hips"), P(0, y, z), 2.4 * u, k=1.8 * u)
    for (y, lean, length) in ((276, 0.5, 26), (262, 0.2, 34), (246, -0.1, 22), (214, 0.35, 16)):
        b.chain("chest" if y > 222 else "spine", [P(0, y, 14), P(lean * 6, y + length * 0.5, 14 + length * 0.55), P(lean * 14, y + length * 0.8, 14 + length)], [2.0 * u, 1.3 * u, 0.5 * u], k=1.5 * u)
        b.paint_capsule(P(0, y + 3, 17), P(lean * 14, y + length * 0.8, 14 + length), 3.0 * u, BONE, 0.6, shine=0.5)
    for i, (x, y) in enumerate(((-13, 262), (-5, 255), (4, 249), (12, 242), (19, 236))):
        b.cut_ball(P(x, y, -15.5 + abs(x) * 0.12), 4.2 * u, (1.0, 1.0, 0.7), k=1.2 * u)
        b.paint_ball(P(x, y, -15), 5.4 * u, CHAR, 0.5)
    for sx in (-1, 1):
        b.ball("chest", P(sx * 28, sh_y, 0), 7.0 * u, k=5 * u)
        b.capsule("chest", P(sx * 3, sh_y - 4, -12), P(sx * 26, sh_y + 1, -4), 1.7 * u, 2.0 * u, k=2.2 * u)
        b.chain("chest", [P(sx * 27, sh_y + 4, 2), P(sx * 33, sh_y + 17, 5), P(sx * 37, sh_y + 30, 10)], [2.0 * u, 1.2 * u, 0.45 * u], k=1.5 * u)
        b.paint_capsule(P(sx * 30, sh_y + 8, 3), P(sx * 37, sh_y + 30, 10), 2.6 * u, BONE, 0.6, shine=0.5)
    b.capsule("arm_l", P(-30, sh_y, 0), P(-36, 172, 3), 5.4 * u, 3.9 * u, k=3.5 * u)
    b.ball("fore_l", P(-36, 172, 4), 4.7 * u, k=2 * u)
    b.capsule("fore_l", P(-36, 172, 3), P(-38, 70, -2), 4.1 * u, 2.9 * u, k=3 * u)
    b.ball("hand_l", P(-38, 62, -2), 5.2 * u, (0.6, 1.3, 1.0), k=2.5 * u)
    for f, (dz, reach) in enumerate(((-5.0, 36.0), (0.0, 42.0), (5.0, 33.0))):
        b.chain("hand_l", [P(-38, 56, -2 + dz * 0.6), P(-39.5, 56 - reach * 0.55, -2 + dz * 1.3), P(-35, 56 - reach, -2 + dz * 1.5 - 5)], [2.6 * u, 2.1 * u, 0.5 * u], k=1.6 * u)
        b.paint_capsule(P(-39.5, 56 - reach * 0.5, -2 + dz * 1.3), P(-35, 56 - reach, -2 + dz * 1.5 - 5), 3.2 * u, BONE, 0.7, shine=0.5)
    b.capsule("arm_r", P(30, sh_y, 0), P(35, 190, 2), 5.4 * u, 3.6 * u, k=3.5 * u)
    b.ball("arm_r", P(35.5, 186, 2), 4.0 * u, (1.0, 0.7, 1.0), k=2 * u)
    b.paint_ball(P(35.5, 184, 2), 9.5 * u, CHAR, 0.7)
    b.ball("chest", P(-17, 262, 14), 6.0 * u, (1.0, 1.2, 0.7), k=4 * u)
    b.capsule("arm3", P(-17, 262, 15), P(-25, 208, 30), 3.2 * u, 2.3 * u, k=2.5 * u)
    b.ball("fore3", P(-25, 208, 30), 2.8 * u, k=1.4 * u)
    b.capsule("fore3", P(-25, 208, 30), P(-27, 150, 26), 2.4 * u, 1.7 * u, k=2 * u)
    for dz in (-2.6, 0.0, 2.6):
        b.chain("hand3", [P(-27, 150, 26 + dz * 0.5), P(-28, 138, 26 + dz), P(-26, 126, 25 + dz * 1.2)], [1.4 * u, 1.1 * u, 0.35 * u], k=0.9 * u)
    b.chain("neck", [P(0, neck_y - 4, 0), P(0, 290, -2), P(0, 299, -4)], [6.4 * u, 4.6 * u, 5.0 * u], k=4.5 * u)
    for sx in (-1, 1):
        b.capsule("neck", P(sx * 4.5, neck_y - 2, -6), P(sx * 5.5, 299, 2), 1.4 * u, k=1.6 * u)
    b.ball("head", P(0, head_y + 3, -3), 13.5 * u, (0.84, 1.2, 1.05), k=4 * u)
    b.ball("head", P(0, head_y - 7, -8), 9.5 * u, (0.9, 1.15, 0.95), k=4.5 * u)
    b.capsule("head", P(-7, head_y + 4, -14.5), P(7, head_y + 4, -14.5), 2.0 * u, k=2.4 * u)
    for sx in (-1, 1):
        b.cut_ball(P(sx * 5.2, head_y + 0.5, -16.5), 2.6 * u, (1.2, 0.9, 0.6), k=2.2 * u)
        for (x, y, z, ex, ey, ez) in ((4, 14, -2, 13, 34, 4), (8, 9, 2, 22, 22, 9), (2, 15, 5, 5, 30, 14)):
            b.chain("head", [P(sx * x, head_y + y, z), P(sx * (x + ex) * 0.55, head_y + (y + ey) * 0.62, (z + ez) * 0.6), P(sx * ex, head_y + ey, ez)], [1.9 * u, 1.2 * u, 0.4 * u], k=1.3 * u)
            b.paint_capsule(P(sx * x * 1.2, head_y + y + 3, z), P(sx * ex, head_y + ey, ez), 2.6 * u, BONE, 0.6, shine=0.5)
    top, bottom = head_y + 0.5, 266.0
    ys = np.linspace(top, bottom, 12)

    def lip_z(y):
        return float(np.interp(y, [bottom, 281, 291, 300, top], [-16.2, -8.2, -8.6, -14.6, -16.6]))
    for i in range(len(ys) - 1):
        a_ = P(0, ys[i], lip_z(ys[i]) - 0.3)
        c_ = P(0, ys[i + 1], lip_z(ys[i + 1]) - 0.3)
        b.cut_capsule(a_, c_, 1.25 * u, k=0.7 * u)
        b.paint_capsule(P(0, ys[i], lip_z(ys[i]) + 1.4), P(0, ys[i + 1], lip_z(ys[i + 1]) + 1.4), 2.3 * u, (0.10, 0.02, 0.02), 0.4)
    for i, y in enumerate(np.linspace(top - 1.5, bottom + 1.5, 15)):
        sx = -1 if i % 2 else 1
        z = lip_z(y) + 0.5
        b.extra_capsule("mouth_l" if sx < 0 else "mouth_r", P(sx * 1.3, y, z), P(-sx * 0.9, y - 0.5, z - 0.9), 0.62 * u, 0.2 * u, k=0.2 * u)
        b.paint_ball(P(0, y, z - 0.4), 1.5 * u, BONE, 0.3, shine=0.6)
    for sx, bone in ((-1, "mouth_l"), (1, "mouth_r")):
        b.capsule(bone, P(sx * 4.2, top - 3, -13.5), P(sx * 4.5, 292, -8.5), 3.4 * u, 3.0 * u, k=3 * u)
        b.capsule(bone, P(sx * 4.5, 292, -8.0), P(sx * 5.5, bottom + 2, -13), 3.0 * u, 3.6 * u, k=3 * u)
    b.cuts.append((lambda Q: Q[:, 1] + 0.0, 0.5 * u))
    b.lumpy(0.045 / u, 1.5 * u, 31)
    b.lumpy(0.17 / u, 0.5 * u, 32)
    return b


WATCHERS = {
    "watcher_smile": dict(face="smile"),
    "watcher_frown": dict(face="frown", arms="ground", seed=3),
    "watcher_open": dict(face="open", neck=0.42, seed=5),
    "watcher_none": dict(face="none", missing_arm=True, seed=7),
}


def main():
    want = sys.argv[1:]
    out = maplib.out_dir("creatures")
    path = os.path.join(out, "creatures.json")
    info = json.load(open(path)) if os.path.exists(path) else {}
    for name, kw in WATCHERS.items():
        if want and name not in want and "watchers" not in want:
            continue
        b = watcher(name, **kw)
        info[name] = b.build(voxel=0.005, triangles=10000, soft=0.035, scale_ao=0.03)
    if not want or "colossus" in want:
        info["colossus"] = colossus().build(voxel=0.85, triangles=30000, soft=4.5, scale_ao=4.0)
    if not want or "reacher" in want:
        info["reacher"] = reacher().build(voxel=0.011, triangles=14000, soft=0.06, scale_ao=0.045)
    with open(path, "w") as f:
        json.dump(info, f, indent=1)


if __name__ == "__main__":
    main()
