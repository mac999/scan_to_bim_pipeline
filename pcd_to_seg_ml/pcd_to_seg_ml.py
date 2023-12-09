# title: seg to geo ml
# author: taewook kang
# version: 1.0.0
# email: laputa99999@gmail.com
# date: 2023.9.1
# install:
# import open3d.ml.tf as ml3d
# sudo apt-get update
# sudo apt-get install libx11-6
# sudo apt-get install -y libgl1-mesa-glx
# pip install open3d tensorboard numpy
# appendix: 
''' segmentation target. 
    label_to_names = {
        0: 'ceiling', # dark red              # red         [1,0,0]
        1: 'floor',   # red                   # green       [0,1,0]
        2: 'wall',    # light red             # blue        [1,1,0]
        3: 'beam',      # dark green          # yellow      [0,1,1]
        4: 'column',    # green               # cyan        [0,0,1]
        5: 'window',    # light green         # blue
        6: 'door',      # dark blue           # dark blue
        7: 'table',     # blue                # dark pink
        8: 'chair',     # light blue          # middle pink
        9: 'sofa',      # dark yellow         # light pink
        10: 'bookcase', # yellow              # gray
        11: 'board',    # light yellow        # blue
        12: 'clutter'   # dark cyan           # white
    }
'''

import os, argparse, glob, logging, pickle, shutil, pdb, subprocess
import torch
import numpy as np
import open3d as o3d
import open3d.ml as _ml3d
import open3d.ml.torch as ml3d
from open3d._ml3d.datasets.base_dataset import BaseDataset, BaseDatasetSplit
from pathlib import Path

log = logging.getLogger(__name__)

def save_pcd_to_pkl(input_fname, output_fname):
    try:
        # Load point cloud data in PCD format
        pcd = o3d.io.read_point_cloud(input_fname)

        # Convert point cloud data to dictionary format
        # Attention. Train dataset point format should be matched. ex) X, Y, Z, R, G, B or X, Y, Z, nx, ny, nz
        points = np.asarray(pcd.points)
        feature = np.asarray(pcd.normals)
        if feature.shape[0] == 0:
            colors = np.asarray(pcd.colors) * 256
            feature = colors # .astype(np.integer)
        if feature.shape[0] == 0:
            feature = np.zeros(points.shape)
        new_points = np.concatenate([points, feature], axis=1)
        
        bbox_example = ['wall', 0, 0, 0, 1, 1, 1]
        bbox_list = [bbox_example]
        dataset = [new_points, bbox_list]
            
        with open(output_fname, "wb") as f:
            pickle.dump(dataset, f)    
        print("save ", output_fname)
        
    except Exception as e:
        print(e)

def convert_pcd_to_pkl(input_path, output_path):
    files = glob.glob(input_path)
    
    for fname in files:
        output_path = os.path.dirname(output_path)
        input_fname_ext = os.path.basename(fname)
        input_fname = os.path.splitext(input_fname_ext)[0]        
        save_pcd_to_pkl(fname, output_path + "/" + input_fname + ".pkl")

class pcd_dataset_default(ml3d.datasets.S3DIS): # pretrain model. default set. 
    def __init__(self, 
                 dataset_path, 
                 name='S3DIS',
                 task='segmentation',
                 cache_dir='./logs/cache',
                 use_cache=False,
                 class_weights=[
                     3370714, 2856755, 4919229, 318158, 375640, 478001, 974733,
                     650464, 791496, 88727, 1284130, 229758, 2272837
                 ],
                 num_points=40960,
                 test_area_idx=3,
                 ignored_label_inds=[],
                 ignored_objects=[
                     'wall', 'floor', 'ceiling', 'beam', 'column', 'clutter'
                 ],
                 test_result_folder='./test',                 
                 **kwargs):
        super().__init__(dataset_path=dataset_path,
                         name=name,
                         task=task,
                         cache_dir=cache_dir,
                         use_cache=use_cache,
                         class_weights=class_weights,
                         test_result_folder=test_result_folder,
                         num_points=num_points,
                         test_area_idx=test_area_idx,
                         ignored_label_inds=ignored_label_inds,
                         ignored_objects=ignored_objects,
                         **kwargs)
        return
        
    def get_split(self, split):
        return pcd_dataset_default_split(self, split=split)

