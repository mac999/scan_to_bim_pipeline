# Title: Scan to BIM pipieline
# Programmer: Kang Taewook
# Date: 2022.6.1
import sys
import json
import subprocess
import config
import glob
import re

conf = config.config()

class pipeline_stage:
    name = None
    pipe = None
    stage_config = None
    active_run = True
    def __init__(self, pipe_obj, name):
        self.name = name
        self.pipe = pipe_obj

    def get_stage_config_params(self):
        input = output = filter_type = model = ""

        if self.stage_config == None:
            return input, output, filter_type, model

        input = self.stage_config.get('input')
        output = self.stage_config.get('output')
        filter_type = self.stage_config.get('type')
        if input == None or output == None or filter_type == None:
            return input, output, filter_type, model
        model = self.stage_config.get('model')
        if model == None:
            model = ""

        program_path = conf.get_bin_path() + self.name
        output_fname_tag = output + self.name

        return program_path, input, output, output_fname_tag, filter_type, model

    def init(self, input_path = None):
        print(self.name)

        self.stage_config = self.pipe.get_stage_config(self.name)
        if self.stage_config != None:
            self.stage_config['input'] = conf.get_input_path()
            self.stage_config['output'] = conf.get_output_path()

        self.stage_config['input'] = input_path
        
    def set_input_path(self, path):
        self.stage_config['input'] = path

    def set_output_path(self, path):
        self.stage_config['output'] = path

    def set_active_run(self, flag):
        self.active_run = flag

    def get_active_run(self):
        return self.active_run

    def run(self):
        program_path, input, output, output_fname_tag, filter_type, model = self.get_stage_config_params()
        if self.active_run == False:
            return output_fname_tag

        app_conf = self.pipe.get_app_config()
        root_path = app_conf.get_root()

        cmd = ["python", program_path + ".py", "--input", input, "--output", output_fname_tag]

        for param in self.stage_config:
            if param == "type" or param == "module" or param == "input" or param == "output":
                continue
            value = str(self.stage_config[param])
            if param == "pdal_pipeline":
                value = root_path + value
            cmd.append("--" + param)
            cmd.append(value)

        ret = subprocess.call(cmd) 
        print(ret)

        return output_fname_tag         

# indoor
class pcd_to_seg_stage(pipeline_stage): # get segments
    def run(self):
        program_path, input, output, output_fname_tag, filter_type, model = self.get_stage_config_params()
        if self.active_run == False:
            return output_fname_tag + "*.pcd"
        
        docker = self.stage_config.get('docker')
        iter = self.stage_config.get('iteration')
        thresh = self.stage_config.get('threshold')
        projection = self.stage_config.get('projection')    # projection on model
        min_points_ratio = self.stage_config.get('min_points_ratio')

        files = glob.glob(input + "*.pcd")
        print(files)

        for f in files: 
            if docker != None and len(docker):
                image_name = docker       # docker image name
                cmd = ['docker', image_name, f, output_fname_tag, "-mit", iter, "-th", thresh, "-prj", projection, "-mpr", min_points_ratio, "-ft", "pcd"]
            else:
                cmd = [program_path, f, output_fname_tag, "-mit", iter, "-th", thresh, "-prj", projection, "-mpr", min_points_ratio, "-ft", "pcd"]
            ret = subprocess.call(cmd)
        print(ret)

        return output_fname_tag + "*.pcd"

class pcd_to_clean_stage(pipeline_stage):   # clean pcd
    def run(self):
        program_path, input, output, output_fname_tag, filter_type, model = self.get_stage_config_params()
        if self.active_run == False:
            return output_fname_tag + "*.pcd"

        voxel_down_size = self.stage_config.get('voxel_down_size')
        # stat_neighbors = self.stage_config['stat_neighbors']
        # stat_std_ratio = self.stage_config['stat_std_ratio']
        nb_radius_points = self.stage_config.get('nb_radius_points')
        nb_radius = self.stage_config.get('nb_radius')

        # cmd = ["python", program_path + ".py", "--voxel_down_size", voxel_down_size, "--stat_neighbors", stat_neighbors, "--stat_std_ratio", stat_std_ratio, "--input", input, "--output", output_fname_tag]
        cmd = ["python", program_path + ".py", "--voxel_down_size", voxel_down_size, "--nb_radius_points", nb_radius_points, "--nb_radius", nb_radius, "--input", input, "--output", output_fname_tag]
        ret = subprocess.call(cmd)
        print(ret)

        return output_fname_tag + "*.pcd"

