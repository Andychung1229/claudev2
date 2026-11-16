# COMP 5222 簡報後半段：故事線同講稿（第 8–14 頁，約 6 分鐘）

> 你負責第 8–14 頁：graph 長咩樣、模型點運作、結果、同埋我哋學到咩。
> 第 1–7 頁（背景、AlphaFold、接觸表、點樣將序列變成 graph）由 partner 講。
> 呢版已經加入 Codex 喺 2026-11-16 跑嘅 3-seed edge ablation（GitHub branch `exp/edge-ablation`）。
> 所有數字都由 prediction 檔重新計過，出處喺最尾。

---

## 0. 一句講晒

**沿住條鏈做 message passing 嘅細 GAT（18.7k 參數）喺模擬同實驗數據都贏胺基酸組成模型；但我哋加嘅 non-local contact edge 冇幫手，喺模擬數據仲拖低咗表現，因為揀 edge 嘅規則幾乎只睇序列距離。**

英文版：

> *A small graph network that passes messages along the chain beats a composition baseline on simulations and experiments. Our contact edges do not help yet: sequence distance, not chemistry, decides which edges we draw.*

---

## 1. 故事點樣變咗

| | 上一版（單一 run） | 而家（每個模型 3 個 seed） |
|---|---|---|
| Full model（有 contact edge）模擬 MAE | 0.100 | **0.111 ± 0.015**；舊嘅 0.100 重新 train 唔到 |
| 同組成模型比（模擬） | 打和 | Full 差過組成；**local-only 好過組成** |
| 實驗 | GAT 贏組成 | 所有 GAT 都贏組成；有冇 contact edge 冇分別 |
| 點解 graph 冇用？ | 只係推論（edge 由距離決定） | **有對照實驗**：拎走 non-local edge，模擬表現好咗，模型亦睇到排列 |

### 講得出（有數據支持）

| # | 結論 | 證據 |
|---|---|---|
| 1 | 沿住條鏈嘅 GAT 喺模擬數據贏組成模型 | Local-only 0.066 ± 0.007 vs 組成 0.098；bootstrap −0.036 nm [−0.038, −0.033]；3 個 seed 全部好過組成 |
| 2 | 所有 GAT 喺實驗數據都贏組成模型 | Full 0.301、local-only 0.303 vs 組成 0.331；兩個 CI 都唔包 0 |
| 3 | 我哋嘅 contact edge 冇幫手 | 模擬：local-only 比 full 好 0.044 nm [−0.046, −0.041]；實驗：差 +0.008 [−0.012, +0.028]，即係冇分別 |
| 4 | 原因：edge 由距離決定 | 96.6% partner 喺最遠 band；只按距離揀 edge 嘅對照組表現差唔多 |
| 5 | 拎走 contact edge 之後，模型睇到短鏈嘅排列 | 6 條同組成、107 aa：實驗 Rg 相差 0.73；full 預測相差 0.06，local-only 相差 0.47（Spearman 0.94） |

### 唔可以講

- ❌「接觸先驗令模型更準」：而家嘅證據顯示相反。
- ❌「我哋嘅模型睇得到排列」：只係短鏈嗰組；7 條 334 aa 嗰組冇一個 variant 排得啱。
- ❌「Band-resolved 表會解決問題」：未跑，只可以講係下一步。
- ❌ 用 0.100 做 full model 嘅成績：重新 train 唔到，要用 3-seed 平均。

---

## 2. 新實驗（Codex，`exp/edge-ablation` branch）

**設計：** 同一個 split、模型、optimizer 同 early stopping，只改 graph 規則同 seed（42、43、44）。

| Variant | 意思 |
|---|---|
| full | 原本嘅 graph：local edge + 每個殘基 top-8 contact edge |
| local_only | 只留 \|i−j\| ≤ 2 嘅 local edge 同 self-loop（proposal Table 1 嘅「Local-chain GAT」） |
| distance_only | Non-local edge 數目一樣，但只按距離揀（唔睇胺基酸） |
| train_table / band_resolved | **未跑**：要原本嘅 trajectory zip（`conformational_ensembles.zip`），server 上搵唔到 |

### 結果（每個 seed 嘅 MAE，單位 nm）

