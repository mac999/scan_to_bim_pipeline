# title: pcd to bbox
# author: taewook kang
# version: 1.0.0
# email: laputa99999@gmail.com
# date: 2023.1.4
import os, json, glob, argparse, fnmatch
import numpy as np
import open3d as o3d

def load_pcd(fname):
    # pcd = o3d.io.read_point_cloud(fname)
    pcd_data = np.loadtxt(fname, delimiter=' ')
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pcd_data[:,0:3]) # XYZ points
    pcd_colors = pcd_data[:,3:6] / 256.
    pcd.colors = o3d.utility.Vector3dVector(pcd_colors)
    return pcd

def save_bbox_json(fname, offices, labels, bbox_list):
    objects_dic = {
        "objects": []
    }

    for i, label in enumerate(labels):
        office = offices[i]
        bbox = bbox_list[i]
        # vector3ds = bbox.get_box_points()
        aabb_points = np.asarray(bbox.get_box_points()).tolist()
        min = bbox.get_min_bound().tolist()
        max = bbox.get_max_bound().tolist()

        obj = {
            'office': office,
            'class': label,
            'bbox': aabb_points
        }
        objects_dic['objects'].append(obj)
    
    with open(fname, 'w') as file:
        json_objects = json.dumps(objects_dic, indent=4)
        file.write(json_objects)

def main(args):
    try:
        pcd_files = []
        # files = glob.glob(args.input)
        for path, subdirs, files in os.walk(args.input):
            for name in files:
                f = os.path.join(path, name)
                if fnmatch.fnmatch(name, "*.txt"):
                    pcd_files.append(f)

        pcd_list = []
        offices = []
        labels = []
        aabb_list = []
        for input_fname in pcd_files:
            if 'ceiling' in input_fname:
                continue
            if 'Annotations' not in input_fname:
                continue
            fname = os.path.basename(input_fname)
            label, ext = os.path.splitext(fname)
            base_folder_len = len(args.input)
            if base_folder_len:
                office = input_fname[base_folder_len:]
            tag_index = office.find('\\')
            if tag_index:
                office = office[:tag_index]

            pcd = load_pcd(input_fname)
            pcd_list.append(pcd)

            aabb = pcd.get_axis_aligned_bounding_box()  
            aabb.color = (1, 0, 0)
            aabb_list.append(aabb)

            obb = pcd.get_oriented_bounding_box(robust=True)
            obb.color = (0, 1, 0)

            labels.append(label)
            offices.append(office)

        save_bbox_json(args.output, offices, labels, aabb_list)

        for aabb in aabb_list:
            pcd_list.append(aabb)
            
        o3d.visualization.draw_geometries(pcd_list)

    except Exception as e:
        print(str(e))

    pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='pcd to bbox')
    parser.add_argument('--input', type=str, default='H:/data/Stanford3dDataset_v1.2/Area_1/', help='input PCD text file')
    parser.add_argument('--output', type=str, default='./pcd_to_bbox1.json', help='output BBox json file')
    
    args = parser.parse_args()
    main(args)
