import numpy as np

GROUND = 10.0
BUILDINGS = [  # (col0, row0, size in pixels, roof elevation)
    (40, 40, 40, 25.0),
    (120, 110, 50, 40.0),
]

def write_dsm(path, size=200, pixel=0.5, origin=(724840.0, 6181100.0), epsg=25832):
    # flat ground with box shaped buildings, north up
    from osgeo import gdal, osr
    z = np.full((size, size), GROUND, dtype=np.float32)
    for c, r, s, h in BUILDINGS:
        z[r:r + s, c:c + s] = h

    ds = gdal.GetDriverByName('GTiff').Create(str(path), size, size, 1, gdal.GDT_Float32)
    ds.SetGeoTransform((origin[0], pixel, 0.0, origin[1], 0.0, -pixel))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)
    ds.SetProjection(srs.ExportToWkt())
    ds.GetRasterBand(1).WriteArray(z)
    ds.FlushCache()
    ds = None
    return str(path)

def plane_points(origin, u, v, nu=40, nv=30, noise=0.002, seed=0):
    rng = np.random.default_rng(seed)
    a, b = np.meshgrid(np.linspace(0, 1, nu), np.linspace(0, 1, nv))
    pts = np.asarray(origin) + a.reshape(-1, 1) * np.asarray(u) + b.reshape(-1, 1) * np.asarray(v)
    return pts + rng.normal(0, noise, pts.shape)

def write_pcd(path, points):
    import open3d as o3d
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(np.asarray(points, dtype=np.float64))
    o3d.io.write_point_cloud(str(path), pcd)
    return str(path)

def cylinder_points(start, end, radius, spacing=0.01, arc=360.0, phase=0.0, noise=0.001, seed=0):
    # surface points of a cylinder, arc in degrees for a partly scanned pipe
    rng = np.random.default_rng(seed)
    start, end = np.asarray(start, float), np.asarray(end, float)
    axis = (end - start) / np.linalg.norm(end - start)
    ref = np.eye(3)[np.argmin(np.abs(axis))]
    u = np.cross(axis, ref)
    u /= np.linalg.norm(u)
    v = np.cross(axis, u)
    t = np.arange(0, np.linalg.norm(end - start), spacing)
    a = np.radians(phase) + np.arange(0, np.radians(arc), spacing / radius)
    t, a = np.meshgrid(t, a)
    radial = np.outer(np.cos(a).ravel(), u) + np.outer(np.sin(a).ravel(), v)
    pts = start + np.outer(t.ravel(), axis) + radius * radial
    return pts + rng.normal(0, noise, pts.shape)

def elbow_points(corner, d1, d2, radius, bend, spacing=0.01, noise=0.001, seed=0):
    # torus segment that turns from direction d1 into d2 at the corner
    rng = np.random.default_rng(seed)
    d1, d2 = np.asarray(d1, float), np.asarray(d2, float)
    theta = np.arccos(np.clip(d1 @ d2, -1, 1))
    start = np.asarray(corner, float) - d1 * bend * np.tan(theta / 2)
    inward = d2 - d1 * (d1 @ d2)
    inward /= np.linalg.norm(inward)
    center = start + inward * bend
    e1 = -inward
    normal = np.cross(e1, d1)
    pts = []
    for phi in np.arange(0, theta, spacing / bend):
        radial = np.cos(phi) * e1 + np.sin(phi) * d1
        ring = center + bend * radial
        for a in np.arange(0, 2 * np.pi, spacing / radius):
            pts.append(ring + radius * (np.cos(a) * radial + np.sin(a) * normal))
    pts = np.asarray(pts)
    return pts + rng.normal(0, noise, pts.shape)

def normals_of(points, radius=0.03):
    import open3d as o3d
    pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(points))
    pcd.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=radius, max_nn=40))
    return np.asarray(pcd.normals)
