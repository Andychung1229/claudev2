#!/usr/bin/env bash
set -euo pipefail
experiment_root="${1:?experiment root required}"
mkdir -p "$experiment_root/logs"
export PIP_CACHE_DIR="$experiment_root/pip-cache"
export TMPDIR="$experiment_root/tmp"
mkdir -p "$PIP_CACHE_DIR" "$TMPDIR"
trap 'printf "failed\n" > "$experiment_root/logs/environment.status"' ERR
printf 'installing\n' > "$experiment_root/logs/environment.status"
python3 -m venv --without-pip "$experiment_root/.venv"
curl --fail --location --retry 2 --max-time 120 https://bootstrap.pypa.io/get-pip.py -o "$experiment_root/get-pip.py"
sha256sum "$experiment_root/get-pip.py" > "$experiment_root/logs/get-pip.sha256"
"$experiment_root/.venv/bin/python" "$experiment_root/get-pip.py"
"$experiment_root/.venv/bin/python" -m pip install --timeout 60 --retries 2 --index-url https://download.pytorch.org/whl/cu126 torch==2.7.1
"$experiment_root/.venv/bin/python" -m pip install --timeout 60 --retries 2 numpy==1.26.4 pandas==2.2.3 pyyaml==6.0.2 pytest==8.3.5 matplotlib==3.10.1 mdtraj==1.10.3
"$experiment_root/.venv/bin/python" -m pip freeze > "$experiment_root/logs/environment.txt"
printf 'ready\n' > "$experiment_root/logs/environment.status"
