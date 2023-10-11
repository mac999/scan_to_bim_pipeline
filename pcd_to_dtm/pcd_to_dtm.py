import sys, os, io, json, subprocess, argparse, readline, glob, re
lib_path = os.path.dirname(os.path.abspath(__file__)) + "/../lib"
sys.path.append(lib_path)    
import scan_to_bim_lib

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    parser.add_argument('--pdal_pipeline', type=str, default='pcd_to_dtm_pipeline.json', required=True)
    parser.add_argument('--resolution', type=float, default=0.2, required=False)
    parser.add_argument('--classification', type=str, default='building', required=True)

    args = parser.parse_args() 

    files = glob.glob(args.input)
    print(files)

    for index, infile in enumerate(files): 
        outfilename = scan_to_bim_lib.get_pcd_index_filepath(args.output, infile, ".tif")
        res = str(args.resolution)

        temp_las_file = "pcd_to_dtm_transformed.las"
        pipe_data = {
            "pipeline": [
                infile, 
                {
                "type":"filters.transformation",
                "matrix":"1  0  0  0  0  1  0  0  0  0  1  0  0  0  0  1"
                }, 
                {
                "type":"writers.las",
                "filename":temp_las_file
                },    
                {
                "filename": outfilename,
                "gdaldriver":"GTiff",
                "output_type":"all",
                "resolution":res,
                "type": "writers.gdal"
                }        
            ]
        }

        with open(args.pdal_pipeline, 'w') as f:
            json.dump(pipe_data, f)

        cmd = ["pdal", "pipeline", args.pdal_pipeline]

        ret = subprocess.call(cmd) 
        print(ret)

        os.remove(temp_las_file)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)