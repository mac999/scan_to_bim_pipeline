import sys, os, json, subprocess, argparse, glob
lib_path = os.path.dirname(os.path.abspath(__file__)) + "/../lib"
sys.path.append(lib_path)    
import scan_to_bim_lib

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    parser.add_argument('--pdal_pipeline', type=str, default='pcd_to_dtm_pipeline.json', required=False)   # kept for SBDL compatibility. the pipeline file is written next to the output
    parser.add_argument('--resolution', type=float, default=0.2, required=False)
    parser.add_argument('--classification', type=str, default='building', required=True)
    parser.add_argument('--transform_matrix', type=str, default='1  0  0  0  0  1  0  0  0  0  1  0  0  0  0  1', required=False)   # 4x4 row major, applied by pdal filters.transformation
    parser.add_argument('--gdal_output_type', type=str, default='all', required=False)   # pdal writers.gdal output_type: min, max, mean, idw, count, stdev or all

    args = parser.parse_args() 
    print(f'classification={args.classification} is not applied. the raster is built from all points')

    files = glob.glob(args.input)
    print(files)

    for index, infile in enumerate(files): 
        outfilename = scan_to_bim_lib.get_pcd_index_filepath(args.output, infile, ".tif")
        res = str(args.resolution)

        output_prefix, ext = os.path.splitext(outfilename)
        pdal_pipeline = output_prefix + "_pdal.json"
        temp_las_file = output_prefix + "_transformed.las"
        pipe_data = {
            "pipeline": [
                infile, 
                {
                "type":"filters.transformation",
                "matrix":args.transform_matrix
                }, 
                {
                "type":"writers.las",
                "filename":temp_las_file
                },    
                {
                "filename": outfilename,
                "gdaldriver":"GTiff",
                "output_type":args.gdal_output_type,
                "resolution":res,
                "type": "writers.gdal"
                }        
            ]
        }

        with open(pdal_pipeline, 'w') as f:
            json.dump(pipe_data, f)

        cmd = ["pdal", "pipeline", pdal_pipeline]

        ret = subprocess.call(cmd)
        print(ret)
        if ret != 0:
            sys.exit(ret)

        if os.path.exists(temp_las_file):
            os.remove(temp_las_file)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)
        sys.exit(1)