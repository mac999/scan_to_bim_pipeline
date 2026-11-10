# name: pcd to clean
# programmer: taewook kang (laputa99999@gmail.com)
# date: 2022.5.
# desc:  

import os, sys, glob
import open3d as o3d
import argparse
lib_path = os.path.dirname(os.path.abspath(__file__)) + "/../lib"
sys.path.append(lib_path)    
import scan_to_bim_lib

def remove_outlier(fname, args):
    pcd = scan_to_bim_lib.read_point_cloud(fname)
    # o3d.visualization.draw_geometries([pcd])

    cl = pcd
    if args.voxel_down_size != None and args.voxel_down_size > 0.0:
        cl = pcd.voxel_down_sample(voxel_size = args.voxel_down_size)

    if args.uniform_down_sample != None and args.uniform_down_sample > 0:
        cl = cl.uniform_down_sample(every_k_points = args.uniform_down_sample)

    if args.stat_neighbors != None and args.stat_std_ratio != None and args.stat_neighbors > 0:   # 0 disables the filter
        cl, ind = cl.remove_statistical_outlier(nb_neighbors = args.stat_neighbors,
                                                            std_ratio = args.stat_std_ratio)

    if args.nb_radius_points != None and args.nb_radius_points > 0:   # 0 disables the filter
        cl, ind = cl.remove_radius_outlier(nb_points = args.nb_radius_points, radius = args.nb_radius)

    return cl

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    parser.add_argument('--voxel_down_size', type=float, default=0.0, required=False)
    parser.add_argument('--uniform_down_sample', type=int, default=0, required=False)
    parser.add_argument('--stat_neighbors', type=int, default=10, required=False)
    parser.add_argument('--stat_std_ratio', type=float, default=1.0, required=False)
    parser.add_argument('--nb_radius_points', type=int, default=50, required=False)
    parser.add_argument('--nb_radius', type=float, default=0.1, required=False)
    args = parser.parse_args() # ["--voxel_down_size", "0.02", "--nb_radius_points", "100", "--nb_radius", "0.2", "--input", "/home/ktw/Projects/pcd_pl/output/pcd_to_seg*.pcd", "--output", "/home/ktw/Projects/pcd_pl/output/pcd_to_clean"])

    try:
        files = glob.glob(args.input + "*")
        print("input files = ", files)

        for index, infile in enumerate(files): 
            ext = ".pcd" if os.path.splitext(infile)[1].lower() in (".las", ".laz") else ""   # open3d cannot write las
            outfilename = scan_to_bim_lib.get_pcd_index_filepath(args.output, infile, ext)

            print("cleaning ", infile)
            pcd = remove_outlier(infile, args)
            o3d.io.write_point_cloud(outfilename, pcd)
            
    except Exception as e:
        print(e)
        sys.exit(1)

if __name__ == '__main__':
    main()