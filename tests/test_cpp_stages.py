import os, glob, subprocess
import numpy as np
from conftest import ROOT, requires_build, requires_open3d
from fixtures import plane_points, write_pcd

pytestmark = [requires_build, requires_open3d]

def run_bin(name, *args):
    cmd = [os.path.join(ROOT, 'bin', name)] + [str(a) for a in args]
    return subprocess.run(cmd, capture_output=True, text=True)

def write_room(path):
    pts = np.vstack([
        plane_points([0, 0, 0], [5, 0, 0], [0, 4, 0], nu=60, nv=50),           # floor
        plane_points([0, 0, 0], [5, 0, 0], [0, 0, 3], nu=60, nv=40, seed=1),   # wall y=0
        plane_points([0, 0, 0], [0, 4, 0], [0, 0, 3], nu=50, nv=40, seed=2),   # wall x=0
    ])
    return write_pcd(path, pts)

def test_pcd_to_seg_finds_each_plane(tmp_path):
    write_room(tmp_path / 'room.pcd')
    ret = run_bin('pcd_to_seg', '--input', tmp_path / 'room.pcd', '--output', tmp_path / 'pcd_to_seg',
                  '--iteration', 1000, '--threshold', 0.05, '--projection', 'true', '--min_points_ratio', 0.05)
    assert ret.returncode == 0, ret.stdout + ret.stderr
    assert len(glob.glob(str(tmp_path / 'pcd_to_seg_@*.pcd'))) == 3

def test_pcd_to_seg_reports_unknown_option(tmp_path):
    write_room(tmp_path / 'room.pcd')
    ret = run_bin('pcd_to_seg', '--input', tmp_path / 'room.pcd', '--output', tmp_path / 'pcd_to_seg',
                  '--remove_overlap_distance', 0.1)
    assert 'unknown option ignored: --remove_overlap_distance' in ret.stdout

def test_pcd_to_seg_requires_input(tmp_path):
    ret = run_bin('pcd_to_seg', '--output', tmp_path / 'pcd_to_seg')
    assert ret.returncode != 0

def test_seg_to_geo_writes_hull_per_segment(tmp_path):
    write_room(tmp_path / 'room.pcd')
    run_bin('pcd_to_seg', '--input', tmp_path / 'room.pcd', '--output', tmp_path / 'pcd_to_seg',
            '--iteration', 1000, '--threshold', 0.05, '--min_points_ratio', 0.05)
    ret = run_bin('seg_to_geo', '--input', tmp_path / 'pcd_to_seg', '--output', tmp_path / 'seg_to_geo', '--alpha', 0.15)
    assert ret.returncode == 0, ret.stdout + ret.stderr
    assert len(glob.glob(str(tmp_path / 'seg_to_geo_@*.json'))) == 3
    assert len(glob.glob(str(tmp_path / 'seg_to_geo_@*.pcd'))) == 3

def test_pcd_density_writes_density_per_point(tmp_path):
    write_room(tmp_path / 'room.pcd')
    ret = run_bin('pcd_density', tmp_path / 'room.pcd', tmp_path / 'density.pcd', 8)
    assert ret.returncode == 0, ret.stdout + ret.stderr
    header = lambda f: open(f, 'rb').read(400).decode('ascii', 'ignore').splitlines()
    points = lambda f: [l for l in header(f) if l.startswith('POINTS')]
    assert any('intensity' in l for l in header(tmp_path / 'density.pcd') if l.startswith('FIELDS'))
    assert points(tmp_path / 'density.pcd') == points(tmp_path / 'room.pcd')
