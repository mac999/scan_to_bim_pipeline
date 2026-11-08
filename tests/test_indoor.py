import os, glob, json
import numpy as np
from conftest import run_module, requires_open3d, requires_ifc
from fixtures import plane_points, write_pcd

pytestmark = requires_open3d

INDOOR_ARGS = ['--wall_min_angle', 30.0, '--wall_max_angle', 150.0,
               '--wall_height', 3.0, '--floor_max_height', 0.5]

def write_segments(folder):
    # the segment naming used by pcd_to_seg: <tag>_@<index>.pcd
    os.makedirs(folder)
    write_pcd(folder / 'seg_to_geo_@0.pcd', plane_points([0, 0, 0], [5, 0, 0], [0, 4, 0]))           # floor
    write_pcd(folder / 'seg_to_geo_@1.pcd', plane_points([0, 0, 0], [5, 0, 0], [0, 0, 3], seed=1))   # wall
    write_pcd(folder / 'seg_to_geo_@2.pcd', plane_points([0, 0, 3], [5, 0, 0], [0, 4, 0], seed=2))   # ceiling

def test_geo_to_bim_indoor_labels_segments(tmp_path):
    write_segments(tmp_path / 'seg_to_geo')
    os.makedirs(tmp_path / 'geo_to_bim_indoor')
    ret = run_module('geo_to_bim_indoor/geo_to_bim_indoor.py',
                     '--input', str(tmp_path / 'seg_to_geo' / 'seg_to_geo'),
                     '--output', tmp_path / 'geo_to_bim_indoor' / 'geo_to_bim_indoor',
                     *INDOOR_ARGS, cwd=tmp_path)
    assert ret.returncode == 0, ret.stdout + ret.stderr

    out = str(tmp_path / 'geo_to_bim_indoor' / 'geo_to_bim_indoor')
    for index, label in [(0, 'floor'), (1, 'wall'), (2, 'ceiling')]:
        prefix = f'{out}_@{index}_{label}'
        assert os.path.isfile(prefix + '.json'), sorted(os.listdir(tmp_path / 'geo_to_bim_indoor'))
        assert os.path.isfile(prefix + '_plane_3d.ply')

def test_geo_to_bim_indoor_saves_hull_of_3d_segment(tmp_path):
    # a 3D point set gives a mesh hull. its outline used to be saved empty
    write_segments(tmp_path / 'seg_to_geo')
    os.makedirs(tmp_path / 'geo_to_bim_indoor')
    ret = run_module('geo_to_bim_indoor/geo_to_bim_indoor.py',
                     '--input', str(tmp_path / 'seg_to_geo' / 'seg_to_geo'),
                     '--output', tmp_path / 'geo_to_bim_indoor' / 'geo_to_bim_indoor',
                     *INDOOR_ARGS, cwd=tmp_path)
    assert ret.returncode == 0, ret.stdout + ret.stderr
    fnames = glob.glob(str(tmp_path / 'geo_to_bim_indoor' / '*_wall.json'))
    assert len(fnames) == 1
    for fname in fnames:
        with open(fname) as f:
            coords = json.load(f)['coordinates'][0][0]
        assert len(coords) >= 4

def test_pcd_to_clean_removes_isolated_points(tmp_path):
    import open3d as o3d
    pts = np.vstack([plane_points([0, 0, 0], [2, 0, 0], [0, 2, 0], nu=60, nv=60), [[10.0, 10.0, 10.0]]])
    write_pcd(tmp_path / 'seg_@0.pcd', pts)
    ret = run_module('pcd_to_clean/pcd_to_clean.py', '--input', tmp_path / 'seg', '--output', tmp_path / 'clean',
                     '--nb_radius_points', 5, '--nb_radius', 0.2, cwd=tmp_path)
    assert ret.returncode == 0, ret.stdout + ret.stderr
    cleaned = np.asarray(o3d.io.read_point_cloud(str(tmp_path / 'clean_@0.pcd')).points)
    assert cleaned.max() < 5.0

def test_pcd_to_clean_filters_can_be_disabled(tmp_path):
    import open3d as o3d
    pts = np.vstack([plane_points([0, 0, 0], [2, 0, 0], [0, 2, 0]), [[10.0, 10.0, 10.0]]])
    write_pcd(tmp_path / 'seg_@0.pcd', pts)
    ret = run_module('pcd_to_clean/pcd_to_clean.py', '--input', tmp_path / 'seg', '--output', tmp_path / 'clean',
                     '--stat_neighbors', 0, '--nb_radius_points', 0, cwd=tmp_path)
    assert ret.returncode == 0, ret.stdout + ret.stderr
    cleaned = np.asarray(o3d.io.read_point_cloud(str(tmp_path / 'clean_@0.pcd')).points)
    assert len(cleaned) == len(pts)

@requires_ifc
def test_geo_to_bim_indoor_writes_ifc_elements(tmp_path):
    import ifcopenshell
    write_segments(tmp_path / 'seg_to_geo')
    os.makedirs(tmp_path / 'geo_to_bim_indoor')
    ret = run_module('geo_to_bim_indoor/geo_to_bim_indoor.py',
                     '--input', str(tmp_path / 'seg_to_geo' / 'seg_to_geo'),
                     '--output', tmp_path / 'geo_to_bim_indoor' / 'geo_to_bim_indoor',
                     *INDOOR_ARGS, '--storey_name', 'level 1', cwd=tmp_path)
    assert ret.returncode == 0, ret.stdout + ret.stderr

    ifc = ifcopenshell.open(str(tmp_path / 'geo_to_bim_indoor' / 'geo_to_bim_indoor.ifc'))
    assert len(ifc.by_type('IfcWall')) == 1
    assert [s.PredefinedType for s in ifc.by_type('IfcSlab')] == ['FLOOR']
    assert [c.PredefinedType for c in ifc.by_type('IfcCovering')] == ['CEILING']
    assert ifc.by_type('IfcBuildingStorey')[0].Name == 'level 1'
    for e in ifc.by_type('IfcWall') + ifc.by_type('IfcSlab') + ifc.by_type('IfcCovering'):
        assert e.Representation is not None
        assert e.ContainedInStructure
