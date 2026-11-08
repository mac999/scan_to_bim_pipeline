import os, sys, json, subprocess
from conftest import ROOT, write_json

STAGE_CODE = '''import sys, argparse
parser = argparse.ArgumentParser()
parser.add_argument('--input')
parser.add_argument('--output')
args, extra = parser.parse_known_args()
with open(args.output + '_args.json', 'w') as f:
    f.write(repr(sys.argv[1:]))
sys.exit(EXIT_CODE)
'''

def make_stage(bin_dir, name, exit_code=0):
    os.makedirs(bin_dir / name)
    with open(bin_dir / name / (name + '.py'), 'w') as f:
        f.write(STAGE_CODE.replace('EXIT_CODE', str(exit_code)))

def run_app(tmp_path, stages, cwd=None, **app_config):
    bin_dir = tmp_path / 'bin_root'
    os.makedirs(bin_dir, exist_ok=True)
    config = write_json(tmp_path / 'config.json', dict({
        'app': 'pcd_pipeline',
        'root_path': str(tmp_path) + '/',
        'bin_path': str(bin_dir) + '/',
        'lib_path': ROOT + '/lib/',
        'data_path': str(tmp_path) + '/input/',
        'debug_gui': False}, **app_config))
    os.makedirs(tmp_path / 'input', exist_ok=True)
    (tmp_path / 'input' / 'sample.pcd').write_text('')
    write_json(tmp_path / 'input' / 'sample_scan_to_bim.json', {'pipeline.test': stages})
    cmd = [sys.executable, os.path.join(ROOT, 'pipeline', 'app.py'),
           '--config', config,
           '--input_path', str(tmp_path) + '/input/*.*',
           '--output_path', str(tmp_path) + '/output/']
    return subprocess.run(cmd, cwd=cwd or tmp_path, capture_output=True, text=True)

def stage_ran(tmp_path, name):
    return os.path.isfile(tmp_path / 'output' / 'sample' / name / (name + '_args.json'))

def test_stages_run_in_order_and_chain_output(tmp_path):
    make_stage(tmp_path / 'bin_root', 'first_stage')
    make_stage(tmp_path / 'bin_root', 'second_stage')
    ret = run_app(tmp_path, [{'type': 'first_stage', 'alpha': '0.15'}, {'type': 'second_stage'}])
    assert ret.returncode == 0, ret.stdout + ret.stderr
    assert stage_ran(tmp_path, 'first_stage')
    assert stage_ran(tmp_path, 'second_stage')

    first_args = (tmp_path / 'output' / 'sample' / 'first_stage' / 'first_stage_args.json').read_text()
    assert "'--alpha', '0.15'" in first_args
    second_args = (tmp_path / 'output' / 'sample' / 'second_stage' / 'second_stage_args.json').read_text()
    expected_input = str(tmp_path) + '/output/sample/first_stage/first_stage'
    assert repr(expected_input) in second_args

def test_failed_stage_stops_pipeline(tmp_path):
    make_stage(tmp_path / 'bin_root', 'first_stage', exit_code=2)
    make_stage(tmp_path / 'bin_root', 'second_stage')
    ret = run_app(tmp_path, [{'type': 'first_stage'}, {'type': 'second_stage'}])
    assert 'first_stage failed with exit code 2' in ret.stdout
    assert stage_ran(tmp_path, 'first_stage')
    assert not stage_ran(tmp_path, 'second_stage')

def test_missing_program_stops_pipeline(tmp_path):
    make_stage(tmp_path / 'bin_root', 'second_stage')
    ret = run_app(tmp_path, [{'type': 'unknown_stage'}, {'type': 'second_stage'}])
    assert 'unknown_stage: program not found' in ret.stdout
    assert not stage_ran(tmp_path, 'second_stage')

def test_inactive_stage_is_skipped(tmp_path):
    make_stage(tmp_path / 'bin_root', 'first_stage')
    make_stage(tmp_path / 'bin_root', 'second_stage')
    ret = run_app(tmp_path, [{'type': 'first_stage', 'active': False}, {'type': 'second_stage'}])
    assert ret.returncode == 0
    assert not stage_ran(tmp_path, 'first_stage')
    assert stage_ran(tmp_path, 'second_stage')

def test_active_flag_is_not_forwarded_to_module(tmp_path):
    make_stage(tmp_path / 'bin_root', 'first_stage')
    ret = run_app(tmp_path, [{'type': 'first_stage', 'active': True}])
    assert ret.returncode == 0
    first_args = (tmp_path / 'output' / 'sample' / 'first_stage' / 'first_stage_args.json').read_text()
    assert '--active' not in first_args

def test_app_runs_from_another_directory(tmp_path):
    make_stage(tmp_path / 'bin_root', 'first_stage')
    os.makedirs(tmp_path / 'elsewhere')
    ret = run_app(tmp_path, [{'type': 'first_stage'}], cwd=tmp_path / 'elsewhere')
    assert ret.returncode == 0
    assert stage_ran(tmp_path, 'first_stage')

def test_data_ext_from_config_selects_input_files(tmp_path):
    make_stage(tmp_path / 'bin_root', 'first_stage')
    ret = run_app(tmp_path, [{'type': 'first_stage'}], data_ext=['.las'])
    assert ret.returncode == 0
    assert not stage_ran(tmp_path, 'first_stage')

def test_pipeline_tag_from_config(tmp_path):
    make_stage(tmp_path / 'bin_root', 'first_stage')
    os.makedirs(tmp_path / 'input')
    write_json(tmp_path / 'input' / 'sample_custom.json', {'pipeline.test': [{'type': 'first_stage'}]})
    ret = run_app(tmp_path, [], pipeline_tag='custom.json')
    assert ret.returncode == 0
    assert stage_ran(tmp_path, 'first_stage')

def test_config_paths_resolve_from_repository_root(tmp_path):
    sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
    import config
    conf = config.config()
    conf.load(os.path.join(ROOT, 'pipeline', 'config.json'))
    assert conf.bin_path == ROOT + '/'
    assert conf.lib_path == ROOT + '/lib/'
    assert conf.root_path == ROOT + '/pipeline/'
