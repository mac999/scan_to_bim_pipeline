import sys, os, io, json, subprocess, argparse, readline, glob, re
lib_path = os.path.dirname(os.path.abspath(__file__)) + "/../lib"
sys.path.append(lib_path)    
import scan_to_bim_lib

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    parser.add_argument('--output_type', type=str, required=True)
    args = parser.parse_args() 

    files = glob.glob(args.input)
    print(files)

    output_fname, ext = os.path.splitext(args.output)

    for index, infile in enumerate(files): 
        outfilename = scan_to_bim_lib.get_pcd_index_filepath(args.output, infile, args.output_type)

        pipe_data = {
            "pipeline": [
                infile, 
                {
                    "type":"filters.transformation",
                    "matrix":"1  0  0  0  0  1  0  0  0  0  1  0  0  0  0  1"
                }, 
                {
                    "type":"writers" + args.output_type,
                    "filename":outfilename
                }
            ]
        }

        pdal_pipeline = output_fname + "_pdal.json"
        with open(pdal_pipeline, 'w') as f:
            json.dump(pipe_data, f)

        cmd = ["pdal", "pipeline", pdal_pipeline]

        ret = subprocess.call(cmd) 
        print(ret)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)