# title: straight pipes and elbows from detected cylinders
# created date: 2026.11, taewook kang, laputa99999@gmail.com
# desc: cylinders on one axis are merged into one pipe, radii are snapped to nominal sizes, and two
#       pipe ends that point at a common corner are joined by an elbow. the elbow is a torus segment
#       tangent to both pipes, and both pipes are cut or extended to the tangent points.

import numpy as np

class Pipe:
    def __init__(self, start, end, radius, points=0, coverage=0.0, sources=None):
        self.start = np.asarray(start, float)
        self.end = np.asarray(end, float)
        self.radius = float(radius)
        self.measured_radius = float(radius)
        self.nominal = None
        self.points = int(points)
        self.coverage = float(coverage)
        self.sources = list(sources or [])

    @property
    def axis(self):
        return (self.end - self.start) / self.length

    @property
    def length(self):
        return float(np.linalg.norm(self.end - self.start))

    def to_dict(self, index):
        return {'id': index, 'start': self.start.tolist(), 'end': self.end.tolist(), 'radius': self.radius,
                'measured_radius': self.measured_radius, 'nominal': self.nominal, 'length': self.length,
                'points': self.points, 'coverage': self.coverage, 'cylinders': self.sources}

def line_distance(point, origin, axis):
    d = point - origin
    return float(np.linalg.norm(d - axis * (d @ axis)))

def can_merge(a, b, angle, distance, radius_tolerance, gap):
    if abs(a.axis @ b.axis) < np.cos(np.radians(angle)):
        return False
    if abs(a.radius - b.radius) > radius_tolerance:
        return False
    if max(line_distance(b.start, a.start, a.axis), line_distance(b.end, a.start, a.axis),
           line_distance(a.start, b.start, b.axis), line_distance(a.end, b.start, b.axis)) > distance:
        return False
    ta = sorted([0.0, a.length])
    tb = sorted([(b.start - a.start) @ a.axis, (b.end - a.start) @ a.axis])
    return max(ta[0], tb[0]) - min(ta[1], tb[1]) <= gap

def merge_two(a, b):
    axis = b.axis if a.axis @ b.axis > 0 else -b.axis
    wa, wb = a.points * a.length, b.points * b.length
    axis = (a.axis * wa + axis * wb) / (wa + wb)
    axis /= np.linalg.norm(axis)
    center = ((a.start + a.end) * wa + (b.start + b.end) * wb) / (2 * (wa + wb))
    t = [(p - center) @ axis for p in (a.start, a.end, b.start, b.end)]
    radius = (a.radius * a.points + b.radius * b.points) / (a.points + b.points)
    return Pipe(center + axis * min(t), center + axis * max(t), radius, a.points + b.points,
                max(a.coverage, b.coverage), a.sources + b.sources)

def merge(pipes, angle=5.0, distance=0.02, radius_tolerance=0.01, gap=0.3):
    pipes = list(pipes)
    merged = True
    while merged:
        merged = False
        for i in range(len(pipes)):
            for j in range(i + 1, len(pipes)):
                if can_merge(pipes[i], pipes[j], angle, distance, radius_tolerance, gap):
                    pipes[i] = merge_two(pipes[i], pipes[j])
                    del pipes[j]
                    merged = True
                    break
            if merged:
                break
    return pipes

def snap_radius(pipes, sizes, tolerance):
    # sizes: list of {'name', 'outer_diameter'} in meters
    for p in pipes:
        if not sizes:
            break
        best = min(sizes, key=lambda s: abs(s['outer_diameter'] / 2 - p.measured_radius))
        if abs(best['outer_diameter'] / 2 - p.measured_radius) <= tolerance:
            p.radius = best['outer_diameter'] / 2
            p.nominal = best['name']
    return pipes

def closest_points(p, d, q, e):
    # closest points of the lines p + s d and q + t e
    w = p - q
    b = d @ e
    den = 1 - b * b
    if den < 1e-9:
        return None
    s = (b * (e @ w) - (d @ w)) / den
    t = ((e @ w) - b * (d @ w)) / den
    return p + d * s, q + e * t

def end_toward(pipe, corner):
    # the pipe end nearer the corner, and the direction from the pipe out to that end
    if np.linalg.norm(pipe.end - corner) <= np.linalg.norm(pipe.start - corner):
        return 'end', pipe.axis
    return 'start', -pipe.axis

def elbow_candidates(pipes, angles, angle_tolerance, axis_tolerance, reach, radius_tolerance):
    found = []
    for i in range(len(pipes)):
        for j in range(i + 1, len(pipes)):
            a, b = pipes[i], pipes[j]
            if abs(a.radius - b.radius) > radius_tolerance:
                continue
            close = closest_points(a.start, a.axis, b.start, b.axis)
            if close is None:
                continue
            pa, pb = close
            r = max(a.radius, b.radius)
            if np.linalg.norm(pa - pb) > axis_tolerance * r:
                continue
            corner = (pa + pb) / 2
            ea, da = end_toward(a, corner)
            eb, db = end_toward(b, corner)
            # the corner lies beyond both ends, or just inside them; past that it is a tee
            sa = (corner - getattr(a, ea)) @ da
            sb = (corner - getattr(b, eb)) @ db
            if not (-2 * r <= sa <= reach and -2 * r <= sb <= reach):
                continue
            deflection = np.degrees(np.arccos(np.clip(da @ -db, -1, 1)))
            if min(abs(deflection - a) for a in angles) > angle_tolerance:
                continue
            found.append((max(sa, 0) + max(sb, 0), i, j, ea, eb, da, db, corner, deflection))
    return sorted(found, key=lambda f: f[0])

