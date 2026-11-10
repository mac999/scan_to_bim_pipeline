# title: cylinder detection in point clouds
# created date: 2026.11, taewook kang, laputa99999@gmail.com
# desc: repeated RANSAC cylinder extraction for pipes. a hypothesis is made from two points and their
#       normals, scored in the neighbourhood of a seed point, refined by least squares on all points
#       and cut where the points along the axis stop. based on Kang et al. 2020, Appl. Sci. 10, 7422,
#       with two point sampling instead of three, since three points rarely lie on one cross section.

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import cKDTree

AXES = np.eye(3)

class Cylinder:
    def __init__(self, point, axis, radius):
        self.axis = np.asarray(axis, float) / np.linalg.norm(axis)
        self.point = np.asarray(point, float)
        self.radius = float(radius)
        self.start = self.end = None
        self.inliers = None
        self.coverage = 0.0

    @property
    def length(self):
        return float(np.linalg.norm(self.end - self.start))

    def radial(self, points):
        # vectors from the axis to the points, perpendicular to the axis
        d = points - self.point
        return d - np.outer(d @ self.axis, self.axis)

    def distance(self, points):
        return np.linalg.norm(self.radial(points), axis=1)

    def to_dict(self):
        return {'start': self.start.tolist(), 'end': self.end.tolist(), 'axis': self.axis.tolist(),
                'radius': self.radius, 'length': self.length, 'points': int(len(self.inliers)),
                'coverage': self.coverage}

def from_normals(p1, n1, p2, n2):
    # both normals are perpendicular to the axis and point away from it
    axis = np.cross(n1, n2)
    norm = np.linalg.norm(axis)
    if norm < 1e-3:
        return None
    axis /= norm
    # in the plane perpendicular to the axis, the lines p + t n meet at the center
    u = n1 - axis * (n1 @ axis)
    v = n2 - axis * (n2 @ axis)
    w = p2 - p1
    w = w - axis * (w @ axis)
    a = np.array([[u @ u, -(u @ v)], [u @ v, -(v @ v)]])
    try:
        t, s = np.linalg.solve(a, [w @ u, w @ v])
    except np.linalg.LinAlgError:
        return None
    center = (p1 + u * t + p2 - axis * ((p2 - p1) @ axis) + v * s) / 2
    radius = (abs(t) * np.linalg.norm(u) + abs(s) * np.linalg.norm(v)) / 2
    return Cylinder(center, axis, radius)

def axis_from_normals(normals):
    # normals of a cylinder are perpendicular to its axis
    return np.linalg.eigh(normals.T @ normals)[1][:, 0]

def snap_axis(axis, angle):
    for a in AXES:
        if abs(axis @ a) > np.cos(np.radians(angle)):
            return a * np.sign(axis @ a)
    return axis

def basis(axis):
    ref = AXES[np.argmin(np.abs(axis))]
    u = np.cross(axis, ref)
    u /= np.linalg.norm(u)
    return u, np.cross(axis, u)

def fit_circle(xy):
    # algebraic fit as a start, then geometric least squares
    a = np.c_[2 * xy, np.ones(len(xy))]
    b = (xy ** 2).sum(axis=1)
    cx, cy, c = np.linalg.lstsq(a, b, rcond=None)[0]
    r = np.sqrt(max(c + cx ** 2 + cy ** 2, 1e-12))
    res = least_squares(lambda q: np.linalg.norm(xy - q[:2], axis=1) - q[2], [cx, cy, r], loss='soft_l1', f_scale=0.005)
    return res.x[:2], abs(res.x[2])

def refine(points, normals, cyl, axis_snap_angle=0.0, fixed_axis=False):
    axis = cyl.axis if fixed_axis else axis_from_normals(normals)
    if axis @ cyl.axis < 0:
        axis = -axis
    if axis_snap_angle > 0:
        axis = snap_axis(axis, axis_snap_angle)
    u, v = basis(axis)
    origin = points.mean(axis=0)
    d = points - origin
    center, radius = fit_circle(np.c_[d @ u, d @ v])
    return Cylinder(origin + u * center[0] + v * center[1], axis, radius)

