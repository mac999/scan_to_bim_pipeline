# title: pipeline for scan to BIM
# created date: 2022.6, taewook kang, laputa99999@gmail.com
# revised date: 2023.1.2, taewook kang, major update about new stage class dynamically. 

import sys, re, json, glob, subprocess
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

        program_path = conf.bin_path + self.name
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
        root_path = app_conf.root_path

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

            cls = globals()[stage_name]
            obj = cls(self, type_name)
        except Exception as e:
            print(e)
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
        print('pipeline')
        print(conf.root_path)
        print(conf.bin_path)
        print(conf.data_path)
        print(conf.get_output_path())

        if self.pipes == None or len(self.pipes) == 0:
            return

        if self.active_run == False:
            return

        # self.pipes[0].set_active_run(False)   # for test.
        # self.pipes[1].set_active_run(False)
        # self.pipes[2].set_active_run(False)
        # self.pipes[3].set_active_run(False)

        input = conf.get_input_path()
        for idx, p in enumerate(self.pipes):
            p.init(input) 
            input = p.run()