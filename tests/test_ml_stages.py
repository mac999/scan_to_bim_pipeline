import os, sys, json
import numpy as np
import pytest
from conftest import ROOT, has_module, requires_open3d, run_module, write_json

pytestmark = [requires_open3d, pytest.mark.skipif(not has_module('laspy'), reason='laspy not installed')]

sys.path.insert(0, os.path.join(ROOT, 'pcd_to_seg_ml'))

def stage():
    import pcd_to_seg_ml
    return pcd_to_seg_ml

def by_height(points, feat):
    # stands in for the network: floor below 0.5 m, ceiling above 2.5 m, wall between
    return np.where(points[:, 2] < 0.5, 1, np.where(points[:, 2] > 2.5, 0, 2))

def room_points(n=2000, seed=0):
    rng = np.random.default_rng(seed)
    return rng.uniform([0, 0, 0], [4, 3, 3], (n, 3)), rng.uniform(0, 1, (n, 3))

def write_colored_pcd(path, points, colors):
    import open3d as o3d
    pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(points))
    pcd.colors = o3d.utility.Vector3dVector(colors)
    o3d.io.write_point_cloud(str(path), pcd)
    return str(path)

def write_las(path, points, colors, intensity):
    import laspy
    header = laspy.LasHeader(point_format=3, version='1.2')
    header.offsets = points.min(axis=0)
    header.scales = [0.001, 0.001, 0.001]
    las = laspy.LasData(header)
    las.x, las.y, las.z = points[:, 0], points[:, 1], points[:, 2]
    rgb = (colors * 65535).astype(np.uint16)
    las.red, las.green, las.blue = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    las.intensity = intensity
    las.write(str(path))
    return str(path)

def test_labels_go_to_classification_and_class_color(tmp_path):
    import laspy
    m = stage()
    model = m.load_model_file('model_randlanet_s3dis.json')
    points, colors = room_points()
    infile = write_colored_pcd(tmp_path / 'room.pcd', points, colors)
    results = m.segment_files([infile], str(tmp_path / 'seg'), model, by_height)

    las = laspy.read(str(tmp_path / 'seg.las'))
    expected = by_height(points, None)
    assert len(las.points) == len(points)
    assert np.allclose(np.c_[las.x, las.y, las.z], points, atol=0.001)
    assert (np.asarray(las.classification) == expected).all()
    wall = expected == 2
    assert (np.asarray(las.red)[wall] == 179 * 257).all()
    assert results[0]['classes']['wall'] == wall.sum()
    assert results[0]['classes']['sofa'] == 0

def test_las_input_keeps_its_dimensions_and_colors(tmp_path):
    import laspy
    m = stage()
    model = m.load_model_file('model_randlanet_s3dis.json')
    points, colors = room_points()
    intensity = np.arange(len(points), dtype=np.uint16)
    infile = write_las(tmp_path / 'room.las', points, colors, intensity)
    m.segment_files([infile], str(tmp_path / 'seg'), model, by_height, output_format='laz', color='original')

    las = laspy.read(str(tmp_path / 'seg.laz'))
    assert (np.asarray(las.intensity) == intensity).all()
    assert (np.asarray(las.red) == (colors[:, 0] * 65535).astype(np.uint16)).all()
    assert (np.asarray(las.classification) == by_height(points, None)).all()

def test_rgb_model_rejects_a_cloud_without_colors(tmp_path):
    import open3d as o3d
    m = stage()
    pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(room_points()[0]))
    with pytest.raises(ValueError):
        m.get_features(pcd, 'rgb')
    points, feat = m.get_features(pcd, 'normal')
    assert feat.shape == points.shape

def test_model_file_is_checked(tmp_path):
    m = stage()
    good = m.load_model_file('model_randlanet_s3dis.json')
    assert len(good['classes']) == 13
    assert os.path.isfile(m.resolve(good['model_config']))
    for change in ({'framework': 'tensorflow'}, {'feature': 'intensity'},
                   {'classes': [{'name': str(i), 'color': [0, 0, 0]} for i in range(33)]}):
        bad = write_json(tmp_path / 'bad.json', dict(good, **change))
        with pytest.raises(ValueError):
            m.load_model_file(bad)

def test_failed_download_leaves_no_checkpoint(tmp_path):
    m = stage()
    ckpt = tmp_path / 'logs' / 'model.pth'
    with pytest.raises(Exception):
        m.download((tmp_path / 'missing.pth').as_uri(), str(ckpt))
    assert not os.path.exists(ckpt)

def test_missing_input_fails(tmp_path):
    ret = run_module('pcd_to_seg_ml/pcd_to_seg_ml.py', '--input', tmp_path / 'none', '--output', tmp_path / 'seg')
    assert ret.returncode == 1
    assert 'no point cloud file' in ret.stdout