| | Seed 42 | 43 | 44 | 平均 ± sd |
|---|---|---|---|---|
| Full，模擬 | 0.128 | 0.108 | 0.098 | 0.111 ± 0.015 |
| Local-only，模擬 | 0.061 | 0.064 | 0.074 | **0.066 ± 0.007** |
| Distance-only，模擬 | 0.140 | 0.073 | 0.070 | 0.094 ± 0.040 |
| Full，實驗 | 0.298 | 0.311 | 0.294 | 0.301 ± 0.009 |
| Local-only，實驗 | 0.299 | 0.299 | 0.311 | 0.303 ± 0.007 |
| Distance-only，實驗 | 0.343 | 0.312 | 0.307 | 0.320 ± 0.020 |

Baseline：只睇長度，模擬 0.124、實驗 0.416；組成 + 長度，模擬 0.098、實驗 0.331。

### 要知嘅限制
- **0.100 重新 train 唔到。** Codex 喺新機用同一個 seed 42 train 出 0.128。用舊 checkpoint 重新做 inference 仍然係 0.100，所以問題出喺 training 嗰邊，可能同硬件或者 runtime 有關，原因未搵到。所以簡報用 3-seed 平均。
- **Bootstrap 嘅計法：** 先將 3 個 seed 嘅預測平均，再對序列 resample。所以 CI 唔包括 seed 之間嘅差異；要配合「每個 seed 都好過」呢點一齊講。
- **Distance-only 唔穩定：** 3 個 seed 由 0.070 到 0.140。所以只講「胺基酸項冇顯示到有幫助」，唔好講「distance-only 好過 full」。
- **「Attention 被遠距離 edge 沖淡」只係推測。** 每個殘基平均有約 12 條 non-local edge，但得 2–4 條 local edge。未做 attention 分析。

---

## 3. 成個簡報點樣串連

| 頁 | 講者 | 一句重點 | 時間 |
|---|---|---|---|
| 1 | Partner | 題目同兩個人 | 0:25 |
| 2 | Partner | AlphaFold 只俾一張靜態結構，睇唔到 IDP 點郁 | 0:50 |
| 3 | Partner | IDP 冇固定結構，要用 ensemble 描述 | 1:00 |
| 4 | Partner | Rg 係 ensemble 嘅大細；殘基之間嘅非共價作用決定佢 | 1:00 |
| 5 | Partner | 我哋嘅想法：將殘基對資訊放入 graph | 0:45 |
| 6 | Partner | 由 2,800 萬幀模擬數出接觸表 | 1:10 |
| 7 | Partner | 序列 → graph：node、local edge、non-local edge | 1:15 |
| **8** | **你** | **Graph 好稀疏；橙色 edge 全部離對角線好遠（伏筆）** | **0:50** |
| **9** | **你** | **Edge-aware GAT；18.7k 參數** | **0:55** |
| **10** | **你** | **按蛋白分 split；每個模型 3 個 seed** | **0:35** |
| **11** | **你** | **模擬：拎走 contact edge 先贏組成模型** | **1:10** |
| **12** | **你** | **實驗：所有 GAT 都贏組成；edge 冇分別** | **0:45** |
| **13** | **你** | **原因：距離揀 edge，排列被沖淡** | **1:00** |
| **14** | **你** | **三個 takeaway** | **0:30** |

你嗰半 speaker notes 共 748 字，照每分鐘 130 字計大約 5:45，加埋停頓剛好 6 分鐘。如果超時，第 9 頁最易縮。

Partner 嗰半照 notes 計大約 6:25，要再壓 25 秒左右。另外第 4 頁最好加返一行 Rg 定義（Rg ∝ N^ν，ν ≈ 0.53），因為第 11 頁要用「只睇長度」嚟做 baseline。

### 你嗰半嘅弧線
1. **鋪墊（8–10）：** Graph 長咩樣、模型點讀佢、點樣公平咁 test。第 8 頁埋伏筆：橙色 edge 全部好遠。
2. **好消息加轉折（11）：** GAT 贏組成模型，但要拎走我哋自己加嘅 contact edge 先得。
3. **再確認（12）：** 實驗數據上所有 GAT 都贏組成模型，edge 冇分別。
4. **偵探（13）：** 點解？因為 edge 由距離揀，而且佢哋令模型睇唔到排列。
5. **收尾（14）：** 邊樣行得通、邊樣未得、下一步做咩。

**第 11 頁係成段最重要嘅一頁。** 要講得自信：我哋做咗受控實驗，搵到邊個部分有用、邊個部分冇用。

---

## 4. 逐頁講稿（同 .pptx speaker notes 一樣）

### 第 8 頁：A sparse graph with 10 features per edge（0:50）
- **指住：** 先指 adjacency matrix 嘅藍色對角線，再指橙色點，強調橙色全部離對角線好遠。
- **數字：** 155 個殘基；10%（1,192 / 11,935）；每條 edge 10 個 feature。

