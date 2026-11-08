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
