# name: pcd to cylinder
# programmer: taewook kang (laputa99999@gmail.com)
# date: 2026.11.
# desc: extracts cylinders (pipes) from a point cloud with RANSAC. writes the inliers of each cylinder
#       as <output>_@<n>.pcd, the points left over as <output>_residual.pcd and the cylinder
#       parameters as <output>_cylinder.json. <output>_log.json lists the parameters, counts and the
#       cylinders rejected by pipe_angles, whose points are in <output>_rejected_@<n>.pcd

import os, sys, json, glob, time, argparse
import numpy as np
import open3d as o3d
lib_path = os.path.dirname(os.path.abspath(__file__)) + "/../lib"
sys.path.append(lib_path)
import scan_to_bim_lib
import cylinder

def load(files, voxel_size):
    pcd = o3d.geometry.PointCloud()
    for f in files:
        pcd += scan_to_bim_lib.read_point_cloud(f)
    if voxel_size > 0:
        pcd = pcd.voxel_down_sample(voxel_size)
    return pcd

def axis_angles(axis, grid_azimuth):
    # elevation from the horizontal plane and azimuth from the grid, in degrees
    elevation = np.degrees(np.arcsin(min(1.0, abs(axis[2]))))
    azimuth = (np.degrees(np.arctan2(axis[1], axis[0])) - grid_azimuth) % 180 if elevation < 89.9 else 0.0
    return round(float(elevation), 2), round(float(azimuth), 2)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    parser.add_argument('--voxel_size', type=float, default=0.0)          # 0 keeps the input density
    parser.add_argument('--normal_radius', type=float, default=0.03)      # keep below the smallest pipe radius x 2
    parser.add_argument('--normal_max_nn', type=int, default=40)
    parser.add_argument('--min_radius', type=float, default=0.01)
    parser.add_argument('--max_radius', type=float, default=0.3)
    parser.add_argument('--distance_tolerance', type=float, default=0.005)  # distance of an inlier from the surface
    parser.add_argument('--normal_angle', type=float, default=20.0)       # largest angle between a normal and the radial direction
    parser.add_argument('--min_points', type=int, default=150)
    parser.add_argument('--min_length', type=float, default=0.15)
    parser.add_argument('--max_gap', type=float, default=0.05)            # a cylinder is cut where its points stop for longer than this
    parser.add_argument('--min_coverage', type=float, default=0.25)       # shortest unbroken arc around the axis, fraction of the circle
    parser.add_argument('--axis_snap_angle', type=float, default=5.0)     # axes this close to x, y or z are made parallel to it
    parser.add_argument('--hypotheses', type=int, default=50)             # hypotheses scored per seed point
    parser.add_argument('--max_failures', type=int, default=200)          # stop after this many seed points in a row give nothing
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--pipe_angles', type=str, default='[]')         # fitting angles, e.g. [45, 90]. axes off their multiples are rejected. [] allows any axis
    parser.add_argument('--grid_azimuth', type=float, default=0.0)        # azimuth of the building grid from x, in degrees
    parser.add_argument('--tiles', type=str, default='[1, 1]')            # tiles along x, y (and z). [1, 1] searches the whole cloud at once
    parser.add_argument('--tile_overlap', type=float, default=0.0)        # margin around a tile. 0 takes max(min_length, 2 x max_radius) + max_gap
    parser.add_argument('--tile_workers', type=int, default=1)            # tiles searched in parallel
    args = parser.parse_args()

    files = sorted(f for f in glob.glob(args.input + "*") if os.path.splitext(f)[1].lower() in ('.pcd', '.ply', '.las', '.laz', '.xyz'))
    print("input files = ", files)
    if not files:
        print("no input point cloud")
        sys.exit(1)

    pcd = load(files, args.voxel_size)
    pcd.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=args.normal_radius, max_nn=args.normal_max_nn))
    points, normals = np.asarray(pcd.points), np.asarray(pcd.normals)
    print(f'{len(points)} points')

    angles = json.loads(args.pipe_angles)
    directions = cylinder.pipe_directions(angles, args.grid_azimuth) if angles else None
    rejected = []
    start = time.time()
    found, residual = cylinder.detect_tiled(points, normals, args.min_radius, args.max_radius, args.distance_tolerance,
                                            args.normal_angle, args.min_points, args.min_length, args.max_gap,
                                            args.min_coverage, args.axis_snap_angle, args.hypotheses, args.max_failures,
                                            args.seed, json.loads(args.tiles), args.tile_overlap, args.tile_workers, log=print,
                                            directions=directions, rejected=rejected)
    elapsed = time.time() - start
    print(f'{len(found)} cylinders, {len(rejected)} rejected, {len(residual)} points left, {elapsed:.1f} s')

    records = []
    for index, cyl in enumerate(found):
        o3d.io.write_point_cloud(f'{args.output}_@{index}.pcd', pcd.select_by_index(cyl.inliers.tolist()))
        records.append(dict(id=index, **cyl.to_dict()))
    o3d.io.write_point_cloud(args.output + '_residual.pcd', pcd.select_by_index(residual.tolist()))
    with open(args.output + '_cylinder.json', 'w') as f:
        json.dump({'cylinders': records}, f, indent=1)

    for old in glob.glob(glob.escape(args.output) + '_rejected_@*.pcd'):
        os.remove(old)
    rejects = []
    for index, cyl in enumerate(rejected):
        fname = f'{args.output}_rejected_@{index}.pcd'
        o3d.io.write_point_cloud(fname, pcd.select_by_index(cyl.inliers.tolist()))
        elevation, azimuth = axis_angles(cyl.axis, args.grid_azimuth)
        rejects.append(dict(id=index, reason=cyl.reason, elevation=elevation, azimuth=azimuth,
                            file=os.path.basename(fname), **cyl.to_dict()))
    log = {'stage': 'pcd_to_cylinder', 'input': files, 'parameters': vars(args),
           'points': len(points), 'cylinders': len(found), 'rejected': len(rejected), 'residual': len(residual),
           'seconds': round(elapsed, 1), 'rejected_cylinders': rejects}
    with open(args.output + '_log.json', 'w') as f:
        json.dump(log, f, indent=1)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
        sys.exit(1)
