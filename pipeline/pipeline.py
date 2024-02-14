# title: pipeline for scan to BIM
# author: taewook kang
# version: 1.0.0
# email: laputa99999@gmail.com
# date:  
#   2022.6, taewook kang, init
#   2023.1.2, taewook kang, major update about new stage class dynamically. 
#   2023.1.30, taewook kang, update 

import os, sys, re, json, glob, subprocess, shutil
import config

conf = config.config()

class pipeline_stage:
    name = None
    pipe = None
    stage_config = None
    active_run = True

    def __init__(self, pipe_obj, name):
        self.name = name
        self.pipe = pipe_obj
        
    def update_docker_io_path(self, path):
        remote_io_root = self.stage_config.get('remote_io_root')
        if remote_io_root == None:
            return path
        remote_io_root = remote_io_root.replace('$bin_path', conf.bin_path)

        # split token list using ':' from remote_io_root. ex) "remote_io_root": "$bin_path:/pcd_pl"
        split = remote_io_root.split(':')
        if len(split) < 2:
            return path
        
        map1 = split[0]
        map2 = split[1]
        
        mapped_path = path.replace(map1, map2)
        return mapped_path

    def get_stage_config_params(self):
        input = output = ""

        if self.stage_config == None:
            return None

        input = self.stage_config.get('input')
        output = self.stage_config.get('output')
        
        input = self.update_docker_io_path(input)
        output = self.update_docker_io_path(output)
                                
        filter_type = self.stage_config.get('type')
        if input == None or output == None or filter_type == None:
            return None

        cmds = []
        cmd = self.stage_config.get('cmd')
        if cmd == None:            
            program_path = conf.bin_path + self.name + "/" + self.name
            if os.path.isfile(program_path + ".py"):
                cmds.append('python')
                program_path = program_path + ".py"
            else: 
                program_path = conf.bin_path + "bin/" + self.name
                if os.path.isfile(program_path) == False:
                    return None
            
            cmds.append(program_path)
        else:
            cmd = cmd.replace('$bin_path/', conf.bin_path)
            cmds = cmd.split()

        output_fname_tag = output + self.name

        return cmds, input, output, output_fname_tag

    def init(self, input_path = None):
        print('\n*', self.name)

        self.stage_config = self.pipe.get_stage_config(self.name)
        if self.stage_config != None:
            self.stage_config['input'] = conf.get_input_path()
            output_path = conf.get_output_path()
            output_path = output_path + self.name + "/"

            if 'active' in self.stage_config:
                self.active_run = self.stage_config['active']
            print(f'active={self.active_run}')
            if self.active_run == True:
                try:
                    shutil.rmtree(output_path)
                except Exception as e:
                    pass
            if not os.path.exists(output_path):
                os.makedirs(output_path)

            self.stage_config['output'] = output_path

                            
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
        try:
            cmds, input, output, output_fname_tag = self.get_stage_config_params()
            if cmds == None:
                return ""
            if self.active_run == False:
                return output_fname_tag

            app_conf = self.pipe.get_app_config()
            root_path = app_conf.root_path
            
            exec_cmd = cmds
            exec_cmd.append("--input")
            exec_cmd.append(input)
            exec_cmd.append("--output")
            exec_cmd.append(output_fname_tag)

            for param in self.stage_config:
                if param == "type" or param == 'cmd' or param == "input" or param == "output" or param == 'note':
                    continue
                value = str(self.stage_config[param])
                if param == "pdal_pipeline":
                    value = root_path + value
                exec_cmd.append("--" + param)
                exec_cmd.append(value)

            ret = subprocess.call(exec_cmd) 

        except Exception as e:
            print(e)

        return output_fname_tag         

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

    def create_dynamic_pipeline_stage(self, class_name, type_name):
        try:
            def run(self):
                return pipeline_stage.run(self)

            dynamic_stage_class_dict = {
                "run": run
            }

            stage_class = type(class_name, (pipeline_stage, ), dynamic_stage_class_dict)
            obj = stage_class(self, type_name)
            return obj
        except Exception as e:
            print(e)
            pass
        return None

    def create_stage(self, type_name):   # factory design pattern. create instance of class, dynamically
        stage_name = type_name + '_stage'
        try:
            import pipeline_default_stage

            cls = getattr(pipeline_default_stage, stage_name)   # globals()[stage_name]
            obj = cls(self, type_name)
        except Exception as e:
            print('create default ' + stage_name)
            obj = self.create_dynamic_pipeline_stage(stage_name, type_name)
        return obj

    def set_active_run(self, flag):
        self.active_run = flag

    def get_active_run(self):
        return self.active_run

    def load(self, fname):        
        print('load pipeline')
        with open(fname, 'r') as f:
            self.pipeline_config = json.load(f)
            # print(self.pipeline_config)

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
        print('\n* run pipeline')
        print('root path: ', conf.root_path)
        print('bin path: ', conf.bin_path)
        print('data path: ', conf.data_path)
        print('output path: ', conf.get_output_path())

        if self.pipes == None or len(self.pipes) == 0:
            return

        if self.active_run == False:
            return

        # self.pipes[0].set_active_run(False)   # TBD. json. for test.
        # self.pipes[1].set_active_run(False)
        # self.pipes[2].set_active_run(False)
        # self.pipes[3].set_active_run(False)

        input = conf.get_input_path()
        for idx, p in enumerate(self.pipes):
            p.init(input) 
            input = p.run()