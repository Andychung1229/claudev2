#!/usr/bin/env bash
# PDF 构图的 ContactGAT：IDRome 70/15/15 模拟 Rg，局部窗 + top-k 非局部边。
# 可 bash 直接跑，也可 sbatch。
#
#SBATCH --job-name=comp5222-sparse-gat
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=7-00:00:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
mkdir -p "$ROOT/logs" "$ROOT/data/processed" "$ROOT/runs"

export PYTHONUNBUFFERED=1
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"

PYTHON="${PYTHON:-python3}"
CONFIG="${CONFIG:-$ROOT/configs/sparse_gat.yaml}"
TABLE="${CONTACT_TABLE:-$ROOT/data/processed/aa_contact_table.npz}"
TRAIN_TSV="$ROOT/data/processed/idrome_split_train.tsv"
VAL_TSV="$ROOT/data/processed/idrome_split_val.tsv"
TEST_TSV="$ROOT/data/processed/idrome_split_test.tsv"

echo "==== COMP-5222 sparse contact GAT ===="
echo "host=$(hostname)  date=$(date -Iseconds)"
echo "ROOT=$ROOT"
echo "PYTHON=$PYTHON  ($("$PYTHON" -c 'import sys; print(sys.executable)'))"
"$PYTHON" -c 'import torch,sys; print("torch", torch.__version__, "cuda", torch.cuda.is_available(), "gpu", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu")'
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi -L || true
fi

if [[ ! -e "$TRAIN_TSV" || ! -e "$VAL_TSV" || ! -e "$TEST_TSV" ]]; then
  echo "划分文件缺失，生成 70/15/15 group split"
  "$PYTHON" "$ROOT/scripts/make_idrome_split.py"
fi

need=(
  "$ROOT/scripts/train.py"
  "$CONFIG"
  "$TRAIN_TSV"
  "$VAL_TSV"
  "$TEST_TSV"
  "$TABLE"
  "$ROOT/data/raw/idrome/IDRome_DB.csv"
)
for f in "${need[@]}"; do
  if [[ ! -e "$f" ]]; then
    echo "缺少文件: $f" >&2
    exit 1
  fi
done

n_train="$("$PYTHON" -c "import pandas as pd; print(len(pd.read_csv('$TRAIN_TSV', sep='\t')))")"
n_val="$("$PYTHON" -c "import pandas as pd; print(len(pd.read_csv('$VAL_TSV', sep='\t')))")"
n_test="$("$PYTHON" -c "import pandas as pd; print(len(pd.read_csv('$TEST_TSV', sep='\t')))")"
echo "train_tsv=$TRAIN_TSV  n=$n_train"
echo "val_tsv=$VAL_TSV  n=$n_val"
echo "test_tsv=$TEST_TSV  n=$n_test"
echo "contact_table=$TABLE  ($(du -h "$TABLE" | cut -f1))"
echo "out=$ROOT/runs/contact_gat_idrome_sparse"

echo "开始训练  graph=sparse w=2 k=8  loss=MSE(log Rg)  readout=mean+max+logN"
"$PYTHON" "$ROOT/scripts/train.py" --config "$CONFIG"
echo "完成 $(date -Iseconds)  out=$ROOT/runs/contact_gat_idrome_sparse"
