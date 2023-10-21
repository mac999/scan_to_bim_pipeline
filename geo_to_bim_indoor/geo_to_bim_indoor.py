# name: geo to obj
# programmer: taewook kang (laputa99999@gmail.com)
# date: 2022.3.
# desc: if alpha = 0 then convex. if alpha = 2.0 then concave. if alpha = 3.5 then loss shape  
# ref: https://pypi.org/project/alphashape/

import os, sys, argparse, readline, alphashape, json, glob, pymesh
import pandas as pd
import numpy as np
from descartes import PolygonPatch
import matplotlib.pyplot as plt
import open3d as o3d

lib_path = os.path.dirname(os.path.abspath(__file__)) + "/../lib"
sys.path.append(lib_path)    
import scan_to_bim_lib

sys.path.insert(0, os.path.dirname(os.getcwd()))

args = None

def importJson(fname): 
    data = []
    with open(fname) as f:
        data = json.load(f)
    return data['coordinates']

def read_data(fpath):
    poly = []

    filename, file_extension = os.path.splitext(fpath) 
    if file_extension.find(".json") >= 0:
        multipoly = importJson(fpath)
        print(fpath, "imported.")

        print(type(multipoly))
        for index in range(len(multipoly)):
            pl = multipoly[index]
            # poly.append([])
            for p in pl:
                poly.extend(p)
        # poly = multipoly[0][0]
    else:
        pcd = o3d.io.read_point_cloud(fpath)
        for p in pcd.points:
            poly.extend([p[0], p[1], p[2]])

    print(poly)
    return poly

def get_obj_type(poly):
    global args
    
    # rule. DL.
    label = 'none'

    normal = scan_to_bim_lib.get_normal_vector(poly)
    angle = scan_to_bim_lib.get_angle_between_vector(normal, base = [0, 0, 1])
    centroid = np.mean(poly, axis=0)

    params = {}
    if angle >= np.deg2rad(args.wall_min_angle) and angle <= np.deg2rad(args.wall_max_angle):        
        label = 'wall'
        params = {'height': args.wall_height}
    else:
        if centroid[1] < args.floor_max_height:
            label = 'floor'
        else:
            label = 'ceiling'

    return label, params

def get_alpha_shape(input_poly, ratio):
    alpha_shape = alphashape.alphashape(input_poly, ratio) # indoor detail convex polygon = 0.7 # convex - concave hull
    # poly3d = scan_to_bim_lib.transform_2d_to_3d(tfInv, poly2d) # for testing
    # print('*alpha shape')
    # print(alpha_shape)

    poly = []
    alpha_type = str(type(alpha_shape))
    print(alpha_type)
    if alpha_type.find('Trimesh') > 0:  # if 3D mesh model
        fig = plt.figure()
        ax = plt.axes(projection='3d')
        ax.plot_trisurf(*zip(*alpha_shape.vertices), triangles=alpha_shape.faces)
        plt.show()
    elif alpha_type.find('MultiPolygon') > 0:  # if 2D multi polygon model
        multipoly = list(alpha_shape)
        poly = None
        for p in multipoly:
            if poly == None:
                poly = list(p.exterior.coords)
            elif len(poly) < len(p.exterior.coords):
                poly = list(p.exterior.coords)
    else:
        poly = list(alpha_shape.exterior.coords)  # if 2D polygon model
    return poly

def transform_3D_to_2D(tf, poly):
    poly4d = scan_to_bim_lib.transform_3d_to_4d(tf, poly)
    poly4d_mean = np.mean(poly4d, axis=0)
    poly2d = scan_to_bim_lib.convert_3d_2d_vector(poly4d)

    return poly2d, poly4d_mean

def transform_2D_to_3D(tf, shp, mean4d):
    shp2d = scan_to_bim_lib.convert_3d_2d_vector(shp)
    obb = scan_to_bim_lib.get_OBB(shp2d)
    vector4d = scan_to_bim_lib.convert_2d_4d_vector(obb)
    mean4d[0] = mean4d[1] = 0
    vector4d = vector4d + mean4d
    tfInv = np.linalg.inv(tf)
    poly4d = np.matmul(vector4d, tfInv) # Y = np.dot(X, tf)
    plane3d = scan_to_bim_lib.convert_4d_3d_vector(poly4d)

    return plane3d, obb

