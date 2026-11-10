# Command line and configuration files

## pipeline/app.py

```
python ./pipeline/app.py [--input_path GLOB] [--stage REGEX] [--pipeline FILE] [--pipeline_tag SUFFIX] [--output_path DIR] [--config FILE]
```

| option | default | |
|---|---|---|
| `--input_path` | `./input/*.*` | glob of the input files. quote it so the shell does not expand it. only extensions in `data_ext` of config.json are processed |
| `--stage` | `.*` | regular expression; only pipelines whose name matches are run, e.g. `pipe_rule` for `pipeline.pipe_rule` |
| `--pipeline` | | SBDL file used for every input. without it each input uses `<input name>_<pipeline_tag>` next to it |
| `--pipeline_tag` | `pipeline_tag` of config.json (`scan_to_bim.json`) | suffix of the SBDL file looked up next to each input |
| `--output_path` | `./output/` | results go to `<output_path>/<input name>/<stage>/<stage>*` |
| `--config` | `./pipeline/config.json` | |

Examples:

```
python ./pipeline/app.py --input_path "./input/conference_room1/*.pcd" --stage indoor_rule
python ./pipeline/app.py --input_path "./input/kict_mep_zero_en_bdlg_parts/*.laz" --stage pipe_rule
python ./pipeline/app.py --input_path "./scans/*.laz" --pipeline ./my_pipe.json --output_path ./result/
```

Stages written in python are run with the same interpreter as app.py, so start app.py from the environment that has the packages installed.

## running one stage

Every stage is a program that can also be run by itself. The SBDL keys of a stage are its command line options.

```
python <stage>/<stage>.py --input <prefix> --output <prefix> [--<parameter> <value> ...]
bin/<stage> --input <prefix> --output <prefix> [--<parameter> <value> ...]       (C++ stages)
```

- `--input` is a file or a path prefix. A stage reads every file that starts with it and has the extension it expects, so the output prefix of one stage is the input of the next.
- `--output` is the prefix of the files the stage writes, for example `./output/mep/cyl` gives `./output/mep/cyl_cylinder.json`.
- Lists are written as JSON, `--tiles "[2, 2]"`, and booleans as `true` or `false`.
- `python <stage>/<stage>.py --help` lists the options; their defaults are in [sbdl.md](./sbdl.md).

```
python pcd_to_cylinder/pcd_to_cylinder.py --input ./output/mep/clean --output ./output/mep/cyl --tiles "[2, 2]" --tile_workers 4
```

## scripts

| script | |
|---|---|
| `build.sh`, `build.bat` | builds the C++ stages into `./bin`. `--install` installs requirements_simple.txt first |
| `run_samples.sh`, `run_samples.bat` | runs the indoor and pipe samples, or one of them with `indoor` or `pipe` |

The python interpreter is taken from the `PYTHON` environment variable, default `python`.

## configuration files

| file | what it sets | reference |
|---|---|---|
| `pipeline/config.json` | paths, input extensions, SBDL file suffix | [sbdl.md](./sbdl.md#pipelineconfigjson) |
| `<input name>_scan_to_bim.json` | the pipelines and the parameters of each stage (SBDL) | [sbdl.md](./sbdl.md) |
| `cylinder_to_pipe/pipe_standard.json` | nominal pipe sizes, elbow angles and bend radii | [pipe.md](./pipe.md#pipe-standard-file) |
| `geo_to_bim_pipe/pipe_mapping_rule.json` | IFC class, predefined type, name and properties of pipes and elbows, by rule | [pipe.md](./pipe.md#mapping-rule-file) |

The standard and rule files are stage parameters (`pipe_standard`, `mapping_rule`), so a pipeline can point to its own copy. Relative paths are taken from the working directory, then from the repository root.

A pipeline file with the parameters that are most often changed:

```
{
    "pipeline.pipe_rule": [
        {"type": "pcd_to_clean", "voxel_down_size": 0.01, "nb_radius_points": 10, "nb_radius": 0.03},
        {"type": "pcd_to_cylinder", "min_radius": 0.01, "max_radius": 0.3, "pipe_angles": [45, 90], "tiles": [2, 2], "tile_workers": 4},
        {"type": "cylinder_to_pipe", "pipe_standard": "cylinder_to_pipe/pipe_standard.json", "min_length_ratio": 1.5},
        {"type": "geo_to_bim_pipe", "mapping_rule": "geo_to_bim_pipe/pipe_mapping_rule.json"}
    ]
}
```

A mapping rule maps an element when all its conditions hold, and the first matching rule wins:

```
{
    "rules": [
        {"condition": [["kind", "==", "elbow"]], "type": "IfcPipeFitting", "predefined_type": "BEND", "name": "elbow {nominal}"},
        {"condition": [["kind", "==", "pipe"], ["orientation", "==", "vertical"]], "type": "IfcPipeSegment", "predefined_type": "RIGIDSEGMENT", "name": "riser {nominal}"},
        {"condition": [["kind", "==", "pipe"]], "type": "IfcPipeSegment", "predefined_type": "RIGIDSEGMENT", "name": "pipe {nominal}"}
    ]
}
```

pcd_to_cylinder and cylinder_to_pipe also write `<output>_log.json` with their parameters, counts and the cylinders and pipes they rejected, with the reason and the point files, see [pipe.md](./pipe.md#shape-rules).

`pcd_to_bbox/revit_family_types.json` and `seg_to_geo_ml/seg_to_geo_config.json` are kept as examples of a Revit family list and a segment color table. No stage reads them.