> Thanks. So that was one residue. Here is a whole graph, for a chain of 155 residues. This is its adjacency matrix: the blue band along the diagonal is the local edges, and the orange cells are the non-local edges.
>
> Only about ten percent of all residue pairs become edges, so the graph grows like N times w plus k instead of N squared, and message passing stays cheap.
>
> Every edge carries ten numbers: the contact frequency from our table, the sequence distance, a one-hot distance band, and two flags for local edges and self-loops.
>
> Keep one thing in mind: all the orange edges sit far from the diagonal. That will matter when we look at the results.

### 第 9 頁：Edge-aware graph attention network（0:55）
- **指住：** 第一條公式入面嘅 `a_edge · MLP(e(i,j))`，然後指右邊 18,721。唔使逐條讀公式。

> Now, how does the model read this graph? It is a graph attention network that also reads edge features.
>
> For each edge, every attention head scores it from three parts: the sending node, the receiving node, and the edge features. That third term is where the contact prior enters. It is an input to the attention score, not a fixed weight, so the model learns how much to trust it.
>
> The scores are normalised only over each node's neighbours, and each node takes a weighted sum of their messages, with a residual connection and LayerNorm.
>
> After two layers, we pool the whole chain: mean, max, and log of the length. A small MLP then predicts log Rg. The whole model has under nineteen thousand parameters.

### 第 10 頁：Training on unseen-protein splits（0:35）
- **數字：** 18,860 / 4,020 / 4,103；每個模型 3 個 seed。

> We split the data seventy, fifteen, fifteen by protein. Regions from the same protein, and identical sequences, stay in one split, so test proteins are truly unseen. That gives about nineteen thousand training chains and four thousand each for validation and test.
>
> We train on log Rg and keep the checkpoint with the lowest validation error. Because single runs turned out to be noisy, we trained every model with three random seeds.
>
> So, how well does it do?

### 第 11 頁：Simulations: the GAT is best without contact edges（1:10）
- **指住：** 先指兩條灰色 bar 同虛線（組成模型），再指藍色 full model 嘅三粒點，最後指橙色 bar。講完「0.066」停一停。
- **數字：** 0.124、0.098、0.111 ± 0.015、0.066 ± 0.007；−0.036 [−0.038, −0.033]；68% vs 31%。

> Here is the simulated test set: four thousand proteins the model never saw. The grey bars are two simple baselines. Length alone gives 0.124 nanometres. Adding amino-acid composition, with just 21 parameters, gives 0.098.
>
> Our full model, with the contact edges, averages 0.111 over three seeds. That is no better than composition. Our earlier single run gave 0.100, but it did not reproduce on retraining, so we report the three-seed mean.
>
> Now the orange bar. Same network, same training, but we remove every non-local edge and keep only the chain. The error drops to 0.066, and all three seeds beat composition. It explains about two thirds of what length cannot explain, against one third for composition.
>
> So message passing along the chain works. Our contact edges are what hold it back.

### 第 12 頁：On experiments, every GAT beats composition（0:45）
- **指住：** 虛線（組成模型），然後指藍色同橙色兩條 bar 差唔多高。
- **數字：** 0.301 / 0.303 vs 0.331；CI 見 slide。

> Next, 151 sequences with measured Rg. The models saw only simulation labels.
>
> Every graph model beats composition here: about 0.30 nanometres against 0.33, and the bootstrap intervals exclude zero for both the full and the local-only model.
>
> But between the two graph models there is no detectable difference. Removing the contact edges neither helps nor hurts on real data.
>
> The error is still several times larger than on simulations, because we inherit the gap between the simulation model and experiment.
>
> So why do the contact edges fail? We looked at how they are chosen.

### 第 13 頁：Sequence distance dominates the edge score（1:00）
- **指住：** 左邊張圖：藍色線好長、橙色線好短。然後指右上 96.6%，最後指表入面 0.06 同 0.47。
- **數字：** 2.1× vs 1,338×；96.6%；0.73 / 0.06 / 0.47。

> Our edge score divides the pair's contact frequency by the average frequency at that distance. Pair frequency varies only two-fold, but the distance term varies over a thousand-fold. So distance wins: 97 percent of chosen partners sit in the farthest distance band, and amino-acid type only breaks ties. A control that picks edges by distance alone behaves the same.
>
> The cost shows up in residue order. Here are six sequences with the same composition in different orders. Their measured Rg spans 0.73 nanometres. With contact edges, our predictions span 0.06. Without them, 0.47, almost in the right order. Our guess is that a dozen far-away edges per residue drown out the local signal in attention. For the long chains, no variant sees order yet.

