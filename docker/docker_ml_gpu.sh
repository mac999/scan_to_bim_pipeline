# title: docker run shell for open3d ml gpu
# author: taewook kang
# date: 2022.11
echo "begin docker command"

full_path="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

# -it only with a terminal. the pipeline runs this without one
tty_flag=""
if [ -t 0 ]; then
    tty_flag="-it"
fi

echo "$@"
echo $full_path
docker run --rm -v "$full_path/..:/pcd_pl" --gpus all $tty_flag "$@"
status=$?
echo "end docker command"
exit $status   # the pipeline stops on a failed stage only if the status is passed on

# reference
# docker run --rm -it knamdar/open3d:v2 /bin/bash
# /home/ktw/projects/pcd_pl/docker/docker_open3d_ml.sh knamdar/open3d:v2 python predict_indoor_obj.py
