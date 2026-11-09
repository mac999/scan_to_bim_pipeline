# title: planar segments to polygons that meet their neighbours
# created date: 2026.11, taewook kang, laputa99999@gmail.com
# desc: each segment is fitted to a plane and outlined in that plane. where two planes come within
#       a buffer distance of their intersection line, both outlines are extended or trimmed to that
#       line, so walls, floors and ceilings share their edges and corners without gaps.

from itertools import combinations
import numpy as np
from shapely.geometry import MultiPoint, Point, Polygon, LineString
from shapely.ops import unary_union

Z_AXIS = np.array([0.0, 0.0, 1.0])

class Plane:
    def __init__(self, normal, origin):
        self.normal = np.asarray(normal, float) / np.linalg.norm(normal)
        self.origin = np.asarray(origin, float)
        ref = Z_AXIS if abs(self.normal[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        self.u = np.cross(ref, self.normal)
        self.u /= np.linalg.norm(self.u)
        self.v = np.cross(self.normal, self.u)

    @property
    def offset(self):
        return float(self.normal @ self.origin)

    def to_2d(self, pts):
        d = np.asarray(pts, float) - self.origin
        return np.c_[d @ self.u, d @ self.v]

    def to_3d(self, pts2d):
        pts2d = np.asarray(pts2d, float)
        return self.origin + np.outer(pts2d[:, 0], self.u) + np.outer(pts2d[:, 1], self.v)

def sample(points, max_points, seed=0):
    if len(points) <= max_points:
        return points
    return points[np.random.default_rng(seed).choice(len(points), max_points, replace=False)]

def fit_plane(points, axis_snap_angle=0.0):
    # axis_snap_angle makes nearly level planes level and nearly vertical planes vertical,
    # so that floors are flat and wall corners are plumb
    pts = sample(np.asarray(points, float), 50000)
    center = pts.mean(axis=0)
    normal = np.linalg.svd(pts - center, full_matrices=False)[2][2]
    tilt = np.degrees(np.arccos(min(1.0, abs(normal[2]))))
    if tilt < axis_snap_angle:
        normal = np.array([0.0, 0.0, np.sign(normal[2]) or 1.0])
    elif tilt > 90.0 - axis_snap_angle:
        normal = np.array([normal[0], normal[1], 0.0])
        normal /= np.linalg.norm(normal)
    offset = np.median(pts @ normal)    # median keeps clutter near the plane from shifting it
    return Plane(normal, center + (offset - center @ normal) * normal)

def outline(plane, points, alpha=0.0, tolerance=0.0):
    pts2d = plane.to_2d(sample(np.asarray(points, float), 20000))
    if alpha > 0:
        import alphashape
        shape = alphashape.alphashape(pts2d, alpha)
    else:
        shape = MultiPoint(pts2d).convex_hull
    if shape.geom_type == 'MultiPolygon':
        shape = max(shape.geoms, key=lambda g: g.area)
    if shape.geom_type != 'Polygon':
        return None
    shape = Polygon(shape.exterior)
    return shape.simplify(tolerance) if tolerance > 0 else shape

def intersection_line(a, b):
    direction = np.cross(a.normal, b.normal)
    direction /= np.linalg.norm(direction)
    point = np.linalg.solve(np.array([a.normal, b.normal, direction]), [a.offset, b.offset, 0.0])
    # move the point next to the planes, half planes built around it then stay local
    middle = (a.origin + b.origin) / 2
    return point + direction * ((middle - point) @ direction), direction

def line_in_plane(plane, point, direction):
    p = plane.to_2d([point])[0]
    d = plane.to_2d([plane.origin + direction])[0]
    return p, d / np.linalg.norm(d)

def side_distance(poly, p, d):
    # signed distances of the outline vertices from the line, left side positive
    xy = np.asarray(poly.exterior.coords)
    return d[0] * (xy[:, 1] - p[1]) - d[1] * (xy[:, 0] - p[0])

def edge_distance(poly, p, d):
    # how far the outline is from having the line as an edge: the gap to the line, or the
    # overshoot past it. a line through the middle of the outline (a T junction) is far
    s = side_distance(poly, p, d)
    if s.min() > 0 or s.max() < 0:
        return float(np.abs(s).min())
    return float(min(s.max(), -s.min()))

def span(poly, p, d):
    t = (np.asarray(poly.exterior.coords) - p) @ d
    return t.min(), t.max()

def half_plane(p, d, side, size):
    n = np.array([-d[1], d[0]]) * side
    return Polygon([p - d * size, p + d * size, p + d * size + n * size, p - d * size + n * size])

def inner_side(poly, p, d, size):
    left = poly.intersection(half_plane(p, d, 1, size)).area
    return 1 if left >= poly.area - left else -1

def find_edges(planes, polys, buffer, min_angle):
    # a pair of planes shares an edge when the intersection line is within the buffer of an
    # edge of both outlines and the outlines overlap along it
    edges = []
    cos_max = np.cos(np.radians(min_angle))
    for i in range(len(planes)):
        for j in range(i + 1, len(planes)):
            if polys[i] is None or polys[j] is None:
                continue
            if abs(planes[i].normal @ planes[j].normal) > cos_max:
                continue
            point, direction = intersection_line(planes[i], planes[j])
            lines = [line_in_plane(planes[k], point, direction) for k in (i, j)]
            if any(edge_distance(polys[k], *line) > buffer for k, line in zip((i, j), lines)):
                continue
            # point lies on both planes, so both spans are measured from the same 3D point
            ti, tj = (span(polys[k], *line) for k, line in zip((i, j), lines))
            lo, hi = max(ti[0], tj[0]), min(ti[1], tj[1])
            if hi - lo < -buffer:
                continue
            edges.append((i, j, point, direction, lo - buffer, hi + buffer))
    return edges

def corner_fill(poly, a, b, reach, size):
    # two edges of one outline meet at a corner. a scan rarely reaches into the corner, so the
    # outline is cut off there and the buffer alone does not reach the corner point
    (pa, da, sa), (pb, db, sb) = a, b
    det = da[0] * db[1] - da[1] * db[0]
    if abs(det) < 1e-9:
        return None
    t = ((pb[0] - pa[0]) * db[1] - (pb[1] - pa[1]) * db[0]) / det
    corner = pa + da * t
    near = poly.intersection(Point(corner).buffer(reach))
    if near.is_empty:
        return None
    # the hull of the nearby outline, its feet on both edge lines and the corner point
    xy = np.vstack([np.asarray(g.exterior.coords) for g in getattr(near, 'geoms', [near]) if g.geom_type == 'Polygon'])
    feet = [p + np.outer((xy - p) @ d, d) for p, d in ((pa, da), (pb, db))]
    hull = MultiPoint(np.vstack([xy, corner[None, :]] + feet)).convex_hull
    quadrant = half_plane(pa, da, sa, size).intersection(half_plane(pb, db, sb, size))
    return hull.intersection(quadrant)

def snap(planes, polys, edges, buffer, reach):
    out = list(polys)
    grow = [[] for _ in polys]
    cut = [[] for _ in polys]
    lines = [[] for _ in polys]
    for i, j, point, direction, lo, hi in edges:
        for k in (i, j):
            p, d = line_in_plane(planes[k], point, direction)
            seg = LineString([p + d * lo, p + d * hi])
            strip = seg.buffer(buffer, cap_style=2)
            size = 10.0 * (np.sqrt(polys[k].area) + seg.length + buffer) + np.linalg.norm(p)
            side = inner_side(polys[k], p, d, size)
            grow[k].append(polys[k].buffer(buffer, join_style=2).intersection(strip))
            # the edge test bounds the overshoot by the buffer, so trimming along the whole line is safe
            band = LineString([p - d * size, p + d * size]).buffer(buffer * 2, cap_style=2)
            cut[k].append(half_plane(p, d, -side, size).intersection(band))
            lines[k].append((p, d, side))
    for k, poly in enumerate(polys):
        if poly is None or not grow[k]:
            continue
        size = 10.0 * (np.sqrt(poly.area) + buffer) + max(np.linalg.norm(p) for p, _, _ in lines[k])
        for a, b in combinations(lines[k], 2):
            fill = corner_fill(poly, a, b, reach, size)
            if fill is not None and not fill.is_empty:
                grow[k].append(fill)
        shape = unary_union([poly] + grow[k]).difference(unary_union(cut[k]))
        if shape.geom_type == 'MultiPolygon':
            shape = max(shape.geoms, key=lambda g: g.area)
        if shape.geom_type == 'Polygon' and not shape.is_empty:
            out[k] = Polygon(shape.exterior).simplify(1e-6)
    return out

def plane_polygons(segments, buffer, min_angle=30.0, axis_snap_angle=10.0, alpha=0.0, tolerance=0.05, reach=1.0):
    # segments: list of point arrays. returns the planes and their outlines in plane coordinates
    planes = [fit_plane(s, axis_snap_angle) for s in segments]
    polys = [outline(p, s, alpha, tolerance) for p, s in zip(planes, segments)]
    edges = find_edges(planes, polys, buffer, min_angle)
    return planes, snap(planes, polys, edges, buffer, reach), edges

def ring_3d(plane, poly):
    return plane.to_3d(np.asarray(poly.exterior.coords)[:-1])

def triangulate(ring2d):
    # ear clipping of a simple polygon, counter clockwise
    pts = [tuple(p) for p in ring2d]
    idx = list(range(len(pts)))
    if Polygon(pts).exterior.is_ccw is False:
        idx.reverse()

    def cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    def inside(p, a, b, c):
        return cross(a, b, p) >= 0 and cross(b, c, p) >= 0 and cross(c, a, p) >= 0

    tris = []
    while len(idx) > 3:
        for n in range(len(idx)):
            i0, i1, i2 = idx[n - 1], idx[n], idx[(n + 1) % len(idx)]
            a, b, c = pts[i0], pts[i1], pts[i2]
            if cross(a, b, c) <= 1e-12:
                continue
            if any(inside(pts[m], a, b, c) for m in idx if m not in (i0, i1, i2)):
                continue
            tris.append((i0, i1, i2))
            idx.pop(n)
            break
        else:
            break   # degenerate rest, nothing left to clip
    if len(idx) == 3:
        tris.append(tuple(idx))
    return tris

def prism(plane, poly, thickness, outward):
    # solid of the outline pushed by thickness along outward, which is the plane normal or its negative
    ring2d = np.asarray(poly.exterior.coords)[:-1]
    if not Polygon(ring2d).exterior.is_ccw:
        ring2d = ring2d[::-1]
    base = plane.to_3d(ring2d)
    n = len(base)
    shift = plane.normal * thickness * (1 if outward @ plane.normal > 0 else -1)
    vertices = np.vstack([base, base + shift])
    tris = triangulate(ring2d)
    top_up = shift @ plane.normal > 0     # ccw in plane coordinates faces +normal
    faces = []
    for a, b, c in tris:
        faces.append((a, c, b) if top_up else (a, b, c))
        faces.append((a + n, b + n, c + n) if top_up else (a + n, c + n, b + n))
    for k in range(n):
        m = (k + 1) % n
        quad = [(k, m, m + n), (k, m + n, k + n)] if top_up else [(k, m + n, m), (k, k + n, m + n)]
        faces.extend(quad)
    return [tuple(float(c) for c in v) for v in vertices], [tuple(int(i) for i in f) for f in faces]
