# Pipe stages

The pipe stages turn a scan of MEP piping into IFC pipe segments and elbows. They follow the rule-based plumbing pipeline of Kang et al. 2020 (Applied Sciences 10(21), 7422): cylinders are found with RANSAC, joined into straight pipes and elbows, and mapped to IFC classes by rules.

```
pipeline.pipe_rule = pcd_to_clean > pcd_to_cylinder > cylinder_to_pipe > geo_to_bim_pipe
pipeline.pipe_rule(*.laz | *.las | *.pcd) > *.ifc
```

| stage | input | output |
|---|---|---|
| pcd_to_clean | LAS, LAZ, PCD, PLY | `pcd_to_clean.pcd`, down sampled and without outliers |
| pcd_to_cylinder | point cloud | `_@<n>.pcd` per cylinder, `_residual.pcd`, `_cylinder.json` |
| cylinder_to_pipe | `_cylinder.json` | `_pipe.json` (pipes and elbows), `_pipe.ply` (mesh for checking) |
| geo_to_bim_pipe | `_pipe.json` | `.ifc` with IfcPipeSegment and IfcPipeFitting |

Coordinates are taken as meters. Scans in millimeters or feet have to be scaled first, or every length parameter below changed to that unit.

## sample

`input/kict_mep_zero_en_bdlg_parts/kict_mep_zero_en_bdlg_parts.laz` is part of the mechanical room of the KICT zero energy building: a pipe rack, risers, elbows, pumps, an expansion tank and a control panel. 2,016,241 points, about 4.4 x 4.0 x 2.7 m, 2 mm point spacing. Its pipeline is `kict_mep_zero_en_bdlg_parts_scan_to_bim.json` in the same folder.

## command line

Run the whole pipeline from the repository root:

```
python ./pipeline/app.py --input_path "./input/kict_mep_zero_en_bdlg_parts/*.laz" --stage pipe_rule
```

`--input_path` is a glob of the input files. For each file `app.py` reads `<name>_scan_to_bim.json` next to it, or the file given with `--pipeline`. `--stage pipe_rule` runs only the pipelines whose name matches. Results go to `output/<name>/<stage>/`.

Each stage is also a program of its own. `--input` is a path prefix; the stage reads every file that starts with it. `--output` is the prefix of the files it writes. Parameters not given keep their defaults (see [sbdl.md](./sbdl.md)).

```
python pcd_to_clean/pcd_to_clean.py --input ./input/kict_mep_zero_en_bdlg_parts/kict_mep_zero_en_bdlg_parts.laz --output ./output/mep/clean --voxel_down_size 0.01 --stat_neighbors 20 --stat_std_ratio 2.0 --nb_radius_points 10 --nb_radius 0.03
python pcd_to_cylinder/pcd_to_cylinder.py --input ./output/mep/clean --output ./output/mep/cyl --min_radius 0.01 --max_radius 0.3
python cylinder_to_pipe/cylinder_to_pipe.py --input ./output/mep/cyl --output ./output/mep/net --pipe_standard cylinder_to_pipe/pipe_standard.json
python geo_to_bim_pipe/geo_to_bim_pipe.py --input ./output/mep/net --output ./output/mep/mep --mapping_rule geo_to_bim_pipe/pipe_mapping_rule.json
```

The messages of a run on the sample (the per cylinder lines shortened):

```
263967 points
cylinder 0: r=0.098 length=1.65 points=9556 coverage=0.89
cylinder 1: r=0.022 length=0.80 points=287 coverage=0.28
...
106 cylinders, 132222 points left, 51.4 s
106 cylinders merged into 78 pipes, 8 elbows, 64 pipes with a nominal size
86 elements saved to .../geo_to_bim_pipe/geo_to_bim_pipe.ifc: {'IfcPipeSegment': 78, 'IfcPipeFitting': 8}
```

## results on the sample

The whole run takes about one minute on a 20 core ARM machine, most of it in pcd_to_cylinder.

