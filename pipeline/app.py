import sys
import os
from yaml import parse
import pipeline
import argparse, readline
import config
import json
import shutil
import re

parser = args = None

# define app
class application:
    pipes = None

    def __init__(self, name):
        self.name = name
        self.config = config.config()
        self.pipes = list()

    def load(self, pipeline_name = "*"):
        self.config.load(args.config) # '/home/ktw/Projects/pcd_pl/pipeline/config.json'
        self.config.set_pipeline_fname(args.pipeline) # '/home/ktw/Projects/pcd_pl/pipeline/scan_to_bim_test.json'
        if args.input != None:
            self.config.set_input_path(args.input)
        if args.output != None:
            self.config.set_output_path(args.output)
            fname = os.path.basename(args.pipeline)
            shutil.copyfile(args.pipeline, args.output + fname)

        if len(sys.argv) >= 2:
            self.config.set_pipeline_fname(sys.argv[1])

        print('load pipeline')
        with open(args.pipeline, 'r') as f:
            self.pipeline_config = json.load(f)
            print(self.pipeline_config)
                
            for p in self.pipeline_config:
                print(p)

                find = re.search(p, pipeline_name) 
                if find == None:
                    continue

                pipe = pipeline.pipeline(p, self.config)
                pipe.load(args.pipeline)
                self.pipes.append(pipe)

    def run(self):
        for p in self.pipes:
            p.run()

        print('exit pipeline...')

def main():
    # load argument
    try:
        global parse, args
        
        parser = argparse.ArgumentParser()
        parser.add_argument('--config', type=str, required=True)
        parser.add_argument('--pipeline', type=str, required=True)
        parser.add_argument('--input', type=str, required=True)
        parser.add_argument('--output', type=str, required=True)
        args = parser.parse_args(["--config", "/home/ktw/Projects/pcd_pl/pipeline/config.json", "--pipeline", "/home/ktw/Projects/pcd_pl/pipeline/scan_to_bim_test.json", "--input", "/home/ktw/Projects/pcd_pl/input/PUNK*.las", "--output", "/home/ktw/Projects/pcd_pl/output/"])

        # args.config = '/home/ktw/Projects/pcd_pl/pipeline/config.json'
        # args.pipeline = '/home/ktw/Projects/pcd_pl/pipeline/scan_to_bim_test.json'
        # args.input = '/home/ktw/Projects/pcd_pl/data/MapData_3_15_indoor_c.pcd'
    except Exception as e:
        print(e.__cause__)
        pass

    # run app
    app = application("pcd_pipeline_app")
    app.load("pipeline.outdoor_ground")
    app.run()

if __name__ == "__main__":
    main()