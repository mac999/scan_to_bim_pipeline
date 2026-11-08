import os, sys, json, shutil, subprocess
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))

def has_module(name):
    try:
        __import__(name)
        return True
    except ImportError:
        return False

def has_program(name):
    return shutil.which(name) is not None

requires_open3d = pytest.mark.skipif(not has_module('open3d'), reason='open3d not installed')
requires_gdal = pytest.mark.skipif(not has_module('osgeo'), reason='gdal not installed')
requires_ifc = pytest.mark.skipif(not has_module('ifcopenshell'), reason='ifcopenshell not installed')
requires_pdal = pytest.mark.skipif(not has_program('pdal'), reason='pdal not installed')
requires_build = pytest.mark.skipif(not os.path.isfile(os.path.join(ROOT, 'bin', 'pcd_to_seg')), reason='C++ modules not built')

def run_module(module, *args, cwd=None):
    # run a stage the same way the pipeline does: as a separate process
    cmd = [sys.executable, os.path.join(ROOT, module)] + [str(a) for a in args]
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)

def write_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f)
    return str(path)