def save_data(outfilename, shp, plane3d, obb):
    fpath = outfilename + '.json'
    scan_to_bim_lib.save_json(fpath, shp) # Bug. alpha_shape shapely Polygon. https://geojson.io/#map=2/20.0/0.0

    fpath = outfilename + '_obb.json'
    scan_to_bim_lib.save_json(fpath, obb) 

    fpath = outfilename + '_plane_3d.xyz'
    scan_to_bim_lib.save_pcd(fpath, plane3d)

def save_mesh_data(fname, plane3d):
    # inner normal vector
    # 3, 2
    # 0, 1
    vertex_N = 8
    vertices = o3d.utility.Vector3dVector(np.array(plane3d))
    triangles = o3d.utility.Vector3iVector(np.array([[0, 2, 1], [2, 4, 1]])) # np.array([[0, 3, 1], [1, 3, 2]]))
    mesh3 = o3d.geometry.TriangleMesh(vertices, triangles)
    mesh3.vertex_colors = o3d.utility.Vector3dVector(np.random.uniform(0, 1, size=(vertex_N, 3)))
    mesh3.compute_vertex_normals()
    o3d.io.write_triangle_mesh(fname + '_plane_3d.ply', mesh3)  

    # mesh test
    '''mesh1 = o3d.geometry.TriangleMesh.create_cylinder()
    mesh1.compute_vertex_normals()
    o3d.io.write_triangle_mesh(fname + '_plane_3d_1.ply', mesh1)    

    mesh2 = o3d.geometry.TriangleMesh.create_cylinder()
    mesh2.compute_vertex_normals()
    mesh2.translate([0.5, 0, 0.2]) 
    o3d.io.write_triangle_mesh(fname + '_plane_3d_2.ply', mesh2)   '''

def show_data(shp, plane3d, obb):
    '''
    fig = plt.figure()
    ax = plt.axes(projection='3d')

    ax.scatter(shp[:,0], shp[:,1], shp[:,2], c="red")
    ax.plot(plane3d[:,0], plane3d[:,1], plane3d[:,2])
    ax.scatter(obb[:,0], obb[:,1], obb[:,2], c="green")
    ax.set_xlim(-40, 40)
    ax.set_ylim(-40, 40)
    ax.set_zlim(-40, 40)

    plt.show()
    '''

def geo_to_obj(infile, outfilename):
    # read file
    ''' poly = read_data(infile)
    label, params = get_obj_type(poly)    

    tf, centroid = scan_to_bim_lib.align_transform_matrix(poly)    # z vector alignment with normal vector of plane based poly
    poly2d, mean4d = transform_3D_to_2D(tf, poly)           # transform 3D to 2D
    bound2d = get_alpha_shape(poly2d, 0) # 0.15) # 0.2)     # alpha shape process
    plane3d, obb = transform_2D_to_3D(tf, bound2d, mean4d)  # transform 2D to 3D with OBB
    '''
    pcd = o3d.io.read_point_cloud(infile)
    poly = np.asarray(pcd.points)
    label, params = get_obj_type(poly)    

    bound2d = get_alpha_shape(poly, 0) # 0.15) # 0.2)
    bound3d = np.asarray(bound2d)
    obb = o3d.geometry.OrientedBoundingBox.create_from_points(pcd.points)
    box3d = obb.get_box_points()
    plane3d = np.asarray(box3d)
    obb3d = np.asarray(box3d)

    # show
    show_data(bound3d, plane3d, obb3d)

    # save file
    save_data(outfilename + "_" + label, bound3d, plane3d, obb3d)

    # save mesh file
    save_mesh_data(outfilename + "_" + label, plane3d)

    return label, plane3d, obb

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    parser.add_argument("--wall_min_angle", type=float, default=30.0, required=True)
    parser.add_argument("--wall_max_angle", type=float, default=150.0, required=True)
    parser.add_argument("--wall_height", type=float, default=3.5, required=True)
    parser.add_argument("--floor_max_height", type=float, default=0.5, required=True)

    global args
    args = parser.parse_args() # ["--input", "/home/ktw/Projects/pcd_pl/output/seg_to_geo", "--output", "/home/ktw/Projects/pcd_pl/output/geo_to_obj"])

    files = glob.glob(args.input + "*.pcd")
    print(files)

    for index, infile in enumerate(files): 
        outfilename = scan_to_bim_lib.get_pcd_index_filepath(args.output, infile, fname_only=True)

        labels = plane3ds = obbs = []
        label, plane3d, obb = geo_to_obj(infile, outfilename)
        labels.append(label)
        plane3ds.append(plane3d)
        obbs.append(obb)

if __name__ == '__main__':
    main()

