"""Shared millimetre geometry for the new nozzles and CFD passages."""
import json
import math
from pathlib import Path

from geometry import smooth

ROOT = Path(__file__).resolve().parent
GAP = 16.0
FLOW = 51.0
SOCKET = 55.4
WALL = 2.4
MAPPING = {0: 225, 1: 180, 2: 315}
SCREEN = [(180, 140), (225, 180), (225, 220), (315, 260), (315, 320)]


def height(length):
    return 25.0 + length + 35.0 + 8.0


def widening_fraction(t, kind):
    if kind == 'quintic':
        return float(smooth(t))
    t = max(0., min(1., t))
    ramp = .2
    def integral(x):
        return 2.5*x**4 - 3*x**5 + x**6
    if t < ramp:
        return ramp*integral(t/ramp)/(1-ramp)
    if t > 1-ramp:
        return 1-ramp*integral((1-t)/ramp)/(1-ramp)
    return (t-ramp/2)/(1-ramp)


def profile(z, width, length, kind='quintic'):
    if z <= 25:
        return FLOW, FLOW, FLOW / 2
    inlet_area = math.pi * (FLOW / 2) ** 2
    chamber_area = width * 22 - (4 - math.pi) * 3**2
    if z <= 25 + length:
        q = widening_fraction((z - 25) / length, kind)
        w = FLOW + (width - FLOW) * q
        radius = FLOW / 2 + (3 - FLOW / 2) * q
        area = inlet_area + (chamber_area - inlet_area) * q
        depth = (area + (4 - math.pi) * radius**2) / w
        if radius > depth / 2:
            alpha = 1 - math.pi / 4
            depth = 2 * area / (w + math.sqrt(w*w - 4*alpha*area))
            radius = depth / 2
        return w, depth, radius
    q = float(smooth((z - 25 - length) / 35))
    radius = 3 + (.8 - 3) * q
    outlet_area = width * GAP - (4 - math.pi) * .8**2
    area = chamber_area + (outlet_area - chamber_area) * q
    return width, (area + (4 - math.pi) * radius**2) / width, radius


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
