# title: scan_to_bim_lib for scan to BIM
# created date: 2022.6, taewook kang, laputa99999@gmail.com

import os, math
import numpy as np
from sklearn.decomposition import PCA # as RandomizedPCA

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
 
def get_normal_vector(pcd):
  pca = PCA(n_components=3)
  pca.fit(pcd)
  eig_vec = pca.components_
  normal = eig_vec[2, :]  # (a, b, c)

  return normal

def dotproduct(v1, v2):
  return sum((a*b) for a, b in zip(v1, v2))

def length(v):
  return math.sqrt(dotproduct(v, v))

def get_angle_between_vector(v, base = [0, 0, 1]):
  cos_angle = dotproduct(v, base) / (length(v) * length(base))
  cos_angle = max(-1.0, min(1.0, cos_angle))  # clamp against floating point error
  return math.acos(cos_angle)

def read_point_cloud(fname):
  # open3d does not read las/laz, so those go through laspy
  import open3d as o3d
  if os.path.splitext(fname)[1].lower() not in ('.las', '.laz'):
    return o3d.io.read_point_cloud(fname)
  import laspy
  las = laspy.read(fname)
  pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(np.c_[las.x, las.y, las.z]))
  if 'red' in las.point_format.dimension_names:
    rgb = np.c_[las.red, las.green, las.blue].astype(float)
    pcd.colors = o3d.utility.Vector3dVector(rgb / (65535.0 if rgb.max() > 255 else 255.0))
  return pcd
