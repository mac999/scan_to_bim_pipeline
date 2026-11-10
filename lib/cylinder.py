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

def snap_axis(axis, angle, directions=None):
    for a in AXES if directions is None else directions:
        if abs(axis @ a) > np.cos(np.radians(angle)):
            return a * np.sign(axis @ a)
    return axis

def pipe_directions(angles, azimuth=0.0):    # azimuth of the grid in degrees
    # axis directions a pipe run can take: elevations and azimuths (from the grid azimuth) that are
    # multiples of the fitting angles, e.g. [45, 90] gives 0, 45 and 90 degrees in both
    steps = [a for a in angles if 0 < a <= 90]
    elevations = sorted({0.0, 90.0} | {float(k * a) for a in steps for k in range(1, int(90 // a) + 1)})
    azimuths = sorted({0.0} | {float(k * a) % 180 for a in steps for k in range(1, int(180 // a) + 1)})
    found = []
    for e in np.radians(elevations):
        for z in np.radians(np.array(azimuths) + azimuth) if e < np.pi / 2 - 1e-9 else [0.0]:
            d = np.array([np.cos(e) * np.cos(z), np.cos(e) * np.sin(z), np.sin(e)])
            if all(abs(d @ f) < 1 - 1e-9 for f in found):
                found.append(d)
    return np.array(found)

def off_directions(axis, directions, angle):
    return directions is not None and np.max(np.abs(directions @ axis)) < np.cos(np.radians(angle))

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

def refine(points, normals, cyl, axis_snap_angle=0.0, fixed_axis=False, directions=None):
    axis = cyl.axis if fixed_axis else axis_from_normals(normals)
    if axis @ cyl.axis < 0:
        axis = -axis
    if axis_snap_angle > 0:
        axis = snap_axis(axis, axis_snap_angle, directions)
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
           max_failures=200, seed=0, log=None, directions=None, rejected=None):
    # directions: allowed axis directions (pipe_directions). a cylinder on another axis is not a pipe; it is
    # added to the rejected list when one is given
    rng = np.random.default_rng(seed)
    points = np.asarray(points, float)
    normals = np.asarray(normals, float)
    tree = cKDTree(points)
    alive = np.ones(len(points), bool)
    tried = np.zeros(len(points), bool)
    listed = np.zeros(len(points), bool)
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
            cyl = refine(points[index], normals[index], cyl, axis_snap_angle, directions=directions)
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
        if off_directions(cyl.axis, directions, max(axis_snap_angle, 1.0)):
            # its points stay for other cylinders but are not used as seeds again
            tried[index] = True
            # other seeds on the same surface find it again; it is listed once
            if rejected is not None and listed[index].mean() < 0.5:
                cyl.reason = 'direction'
                rejected.append(cyl)
                listed[index] = True
            failures += 1
            continue
        alive[index] = False
        found.append(cyl)
        failures = 0
        if log:
            log(f'cylinder {len(found) - 1}: r={cyl.radius:.3f} length={cyl.length:.2f} points={len(index)} coverage={cyl.coverage:.2f}')
    return found, np.flatnonzero(alive)

# tiled detection. each tile is searched with a margin around it, so a cylinder that crosses the tile
# border is seen with at least the margin of its length. pieces of one cylinder found in neighbouring
# tiles are joined, refitted and checked once more against the thresholds of the whole cloud.

def tile_boxes(points, tiles, overlap):
    lo, hi = points.min(axis=0), points.max(axis=0)
    counts = list(tiles) + [1] * (3 - len(tiles))
    edges = [np.linspace(lo[a], hi[a], counts[a] + 1) for a in range(3)]
    boxes = []
    for i in range(counts[0]):
        for j in range(counts[1]):
            for k in range(counts[2]):
                core_lo = np.array([edges[0][i], edges[1][j], edges[2][k]])
                core_hi = np.array([edges[0][i + 1], edges[1][j + 1], edges[2][k + 1]])
                boxes.append((core_lo - overlap, core_hi + overlap))
    return boxes

def _detect_tile(job):
    index, points, normals, params = job
    rejected = []
    found, _ = detect(points, normals, rejected=rejected, **params)
    for c in found + rejected:
        c.inliers = index[c.inliers]
    return found, rejected

def same_cylinder(a, b, angle, offset, radius_tolerance, gap):
    if abs(a.axis @ b.axis) < np.cos(np.radians(angle)) or abs(a.radius - b.radius) > radius_tolerance:
        return False
    if max(a.distance(np.array([b.start, b.end])).max(), b.distance(np.array([a.start, a.end])).max()) > offset:
        return False
    ta = sorted([(a.start - a.point) @ a.axis, (a.end - a.point) @ a.axis])
    tb = sorted([(b.start - a.point) @ a.axis, (b.end - a.point) @ a.axis])
    return max(ta[0], tb[0]) - min(ta[1], tb[1]) <= gap

def longest_run(cyl, index, points, max_gap):
    t = (points[index] - cyl.point) @ cyl.axis
    order = np.argsort(t)
    cuts = np.r_[0, np.where(np.diff(t[order]) > max_gap)[0] + 1, len(t)]
    k = np.argmax(np.diff(cuts))
    return index[order[cuts[k]:cuts[k + 1]]]

def stitch(pieces, points, normals, min_radius, max_radius, tolerance, normal_angle, min_points, min_length,
           max_gap, min_coverage, axis_snap_angle, merge_angle=5.0, directions=None, rejected=None):
    group = list(range(len(pieces)))
    def root(i):
        while group[i] != i:
            i = group[i]
        return i
    for i in range(len(pieces)):
        for j in range(i + 1, len(pieces)):
            a, b = pieces[i], pieces[j]
            if same_cylinder(a, b, merge_angle, max(2 * tolerance, 0.2 * a.radius), 2 * tolerance, max_gap):
                group[root(j)] = root(i)
    groups = {}
    for i in range(len(pieces)):
        groups.setdefault(root(i), []).append(pieces[i])

    cos_normal = np.cos(np.radians(normal_angle))
    candidates = []
    for members in groups.values():
        cyl = max(members, key=lambda c: len(c.inliers))
        index = np.unique(np.concatenate([c.inliers for c in members]))
        if len(members) > 1:
            cyl = refine(points[index], normals[index], cyl, axis_snap_angle, directions=directions)
            index = index[inlier_mask(cyl, points[index], normals[index], 2 * tolerance, cos_normal)]
            if len(index):
                index = longest_run(cyl, index, points, max_gap)
        candidates.append((cyl, index))

    # a point found by two cylinders stays with the larger one
    taken = np.zeros(len(points), bool)
    found = []
    for cyl, index in sorted(candidates, key=lambda c: -len(c[1])):
        index = index[~taken[index]]
        if len(index) < min_points or not min_radius <= cyl.radius <= max_radius:
            continue
        t = (points[index] - cyl.point) @ cyl.axis
        if t.max() - t.min() < min_length:
            continue
        cyl.coverage = coverage(cyl, points[index])
        if cyl.coverage < min_coverage:
            continue
        cyl.start, cyl.end = cyl.point + cyl.axis * t.min(), cyl.point + cyl.axis * t.max()
        cyl.inliers = index
        if off_directions(cyl.axis, directions, max(axis_snap_angle, 1.0)):
            if rejected is not None:
                cyl.reason = 'direction'
                rejected.append(cyl)
            continue
        taken[index] = True
        found.append(cyl)
    return found

def detect_tiled(points, normals, min_radius, max_radius, tolerance=0.005, normal_angle=20.0, min_points=200,
                 min_length=0.1, max_gap=0.05, min_coverage=0.25, axis_snap_angle=0.0, hypotheses=50,
                 max_failures=200, seed=0, tiles=(1, 1), overlap=0.0, workers=1, log=None, directions=None,
                 rejected=None):
    params = dict(min_radius=min_radius, max_radius=max_radius, tolerance=tolerance, normal_angle=normal_angle,
                  min_points=min_points, min_length=min_length, max_gap=max_gap, min_coverage=min_coverage,
                  axis_snap_angle=axis_snap_angle, hypotheses=hypotheses, max_failures=max_failures,
                  directions=directions)
    points = np.asarray(points, float)
    normals = np.asarray(normals, float)
    if int(np.prod(tiles)) <= 1:
        return detect(points, normals, seed=seed, log=log, rejected=rejected, **params)
    if overlap <= 0:
        overlap = max(min_length, 2 * max_radius) + max_gap
    jobs = []
    for k, (lo, hi) in enumerate(tile_boxes(points, tiles, overlap)):
        index = np.flatnonzero(np.all((points >= lo) & (points <= hi), axis=1))
        if len(index) >= min_points:
            jobs.append((index, points[index], normals[index], dict(params, seed=seed + k)))
    if workers > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(workers) as pool:
            results = list(pool.map(_detect_tile, jobs))
    else:
        results = [_detect_tile(job) for job in jobs]
    pieces = [c for found, _ in results for c in found]
    if rejected is not None:
        rejected += [c for _, r in results for c in r]
    if log:
        log(f'{len(jobs)} tiles, overlap {overlap:.2f}, {len(pieces)} pieces')
    found = stitch(pieces, points, normals, min_radius, max_radius, tolerance, normal_angle, min_points,
                   min_length, max_gap, min_coverage, axis_snap_angle, directions=directions, rejected=rejected)
    alive = np.ones(len(points), bool)
    for c in found:
        alive[c.inliers] = False
    if log:
        for k, c in enumerate(found):
            log(f'cylinder {k}: r={c.radius:.3f} length={c.length:.2f} points={len(c.inliers)} coverage={c.coverage:.2f}')
    return found, np.flatnonzero(alive)
