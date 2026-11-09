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

Outlier removal with Open3D. Each filter is skipped when its size parameter is 0.

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
