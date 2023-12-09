FROM pytorch/pytorch:1.12.1-cuda11.3-cudnn8-devel
MAINTAINER kangtaewook

RUN apt-get update
RUN apt-get install -y libx11-6 libgl1-mesa-glx
RUN pip install torch open3d==0.16.0 tensorboard numpy

# FROM 17867415107/open3d_gpu
# RUN apt-get install python3-pip -y
# ENV PIP_ROOT_USER_ACTION=ignore
# RUN apt-get install python3.9
# RUN python3.9 -m pip install -U pip
# RUN apt-get install python3-pip -y
# ENV PATH /usr/
# RUN pip install --root-user-action=ignore
# RUN pip install --upgrade pip 
# RUN conda --yes install open3d tensorboard 
# CMD ["bash"]
# CMD ["pip install torch open3d tensorboard numpy"]
# CMD tail -f /dev/null