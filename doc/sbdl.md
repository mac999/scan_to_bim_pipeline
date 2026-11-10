# SBDL reference

An SBDL file is a JSON object. Each key that starts with `pipeline.` is a pipeline, and its value is the list of stages run in order.

```
{
    "pipeline.<name>": [
        {"type": "<stage>", "<parameter>": <value>, ...},
        ...
    ]
}
```

`pipeline/app.py` looks for `<input name>_scan_to_bim.json` next to each input file (the suffix is `pipeline_tag` in `pipeline/config.json`), or uses the file given with `--pipeline`. `--stage <regex>` limits the run to the matching pipelines, for example `--stage indoor_rule`.

## How a stage runs

A stage is a separate program. For `"type": "pcd_to_seg"` the pipeline runs, in this order of preference,

1. `<bin_path>/pcd_to_seg/pcd_to_seg.py` with python,
2. `<bin_path>/bin/pcd_to_seg`, the C++ build output,
3. the command in the stage's `cmd` key, if one is given.

Every other key of the stage is passed as `--<key> <value>`. The program also receives `--input` and `--output`. The first stage gets the input file; each later stage gets the output prefix of the stage before it, `output/<input name>/<stage>/<stage>`.

Keys that are not passed on:

| key | meaning |
|---|---|
| `type` | stage name |
| `active` | `false` skips the stage and reuses the output already on disk |
| `cmd` | command to run instead of the stage program. `$bin_path/` is replaced |
| `note` | free text |

If a stage exits with a non-zero code, or its program is not found, the rest of that pipeline is not run.

Python stages reject unknown parameters. The C++ stages print `unknown option ignored: --<key>` and continue.

## Stages

### data_to_format

Converts the input with PDAL.

| parameter | default | |
|---|---|---|
| `output_type` | required | output extension, for example `.pcd` |
| `transform_matrix` | identity | 4x4 row major matrix for `filters.transformation` |

PDAL cannot read a PCD file with a padding field (`_`), which PCL writes and the conference_room1 sample has. Start such a pipeline at `pcd_to_seg`.

### pcd_to_dtm

Rasterizes a point cloud with PDAL `writers.gdal`. All points are used, so the result is a surface model including buildings.

| parameter | default | |
|---|---|---|
| `resolution` | 0.2 | cell size in meters |
| `gdal_output_type` | all | `writers.gdal` output_type |
| `transform_matrix` | identity | 4x4 row major matrix |
| `classification` | building | not applied yet |
| `pdal_pipeline` | | not used. the PDAL pipeline is written next to the output |

### dtm_to_geo

Extracts building footprints from the raster and estimates their heights. Writes `.shp`, `.geojson`, `.ply` and `_<output_dataset>`, a CSV with one row per building.

| parameter | default | |
|---|---|---|
| `extract_pixel_min_value` | 60 | gray level (0-255) above which a pixel belongs to a building |
| `extract_pixel_max_value` | 200 | passed to `cv2.threshold` as the output value. it is not an upper bound |
| `remove_area` | 20.0 | footprints smaller than this, in square meters, are dropped |
| `simplify_factor` | 10.0 | footprint simplification tolerance in pixels |
| `height_building_offset` | 5.0 | inward buffer in pixels where the roof height is sampled |
| `height_ground_offset` | 10.0 | outward buffer in pixels where the ground height is sampled. `height_ground_offest` is accepted too |
| `max_building_height` | 100.0 | taller results are dropped |
| `output_dataset` | dataset.csv | CSV suffix |
| `log_view` | false | show plots |

### geo_to_bim_outdoor

Reads `<input>_dimension.csv` and writes one extruded `IfcBuildingElementProxy` per building, placed on its ground elevation, with the property set `ScanToBIM`.

| parameter | default | |
|---|---|---|
| `base_point` | lower left of the footprints | `[x, y]` subtracted from map coordinates |
| `crs` | from `<input>_projection.txt` | EPSG code for `IfcMapConversion` |
| `project_name` | Scan to BIM project | |
| `site_name` | My Site | |
| `link_pset` | | not used yet |

### pcd_to_seg (C++)

Repeated RANSAC plane extraction. Writes `<output>_@<n>.pcd` per plane.

| parameter | default | |
|---|---|---|
| `iteration` | 100 | RANSAC iterations |
| `threshold` | 0.11 | distance to the plane in meters |
| `projection` | true | project the inliers on the plane |
| `min_points_ratio` | 0.2 | stop when fewer points than this ratio remain |
| `output_type` | pcd | `pcd` or `json` |

