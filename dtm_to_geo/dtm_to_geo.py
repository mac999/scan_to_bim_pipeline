# title: dtm_to_geo for scan to BIM
# created date: 2022.6.10, taewook kang, laputa99999@gmail.com

import sys, os, glob, ast, csv, re, json, subprocess, argparse, readline, simplekml, cv2
import numpy as np
import geopandas as gpd
import osgeo.ogr as ogr
import open3d as o3d
import pyvista as pv
from tomlkit import integer
from shapely.geometry import Polygon
from shapely.geometry import MultiPolygon
from shapely import affinity
from rasterstats import zonal_stats
from osgeo import gdal, osr
from ipyleaflet import Map, GeoData, LayersControl
from pyvista import examples
from PIL import Image
import matplotlib.pyplot as plt

lib_path = os.path.dirname(os.path.abspath(__file__)) + "/../lib"
sys.path.append(lib_path)    
import scan_to_bim_lib

args = None

def convert_tiff_png(inputfname, outputfname):
    options_list = [
        '-ot Byte',
        '-of png',
        '-b 1',
        '-scale'
    ]           

    options_string = " ".join(options_list)
        
    gdal.Translate(
        outputfname,
        inputfname,
        options=options_string
    )

def save_elevation_data(infile, outfile):
    gdal.UseExceptions()

    ds = gdal.Open(infile)
    band = ds.GetRasterBand(1)
    elevation = band.ReadAsArray()

    print(elevation.shape)
    print(elevation)

    x0, dx, dxdy, y0, dydx, dy = ds.GetGeoTransform()

    np.save(outfile, elevation)

def save_transform_project_data(infile, outfile):
    # save dtm crs metadata 
    dtm = gdal.Open(infile)
    if dtm == None: 
        return "", ""

    tm = dtm.GetGeoTransform()  # https://gdal.org/tutorials/geotransforms_tut.html
    print(tm)
    json_data = {
        "x": tm[0], 
        "pixel_width": tm[1],
        "row_rotation": tm[2],
        "y": tm[3],
        "col_rotation": tm[4],
        "pixel_height": tm[5]
    }

    transform_json_file = outfile + "_transform.json"
    with open(transform_json_file, 'w') as f:
        json.dump(json_data, f)

    proj_data = dtm.GetProjectionRef()
    proj = osr.SpatialReference(wkt=proj_data)
    proj = proj.GetAttrValue('AUTHORITY',1)
    print(proj_data)
    projection_file = outfile + "_projection.txt"
    with open(projection_file, 'w') as f:
        f.write(proj_data)
    del dtm

    return transform_json_file, projection_file, tm, proj, proj_data

