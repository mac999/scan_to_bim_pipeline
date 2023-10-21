# title: update normal vector of pcd files
# author: kang taewook 
# date: 2023.6.20
import os, argparse, glob, logging, pickle, shutil, pdb, subprocess
import numpy as np
import open3d as o3d

def test_normal():
    bunny = o3d.data.BunnyMesh()
    gt_mesh = o3d.io.read_triangle_mesh(bunny.path)
    gt_mesh.compute_vertex_normals()

    pcd = gt_mesh.sample_points_poisson_disk(5000)
    # Invalidate existing normals.
    pcd.normals = o3d.utility.Vector3dVector(np.zeros((1, 3)))

    print("Displaying input pointcloud ...")
    o3d.visualization.draw_geometries([pcd], point_show_normal=True)

    pcd.estimate_normals()
    print("Displaying pointcloud with normals ...")
    o3d.visualization.draw_geometries([pcd], point_show_normal=True)

    print("Printing the normal vectors ...")
    print(np.asarray(pcd.normals))
    

def update_normal_vector(input_fname, output_fname):
    pcd = o3d.io.read_point_cloud(input_fname, format='xyz')
    print(pcd)
    print(np.asarray(pcd.points))
    # o3d.visualization.draw_geometries([pcd])

    print("Recompute the normal of the downsampled point cloud")
    pcd.estimate_normals()  # o3d.geometry.estimate_normals() not working
    # o3d.visualization.draw_geometries([pcd], point_show_normal=True)

    print("Print a normal vector of the 0th point")
    print(pcd.normals[0])
    print("Print the normal vectors of the first 10 points")
    print(np.asarray(pcd.normals)[:10, :])
    print("")

    o3d.io.write_point_cloud(output_fname, pcd, write_ascii=True)

    '''
    print("Downsample the point cloud with a voxel of 0.05")
    downpcd = o3d.geometry.voxel_down_sample(pcd, voxel_size=0.05)
    o3d.visualization.draw_geometries([downpcd])
    '''

def update_file_with_normal_vector(input_folder, output_folder):
    # enumerate files in all subfolder using glob.        
    for path, subdirs, files in os.walk(input_folder):
        for name in files:
            f = os.path.join(path, name)

            # change the extension from .txt to .xyzn of the output file.
            fname = os.path.basename(f)
            ext = os.path.splitext(fname)[1]
            if ext != '.txt':
                continue

            try:                
                output_fname = os.path.join(output_folder, fname.replace(ext, '.xyzn'))            
                print('writing to {}'.format(output_fname))
                update_normal_vector(f, output_fname)
                
                os.rename(output_fname, output_fname.replace('.xyzn', '.xyz'))
            except Exception as e:
                print(e)
                pass

def replace_pcd_files(input_folder):
    # enumerate files in all subfolder using glob.        
    for path, subdirs, files in os.walk(input_folder):
        for name in files:
            f = os.path.join(path, name)

            # change the extension from .txt to .xyzn of the output file.
            fname = os.path.basename(f)
            ext = os.path.splitext(fname)[1]
            if ext != '.xyz':
                continue

            try:                
                txt_fname = f.replace('.xyz', '.txt')
                os.remove(txt_fname)
                output_fname = f.replace('.xyz', '.txt')
                print('replace to {}'.format(output_fname))
                os.rename(f, output_fname)
            except Exception as e:
                print(e)
                pass

if __name__ == "__main__":
    # pdb.set_trace()    
    parser = argparse.ArgumentParser()
    parser.add_argument('--option', type=str, default='update', help='replace | update', required=False)
    parser.add_argument('--input', type=str, default='./pcd_to_seg_ml/dataset/Stanford3dDataset_v1.2_Aligned_Version_normal/', help='input data folder', required=False)
    # parser.add_argument('--output', type=str, default='./pcd_to_seg_ml/test_data/', help='output data folder', required=False)    
    args = parser.parse_args()        

    if args.option == 'replace':
        replace_pcd_files(args.input)
    elif args.option == 'update':
        update_file_with_normal_vector(args.input, args.input)


