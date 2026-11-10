#!/usr/bin/env bash
# runs the sample pipelines. build the C++ stages first with build.sh
# usage: ./run_samples.sh [all|indoor|pipe]
#   indoor  conference_room1, rule-based walls and slabs. needs the C++ stages
#   pipe    kict_mep_zero_en_bdlg_parts, pipes and elbows
# env: PYTHON (default python)

set -u
cd "$(dirname "$0")"
PYTHON=${PYTHON:-python}
target=${1:-all}
case $target in
    all|indoor|pipe) ;;
    *) sed -n '2,6p' "$0"; exit 1 ;;
esac

failed=0
run() {
    # name, input glob, pipeline, result file
    echo "== $1: $3"
    rm -f "$4"
    $PYTHON pipeline/app.py --input_path "$2" --stage "$3"
    if [ -f "$4" ]; then
        echo "$1: $4"
    else
        echo "$1: failed, no $4"
        failed=1
    fi
}

if [ $target = all ] || [ $target = indoor ]; then
    if [ -x bin/pcd_to_seg ] && [ -x bin/seg_to_geo ]; then
        run indoor "./input/conference_room1/*.pcd" indoor_rule output/conference_room1/geo_to_bim_indoor/geo_to_bim_indoor.ifc
    else
        echo "indoor: skipped, run build.sh first"
        failed=1
    fi
fi
if [ $target = all ] || [ $target = pipe ]; then
    run pipe "./input/kict_mep_zero_en_bdlg_parts/*.laz" pipe_rule output/kict_mep_zero_en_bdlg_parts/geo_to_bim_pipe/geo_to_bim_pipe.ifc
fi
exit $failed
