#!/usr/bin/env bash
# builds the C++ stages into ./bin.
# usage: ./build.sh [--install]
#   --install  pip install requirements_simple.txt first
# env: PYTHON (default python), JOBS (default number of cores). PCL is found through CONDA_PREFIX when set

set -u
cd "$(dirname "$0")"
PYTHON=${PYTHON:-python}
JOBS=${JOBS:-$(nproc 2>/dev/null || echo 2)}

case "${1:-}" in
    "") ;;
    --install)
        echo "== install python packages"
        $PYTHON -m pip install -r requirements_simple.txt || exit 1 ;;
    *) sed -n '2,5p' "$0"; exit 1 ;;
esac

echo "== build C++ stages"
options=(-DCMAKE_BUILD_TYPE=Release)
if [ -n "${CONDA_PREFIX:-}" ]; then
    options+=(-DCMAKE_PREFIX_PATH="$CONDA_PREFIX" -DQT_HOST_PATH="$CONDA_PREFIX")
fi
cmake -S . -B build "${options[@]}" && cmake --build build -j "$JOBS" || { echo "build failed"; exit 1; }
ls bin
