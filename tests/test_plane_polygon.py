import os, glob, json
import numpy as np
import pytest
from conftest import run_module, requires_open3d, requires_ifc, has_module
from fixtures import plane_points, write_pcd

pytestmark = pytest.mark.skipif(not has_module('shapely'), reason='shapely not installed')

def room(gap=0.1):
    # floor, two walls and a ceiling of a 5 x 4 x 3 room. each scan stops short of the corners
    g = gap
    return [
        plane_points([g, g, 0], [5 - 2 * g, 0, 0], [0, 4 - 2 * g, 0]),                  # floor
        plane_points([g, 0, g], [5 - 2 * g, 0, 0], [0, 0, 3 - 2 * g], seed=1),         # wall y=0
        plane_points([0, g, g], [0, 4 - 2 * g, 0], [0, 0, 3 - 2 * g], seed=2),         # wall x=0
        plane_points([g, g, 3], [5 - 2 * g, 0, 0], [0, 4 - 2 * g, 0], seed=3),          # ceiling
    ]

def vertices(planes, polys):
    import plane_polygon
    return [plane_polygon.ring_3d(p, q) for p, q in zip(planes, polys)]

def has_vertex(ring, point, tol=1e-6):
    return np.min(np.linalg.norm(ring - point, axis=1)) < tol

def test_neighbouring_planes_meet_at_shared_corners():
    import plane_polygon
    planes, polys, edges = plane_polygon.plane_polygons(room(), buffer=0.3)
    assert sorted((i, j) for i, j, *_ in edges) == [(0, 1), (0, 2), (1, 2), (1, 3), (2, 3)]
    rings = vertices(planes, polys)
    for corner, members in [([0, 0, 0], (0, 1, 2)), ([0, 0, 3], (1, 2, 3))]:
        for k in members:
            assert has_vertex(rings[k], np.array(corner, float), tol=0.01), (corner, k, rings[k])

def test_gap_wider_than_buffer_is_left_open():
    import plane_polygon
    planes, polys, edges = plane_polygon.plane_polygons(room(gap=0.5), buffer=0.3)
    assert edges == []
    assert np.min(vertices(planes, polys)[0][:, 0]) > 0.4

def test_plane_through_the_middle_is_not_an_edge():
    # a table top crosses the wall halfway up. the wall must not be cut there
    import plane_polygon
    segments = room()[1:2] + [plane_points([0.1, 0.1, 1.0], [2, 0, 0], [0, 2, 0], seed=4)]
    planes, polys, edges = plane_polygon.plane_polygons(segments, buffer=0.3)
    assert edges == []

def test_prism_is_closed_and_faces_outward():
    import plane_polygon, trimesh
    planes, polys, _ = plane_polygon.plane_polygons(room(), buffer=0.3)
    center = np.array([2.5, 2.0, 1.5])
    for plane, poly in zip(planes, polys):
        vertices, faces = plane_polygon.prism(plane, poly, 0.2, plane.origin - center)
        mesh = trimesh.Trimesh(vertices, faces, process=False)
        assert mesh.is_watertight
        assert mesh.volume == pytest.approx(poly.area * 0.2, rel=1e-6)

INDOOR_ARGS = ['--wall_min_angle', 30.0, '--wall_max_angle', 150.0,
               '--wall_height', 3.0, '--floor_max_height', 0.5]

@requires_open3d
@requires_ifc
def test_geo_to_bim_indoor_writes_snapped_polygons(tmp_path):
    import ifcopenshell
    os.makedirs(tmp_path / 'seg_to_geo')
    os.makedirs(tmp_path / 'geo_to_bim_indoor')
    for index, points in enumerate(room()):
        write_pcd(tmp_path / 'seg_to_geo' / f'seg_to_geo_@{index}.pcd', points)
    ret = run_module('geo_to_bim_indoor/geo_to_bim_indoor.py',
                     '--input', str(tmp_path / 'seg_to_geo' / 'seg_to_geo'),
                     '--output', tmp_path / 'geo_to_bim_indoor' / 'geo_to_bim_indoor',
                     *INDOOR_ARGS, '--corner_buffer', 0.3, cwd=tmp_path)
    assert ret.returncode == 0, ret.stdout + ret.stderr
    assert '5 shared edges' in ret.stdout

    out = tmp_path / 'geo_to_bim_indoor'
    fnames = glob.glob(str(out / '*_polygon.json'))
    assert len(fnames) == 4
    for fname in fnames:
        with open(fname) as f:
            ring = json.load(f)['coordinates'][0]
        assert ring[0] == ring[-1] and len(ring[0]) == 3
    assert os.path.isfile(out / 'geo_to_bim_indoor_polygon.ply')

    ifc = ifcopenshell.open(str(out / 'geo_to_bim_indoor.ifc'))
    assert len(ifc.by_type('IfcWall')) == 2