<p align="center">
<img width="360" src="./pipe_scan.png"/><img width="360" src="./pipe_cylinders.png"/></br>
<img width="360" src="./pipe_residual.png"/><img width="360" src="./pipe_bim.png"/></br>
<img width="360" src="./pipe_ifc.png"/>
</p>

1. pcd_to_clean. A 1 cm voxel grid and the outlier filters leave 263,967 points.
2. pcd_to_cylinder. 106 cylinders, one color each. Pipes of the rack that are scanned from one side only are found, because a cylinder needs an unbroken arc of a quarter of the circle, not the full circle.
3. The residual. 132,222 points are not on any cylinder: pumps, valves, flanges, the panel, cable trays and the elbows, whose bends are not cylinders. The flat trays above the rack stay here as they should.
4. cylinder_to_pipe. 106 cylinders are merged into 78 straight pipes (blue), and 8 elbows (red) are made where two pipe ends meet at 90 degrees. 64 pipes got a nominal size, most of them 80A, 90A and 175A. Each elbow is tangent to both pipes with no gap.
5. geo_to_bim_pipe. The IFC file opened again with ifcopenshell: 78 IfcPipeSegment (pipes blue, risers green) and 8 IfcPipeFitting BEND (red). All 86 shapes are valid solids.

What it does not do yet:

- The cylindrical bodies of pumps and the expansion tank come out as short, thick pipes. A rule on `length` and `diameter` can map them to another class or leave them out.
- Where pipes turn twice in a short distance the pieces between the turns are too short to find, so those elbows are missing.
- The measured diameter of an insulated pipe is the insulation, so its nominal size is that of a larger pipe. Use the nominal sizes as a guide.
- Tees, reducers, valves and flanges are not modeled. Their points are in the residual.

## options

All stage parameters are listed in [sbdl.md](./sbdl.md). These are the ones to look at first for a new scan.

| parameter | stage | when to change it |
|---|---|---|
| `voxel_down_size` | pcd_to_clean | 0.005 to 0.01 for pipes. a coarser grid loses the small pipes |
| `normal_radius` | pcd_to_cylinder | a few times the point spacing, and below twice the smallest pipe radius. too large bends the normals of small pipes |
| `min_radius`, `max_radius` | pcd_to_cylinder | the range of pipe radii in the scan. a larger `max_radius` picks up tanks and pump bodies |
| `distance_tolerance` | pcd_to_cylinder | about the scan noise. raise it for SLAM or photogrammetry |
| `min_coverage` | pcd_to_cylinder | lower it for pipes seen from one side only, raise it when false cylinders appear between pipes lying side by side |
| `min_points`, `min_length` | pcd_to_cylinder | lower them to keep short pieces such as the pipe between two elbows |
| `axis_snap_angle` | pcd_to_cylinder | 0 for sloped pipes such as drains |
| `merge_gap` | cylinder_to_pipe | the largest gap along a pipe, such as a valve or a hanger that hides the pipe |
| `pipe_standard` | cylinder_to_pipe | another file for another standard. empty keeps the measured radii |
| `nominal_tolerance` | cylinder_to_pipe | how far a measured radius may be from a nominal size |
| `elbow_reach` | cylinder_to_pipe | how far a pipe end may stop short of the corner. raise it when the bend is long or poorly scanned |
| `mapping_rule` | geo_to_bim_pipe | another rule file for other IFC classes, names or properties |

The SBDL file of the sample sets them like this:

```
{
    "type": "pcd_to_cylinder",
    "normal_radius": 0.03,
    "min_radius": 0.01,
    "max_radius": 0.3,
    "distance_tolerance": 0.005,
    "min_coverage": 0.25,
    "axis_snap_angle": 5.0
}
```

## pipe standard file

[cylinder_to_pipe/pipe_standard.json](../cylinder_to_pipe/pipe_standard.json) holds the sizes of KS D 3507 (15A to 300A) and the long radius bends of KS B 1522. For another standard copy the file, change the sizes and give the copy as `pipe_standard`.