class pcd_dataset_default_split(BaseDatasetSplit):
    def __init__(self, dataset, split='training'):
        super().__init__(dataset, split=split)
        log.info("Found {} pointclouds for {}".format(len(self.path_list),
                                                      split))

    def __len__(self):
        return len(self.path_list)

    def load_data(self, fname):
        data = pickle.load(open(fname, 'rb'))

        pc, bboxes = data
        pc = pc[~np.isnan(pc).any(1)]

        bboxes = self.dataset.read_bboxes(bboxes, self.cfg.ignored_objects)

        points = np.array(pc[:, :3], dtype=np.float32)
        feat = np.array(pc[:, 3:6], dtype=np.float32)
        labels = np.zeros(points.shape[0]) # np.array(pc[:, 6], dtype=np.int32).reshape((-1,))
        labels = labels.astype(np.integer)

        data = {
            'point': points,
            'feat': feat,
            'label': labels,
            'bounding_boxes': bboxes
        }

        return data

    def get_data(self, idx):
        pc_path = self.path_list[idx]
        
        return self.load_data(pc_path)

    def get_attr(self, idx):
        pc_path = Path(self.path_list[idx])
        name = pc_path.name.replace('.pkl', '')

        pc_path = str(pc_path)
        split = self.split
        attr = {'idx': idx, 'name': name, 'path': pc_path, 'split': split}
        return attr

# TBD
# class pcd_...

def get_gpu_device():
    dev = 'cpu'
    gpu_flag = torch.cuda.is_available()
    if gpu_flag:
        print('GPU device = ', torch.cuda.device_count())
        print('GPU index = ', torch.cuda.current_device())
        print(torch.cuda.get_device_name(0))

        dev = 'cuda:0'

    return dev

def get_module_path():
    cwd = os.getcwd()
    print('CWD = ', cwd)
    mpath = os.path.dirname(__file__)
    if len(mpath) == 0:
        mpath = '.'
    print("module path = ", mpath)
    return mpath

def update_remote_input_folder(fname):
    return os.path.dirname(fname) + '/' # .../*.pcd    

def update_remote_output_folder(fname):
    dirname = os.path.dirname(fname)
    return dirname

def chmod(path):
    for fname in os.listdir(path):
        file = os.path.join(path, fname)
        subprocess.Popen("chmod 666 " + file, shell=True)

