# title: pipeline for scan to BIM
# author: taewook kang
# version: 1.0.0
# email: laputa99999@gmail.com
# date:  
#   2022.6, taewook kang, init
#   2023.1.2, taewook kang, major update about new stage class dynamically. 
#   2023.1.30, taewook kang, update 

import sys, re, json, glob, subprocess
import config
from pipeline import pipeline_stage 

conf = config.config()

# a class named <type>_stage defined here replaces the default stage for that SBDL type.
# see pipeline.create_stage(). every type currently runs with the default pipeline_stage.