```
{
    "name": "KS D 3507 carbon steel pipe for ordinary piping, KS B 1522 butt welding elbows",
    "sizes": [
        {"name": "80A", "outer_diameter": 0.0891, "bend_radius": 0.1143},
        {"name": "100A", "outer_diameter": 0.1143, "bend_radius": 0.1524}
    ],
    "elbow": {"angles": [45, 90], "bend_ratio": 1.5, "min_bend_ratio": 1.0}
}
```

A measured radius is snapped to the nearest `outer_diameter` / 2 within `nominal_tolerance`. The elbow of a size uses its `bend_radius`, or `bend_ratio` x outer diameter when the size has none. Only pipe pairs at one of `angles` get an elbow. When the straight pipes are too short for the full bend radius, the bend is made tighter, down to `min_bend_ratio` x outer diameter; below that the elbow is left out.

## mapping rule file

[geo_to_bim_pipe/pipe_mapping_rule.json](../geo_to_bim_pipe/pipe_mapping_rule.json) decides the IFC class, predefined type, name and properties of each element. The first rule whose conditions hold is used, and an element that matches no rule is not written. For example, to keep short thick cylinders out of the pipes, put this rule first:

```
{
    "condition": [["kind", "==", "pipe"], ["diameter", ">", 0.25], ["length", "<", 0.6]],
    "type": "IfcBuildingElementProxy",
    "name": "equipment {nominal}"
}
```

The parameters a condition can use are `kind`, `radius`, `diameter`, `length`, `nominal`, `orientation`, `angle`, `points` and `coverage`. They are also written to the `ScanToBIM` property set of each element, together with the `properties` of the rule.

## output files

`_cylinder.json`

```
{"cylinders": [{"id": 0, "start": [x, y, z], "end": [x, y, z], "axis": [x, y, z], "radius": 0.098,
                "length": 1.65, "points": 9556, "coverage": 0.89}, ...]}
```

`_pipe.json`. `cylinders` are the ids of the merged cylinders; `pipes` of an elbow are the ids of the two pipes it joins.

```
{"pipes": [{"id": 0, "start": [...], "end": [...], "radius": 0.09535, "measured_radius": 0.0986,
            "nominal": "175A", "length": 1.655, "points": 9878, "coverage": 0.89, "cylinders": [0, 58]}, ...],
 "elbows": [{"id": 0, "pipes": [43, 53], "corner": [...], "center": [...], "start": [...], "end": [...],
             "start_direction": [...], "radius": 0.0508, "bend_radius": 0.1334, "angle": 90.0, "nominal": "90A"}, ...]}
```

## tests

`tests/test_cylinder.py` checks the stages on synthetic pipes: a pipe scanned from one side next to a wall, axis snapping and splitting at gaps, merging, nominal sizes, elbows with their tangent points, no elbow at a tee or an odd angle, elbow pieces and 45 degree offsets, the mapping rules, and a run of the three stages whose IFC elbow is checked against a quarter torus.

```
python -m pytest tests/test_cylinder.py
```

## revision history

| date | changes |
|---|---|
| 2026.11 | pcd_to_clean reads LAS and LAZ (laspy with lazrs). |
| 2026.11 | pcd_to_cylinder: RANSAC cylinders from two points and their normals, least squares refinement, cut at gaps along the axis, unbroken arc coverage against false cylinders between pipes. |
| 2026.11 | cylinder_to_pipe: merging on one axis, nominal sizes and elbows from a pipe standard file, removal of short pieces inside a bend. |
| 2026.11 | geo_to_bim_pipe: IfcPipeSegment as extruded circles, IfcPipeFitting BEND as a disk swept along an arc, classes and properties from a mapping rule file. |
| 2026.11 | pipe_rule sample pipeline on part of the KICT zero energy building mechanical room. |
