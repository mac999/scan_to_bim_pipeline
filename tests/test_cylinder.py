import os, json
import numpy as np
import pytest
from conftest import run_module, requires_open3d, requires_ifc
from fixtures import cylinder_points, elbow_points, plane_points, normals_of, write_pcd

R = 0.0445    # 80A

def angle(a, b):
    return np.degrees(np.arccos(min(1.0, abs(np.dot(a, b)))))

@requires_open3d
def test_detects_a_half_scanned_pipe_next_to_a_wall():
    import cylinder
    pipe = cylinder_points([0, 0, 0.5], [1.5, 0.02, 0.5], R, arc=180, phase=0)
    wall = plane_points([0, 0.2, 0], [1.5, 0, 0], [0, 0, 1], nu=150, nv=100)
    points = np.vstack([pipe, wall])
    found, residual = cylinder.detect(points, normals_of(points), 0.01, 0.3, axis_snap_angle=0)
    assert len(found) == 1
    cyl = found[0]
    assert cyl.radius == pytest.approx(R, abs=0.002)
    assert angle(cyl.axis, [1.5, 0.02, 0]) < 1.0
    assert cyl.length == pytest.approx(1.5, abs=0.03)
    assert 0.4 < cyl.coverage < 0.6
    assert len(residual) >= len(wall) * 0.95

@requires_open3d
def test_axis_snap_and_gap_split():
    import cylinder
    points = np.vstack([cylinder_points([0, 0, 0], [0.01, 0, 1.0], R),
                        cylinder_points([0.01, 0, 1.3], [0.013, 0, 2.0], R, seed=1)])
    found, _ = cylinder.detect(points, normals_of(points), 0.01, 0.3, axis_snap_angle=5.0, max_gap=0.1)
    assert len(found) == 2
    for cyl in found:
        assert abs(cyl.axis[2]) == pytest.approx(1.0)

def l_shape():
    import pipe_network as pn
    # an x pipe and a z pipe that stop short of the corner at (1, 0, 0), the x pipe in two pieces
    return [pn.Pipe([0, 0, 0], [0.4, 0, 0], R, 500, 1.0, [0]),
            pn.Pipe([0.45, 0.001, 0], [0.8, 0.001, 0], R + 0.001, 500, 1.0, [1]),
            pn.Pipe([1, 0, 0.2], [1, 0, 1.0], R, 500, 1.0, [2])]

def test_merge_snap_and_elbow():
    import pipe_network as pn
    pipes = pn.merge(l_shape())
    assert len(pipes) == 2
    pipes = pn.snap_radius(pipes, [{'name': '65A', 'outer_diameter': 0.0763}, {'name': '80A', 'outer_diameter': 0.0891}], 0.005)
    assert [p.nominal for p in pipes] == ['80A', '80A']
    elbows = pn.make_elbows(pipes, bend_radii={'80A': 0.1143})
    assert len(elbows) == 1
    e = elbows[0]
    assert e['angle'] == pytest.approx(90, abs=0.5)
    assert e['bend_radius'] == pytest.approx(0.1143)
    # both pipes end at the tangent points, one bend radius from the corner
    ends = {tuple(np.round(p.end if np.linalg.norm(p.end - [1, 0, 0]) < 0.5 else p.start, 3)) for p in pipes}
    assert ends == {(round(1 - 0.1143, 3), 0.0, 0.0), (1.0, 0.0, round(0.1143, 3))}
    assert np.allclose(e['center'], [1 - 0.1143, 0, 0.1143], atol=1e-3)

def test_no_elbow_for_a_tee_or_an_odd_angle():
    import pipe_network as pn
    tee = [pn.Pipe([0, 0, 0], [2, 0, 0], R), pn.Pipe([1, 0, 0.1], [1, 0, 1], R)]
    assert pn.make_elbows(tee) == []
    odd = [pn.Pipe([0, 0, 0], [1, 0, 0], R), pn.Pipe([1.1, 0, 0.1], [1.6, 0, 0.6 * np.tan(np.radians(65))], R)]
    assert pn.make_elbows(odd, angles=[45, 90]) == []

def test_short_pipe_in_an_elbow_corner_is_dropped_but_an_offset_is_kept():
    import pipe_network as pn
    corner = [pn.Pipe([0, 0, 0], [0.8, 0, 0], R), pn.Pipe([1, 0, 0.2], [1, 0, 1], R),
              pn.Pipe([0.88, 0, 0.02], [0.98, 0, 0.12], R)]
    assert len(pn.drop_elbow_pieces(corner)) == 2
    offset = [pn.Pipe([0, 0, 0], [0.8, 0, 0], R), pn.Pipe([1.2, 0, 0.4], [2, 0, 0.4], R),
              pn.Pipe([0.85, 0, 0.05], [1.15, 0, 0.35], R)]
    assert len(pn.drop_elbow_pieces(offset)) == 3
    assert len(pn.make_elbows(offset, bend_ratio=1.0)) == 2

