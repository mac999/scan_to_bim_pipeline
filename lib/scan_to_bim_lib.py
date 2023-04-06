# title: scan_to_bim_lib for scan to BIM
# created date: 2022.6, taewook kang, laputa99999@gmail.com

import os, sys, json, math, re, glob, subprocess, argparse, readline
import cv2, trimesh
import geopandas as gpd
import numpy as np
import sympy as sp
import matplotlib.pyplot as plt
from shapely.geometry import Polygon
from sys import base_exec_prefix
from sklearn.decomposition import PCA # as RandomizedPCA
from scipy.linalg import norm
from mpl_toolkits.mplot3d import Axes3D

def get_file_index(infile):
  filename, file_extension = os.path.splitext(infile) 
  index1 = infile.rfind('_@')
  if index1 < 0:
    return -1
  index2 = len(filename)
  if len(file_extension) > 0:
    index2 = infile.rfind(file_extension)
  if index2 < 0:
    return -1
  index = filename[index1 + 2: index2]

  return int(index)

def get_pcd_index_filepath(outputpath, infile, ext = ""):
  filename, file_extension = os.path.splitext(infile)
  if len(ext):
    file_extension = ext 

  index = get_file_index(filename)
  if index >= 0:
      outfilename = outputpath + "_@" + str(index) + file_extension
  else:
      outfilename = outputpath + file_extension

  return outfilename

def save_json(fname, poly, baseX = 0, baseY = 0, scale = 1):
  with open(fname, 'w') as f:
    # json.dump(g[0], dst)
    f.write('{')
    f.write('"type": "MultiPolygon", ')
    f.write('"coordinates": [[[')
    j = 0

    for p in poly:
      x = (p[0] - baseX) * scale
      y = (p[1] - baseY) * scale
      f.write('[' + str(x) + ',' + str(y) + ']')
      if j == len(poly) - 1:
        continue
      j = j + 1
      f.write(',')

    f.write(']]]')
    f.write('}')

def save_pcd(fname, poly3d, baseX = 0, baseY = 0, baseZ = 0, scale = 1):
  j = 0

  with open(fname, 'w') as f:
    for p in poly3d:
      x = (p[0] - baseX) * scale
      y = (p[1] - baseY) * scale
      z = (p[2] - baseZ) * scale
      f.write(str(x) + ',' + str(y) + ',' + str(z) + '\n')
      if j == len(poly3d) - 1:
        continue
      j = j + 1
 
# 3D plane > 2D. https://math.stackexchange.com/questions/180418/calculate-rotation-matrix-to-align-vector-a-to-vector-b-in-3d  https://www.itread01.com/content/1547079251.html  https://math.stackexchange.com/questions/180418/calculate-rotation-matrix-to-align-vector-a-to-vector-b-in-3d
def rotation_4x4matrix_from_vectors(vec1, vec2, origin):
  a, b = (vec1 / np.linalg.norm(vec1)).reshape(3), (vec2 / np.linalg.norm(vec2)).reshape(3)
  v = np.cross(a, b)
  s = np.linalg.norm(v)
  c = np.dot(a, b)
  kmat = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
  I = np.eye(3)
  rotation_matrix = I + kmat + kmat.dot(kmat) * ((1 - c) / (s ** 2))

  r2 = []
  for v in rotation_matrix:
      v2 = []
      v2.append(v[0])
      v2.append(v[1])
      v2.append(v[2])
      v2.append(0.0)
      r2.append(v2)
  v2 = []
  v2.append(-origin[0])
  v2.append(-origin[1])
  v2.append(-origin[2])
  v2.append(1)
  r2.append(v2)

  return np.array(r2)

def get_normal_vector(pcd):
  pca = PCA(n_components=3)
  pca.fit(pcd)
  eig_vec = pca.components_
  normal = eig_vec[2, :]  # (a, b, c)

  return normal

def align_transform_matrix(X, base_vector = [0, 0, 1]):
  origin = X[0]

  normal = get_normal_vector(X)  
  centroid = np.mean(X, axis=0)

  tf = rotation_4x4matrix_from_vectors(normal, base_vector, origin)

  return tf, centroid

def convert_2d_4d_vector(vec2d): 
    vec4d = []
    for v in vec2d:
        v4d = []
        v4d.append(v[0])
        v4d.append(v[1])
        v4d.append(0.0)
        v4d.append(0.0)
        vec4d.append(v4d)
    return vec4d

def convert_3d_4d_vector(vec3d): 
    vec4d = []
    for v in vec3d:
        v4d = []
        v4d.append(v[0])
        v4d.append(v[1])
        v4d.append(v[2])
        v4d.append(0.0)
        vec4d.append(v4d)
    return vec4d

def convert_4d_3d_vector(vec4d):
    vec3d = []
    for v in vec4d:
        v3d = []
        v3d.append(v[0])
        v3d.append(v[1])
        v3d.append(v[2])
        vec3d.append(v3d)
    return vec3d

def convert_3d_2d_vector(vec3d): 
    vec2d = []
    for v in vec3d:
        v2d = []
        v2d.append(v[0])
        v2d.append(v[1])
        vec2d.append(v2d)
    return vec2d

def convert_2d_3d_vector(vec2d): 
    vec3d = []
    for v in vec2d:
        v3d = []
        v3d.append(v[0])
        v3d.append(v[1])
        vec3d.append(v3d)
    return vec3d

def transform_3d_to_4d(tf, X_3d):
  X2 = convert_3d_4d_vector(X_3d)
  Y = np.matmul(X2, tf) # Y = np.dot(X, tf)
  return Y