class seg_to_geo_stage(pipeline_stage): # get concave alpha shape. option.
    def run(self):
        program_path, input, output, output_fname_tag, filter_type, model = self.get_stage_config_params()
        if self.active_run == False:
            return output_fname_tag
        model = self.stage_config.get('model')
        alpha = self.stage_config.get('alpha')

        cmd = [program_path, input, output_fname_tag, "-ht", model, "-alpha", alpha]
        ret = subprocess.call(cmd) # ["../build/bin/seg_to_geo", "/home/ktw/Projects/pcd_pl/build/bin/cloud_planner_hull_", "/home/ktw/Projects/pcd_pl/build/bin/indoor/", "-ft", "json", "-alpha", "0.1"])
        print(ret)

        return output_fname_tag

class geo_to_obj_indoor_stage(pipeline_stage): # get object (wall, floor etc)
    def run(self):
        program_path, input, output, output_fname_tag, filter_type, model = self.get_stage_config_params()
        if self.active_run == False:
            return output_fname_tag
        wall = self.stage_config.get('wall')
        floor = self.stage_config.get('floor')            
        wall_min_angle = wall.get('min_angle')
        wall_max_angle = wall.get('max_angle')
        wall_height = wall.get('height')
        floor_max_height = floor.get('max_height')

        cmd = ["python", program_path + ".py", "--input", input, "--output", output_fname_tag, "--wall_min_angle", wall_min_angle, "--wall_max_angle", wall_max_angle, "--wall_height", wall_height, "--floor_max_height", floor_max_height]
        ret = subprocess.call(cmd) # ["python", "/home/ktw/Projects/pcd_pl/pcd_geo_obj/geo_to_obj.py"])
        print(ret)

        return output_fname_tag 

class obj_to_bim_stage(pipeline_stage): # get semantic object
    def run(self):
        return pipeline_stage.run(self)

# outdoor
class pcd_to_outdoor_classification_stage(pipeline_stage):
    def run(self):
        return pipeline_stage.run(self)

class pcd_to_dtm_stage(pipeline_stage): 
    def run(self):
        return pipeline_stage.run(self)

class dtm_to_geo_stage(pipeline_stage): 
    def run(self):
        return pipeline_stage.run(self)

class geo_to_obj_outdoor_stage(pipeline_stage): 
    def run(self):
        return pipeline_stage.run(self)

class obj_to_bim_outdoor_stage(pipeline_stage): 
    def run(self):
        return pipeline_stage.run(self)

# pipeline
class pipeline:
    app_config = None
    pipeline_config = None
    pipes = None
    input_folder = ""
    output_folder = ""
    active_run = True

    def __init__(self, name, app_conf):
        self.name = name
        self.app_config = app_conf

    def create_stage(self, type):   # factory design pattern. create instance of class, dynamically
        name = type + '_stage'
        cls = globals()[name]
        obj = cls(self, type)
        return obj

    def set_active_run(self, flag):
        self.active_run = flag

    def get_active_run(self):
        return self.active_run

    def load(self, fname):        
        print('load pipeline')
        with open(fname, 'r') as f:
            self.pipeline_config = json.load(f)
            print(self.pipeline_config)

        for p in self.pipeline_config:
            find = re.search(p, self.name) 
            if find == None:
                continue

            self.pipes = list()
            for step in self.pipeline_config[p]:
                name = step['type']
                stage = self.create_stage(name)
                if stage == None:
                    continue

                self.pipes.append(stage)

        return self.pipeline_config

    def get_app_config(self):
        return self.app_config

    def get_stage_config(self, stage_name):
        pipe_stages = self.pipeline_config[self.name]
        if pipe_stages == None:
            return None

        for stage in pipe_stages:
            filter_type = stage['type']
            if filter_type == None:
                break
            if stage_name in filter_type:
                return stage

        return None

    def run(self):
        print('pipeline')
        print(conf.get_root())
        print(conf.get_bin_path())
        print(conf.get_data_path())
        print(conf.get_output_path())
        if self.pipes == None or len(self.pipes) == 0:
            return

        if self.active_run == False:
            return

        # self.pipes[0].set_active_run(False)
        # self.pipes[1].set_active_run(False)
        self.pipes[2].set_active_run(False)
        self.pipes[3].set_active_run(False)

        input = conf.get_input_path()
        for idx, p in enumerate(self.pipes):
            p.init(input) 
            input = p.run()