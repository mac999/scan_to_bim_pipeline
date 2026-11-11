# title: docker debug run shell for ML, GPU, open3d
# author: taewook kang
# date: 2022.11
# description: to use open3d_gpu, build and use docker image in bulid_docker_open3d folder.

full_path="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
# full_path="$(dirname "$(pwd)")"

dataset_path=/media/ktw/DL_data11/data/

echo $full_path
docker run -v $full_path/..:/pcd_pl -v $dataset_path:/pcd_pl/pcd_to_seg_ml/data --gpus all -it open3d_gpu bash

# reference
# rel_path=$(dirname -- "$0");
# docker run -v /home/ktw/projects/pcd_pl/docker/program:/tf --gpus all -it knamdar/open3d:v2 bash
