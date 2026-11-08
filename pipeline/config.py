# title: config for scan to BIM
# author: taewook kang
# version: 1.0.0
# email: laputa99999@gmail.com
# date: 2022.6
import sys, os
import json

# relative paths in config.json are resolved against the repository root, not the current directory
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def resolve_path(path):
    if os.path.isabs(path):
        return path
    resolved = os.path.normpath(os.path.join(root_dir, path))
    if path.endswith('/'):
        resolved += '/'
    return resolved

class config:
    pipeline_fname = ""
    input_path = ""
    output_path = ""

    def load(self, fname):
        print('load config')
        with open(fname, 'r') as f:
            dic = json.load(f)

            for k, v in dic.items():
                if k.endswith('_path') and isinstance(v, str):
                    v = resolve_path(v)
                setattr(config, k, v)
            print(dic)

    def set_pipeline_fname(self, fname):
        config.pipeline_fname = fname

    def get_pipeline_fname(self):
        return config.pipeline_fname

    def set_input_path(self, path):
        config.input_path = path

    def get_input_path(self):
        return config.input_path

    def set_output_path(self, path):
        config.output_path = path

    def get_output_path(self):
        return config.output_path