def test_mapping_rule():
    import importlib.util
    spec = importlib.util.spec_from_file_location('geo_to_bim_pipe', os.path.join(os.path.dirname(__file__), '..', 'geo_to_bim_pipe', 'geo_to_bim_pipe.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rules = [{'condition': [['kind', '==', 'elbow'], ['radius', '>', 0.1]], 'type': 'big'},
             {'condition': [['nominal', 'in', ['80A', '100A']], ['orientation', '==', 'vertical']], 'logic': 'or', 'type': 'listed'}]
    assert module.match(rules, {'kind': 'elbow', 'radius': 0.2})['type'] == 'big'
    assert module.match(rules, {'kind': 'elbow', 'radius': 0.05, 'nominal': '80A'})['type'] == 'listed'
    assert module.match(rules, {'kind': 'pipe', 'radius': 0.05, 'nominal': '', 'orientation': 'horizontal'}) is None

@requires_open3d
@requires_ifc
def test_pipe_stages_make_segments_and_a_bend(tmp_path):
    import ifcopenshell, ifcopenshell.geom
    points = np.vstack([cylinder_points([0, 0, 0], [0.8, 0, 0], R),
                        elbow_points([1, 0, 0], [1, 0, 0], [0, 0, 1], R, 0.2 - 0.0)[::1],
                        cylinder_points([1, 0, 0.2], [1, 0, 1.0], R, seed=1),
                        plane_points([-0.2, -0.3, -0.2], [1.6, 0, 0], [0, 0.6, 0], nu=160, nv=60)])
    for name in ('pcd_to_cylinder', 'cylinder_to_pipe', 'geo_to_bim_pipe'):
        os.makedirs(tmp_path / name)
    write_pcd(tmp_path / 'input.pcd', points)

    stages = [('pcd_to_cylinder', str(tmp_path / 'input.pcd'), []),
              ('cylinder_to_pipe', str(tmp_path / 'pcd_to_cylinder' / 'pcd_to_cylinder'), []),
              ('geo_to_bim_pipe', str(tmp_path / 'cylinder_to_pipe' / 'cylinder_to_pipe'), [])]
    for name, source, extra in stages:
        ret = run_module(f'{name}/{name}.py', '--input', source, '--output', tmp_path / name / name, *extra, cwd=tmp_path)
        assert ret.returncode == 0, ret.stdout + ret.stderr

    with open(tmp_path / 'cylinder_to_pipe' / 'cylinder_to_pipe_pipe.json') as f:
        network = json.load(f)
    assert len(network['pipes']) == 2 and len(network['elbows']) == 1
    assert {p['nominal'] for p in network['pipes']} == {'80A'}
    assert os.path.isfile(tmp_path / 'pcd_to_cylinder' / 'pcd_to_cylinder_residual.pcd')

    ifc = ifcopenshell.open(str(tmp_path / 'geo_to_bim_pipe' / 'geo_to_bim_pipe.ifc'))
    assert len(ifc.by_type('IfcPipeSegment')) == 2
    fittings = ifc.by_type('IfcPipeFitting')
    assert len(fittings) == 1 and fittings[0].PredefinedType == 'BEND'
    # the bend is a quarter torus
    shape = ifcopenshell.geom.create_shape(ifcopenshell.geom.settings(), fittings[0])
    verts = np.array(shape.geometry.verts).reshape(-1, 3)
    e = network['elbows'][0]
    assert np.ptp(verts[:, 0]) == pytest.approx(e['bend_radius'] + R, abs=0.01)
    assert np.ptp(verts[:, 2]) == pytest.approx(e['bend_radius'] + R, abs=0.01)

@requires_open3d
def test_pcd_to_clean_reads_las(tmp_path):
    import laspy, open3d as o3d
    points = cylinder_points([0, 0, 0], [1, 0, 0], R)
    las = laspy.LasData(laspy.LasHeader(point_format=2, version='1.2'))
    las.header.scales = [0.001] * 3
    las.x, las.y, las.z = points.T
    las.red = las.green = las.blue = np.full(len(points), 65280, np.uint16)
    las.write(str(tmp_path / 'scan.las'))
    os.makedirs(tmp_path / 'pcd_to_clean')
    ret = run_module('pcd_to_clean/pcd_to_clean.py', '--input', tmp_path / 'scan.las',
                     '--output', tmp_path / 'pcd_to_clean' / 'pcd_to_clean', '--nb_radius_points', 0, '--stat_neighbors', 0)
    assert ret.returncode == 0, ret.stdout + ret.stderr
    pcd = o3d.io.read_point_cloud(str(tmp_path / 'pcd_to_clean' / 'pcd_to_clean.pcd'))
    assert len(pcd.points) == len(points) and pcd.has_colors()