def save_shp(out_fname, polygons, transform_json_file, projection_file, tm, proj, proj_data):
    # https://gis.stackexchange.com/questions/392515/create-a-shapefile-from-geometry-with-ogr
    # https://gis.stackexchange.com/questions/264618/reprojecting-and-saving-shapefile-in-gdal

    try:
        tm = []
        proj_data = ""
        with open(transform_json_file, 'r') as f:
            data = json.load(f)
            for v in data:
                tm.append(data[v])
        with open(projection_file, 'r') as f:
            text = f.read()
            proj_data = text

        shapes = []    
        for i in range(len(polygons)):
            polygon = polygons[i]

            if isinstance(polygon, MultiPolygon):
                max_p = None
                for p in polygon:
                    if max_p == None:
                        max_p = p
                    if max_p.area < p.area:
                        max_p = p
                polygon = max_p

            x, y = polygon.exterior.coords.xy

            coords = np.array([x, y])
            points_2d = coords.T  # shape (N, 2)
            for p in points_2d: 
                p[0] = p[0] * tm[1] + tm[0]    # points_3d[0] = points_3d[0] + tm[0] # + Xpixel * (1.0 / tm[1]) + Yline * tm[2]
                p[1] = p[1] * tm[5] + tm[3]    # points_3d[1] = points_3d[1] + tm[3] # + Xpixel * (1.0 / tm[1]) + Yline * tm[5]
            N = len(points_2d)

            # embed in 3d, create filled polygon, extrude it
            points_3d = np.pad(points_2d, [(0, 0), (0, 1)])  # shape (N, 3)

            face = [N + 1] + list(range(N)) + [0]  # cell connectivity for a single cell
            polygon = pv.PolyData(points_3d, faces=face)

            line_string = ogr.Geometry(ogr.wkbLinearRing)   # https://pcjericks.github.io/py-gdalogr-cookbook/geometry.html

            for p in points_3d:
                line_string.AddPoint(p[0], p[1])    
            shapes.append(line_string)
                
        driver = ogr.GetDriverByName("ESRI Shapefile")    # ("GTiff")  # ("HFA") # Get a handler to a driver
        dataset_out = driver.CreateDataSource(out_fname)

        ref = osr.SpatialReference()
        ref.ImportFromEPSG(int(proj))    # 25832

        layer = dataset_out.CreateLayer("data", ref, ogr.wkbPolygon)

        id_field = ogr.FieldDefn("id", ogr.OFTInteger)
        layer.CreateField(id_field)
        # elev_field = ogr.FieldDefn("Elevation", ogr.OFSTFloat32)
        # layer.CreateField(elev_field)

        featureDefn = layer.GetLayerDefn()
        # Create the feature and set values    
        for index, s in enumerate(shapes):
            poly = ogr.Geometry(ogr.wkbPolygon) 
            poly.AddGeometry(s)

            feature = ogr.Feature(featureDefn)
            feature.SetGeometry(poly)
            feature.SetField("id", index)
            # feature.SetField("Elevation", 11.0)
            layer.CreateFeature(feature)

            feature = None
        dataset_out = None

    except BaseException as err:
        print(err)    

def get_elevation_from_area(elev_map, poly):
    try:
        # stat = zonal_stats(vectors = poly, raster = tif_file, stats='mean')

        if isinstance(poly, MultiPolygon):
            max_p = None
            for p in poly:
                if max_p == None:
                    max_p = p
                if max_p.area < p.area:
                    max_p = p
            poly = max_p

        t = 0.0
        max_height = 0.0
        x, y = poly.exterior.coords.xy
        z = np.where(elev_map >= 0.0, elev_map, 0.0)

        rows = len(elev_map)
        columns = len(elev_map[0])
        count = len(x)
        for i in range(count):
            height = 0.0
            vx = int(x[i])
            vy = int(y[i])  # vy = rows - vy
            if vy < rows and vx < columns:
                height = elev_map[vy, vx]
            if height <= -99:
                continue
            if max_height < height:
                max_height = height

            count = count + 1
            t = t + height
        if count == 0:
            return 0.0
        return max_height # t / count
    except BaseException as err:
        print(err)

    return 0.0

def get_elevation_from_map(tif_file, elev_map, polygon):
    poly1 = polygon.buffer(-5.0, resolution=16, join_style=2, mitre_limit=1)
    height1 = get_elevation_from_area(elev_map, poly1)

    poly2 = polygon.buffer(10.0, resolution=16, join_style=2, mitre_limit=1)
    height2 = get_elevation_from_area(elev_map, poly2)

    return np.abs(height1 - height2)

