# title: docker run shell for open3d ml gpu
# author: taewook kang
# date: 2022.11
echo "begin docker command"

full_path="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
# full_path="$(dirname "$(pwd)")"

echo $@
echo $full_path
docker run -v $full_path/..:/pcd_pl --gpus all -it $@
echo "end docker command"

# reference
# docker run --rm -it knamdar/open3d:v2 /bin/bash
# /home/ktw/projects/pcd_pl/docker/docker_open3d_ml.sh knamdar/open3d:v2 python predict_indoor_obj.py