def coverage(cyl, points, bins=36):
    # longest unbroken arc around the axis, as a fraction of the circle. a false cylinder that
    # touches several pipes side by side picks up short separate arcs
    u, v = basis(cyl.axis)
    r = cyl.radial(points)
    angle = np.arctan2(r @ v, r @ u)
    count = np.bincount((np.floor((angle + np.pi) / (2 * np.pi) * bins).astype(int)) % bins, minlength=bins)
    filled = count >= max(2, 0.2 * count.max())
    if filled.all():
        return 1.0
    best = run = 0
    for f in np.roll(filled, -int(np.argmin(filled))):
        run = run + 1 if f else 0
        best = max(best, run)
    return best / bins

def inlier_mask(cyl, points, normals, tolerance, cos_normal):
    r = cyl.radial(points)
    dist = np.linalg.norm(r, axis=1)
    ok = np.abs(dist - cyl.radius) < tolerance
    ok[ok] &= np.abs(np.einsum('ij,ij->i', r[ok], normals[ok])) > cos_normal * dist[ok]
    return ok

def split(cyl, index, points, max_gap, seed_point):
    # keep the run of points along the axis that holds the seed
    t = (points[index] - cyl.point) @ cyl.axis
    order = np.argsort(t)
    ts = t[order]
    breaks = np.where(np.diff(ts) > max_gap)[0]
    lo = np.r_[0, breaks + 1]
    hi = np.r_[breaks + 1, len(ts)]
    t_seed = (seed_point - cyl.point) @ cyl.axis
    k = np.searchsorted(ts[hi - 1], t_seed)
    k = min(k, len(lo) - 1)
    return index[order[lo[k]:hi[k]]]

def detect(points, normals, min_radius, max_radius, tolerance=0.005, normal_angle=20.0, min_points=200,
           min_length=0.1, max_gap=0.05, min_coverage=0.25, axis_snap_angle=0.0, hypotheses=50,
           max_failures=200, seed=0, log=None):
    rng = np.random.default_rng(seed)
    points = np.asarray(points, float)
    normals = np.asarray(normals, float)
    tree = cKDTree(points)
    alive = np.ones(len(points), bool)
    tried = np.zeros(len(points), bool)
    cos_normal = np.cos(np.radians(normal_angle))
    found = []
    failures = 0
    while failures < max_failures:
        candidates = np.flatnonzero(alive & ~tried)
        if len(candidates) < min_points:
            break
        s = rng.choice(candidates)
        tried[s] = True
        near = np.array(tree.query_ball_point(points[s], 2 * max_radius), int)
        near = near[alive[near]]
        if len(near) < min_points / 4:
            failures += 1
            continue
        # hypotheses from the seed and random neighbours, scored on the neighbourhood
        best, best_score = None, 0
        for o in rng.choice(near, min(hypotheses, len(near)), replace=False):
            cyl = from_normals(points[s], normals[s], points[o], normals[o])
            if cyl is None or not min_radius <= cyl.radius <= max_radius:
                continue
            score = inlier_mask(cyl, points[near], normals[near], tolerance, cos_normal).sum()
            if score > best_score:
                best, best_score = cyl, score
        if best is None or best_score < min_points / 4:
            failures += 1
            continue
        cyl = best
        index = np.flatnonzero(alive)
        for _ in range(3):
            index = np.flatnonzero(alive)
            index = index[inlier_mask(cyl, points[index], normals[index], tolerance * 2, cos_normal)]
            if len(index) < min_points:
                break
            index = split(cyl, index, points, max_gap, points[s])
            if len(index) < min_points:
                break
            cyl = refine(points[index], normals[index], cyl, axis_snap_angle)
            if not min_radius <= cyl.radius <= max_radius:
                break
        index = np.flatnonzero(alive)
        index = index[inlier_mask(cyl, points[index], normals[index], tolerance, cos_normal)]
        if len(index) >= min_points:
            index = split(cyl, index, points, max_gap, points[s])
        t = (points[index] - cyl.point) @ cyl.axis if len(index) else np.zeros(1)
        if (len(index) < min_points or not min_radius <= cyl.radius <= max_radius
                or t.max() - t.min() < min_length):
            failures += 1
            continue
        cyl.coverage = coverage(cyl, points[index])
        if cyl.coverage < min_coverage:
            failures += 1
            continue
        cyl.start = cyl.point + cyl.axis * t.min()
        cyl.end = cyl.point + cyl.axis * t.max()
        cyl.inliers = index
        alive[index] = False
        found.append(cyl)
        failures = 0
        if log:
            log(f'cylinder {len(found) - 1}: r={cyl.radius:.3f} length={cyl.length:.2f} points={len(index)} coverage={cyl.coverage:.2f}')
    return found, np.flatnonzero(alive)
