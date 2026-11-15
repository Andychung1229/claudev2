# ContactGAT sparse（IDP \(R_g\)）

Human IDRome 轨迹上统计 **非相邻**（\(|i-j|\ge 2\)）、**\(r<8\,\text{Å}\)** 接触，得到氨基酸对频率。图是 PDF 构图：局部窗 \(1\le|i-j|\le 2\) + 每点 top-8 非局部边 + 自环。2 层 GAT（4×16），readout = mean∥max∥log N，在 \(\ln R_g\) 上用 MSE。训练标签是 IDRome 模拟 \(R_g\)，UniProt 分组 70/15/15。

推理 **不需要轨迹**：边权来自全局接触表。

## 跑训练

```bash
bash submit_sparse.sh
# 或
python scripts/train.py --config configs/sparse_gat.yaml
```

权重与误差图：`runs/contact_gat_idrome_sparse/`。

```bash
python scripts/plot_sparse_errors.py   # IDRome test + 实验 exp151
```

## 数据

| 路径 | 作用 |
|------|------|
| `data/processed/idrome_split_{train,val,test}.tsv` | 70/15/15 划分 |
| `data/processed/aa_contact_table.npz` | 8 Å 接触表 |
| `data/processed/labels_exp151.tsv` | 151 条实验 \(R_g\) |
| `data/raw/idrome/IDRome_DB.csv` | 官方序列表（重划分用） |

重建接触表（只需有 zip 的机器跑一次）：

```bash
python scripts/build_contact_table.py --zip /path/to/conformational_ensembles.zip
```

重划分：

```bash
python scripts/make_idrome_split.py
```

## 代码

| 路径 | 作用 |
|------|------|
| `configs/sparse_gat.yaml` | 超参 |
| `contact_mpnn/` | 接触表、稀疏图、GAT、训练循环 |
| `scripts/train.py` | 训练入口 |
| `scripts/plot_sparse_errors.py` | 误差图 |
