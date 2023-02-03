# name: pcd to clean
# programmer: taewook kang (laputa99999@gmail.com)
# date: 2022.5.
# desc:  

import os, sys, json, glob
import trimesh
import open3d as o3d
import argparse, readline
import numpy as np
import sympy as sp
import matplotlib.pyplot as plt
from telnetlib import theNULL
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
lib_path = os.path.dirname(os.path.abspath(__file__)) + "/../lib"
sys.path.append(lib_path)    
import scan_to_bim_lib

def importJson(fname): 
    data = []
    with open(fname) as f:
        data = json.load(f)
    print(data)

    return data

def select_down_sample(cloud, ind):
    for i in ind:
        cloud[i]

def display_inlier_outlier(cloud, ind):
    inlier_cloud = cloud.select_by_index(ind) 
    outlier_cloud = cloud.select_by_index(ind, invert=True) 

    outlier_cloud.paint_uniform_color([1, 0, 0])
    inlier_cloud.paint_uniform_color([0.8, 0.8, 0.8])
    o3d.visualization.draw_geometries([inlier_cloud, outlier_cloud])

def remove_outlier(fname, args):
    pcd = o3d.io.read_point_cloud(fname)
    # o3d.visualization.draw_geometries([pcd])

    cl = pcd
    if args.voxel_down_size != None and args.voxel_down_size > 0.0:
        cl = pcd.voxel_down_sample(voxel_size = args.voxel_down_size)

    if args.uniform_down_sample != None and args.uniform_down_sample > 0:
        cl = cl.uniform_down_sample(every_k_points = args.uniform_down_sample)

    if args.stat_neighbors != None and args.stat_std_ratio != None:
        cl, ind = cl.remove_statistical_outlier(nb_neighbors = args.stat_neighbors,
                                                            std_ratio = args.stat_std_ratio)
        # display_inlier_outlier(cl, ind)

    if args.nb_radius_points != None :
        cl, ind = cl.remove_radius_outlier(nb_points = args.nb_radius_points, radius = args.nb_radius)
        # display_inlier_outlier(cl, ind)

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
    # args = parser.parse_args(["--voxel_down_size", "0.02", "--uniform_down_sample", "5", "--nb_neighbors", "20", "--nb_std_ratio", "2.0", "--nb_radius_points", "10", "--nb_radius", "0.05", "--input", "/home/ktw/Projects/pcd_pl/output/pcd_to_seg", "--output", "/home/ktw/Projects/pcd_pl/output/seg_to_seg"])
    # args = parser.parse_args(["--nb_neighbors", "50", "--nb_std_ratio", "1.0", "--input", "/home/ktw/Projects/pcd_pl/output/pcd_to_seg", "--output", "/home/ktw/Projects/pcd_pl/output/seg_to_seg"])
    args = parser.parse_args() # ["--voxel_down_size", "0.02", "--nb_radius_points", "100", "--nb_radius", "0.2", "--input", "/home/ktw/Projects/pcd_pl/output/pcd_to_seg*.pcd", "--output", "/home/ktw/Projects/pcd_pl/output/pcd_to_clean"])

    try:
        files = glob.glob(args.input + "*")
        print("input files = ", files)

        for index, infile in enumerate(files): 
            outfilename = scan_to_bim_lib.get_pcd_index_filepath(args.output, infile)

            print("cleaning ", infile)
            pcd = remove_outlier(infile, args)
            o3d.io.write_point_cloud(outfilename, pcd)
            
    except Exception as e:
        print(e)

if __name__ == '__main__':
    main()