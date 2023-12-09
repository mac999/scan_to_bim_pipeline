# title: config for scan to BIM
# author: taewook kang
# version: 1.0.0
# email: laputa99999@gmail.com
# date: 2022.6
import sys
import json
from sympy import root

class config:
    pipeline_fname = ""
    input_path = ""
    output_path = ""

    def load(self, fname):
        print('load config')
        with open(fname, 'r') as f:
            dic = json.load(f)

            for k, v in dic.items():
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