### pcd_to_clean

Outlier removal with Open3D. Each filter is skipped when its size parameter is 0. LAS and LAZ input is read with laspy and written as PCD.

| parameter | default | |
|---|---|---|
| `voxel_down_size` | 0.0 | |
| `uniform_down_sample` | 0 | |
| `stat_neighbors`, `stat_std_ratio` | 10, 1.0 | statistical outlier removal |
| `nb_radius_points`, `nb_radius` | 50, 0.1 | radius outlier removal |

### seg_to_geo (C++)

Hull of each segment. Writes `<output>_@<n>.pcd` and `.json`.

| parameter | default | |
|---|---|---|
| `hull_type` | cc | `cc` concave, otherwise convex |
| `alpha` | 0.15 | concave hull alpha |
| `output_type` | pcd | |

### geo_to_bim_indoor

Labels each segment as wall, floor or ceiling from its normal and height, and writes an IFC file with an `IfcWall`, `IfcSlab` (FLOOR) or `IfcCovering` (CEILING) per segment.

With `corner_buffer` above 0, each segment is fitted to a plane and outlined in it. Where two planes come within the buffer of their intersection line, both outlines are extended or trimmed to that line, and corners are filled out to the point where the edges meet. Each outline is saved as `<output>_@<index>_<label>_polygon.json` (GeoJSON Polygon, 3D), all of them as `<output>_polygon.ply`, and the IFC elements are the outlines extruded by `element_thickness` away from the room center. A plane that crosses another one in its middle (a table top against a wall) is left as it is.

| parameter | default | |
|---|---|---|
| `wall_min_angle`, `wall_max_angle` | 30, 150 | normal angle to +Z in degrees for a wall |
| `wall_height` | 3.5 | |
| `floor_max_height` | 0.5 | a horizontal segment below this z is a floor, otherwise a ceiling |
| `alpha` | 0.0 | alpha shape of the boundary. 0 gives the convex hull |
| `element_thickness` | 0.2 | minimum thickness of an element in meters |
| `corner_buffer` | 0.0 | largest gap in meters closed between neighbouring planes. 0 keeps one box per segment |
| `corner_min_angle` | 30 | planes closer in angle than this do not share an edge |
| `axis_snap_angle` | 10 | planes within this angle of level or vertical are made exactly level or vertical |
| `polygon_tolerance` | 0.05 | outline simplification in meters |
| `corner_reach` | 1.0 | distance in meters over which a corner is filled out to the point where two edges meet |
| `output_ifc` | true | |
| `project_name`, `site_name`, `building_name`, `storey_name` | | IFC names |
| `log_view` | false | show plots |

### pcd_to_cylinder

The pipe stages, with results on a sample scan, are also described in [pipe.md](./pipe.md).

Extracts cylinders, such as pipes, with RANSAC. A seed point and a neighbour with their normals give a cylinder hypothesis; the hypotheses are scored around the seed, the best one is refined by least squares on all points (axis from the normals, circle fit across the axis) and cut where its points stop along the axis. A cylinder is kept when its points cover an unbroken arc of at least `min_coverage`, so a pipe scanned from one side is still found while a false cylinder touching several pipes is not. Its points are then removed and the search goes on until `max_failures` seeds in a row give nothing.

Reads every point cloud that matches the input prefix, LAS and LAZ included. Writes `<output>_@<n>.pcd` with the points of each cylinder, `<output>_residual.pcd` with the rest and `<output>_cylinder.json` with start, end, axis, radius, length, number of points and coverage of each cylinder.

| parameter | default | |
|---|---|---|
| `voxel_size` | 0.0 | 0 keeps the input density |
| `normal_radius`, `normal_max_nn` | 0.03, 40 | normal estimation. keep the radius below twice the smallest pipe radius |
| `min_radius`, `max_radius` | 0.01, 0.3 | |
| `distance_tolerance` | 0.005 | distance of an inlier from the cylinder surface |
| `normal_angle` | 20 | largest angle in degrees between a normal and the direction from the axis |
| `min_points` | 150 | |
| `min_length` | 0.15 | |
| `max_gap` | 0.05 | a cylinder is cut where its points stop for longer than this along the axis |
| `min_coverage` | 0.25 | shortest unbroken arc around the axis, as a fraction of the circle |
| `axis_snap_angle` | 5 | axes within this angle of x, y or z are made parallel to it |
| `hypotheses` | 50 | hypotheses scored per seed point |
| `max_failures` | 200 | |
| `seed` | 0 | random seed, for repeatable results |

### cylinder_to_pipe

