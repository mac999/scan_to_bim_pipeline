import sys
import json
from sympy import root

class config:
    root = ""
    data_path = ""
    bin_path = ""
    data_path = ""
    input_path = ""
    output_path = ""
    pipeline_fname = ""

    def load(self, fname):
        print('load config')
        with open(fname, 'r') as f:
            dic = json.load(f)
            config.root = dic['root_path']
            config.bin_path = dic['bin_path']
            config.lib_path = dic['lib_path']
            config.data_path = dic['data_path']

            print(dic)
            
    def get_root(self):
        return config.root

    def get_bin_path(self):
        return config.bin_path
    
    def get_data_path(self):
        return config.data_path

    def set_pipeline_fname(self, fname):
        config.pipeline_fname = fname

    def get_pipeline_fname(self):
        return config.pipeline_fname

    def set_input_path(self, path):
        config.input_path = path

    def get_input_path(self):
        return config.input_path

    def get_output_path(self):
        return config.output_path

    def set_output_path(self, path):
        config.output_path = path


