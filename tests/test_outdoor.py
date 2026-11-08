import os, csv
import pytest
from conftest import run_module, requires_gdal, requires_ifc, requires_open3d
from fixtures import write_dsm, GROUND, BUILDINGS

pytestmark = [requires_gdal, requires_open3d]

DTM_TO_GEO_ARGS = ['--simplify_factor', 1.0, '--remove_area', 20.0,
                   '--extract_pixel_min_value', 60, '--extract_pixel_max_value', 255,
                   '--height_building_offset', 3.0, '--height_ground_offset', 3.0,
                   '--max_building_height', 100.0, '--output_dataset', 'dimension.csv']

def run_dtm_to_geo(tmp_path, *extra):
    os.makedirs(tmp_path / 'pcd_to_dtm')
    os.makedirs(tmp_path / 'dtm_to_geo')
    write_dsm(tmp_path / 'pcd_to_dtm' / 'pcd_to_dtm.tif')
    ret = run_module('dtm_to_geo/dtm_to_geo.py',
                     '--input', tmp_path / 'pcd_to_dtm' / 'pcd_to_dtm',
                     '--output', tmp_path / 'dtm_to_geo' / 'dtm_to_geo',
                     *(DTM_TO_GEO_ARGS + list(extra)), cwd=tmp_path)
    assert ret.returncode == 0, ret.stdout + ret.stderr
    with open(tmp_path / 'dtm_to_geo' / 'dtm_to_geo_dimension.csv') as f:
        return list(csv.DictReader(f))

def test_dtm_to_geo_extracts_every_building(tmp_path):
    rows = run_dtm_to_geo(tmp_path)
    assert len(rows) == len(BUILDINGS)
    for ext in ['.shp', '.geojson', '.ply', '_transform.json', '_projection.txt']:
        assert os.path.isfile(str(tmp_path / 'dtm_to_geo' / 'dtm_to_geo') + ext)

def test_dtm_to_geo_building_height_and_area(tmp_path):
    rows = sorted(run_dtm_to_geo(tmp_path), key=lambda r: float(r['area']))
    for row, (c, r, s, h) in zip(rows, sorted(BUILDINGS, key=lambda b: b[2])):
        assert float(row['elevation']) == pytest.approx(h - GROUND, abs=0.01)
        assert float(row['area']) == pytest.approx((s * 0.5) ** 2, rel=0.1)

def test_dtm_to_geo_accepts_old_ground_offset_name(tmp_path):
    rows = run_dtm_to_geo(tmp_path, '--height_ground_offest', 3.0)
    assert len(rows) == len(BUILDINGS)

@requires_ifc
def test_geo_to_bim_outdoor_writes_one_solid_per_building(tmp_path):
    import ifcopenshell
    rows = run_dtm_to_geo(tmp_path)
    os.makedirs(tmp_path / 'geo_to_bim_outdoor')
    ret = run_module('geo_to_bim_outdoor/geo_to_bim_outdoor.py',
                     '--input', tmp_path / 'dtm_to_geo' / 'dtm_to_geo',
                     '--output', tmp_path / 'geo_to_bim_outdoor' / 'geo_to_bim_outdoor',
                     '--base_point', '[724840.0, 6181000.0]', cwd=tmp_path)
    assert ret.returncode == 0, ret.stdout + ret.stderr

    ifc = ifcopenshell.open(str(tmp_path / 'geo_to_bim_outdoor' / 'geo_to_bim_outdoor.ifc'))
    elements = ifc.by_type('IfcBuildingElementProxy')
    assert len(elements) == len(rows)
    depths = sorted(s.Depth for s in ifc.by_type('IfcExtrudedAreaSolid'))
    assert depths == pytest.approx(sorted(float(r['elevation']) for r in rows))
    for e in elements:
        assert e.ContainedInStructure, 'element is not placed in a storey'

def run_geo_to_bim(tmp_path, *extra):
    import ifcopenshell
    rows = run_dtm_to_geo(tmp_path)
    os.makedirs(tmp_path / 'geo_to_bim_outdoor')
    ret = run_module('geo_to_bim_outdoor/geo_to_bim_outdoor.py',
                     '--input', tmp_path / 'dtm_to_geo' / 'dtm_to_geo',
                     '--output', tmp_path / 'geo_to_bim_outdoor' / 'geo_to_bim_outdoor', *extra, cwd=tmp_path)
    assert ret.returncode == 0, ret.stdout + ret.stderr
    return rows, ifcopenshell.open(str(tmp_path / 'geo_to_bim_outdoor' / 'geo_to_bim_outdoor.ifc'))

@requires_ifc
def test_geo_to_bim_outdoor_places_buildings_on_the_ground(tmp_path):
    import ifcopenshell.util.placement
    rows, ifc = run_geo_to_bim(tmp_path)
    for e in ifc.by_type('IfcBuildingElementProxy'):
        matrix = ifcopenshell.util.placement.get_local_placement(e.ObjectPlacement)
        assert matrix[2][3] == pytest.approx(GROUND)

@requires_ifc
def test_geo_to_bim_outdoor_writes_map_conversion(tmp_path):
    rows, ifc = run_geo_to_bim(tmp_path)
    conversion = ifc.by_type('IfcMapConversion')[0]
    assert conversion.TargetCRS.Name == 'EPSG:25832'
    # default base point is the lower left corner of the footprints
    assert conversion.Eastings == pytest.approx(724840.0 + BUILDINGS[0][0] * 0.5, abs=1.0)

@requires_ifc
def test_geo_to_bim_outdoor_keeps_explicit_base_point_and_names(tmp_path):
    rows, ifc = run_geo_to_bim(tmp_path, '--base_point', '[724840.0, 6181000.0]', '--project_name', 'punktsky', '--site_name', 'block A')
    conversion = ifc.by_type('IfcMapConversion')[0]
    assert (conversion.Eastings, conversion.Northings) == (724840.0, 6181000.0)
    assert ifc.by_type('IfcProject')[0].Name == 'punktsky'
    assert ifc.by_type('IfcSite')[0].Name == 'block A'

@requires_ifc
def test_geo_to_bim_outdoor_properties_come_from_the_scan(tmp_path):
    import ifcopenshell.util.element
    rows, ifc = run_geo_to_bim(tmp_path)
    for e in ifc.by_type('IfcBuildingElementProxy'):
        psets = ifcopenshell.util.element.get_psets(e)
        assert 'Pset_WallCommon' not in psets
        assert psets['ScanToBIM']['GroundElevation'] == pytest.approx(GROUND)
        assert psets['ScanToBIM']['Height'] > 0

def test_geo_to_bim_outdoor_fails_on_missing_input(tmp_path):
    ret = run_module('geo_to_bim_outdoor/geo_to_bim_outdoor.py',
                     '--input', tmp_path / 'missing', '--output', tmp_path / 'out', cwd=tmp_path)
    assert ret.returncode != 0
