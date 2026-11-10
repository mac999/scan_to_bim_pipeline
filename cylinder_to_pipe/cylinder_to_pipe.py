# name: cylinder to pipe
# programmer: taewook kang (laputa99999@gmail.com)
# date: 2026.11.
# desc: merges the cylinders of pcd_to_cylinder into straight pipes, snaps their radii to nominal
#       sizes and joins pipe ends that meet at a corner with elbows. writes <output>_pipe.json and
#       <output>_pipe.ply. <output>_log.json lists the parameters, counts and the cylinders and pipes
#       that were dropped, with the reason

import os, sys, json, glob, argparse
import open3d as o3d
lib_path = os.path.dirname(os.path.abspath(__file__)) + "/../lib"
sys.path.append(lib_path)
import pipe_network as pn

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def resolve(path):
    # relative paths are taken from the working directory, then from the repository root
    if not path or os.path.isabs(path) or os.path.exists(path):
        return path
    return os.path.join(ROOT, path)

def load_standard(path):
    # nominal sizes and elbow rules. without a file the measured radii are kept
    if not path:
        return {'sizes': [], 'elbow': {}}
    with open(resolve(path)) as f:
        return json.load(f)

def save_mesh(fname, pipes, elbows):
    mesh = o3d.geometry.TriangleMesh()
    for parts, color in (([pn.pipe_mesh(p) for p in pipes], [0.30, 0.47, 0.66]),
                         ([pn.elbow_mesh(e) for e in elbows], [0.89, 0.34, 0.34])):
        for vertices, faces in parts:
            part = o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(vertices), o3d.utility.Vector3iVector(faces))
            part.paint_uniform_color(color)
            mesh += part
    mesh.compute_vertex_normals()
    o3d.io.write_triangle_mesh(fname, mesh)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    parser.add_argument('--merge_angle', type=float, default=5.0)
    parser.add_argument('--merge_distance', type=float, default=0.02)    # largest offset between the axes
    parser.add_argument('--merge_gap', type=float, default=0.3)          # largest gap along the axis
    parser.add_argument('--radius_tolerance', type=float, default=0.01)  # largest radius difference for merges and elbows
    parser.add_argument('--pipe_standard', type=str, default='cylinder_to_pipe/pipe_standard.json')  # sizes and elbow rules
    parser.add_argument('--nominal_tolerance', type=float, default=0.005)  # largest radius change when snapping
    parser.add_argument('--min_pipe_length', type=float, default=0.05)
    parser.add_argument('--elbow_angle_tolerance', type=float, default=10.0)
    parser.add_argument('--elbow_axis_tolerance', type=float, default=1.0)  # largest distance between the axes, in radii
    parser.add_argument('--elbow_piece_length', type=float, default=0.3)  # shorter pipes in the corner of an elbow are pieces of its bend
    parser.add_argument('--elbow_reach', type=float, default=0.5)        # largest distance from a pipe end to the corner
    parser.add_argument('--min_length_ratio', type=float, default=0.0)   # pipes shorter than this x diameter and not joined by an elbow are dropped
    args = parser.parse_args()

    files = sorted(glob.glob(args.input + "*_cylinder.json"))
    print("input files = ", files)
    if not files:
        print("no cylinder file")
        sys.exit(1)

    pipes = []
    for fname in files:
        with open(fname) as f:
            for c in json.load(f)['cylinders']:
                pipes.append(pn.Pipe(c['start'], c['end'], c['radius'], c['points'], c['coverage'], [c['id']]))
    count = len(pipes)

    pipes = pn.merge(pipes, args.merge_angle, args.merge_distance, args.radius_tolerance, args.merge_gap)
    standard = load_standard(args.pipe_standard)
    elbow = standard.get('elbow', {})
    pipes = pn.snap_radius(pipes, standard['sizes'], args.nominal_tolerance)
    dropped = []
    def drop(kept, before, reason):
        kept_ids = {id(p) for p in kept}
        dropped.extend((p, reason) for p in before if id(p) not in kept_ids)
        return kept
    before = pipes
    pipes = pn.drop_elbow_pieces(pipes, elbow.get('angles', [45, 90]), args.elbow_angle_tolerance, args.elbow_axis_tolerance,
                                 args.elbow_reach, args.radius_tolerance, args.elbow_piece_length)
    pipes = drop(pipes, before, 'elbow_piece')
    elbows = pn.make_elbows(pipes, elbow.get('angles', [45, 90]), elbow.get('bend_ratio', 1.5), elbow.get('min_bend_ratio', 1.0),
                            {s['name']: s['bend_radius'] for s in standard['sizes'] if 'bend_radius' in s},
                            args.elbow_angle_tolerance, args.elbow_axis_tolerance, args.elbow_reach,
                            args.radius_tolerance, args.min_pipe_length)
    joined = {i for e in elbows for i in e['pipes']}
    pipes_out = drop([p for p in pipes if p.length >= args.min_pipe_length], pipes, 'short')
    before = pipes_out
    pipes_out = drop([p for k, p in enumerate(pipes) if p in pipes_out and
                      (k in joined or p.length >= args.min_length_ratio * 2 * p.measured_radius)], before, 'length_ratio')
    index = {id(p): k for k, p in enumerate(pipes_out)}
    for e in elbows:
        e['pipes'] = [index.get(id(pipes[i])) for i in e['pipes']]
    print(f'{count} cylinders merged into {len(pipes_out)} pipes, {len(elbows)} elbows, '
          f'{sum(p.nominal is not None for p in pipes_out)} pipes with a nominal size, {len(dropped)} dropped')

    with open(args.output + '_pipe.json', 'w') as f:
        json.dump({'pipes': [p.to_dict(k) for k, p in enumerate(pipes_out)],
                   'elbows': [dict(id=k, **e) for k, e in enumerate(elbows)]}, f, indent=1)
    save_mesh(args.output + '_pipe.ply', pipes_out, elbows)

    drops = [dict(reason=reason, length_ratio=round(p.length / (2 * p.measured_radius), 2), **p.to_dict(k))
             for k, (p, reason) in enumerate(dropped)]
    log = {'stage': 'cylinder_to_pipe', 'input': files, 'parameters': vars(args), 'cylinders': count,
           'pipes': len(pipes_out), 'elbows': len(elbows), 'dropped': len(dropped), 'dropped_pipes': drops}
    with open(args.output + '_log.json', 'w') as f:
        json.dump(log, f, indent=1)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
        sys.exit(1)