def save_mesh(tif_file, out_fname, polygons, depth_img, transform_json_file, projection_file, tm, elevation_file):
    try:
        if len(polygons) == 0:
            return
        
        elev_map = np.load(elevation_file + ".npy")

        # print(os. getcwd())
        # tex = None
        # image = cv2.imread("tex_brick.png") #, mode='RGB')
        # if image.size > 0:
        #    print(type(image))
        #    tex = pv.numpy_to_texture(image)

        meshes = []    
        for i in range(len(polygons)):
            polygon = polygons[i]

            x, y = polygon.exterior.coords.xy
            height = get_elevation_from_map(tif_file, elev_map, polygon)

            coords = np.array([x, y])
            points_2d = coords.T  # shape (N, 2)
            for p in points_2d: 
                p[0] = p[0] * tm[1] # points_3d[0] = points_3d[0] + tm[0] # + Xpixel * (1.0 / tm[1]) + Yline * tm[2]
                p[1] = p[1] * tm[5] # points_3d[1] = points_3d[1] + tm[3] # + Xpixel * (1.0 / tm[1]) + Yline * tm[5]
            N = len(points_2d)

            # embed in 3d, create filled polygon, extrude it
            points_3d = np.pad(points_2d, [(0, 0), (0, 1)])  # shape (N, 3)
            face = [N + 1] + list(range(N)) + [0]  # cell connectivity for a single cell
            polygon = pv.PolyData(points_3d, faces=face)

            obj = polygon.extrude((0, 0, height), capping=True)   # extrude along z and plot
            
            # obj.textures['tex'] = pv.numpy_to_texture(image)
            # obj.texture_map_to_plane(use_bounds=True, inplace=True)
            # obj.plot(color='white', specular=1, screenshot='extruded.png')
            # obj.plot(color='red')

            meshes.append(obj)

        mesh = pv.PolyData()
        merged_mesh = mesh.merge(meshes)
        merged_mesh.save(out_fname)

        # elevation view
        '''
        rows = elev_map.shape[0]
        z = np.where(elev_map >= 0.0, elev_map, 0.0)
        for i in range(len(polygons)):
            polygon = polygons[i]
            poly = polygon.buffer(-5.0, resolution=16, join_style=2, mitre_limit=1)
            if isinstance(poly, MultiPolygon):
                max_p = None
                for p in poly:
                    if max_p == None:
                        max_p = p
                    if max_p.area < p.area:
                        max_p = p
                poly = max_p

            x, y = poly.exterior.xy
            y2 = y # [(y1 - rows) * -1.0 for y1 in y]
            plt.plot(x, y2)
            
        plt.imshow(z, 'Greys_r')    # cmap='Reds') # 
        plt.show()
        
        # 3D view
        p = pv.Plotter()
        camera = pv.Camera()
        p.camera = camera
        p.camera.position = (0.0, 0.0, 200.0)
        p.camera.focal_point = (0.0, 0.0, 0.0)
        p.camera.up = (0.0, 1.0, 0.0)
        # p.camera.zoom(1.4)

        p.add_mesh(merged_mesh, smooth_shading = False) # , texture = tex)    
        p.show_axes()
        p.show()
        '''
    except Exception as e:
        print(e)

def rotate_image(img, angle):
    if img == None:
        return

    (h, w) = img.shape[:2]
    (cX, cY) = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D((cX, cY), angle, 1.0)
    rot_img = cv2.warpAffine(img, M, (w, h))
    cv2.imshow("Rotated by -90 Degrees", rot_img)

    return rot_img

def save_geojson(outfile, shp_fname, csv_fname):
    shp_file = gpd.read_file(shp_fname)
    shp_file.to_file(outfile, driver='GeoJSON')

def save_dataset(tif_file, outfile, polygons, tm, elevation_file): 
    datafile = open(outfile, 'w', newline='')
    if datafile == None:
        return

    writer = csv.writer(datafile) # delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['ID', 'type', 'area', 'length', 'elevation', 'pos_x', 'pos_y', 'footprint'])

    elev_map = np.load(elevation_file + ".npy")

    for i in range(len(polygons)):
        polygon = polygons[i]

        x, y = polygon.exterior.coords.xy
        height = get_elevation_from_map(tif_file, elev_map, polygon)

        footprint = []       
        coords = np.array([x, y])
        points_2d = coords.T  # shape (N, 2)
        for p in points_2d: 
            p[0] = p[0] * tm[1] + tm[0]    # points_3d[0] = points_3d[0] + tm[0] # + Xpixel * (1.0 / tm[1]) + Yline * tm[2]
            p[1] = p[1] * tm[5] + tm[3]    # points_3d[1] = points_3d[1] + tm[3] # + Xpixel * (1.0 / tm[1]) + Yline * tm[5]
            footprint.append((p[0], p[1]))
        N = len(points_2d)

        poly_footprint = Polygon(footprint)
        area = poly_footprint.area
        length = poly_footprint.length
        pos_x = poly_footprint.centroid.coords.xy[0][0]
        pos_y = poly_footprint.centroid.coords.xy[1][0]

        writer.writerow([i, 'building', area, length, height, pos_x, pos_y, footprint])

    datafile.close()