### 第 14 頁：What we can say, and what comes next（0:30）

> Three takeaways. One: a small graph network that passes messages along the chain beats composition, on simulations and on experiments.
>
> Two: our contact edges, as built, do not help, because sequence distance, not chemistry, decides which edges we draw.
>
> Three: next we rebuild the contact table by distance band, from training chains only, and test whether chemistry-chosen edges can add to the chain.
>
> Thank you. We are happy to take questions.

---

## 5. Q&A 準備

**Q1. 咁你哋個 contact graph 究竟有冇用？**
> As built, no. A controlled ablation with three seeds shows the chain-only graph does better on simulations and the same on experiments. We traced it to the edge rule: distance, not amino-acid type, decides the edges.

**Q2. Local-only 點解會好過 full？**
> We don't know for sure. Our hypothesis is dilution: each residue has two to four local neighbours but about twelve distant ones, and attention is normalised over all of them. We haven't tested that directly yet.

**Q3. 咁點解唔直接報 local-only，仲要講 contact prior？**
> Because the project question was whether pairwise contact information helps. Answering "not this way, and here is why" is the result. Local-only is the baseline that any future contact graph has to beat.

**Q4. 之前 0.100 嘅結果去咗邊？**
> It came from one run on a different machine. Re-evaluating that saved checkpoint still gives 0.100, but retraining with the same seed on the new machine gives 0.128. So we report the mean over three seeds, which is 0.111.

**Q5. Bootstrap CI 有冇包括 seed 嘅不確定性？**
> No. We average predictions over seeds and then resample sequences. That's why we also show every seed: all three local-only seeds beat composition and every full-model seed.

**Q6. Local-only GAT 睇到幾遠？**
> Two layers over neighbours up to two apart, so each residue sees about four residues either side, plus global mean and max pooling. So it learns local sequence patterns, which is consistent with it sensing order in short chains but not long ones.

**Q7. 點解 band-resolved 表未做？**
> It needs pair counts per distance band, which must be recounted from the raw trajectories. That archive wasn't available on our compute server, and we didn't want to fake it from the pooled table.

**Q8. 接觸表有冇 data leakage？**
> Yes, a small one: it was counted over all chains, including test. It's a 20 × 20 summary, and our best model, local-only, uses it only as an edge feature on local edges. A training-only rebuild needs the same trajectory archive.

**Q9. 同 ALBATROSS 或者 STARLING 比點？**
> We haven't run them on our split, so we won't quote numbers.（唔好即場講佢哋 paper 嘅數字。）

**Q10. R² 0.99 唔係好高咩？**
> Length alone gives 0.97, so R² hides most of the differences. That's why we compare MAE against length and composition baselines.

---

## 6. 數字速查同出處

| 數字 | 值 | 出處 |
|---|---|---|
| 只睇長度：模擬 / 實驗 MAE | 0.124 / 0.416 | `comp5222-presentation/analysis/check_story.py` |
| 組成 + 長度：模擬 MAE、R²；實驗 MAE、R²、r | 0.098、0.980；0.331、0.822、0.908 | 同上 |
| 每個 seed 嘅 MAE、R²、r | 見第 2 節 | `exp/edge-ablation`：`COMP-5222/experiments/edge_ablation/seed_metrics.tsv`；我用 `runs/edge_ablation/*/predictions_*.tsv` 重新計過，一致 |
| Bootstrap 差距 | 見 slide 11、12 | `experiments/edge_ablation/bootstrap.tsv` |
| 長度解釋唔到嘅 variance 捉到幾多 | local-only 68%、組成 31%、full 20% | `experiments/edge_ablation/RESULTS.md` |
| 排列測試 | 6×107：0.73 / 0.06 / 0.47；7×334：1.39 / 0.08 / 0.17 | `experiments/edge_ablation/permutation_sensitivity.tsv` |
| 最遠 band 比例 | 96.6%（300 條 test 鏈） | `analysis/check_story.py`；`experiments/edge_ablation/edge_audit.json` |
| f(a,b) 範圍；p(d) 範圍 | 2.1×；1,338× | `scripts/scale_fig.py` |
| 舊 checkpoint 重新評估 | 模擬 0.100、實驗 0.295 | `runs/edge_ablation/historical_checkpoint_eval/` |
| 第 11、12 頁嘅圖 | — | `comp5222-presentation/scripts/ablation_fig.py` |
