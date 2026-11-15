# 随仓库走的数据（不含轨迹）

- `raw/idrome/IDRome_DB.csv`：官方 Human IDRome 表
- `processed/idrome_split_{train,val,test}.tsv`：UniProt 分组 70/15/15（seed 42）
- `processed/idrome_split_meta.json`：划分统计
- `processed/aa_contact_table.npz`：8 Å 非相邻接触频率 / \(\varepsilon_{ab}\)
- `processed/aa_contact_table_freq.tsv` / `_eps.tsv` / `_pairs.tsv`：同一张表的可读版
- `processed/labels_exp151.tsv`：151 条实验 \(R_g\)

轨迹 zip 不放本目录。训练和推理只需要接触表 + 划分 TSV。
