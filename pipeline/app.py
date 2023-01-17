# title: application for scan to BIM
# created date: 2022.6, taewook kang, laputa99999@gmail.com

import sys, os, re, argparse, readline, json, glob, shutil
from yaml import parse
import pipeline, config

# define app
class application:
    pipes = None

    def __init__(self, name):
        self.name = name
        self.config = config.config()
        self.pipes = list()

    def load(self, args, json_pipeline, pipeline_stage, input_file, output_file):
        if args == None:
            return 

        self.config.load(args.config) # '/home/ktw/Projects/pcd_pl/pipeline/config.json'
        self.config.set_pipeline_fname(json_pipeline) # '/home/ktw/Projects/pcd_pl/pipeline/scan_to_bim_test.json'
        if input_file != None:
            self.config.set_input_path(input_file)
        if output_file != None:
            self.config.set_output_path(output_file)
            fname = os.path.basename(json_pipeline)
            try:
                os.makedirs(output_file)
            except Exception as e:
                pass
            shutil.copyfile(json_pipeline, output_file + fname)

        print('load pipeline')
        with open(json_pipeline, 'r') as f:
            self.pipeline_config = json.load(f)
            # print(self.pipeline_config)
                
            for p in self.pipeline_config:
                # print(p)

                find = re.search(pipeline_stage, p) 
                if find == None:
                    continue

                pipe = pipeline.pipeline(p, self.config)
                pipe.load(json_pipeline)
                self.pipes.append(pipe)

    def run(self):
        for p in self.pipes:
            p.run()

        print('exit pipeline...')

def process_multiple_pipeline(args):
    print('Begin processing multiple files...\n')

    files = glob.glob(args.input_path)
    print(files)

    for file in files:
        path = os.path.dirname(file)
        name, ext = os.path.splitext(os.path.basename(file))
        print(f'\n\n* Processing pipline of {name}...\n')

        if args.pipeline != None and args.pipeline != "":
            json_pipeline = args.pipeline
        else:
            json_pipeline = path + '/' + name + '_' + args.pipeline_tag
        output = args.output_path + name + '/'

        app = application("pcd_pipeline_app")
        app.load(args, json_pipeline, args.stage, file, output)
        app.run()

    print('End processing.')


def main():
    # load argument 
    try:        
        parser = argparse.ArgumentParser()
        parser.add_argument('--config', type=str, default="/home/ktw/projects/pcd_pl/pipeline/config.json", required=False)
        parser.add_argument('--pipeline', type=str, default='', required=False)
        parser.add_argument('--pipeline_tag', type=str, default='scan_to_bim.json', required=False)
        parser.add_argument('--stage', type=str, default='.*', required=False)
        parser.add_argument('--input_path', type=str, default='/home/ktw/projects/pcd_pl/input/*.las', required=False)
        parser.add_argument('--output_path', type=str, default='/home/ktw/projects/pcd_pl/output/', required=False)
        args = parser.parse_args() # ["--config", "/home/ktw/projects/pcd_pl/pipeline/config.json", "--pipeline", json_pipeline, "--input", file, "--output", output])

        process_multiple_pipeline(args)    
    except Exception as e:
        print(e)
        pass

if __name__ == "__main__":
    main()