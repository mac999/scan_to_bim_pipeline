# title: pipeline stage for scan to BIM
# created date: 2022.6, taewook kang, laputa99999@gmail.com
# revised date: 2023.1.2, taewook kang, major update about new stage class dynamically. 

import sys, re, json, glob, subprocess
import config
from pipeline import pipeline_stage 

conf = config.config()

# system (default) pipeline stage for indoor
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