def transform_3d_to_2d(tf, X_3d):
  X2 = convert_3d_4d_vector(X_3d)
  Y = np.matmul(X2, tf) # Y = np.dot(X, tf)

  Y2 = convert_3d_2d_vector(Y)
  return Y2

def transform_2d_to_3d(tf, X_2d):
  X2 = convert_2d_4d_vector(X_2d)
  Y = np.matmul(X2, tf) # Y = np.dot(X, tf)

  Y2 = convert_4d_3d_vector(Y)
  return Y2

def get_OBB(vector_2d):
  a  = np.array(vector_2d) # ([(3.7, 1.7), (4.1, 3.8), (4.7, 2.9), (5.2, 2.8), (6.0,4.0), (6.3, 3.6), (9.7, 6.3), (10.0, 4.9), (11.0, 3.6), (12.5, 6.4)])
  ca = np.cov(a,y = None,rowvar = 0,bias = 1)

  v, vect = np.linalg.eig(ca)
  tvect = np.transpose(vect)

  fig = plt.figure(figsize=(12,12))
  ax = fig.add_subplot(111)
  ax.scatter(a[:,0],a[:,1])

  #use the inverse of the eigenvectors as a rotation matrix and rotate the points so they align with the x and y axes
  ar = np.dot(a,np.linalg.inv(tvect))

  # get the minimum and maximum x and y 
  mina = np.min(ar,axis=0)
  maxa = np.max(ar,axis=0)
  diff = (maxa - mina)*0.5

  # the center is just half way between the min and max xy
  center = mina + diff

  #get the 4 corners by subtracting and adding half the bounding boxes height and width to the center
  corners = np.array([center + [-diff[0], -diff[1]], center + [diff[0],-diff[1]], center + [diff[0],diff[1]], center + [-diff[0],diff[1]], center + [-diff[0], -diff[1]]])

  #use the the eigenvectors as a rotation matrix and rotate the corners and the centerback
  corners = np.dot(corners,tvect)
  center = np.dot(center,tvect)

  ax.scatter([center[0]],[center[1]])    
  ax.plot(corners[:,0],corners[:,1],'-')

  plt.axis('equal')
  plt.show()

  return list(corners)

def unit_vector(vector):
    return vector / np.linalg.norm(vector)

def dotproduct(v1, v2):
  return sum((a*b) for a, b in zip(v1, v2))

def length(v):
  return math.sqrt(dotproduct(v, v))

def get_angle_between_vector(v, base = [0, 0, 1]):
  return math.acos(dotproduct(v, base) / (length(v) * length(base)))

def intersect_plane(p1, p2):
  a = sp.Plane(sp.Point3D(p1[0]), sp.Point3D(p1[1]), sp.Point3D(p1[2]))
  b = sp.Plane(sp.Point3D(p2[0]), sp.Point3D(p2[1]), sp.Point3D(p2[2]))

  int_line = a.intersection(b)
  return int_line

  """
  a, b   4-tuples/lists
         Ax + By +Cz + D = 0
         A,B,C,D in order  

  output: 2 points on line of intersection, np.arrays, shape (3,)
  """
  ''' a_vec, b_vec = np.array(a[:3]), np.array(b[:3])

  aXb_vec = np.cross(a_vec, b_vec)

  A = np.array([a_vec, b_vec, aXb_vec])
  d = np.array([-a[3], -b[3], 0.]).reshape(3,1)

  p_inter = np.linalg.solve(A, d).T

  return p_inter[0], (p_inter + aXb_vec)[0]'''


# https://github.com/stevenellisd/gtiff2png/blob/master/gtiff2png.py
def conv_geotiff_png_for_WGS84_googlemap(inputfile, outputfile):
  inputfilename = inputfile
  basefilename = outputfile
  textoutput = open(basefilename+".latlng", "w")
  if textoutput == None:
      return

  from osgeo import gdal, osr

  ds = gdal.Open(inputfilename)
  if ds == None:
      return

  old_cs = osr.SpatialReference()
  old_cs.ImportFromWkt(ds.GetProjectionRef())

  # create the new coordinate system, wgs84 AKA latitude/longitude which Google Maps requires
  wgs84_wkt = """
  GEOGCS["WGS 84",
      DATUM["WGS_1984",
          SPHEROID["WGS 84",6378137,298.257223563,
              AUTHORITY["EPSG","7030"]],
          AUTHORITY["EPSG","6326"]],
      PRIMEM["Greenwich",0,
          AUTHORITY["EPSG","8901"]],
      UNIT["degree",0.01745329251994328,
          AUTHORITY["EPSG","9122"]],
      AUTHORITY["EPSG","4326"]]"""
  new_cs = osr.SpatialReference()
  new_cs.ImportFromWkt(wgs84_wkt)

  transform = osr.CoordinateTransformation(old_cs, new_cs)    # create a transform object to convert between coordinate systems

  width = ds.RasterXSize
  height = ds.RasterYSize
  gt = ds.GetGeoTransform()

  minx = gt[0]
  maxx = gt[0] + width*gt[1] + height*gt[2]
  miny = gt[3] + width*gt[4] + height*gt[5]
  maxy = gt[3]

  latlong = transform.TransformPoint(minx,miny)
  latlong2 = transform.TransformPoint(maxx,maxy)

  #write coordinates to file
  textoutput.write(str(latlong[1]))
  textoutput.write("\n")
  textoutput.write(str(latlong[0]))
  textoutput.write("\n")
  textoutput.write(str(latlong2[1]))
  textoutput.write("\n")
  textoutput.write(str(latlong2[0]))
  textoutput.write("\n")
  textoutput.close()

  color = open("color", "w")
  color.write("0% 0 0 0\n100% 255 255 255\n")
  color.close()

  os.system("gdaldem color-relief " + inputfilename + " color " + basefilename + ".png -of png")
