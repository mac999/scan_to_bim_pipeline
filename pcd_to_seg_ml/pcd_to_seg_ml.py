# title: pcd to seg ml
# author: taewook kang
# version: 1.1.0
# email: laputa99999@gmail.com
# date: 2023.9.1, 2026.11
# desc: labels every point of the input clouds with a deep learning segmentation model and writes
#       <output>.las (or .laz) with the class id in the classification field and the class color as rgb.
#       the model, checkpoint, input feature and classes come from the --model file.
#       <output>_log.json lists the parameters and the point count of each class.
#       needs open3d.ml with torch, so it runs in the docker image of docker/build_docker_open3d

import os, sys, json, glob, argparse, urllib.request
import numpy as np
import open3d as o3d
lib_path = os.path.dirname(os.path.abspath(__file__)) + "/../lib"
sys.path.append(lib_path)
import scan_to_bim_lib

MODULE_PATH = os.path.dirname(os.path.abspath(__file__))
INPUT_EXT = ('.las', '.laz', '.pcd', '.ply', '.xyz', '.pts')

def resolve(path):
    # relative paths are taken from this module
    return path if os.path.isabs(path) else os.path.join(MODULE_PATH, path)

def load_model_file(fname):
    with open(resolve(fname)) as f:
        model = json.load(f)
    if model.get('framework') != 'open3d_ml':
        raise ValueError('unsupported framework: ' + str(model.get('framework')))
    if model.get('feature') not in ('rgb', 'normal'):
        raise ValueError('unsupported feature: ' + str(model.get('feature')))
    if len(model['classes']) > 32:
        raise ValueError('las point format 3 holds 32 classes at most')
    return model

def get_features(pcd, feature):
    points = np.asarray(pcd.points, dtype=np.float32)
    if feature == 'rgb':
        if not pcd.has_colors():
            raise ValueError('the model needs rgb and the cloud has none')
        feat = np.asarray(pcd.colors) * 255.0     # s3dis colors are 0-255
    else:
        if not pcd.has_normals():
            pcd.estimate_normals(o3d.geometry.KDTreeSearchParamKNN(30))
        feat = np.asarray(pcd.normals)
    return points, feat.astype(np.float32)

def download(url, fname):
    # a failed download must not leave a file that looks like a checkpoint on the next run
    os.makedirs(os.path.dirname(fname), exist_ok=True)
    print('download ', url)
    urllib.request.urlretrieve(url, fname + '.part')
    os.replace(fname + '.part', fname)

def load_predictor(model):
    import torch
    import open3d.ml as _ml3d
    import open3d.ml.torch as ml3d

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print('device = ', device)
    cfg = _ml3d.utils.Config.load_from_file(resolve(model['model_config']))
    net = getattr(ml3d.models, cfg.model['name'])(**cfg.model)
    cfg.pipeline['main_log_dir'] = resolve('logs')     # not the working directory, next to the checkpoint
    pipeline = getattr(ml3d.pipelines, cfg.pipeline['name'])(net, dataset=None, device=device, **cfg.pipeline)

    ckpt = resolve(model['ckpt'])
    if not os.path.exists(ckpt):
        download(model['ckpt_url'], ckpt)
    pipeline.load_ckpt(ckpt_path=ckpt)

    def predict(points, feat):
        data = {'point': points, 'feat': feat, 'label': np.zeros(len(points), dtype=np.int32)}
        return pipeline.run_inference(data)['predict_labels']
    return predict

def write_labeled(fname, infile, pcd, labels, classes, color):
    import laspy
    if os.path.splitext(infile)[1].lower() in ('.las', '.laz'):
        las = laspy.read(infile)     # keeps the other dimensions and the crs
        if 'red' not in las.point_format.dimension_names:
            las = laspy.convert(las, point_format_id=3 if las.point_format.id < 6 else 7)
    else:
        points = np.asarray(pcd.points)
        header = laspy.LasHeader(point_format=3, version='1.2')
        header.offsets = points.min(axis=0)
        header.scales = [0.001, 0.001, 0.001]
        las = laspy.LasData(header)
        las.x, las.y, las.z = points[:, 0], points[:, 1], points[:, 2]
        if pcd.has_colors():
            rgb = (np.asarray(pcd.colors) * 65535).astype(np.uint16)
            las.red, las.green, las.blue = rgb[:, 0], rgb[:, 1], rgb[:, 2]

    las.classification = labels.astype(np.uint8)
    if color == 'class':
        palette = np.array([c['color'] for c in classes], dtype=np.uint16) * 257    # las colors are 16 bit
        rgb = palette[labels]
        las.red, las.green, las.blue = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    las.write(fname)

def segment_files(files, output, model, predict, output_format='las', color='class'):
    classes = model['classes']
    results = []
    for infile in files:
        print('segment ', infile)
        pcd = scan_to_bim_lib.read_point_cloud(infile)
        points, feat = get_features(pcd, model['feature'])
        labels = np.asarray(predict(points, feat)).astype(np.int64)
        outfile = scan_to_bim_lib.get_pcd_index_filepath(output, infile, '.' + output_format)
        write_labeled(outfile, infile, pcd, labels, classes, color)
        os.chmod(outfile, 0o666)     # written by root in the container
        counts = np.bincount(labels, minlength=len(classes))
        results.append({'input': infile, 'output': outfile, 'points': len(labels),
                        'classes': {c['name']: int(n) for c, n in zip(classes, counts)}})
        print('save ', outfile)
    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)     # file or path prefix
    parser.add_argument('--output', type=str, required=True)
    parser.add_argument('--model', type=str, default='model_randlanet_s3dis.json')  # relative to this module
    parser.add_argument('--output_format', type=str, default='las', choices=['las', 'laz'])
    parser.add_argument('--color', type=str, default='class', choices=['class', 'original'])
    parser.add_argument('--remote_io_root', type=str, default='$bin_path:/pcd_pl/')  # used by the pipeline runner
    args = parser.parse_args()

    files = sorted(f for f in glob.glob(args.input + '*') if os.path.splitext(f)[1].lower() in INPUT_EXT)
    print('input files = ', files)
    if not files:
        print('no point cloud file')
        sys.exit(1)

    model = load_model_file(args.model)
    print('model = ', model['name'])
    results = segment_files(files, args.output, model, load_predictor(model), args.output_format, args.color)

    log = {'stage': 'pcd_to_seg_ml', 'parameters': vars(args), 'model': model['name'], 'files': results}
    with open(args.output + '_log.json', 'w') as f:
        json.dump(log, f, indent=1)
    os.chmod(args.output + '_log.json', 0o666)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
        sys.exit(1)
