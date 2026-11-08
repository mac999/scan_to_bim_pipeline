import os
import numpy as np
import pytest
from conftest import ROOT, run_module, requires_pdal, has_module

pytestmark = [requires_pdal, pytest.mark.skipif(not has_module('laspy'), reason='laspy not installed')]

def write_las(path):
    import laspy
    rng = np.random.default_rng(0)
    xy = rng.uniform(0, 20, (5000, 2))
    z = np.where((xy[:, 0] > 5) & (xy[:, 0] < 10) & (xy[:, 1] > 5) & (xy[:, 1] < 10), 20.0, 10.0)
    las = laspy.create(point_format=3, file_version='1.2')
    las.header.scales = [0.01, 0.01, 0.01]
    las.x, las.y, las.z = xy[:, 0], xy[:, 1], z
    las.write(str(path))
    return str(path)

def test_pcd_to_dtm_writes_raster_and_leaves_repository_alone(tmp_path):
    tracked = os.path.join(ROOT, 'pipeline', 'pcd_to_dtm_pipeline.json')
    before = open(tracked, 'rb').read()
    write_las(tmp_path / 'scan.las')
    ret = run_module('pcd_to_dtm/pcd_to_dtm.py', '--input', tmp_path / 'scan.las',
                     '--output', tmp_path / 'pcd_to_dtm', '--pdal_pipeline', tracked,
                     '--resolution', 0.5, '--classification', 'building', cwd=tmp_path)
    assert ret.returncode == 0, ret.stdout + ret.stderr
    assert os.path.isfile(tmp_path / 'pcd_to_dtm.tif')
    assert open(tracked, 'rb').read() == before
    assert not os.path.exists(tmp_path / 'pcd_to_dtm_transformed.las')

def test_pcd_to_dtm_fails_on_unreadable_input(tmp_path):
    (tmp_path / 'broken.las').write_bytes(b'not a las file')
    ret = run_module('pcd_to_dtm/pcd_to_dtm.py', '--input', tmp_path / 'broken.las',
                     '--output', tmp_path / 'pcd_to_dtm', '--classification', 'building', cwd=tmp_path)
    assert ret.returncode != 0

def test_data_to_format_converts_las_to_pcd(tmp_path):
    write_las(tmp_path / 'scan.las')
    ret = run_module('data_to_format/data_to_format.py', '--input', tmp_path / 'scan.las',
                     '--output', tmp_path / 'data_to_format', '--output_type', '.pcd', cwd=tmp_path)
    assert ret.returncode == 0, ret.stdout + ret.stderr
    assert os.path.isfile(tmp_path / 'data_to_format.pcd')