def drop_elbow_pieces(pipes, angles=(45.0, 90.0), angle_tolerance=10.0, axis_tolerance=1.0, reach=0.5,
                      radius_tolerance=0.01, max_length=0.3):
    # the bend of an elbow is often fitted as a short pipe at an angle to both pipes it joins. such a
    # short pipe near the corner of two pipes whose axes meet is dropped. a real offset made of two
    # 45 degree elbows joins parallel pipes, whose axes do not meet
    drop = set()
    for _, i, j, _, _, _, _, corner, _ in elbow_candidates(pipes, angles, angle_tolerance, axis_tolerance, reach, radius_tolerance):
        for k, p in enumerate(pipes):
            if k in (i, j) or p.length > max_length:
                continue
            if max(np.linalg.norm(p.start - corner), np.linalg.norm(p.end - corner)) > reach:
                continue
            if min(angle_between(p, pipes[i]), angle_between(p, pipes[j])) < angle_tolerance:
                continue
            drop.add(k)
    return [p for k, p in enumerate(pipes) if k not in drop]

def angle_between(a, b):
    return np.degrees(np.arccos(np.clip(abs(a.axis @ b.axis), 0, 1)))

def make_elbows(pipes, angles=(45.0, 90.0), bend_ratio=1.5, min_bend_ratio=1.0, bend_radii=None, angle_tolerance=10.0,
                axis_tolerance=1.0, reach=0.5, radius_tolerance=0.01, min_pipe_length=0.05):
    # angles: elbow angles made by fittings; a pair of pipes at another angle is not joined.
    # bend radius: bend_radii[nominal size] when given, else bend_ratio x outer diameter
    bend_radii = bend_radii or {}
    elbows = []
    used = set()
    for _, i, j, ea, eb, da, db, corner, deflection in elbow_candidates(pipes, angles, angle_tolerance, axis_tolerance, reach, radius_tolerance):
        if (i, ea) in used or (j, eb) in used:
            continue
        a, b = pipes[i], pipes[j]
        r = (a.radius + b.radius) / 2
        theta = np.radians(deflection)
        nominal = a.nominal if a.nominal == b.nominal else None
        bend = bend_radii.get(nominal) or bend_ratio * 2 * r
        # tangent points sit bend * tan(theta / 2) back from the corner along each pipe
        back = bend * np.tan(theta / 2)
        room = min((corner - getattr(a, 'start' if ea == 'end' else 'end')) @ da,
                   (corner - getattr(b, 'start' if eb == 'end' else 'end')) @ db) - min_pipe_length
        if room <= 0:
            continue
        if back > room:
            # pipes too short for the bend: a tighter bend, down to min_bend_ratio x outer diameter
            back = room
            bend = back / np.tan(theta / 2)
            if bend < min_bend_ratio * 2 * r:
                continue
        ta, tb = corner - da * back, corner - db * back
        setattr(a, ea, ta)
        setattr(b, eb, tb)
        # the arc center is on the bisector of the inner angle
        center = corner - (da + db) / np.linalg.norm(da + db) * (bend / np.cos(theta / 2))
        elbows.append({'pipes': [i, j], 'corner': corner.tolist(), 'center': center.tolist(),
                       'start': ta.tolist(), 'end': tb.tolist(), 'start_direction': da.tolist(),
                       'radius': float(r), 'bend_radius': float(bend), 'angle': float(deflection),
                       'nominal': nominal})
        used.update([(i, ea), (j, eb)])
    return elbows

def tube(rings, radius, segments, frames):
    # rings: centers along the path, frames: (u, v) per ring. returns vertices and faces with end caps
    angle = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    vertices = [c + radius * (np.outer(np.cos(angle), u) + np.outer(np.sin(angle), v)) for c, (u, v) in zip(rings, frames)]
    vertices = np.vstack(vertices + [rings[0][None, :], rings[-1][None, :]])
    n, m = len(rings), segments
    faces = []
    for i in range(n - 1):
        for k in range(m):
            a, b = i * m + k, i * m + (k + 1) % m
            faces += [(a, b, b + m), (a, b + m, a + m)]
    first, last = n * m, n * m + 1
    for k in range(m):
        faces += [(first, (k + 1) % m, k), (last, (n - 1) * m + k, (n - 1) * m + (k + 1) % m)]
    return vertices, np.array(faces)

def frame(axis):
    ref = np.eye(3)[np.argmin(np.abs(axis))]
    u = np.cross(axis, ref)
    u /= np.linalg.norm(u)
    return u, np.cross(axis, u)

def pipe_mesh(pipe, segments=24):
    return tube([pipe.start, pipe.end], pipe.radius, segments, [frame(pipe.axis)] * 2)

def elbow_mesh(elbow, segments=24, steps=12):
    center, start = np.array(elbow['center']), np.array(elbow['start'])
    tangent = np.array(elbow['start_direction'])
    e1 = (start - center) / np.linalg.norm(start - center)
    binormal = np.cross(e1, tangent)
    rings, frames = [], []
    for phi in np.linspace(0, np.radians(elbow['angle']), steps + 1):
        radial = np.cos(phi) * e1 + np.sin(phi) * tangent
        rings.append(center + elbow['bend_radius'] * radial)
        frames.append((radial, binormal))
    return tube(rings, elbow['radius'], segments, frames)