Merges cylinders on one axis into straight pipes, snaps their radii to nominal sizes and joins two pipe ends that point at a common corner with an elbow. The elbow is a torus segment tangent to both pipes; both pipes are cut or extended to its tangent points. A short pipe in the corner of an elbow, at an angle to both pipes, is a piece of the bend and is dropped. Two parallel pipes joined by a short pipe at 45 degrees are an offset and keep the short pipe. Writes `<output>_pipe.json` (pipes and elbows) and `<output>_pipe.ply`.

| parameter | default | |
|---|---|---|
| `merge_angle` | 5 | largest angle in degrees between cylinders that are merged |
| `merge_distance` | 0.02 | largest offset between their axes |
| `merge_gap` | 0.3 | largest gap between them along the axis |
| `radius_tolerance` | 0.01 | largest radius difference for merges and elbows |
| `pipe_standard` | cylinder_to_pipe/pipe_standard.json | nominal sizes and elbow rules. empty keeps the measured radii |
| `nominal_tolerance` | 0.005 | largest radius change when a radius is snapped to a nominal size |
| `min_pipe_length` | 0.05 | |
| `elbow_angle_tolerance` | 10 | largest difference in degrees from an elbow angle of the standard |
| `elbow_axis_tolerance` | 1.0 | largest distance between the two axes, in pipe radii |
| `elbow_reach` | 0.5 | largest distance from a pipe end to the corner |
| `elbow_piece_length` | 0.3 | shorter pipes in the corner of an elbow are dropped |

The pipe standard file holds what a pipe standard defines. Relative paths are taken from the working directory, then from the repository root.

```
{
    "name": "KS D 3507 ...",
    "sizes": [{"name": "80A", "outer_diameter": 0.0891, "bend_radius": 0.1143}, ...],
    "elbow": {"angles": [45, 90], "bend_ratio": 1.5, "min_bend_ratio": 1.0}
}
```

`sizes` lists the nominal sizes with their outer diameters in meters. `bend_radius` of a size is the bend radius of its elbows; sizes without it use `bend_ratio` x outer diameter. `angles` are the elbow angles made by fittings, so two pipes at another angle are not joined. When the pipes are too short for the bend, the bend is made tighter down to `min_bend_ratio` x outer diameter, otherwise no elbow is made.

### geo_to_bim_pipe

Maps the pipes and elbows of `<input>_pipe.json` to IFC elements with a rule file and writes `<output>.ifc`. A pipe is an extruded circle, an elbow a disk swept along an arc (IfcSweptDiskSolid). Every element gets the property set `ScanToBIM` with the values below and the properties of its rule.

| parameter | default | |
|---|---|---|
| `mapping_rule` | geo_to_bim_pipe/pipe_mapping_rule.json | |
| `project_name`, `site_name`, `building_name`, `storey_name` | | IFC names |

The rule file is a list of rules. The first rule whose conditions hold maps an element; an element with no rule is left out.

```
{
    "rules": [
        {
            "condition": [["kind", "==", "pipe"], ["orientation", "==", "vertical"]],
            "logic": "and",
            "type": "IfcPipeSegment",
            "predefined_type": "RIGIDSEGMENT",
            "name": "riser {nominal}",
            "properties": {"Material": "carbon steel"}
        }
    ]
}
```

A condition is `[parameter, operator, value]` with the operators `==`, `!=`, `<`, `<=`, `>`, `>=` and `in`. `logic` is `and` (default) or `or`. The parameters are `kind` (pipe, elbow), `radius`, `diameter`, `length`, `nominal`, `orientation` (vertical, horizontal, inclined), `angle`, `points` and `coverage`. `name` may use them as `{parameter}`.

### pcd_to_seg_ml

Open3D-ML semantic segmentation, run in the docker image given in `cmd`.

| parameter | default | |
|---|---|---|
| `model_config` | configs/randlanet_s3dis.yml | relative to the module |
| `ckpt` | logs/randlanet_s3dis_normalvector_20230707_198.pth | relative to the module |
| `ckpt_url` | Open3D model zoo RandLA-Net S3DIS | downloaded when `ckpt` is missing |
| `max_input_file` | 3 | |
| `remote_io_root` | `$bin_path:/pcd_pl/` | host to container path mapping |

## pipeline/config.json

| key | |
|---|---|
| `root_path`, `bin_path`, `lib_path`, `data_path` | relative paths are resolved from the repository root |
| `data_ext` | input extensions picked up from `--input_path` |
| `pipeline_tag` | SBDL file suffix looked up next to each input |