def main():
    # pdb.set_trace()    
    parser = argparse.ArgumentParser()
    # parser.add_argument('--input', type=str, default='/pcd_pl/input/conferenceRoom1.pcd', help='input data folder', required=False)
    # parser.add_argument('--input', type=str, default='/pcd_pl/input/unf_1f.pcd', help='input data folder', required=False)
    # parser.add_argument('--output', type=str, default='/pcd_pl/output/conferenceRoom1/pcd_to_seg_ml/pcd_to_seg_ml', help='output data folder', required=False)    
    parser.add_argument('--input', type=str, default='/pcd_pl/input/conferenceRoom1_normal.pcd', help='input data folder', required=False)
    parser.add_argument('--output', type=str, default='/pcd_pl/output/conferenceRoom1/pcd_to_seg_ml/pcd_to_seg_ml', help='output data folder', required=False)    
    parser.add_argument('--remote_io_root', type=str, default='$bin_path:/pcd_pl/', help='remote input, output root folder path', required=False) 
    parser.add_argument('--max_input_file', type=int, default=3, help='input max input file count', required=False)
    parser.add_argument('--option', type=str, default='pcd_to_seg_option.json', help='define segments count, class, grouping', required=False)

    args = parser.parse_args()        
    args.input = update_remote_input_folder(args.input)
    mpath = get_module_path()

    print('loading model...')
    dev = get_gpu_device()
    cfg_file = mpath + "/configs/randlanet_s3dis.yml"
    cfg = _ml3d.utils.Config.load_from_file(cfg_file)

    model = ml3d.models.RandLANet(**cfg.model)
    model.to(torch.device(dev))

    print('convert pcd to pkl file')   
    output_folder = update_remote_output_folder(args.output)    
    pkl_output_folder = output_folder + '/original_pkl/'
    try:
        shutil.rmtree(pkl_output_folder)
        os.mkdir(pkl_output_folder)
        convert_pcd_to_pkl(args.input + "*.pcd", pkl_output_folder) # output = /pcd_docker/*.pkl    
        chmod(output_folder)
    except Exception as e:
        print(e)

    print('loading pipeline')    
    cfg.dataset['dataset_path'] = output_folder
    dataset_path = cfg.dataset.pop('dataset_path', None)
    dataset = pcd_dataset_default(dataset_path, **cfg.dataset)

    pipeline = ml3d.pipelines.SemanticSegmentation(model, dataset=dataset, device=dev, **cfg.pipeline)

    print('loading weights')
    ckpt_folder = mpath + "/logs/"
    os.makedirs(ckpt_folder, exist_ok=True)
    ckpt_path = ckpt_folder + "randlanet_s3dis_normalvector_20230707_198.pth"  # "randlanet_s3dis_20230628_183.pth"  # "randlanet_s3dis_20230620_200.pth" #  "randlanet_s3dis_202010091238.pth" #  "randlanet_s3dis_202201071330utc.pth" # "randlanet_s3dis_202010091238.pth"
    randlanet_url = "https://storage.googleapis.com/open3d-releases/model-zoo/randlanet_s3dis_area5_202010091333utc.pth"
    if not os.path.exists(ckpt_path):
        cmd = "wget {} -O {}".format(randlanet_url, ckpt_path)
        os.system(cmd)
    pipeline.load_ckpt(ckpt_path=ckpt_path)

    print('predict using pipeline.run_inference(data)')
    test_split = dataset.get_split('all') # "all") # ("test")
    for index, input_path_fname in enumerate(test_split.path_list):
        if index >= args.max_input_file:
            break
        
        data = test_split.get_data(index)
        print('input file = ', input_path_fname)
        print(data)

        results = pipeline.run_inference(data)

        colors = [[1,0,0], [0,1,0], [0,0,1], [1,1,0], [0,1,1], [0,0,1], 
                  [0,0,0.5], [0.2,0,0.2], [.5,0,.5], [1,0,1], [0.5,0.5,0.5], [0,0,1], [1,1,1], 
                  [0,0,1], [0.2,0.2,0.2]]   # To distinguesh objects, color schema was changed. # colors = [[0.2,0,0], [0.5,0,0], [1.0,0,0], [0,0.2,0], [0,0.5,0], [0,1.0,0], [0,0,0.2], [0,0,0.5], [0,0,1.0], [0.2,0.2,0], [0.5,0.5,0], [1.0,1.0,0], [0,0.2,0.2], [0,0.5,0.5], [0,1.0,1.0]]

        input_path = os.path.dirname(input_path_fname)
        input_fname_ext = os.path.basename(input_path_fname)
        input_fname = os.path.splitext(input_fname_ext)[0]

        xyz = data['point']
        labels = data['label']
        rgb = [colors[i] for i in labels]
        pcd = o3d.geometry.PointCloud() # http://www.open3d.org/docs/0.9.0/tutorial/Basic/working_with_numpy.html
        pcd.points = o3d.utility.Vector3dVector(xyz)
        pcd.colors = o3d.utility.Vector3dVector(np.array(rgb))
        o3d.io.write_point_cloud(args.output + "_" + input_fname + ".pcd", pcd, write_ascii=True) # mpath + "/input_data.pcd", pcd, write_ascii=True)

        predict_labels = results['predict_labels']
        predict_rgb = [colors[i] for i in predict_labels]
        pcd.colors = o3d.utility.Vector3dVector(np.array(predict_rgb))
        o3d.io.write_point_cloud(args.output + "_" + input_fname + "_predict_data.pcd", pcd, write_ascii=True)

        print(results)

    chmod(output_folder)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)