def create_geometry_from_dtm(infile, outfile):
    # load
    transform_json_file, projection_file, tm, proj, proj_data = save_transform_project_data(infile, outfile)    # clone_tiff('/home/ktw/Projects/pcd_pl/dtm_to_geo/dtm_im.tif', '/home/ktw/Projects/pcd_pl/dtm_to_geo/dtm_im_clone.tif')
    save_elevation_data(infile, outfile + "_elevation")
    convert_tiff_png(infile, outfile + ".png")   # '/home/ktw/Projects/pcd_pl/dtm_to_geo/dtm_im.tif', '/home/ktw/Projects/pcd_pl/dtm_to_geo/dtm_im.png')

    # generate contour
    img = cv2.imread(outfile + ".png")  # flip = cv2.flip(img, 0)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret, binary = cv2.threshold(gray, args.extract_pixel_min_value, args.extract_pixel_max_value, 0) 

    contours, h = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # https://opencv-python.readthedocs.io/en/latest/doc/15.imageContours/imageContours.html
    image = cv2.drawContours(img, contours, -1, (0,255,0), 1)

    # simplification
    poly_objs = []
    for i in range(len(contours)):
        if (i > 0) and (len(contours[i])) > 2:
            xy = np.squeeze(contours[i])
            poly = Polygon(xy)
            area = poly.area
            scale_ratio = abs(tm[1] * tm[5])
            if area <= (args.remove_area / scale_ratio):
                continue
            poly_objs.append(poly)

    print("Result = ", len(poly_objs))
    polygons = gpd.GeoDataFrame(poly_objs, columns = ['geometry'])
    polygons = polygons.simplify(args.simplify_factor)    # shapely, https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoSeries.simplify.html

    # save
    save_shp(outfile + ".shp", polygons, transform_json_file, projection_file, tm, proj, proj_data)     # save_shp_with_elevation("/home/ktw/Projects/pcd_pl/output/volcano_data.txt", "/home/ktw/Projects/pcd_pl/output/volcano_elev.shp")
    save_mesh(infile, outfile + ".ply", polygons, img, transform_json_file, projection_file, tm, outfile + "_elevation")
    save_dataset(infile, outfile + '_' + args.output_dataset, polygons, tm, outfile + "_elevation")
    save_geojson(outfile + ".geojson", outfile + '.shp', outfile + '_' + args.output_dataset)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    parser.add_argument('--simplify_factor', type=float, default=10.0, help='simplication factor')
    parser.add_argument('--remove_area', type=float, default=20.0, required=True)
    parser.add_argument('--extract_pixel_min_value', type=int, default=60, required=True)
    parser.add_argument('--extract_pixel_max_value', type=int, default=200, required=True)
    parser.add_argument('--output_dataset', type=str, default="dataset.csv", required=False)  # TBD    
    parser.add_argument('--output_pset', type=str, default="json", required=False)  # TBD

    global args
    args = parser.parse_args() 

    files = glob.glob(args.input + '*.tif')
    print(files)

    for index, infile in enumerate(files): 
        outfilename = scan_to_bim_lib.get_pcd_index_filepath(args.output, infile)        

        outfile, file_extension = os.path.splitext(outfilename) 
        create_geometry_from_dtm(infile, outfile)

if __name__ == "__main__":
    main()
