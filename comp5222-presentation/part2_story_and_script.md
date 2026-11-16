# COMP 5222 簡報後半段：故事線同講稿（第 8–14 頁，約 6 分鐘）

> 你負責第 8–14 頁。第 1–7 頁（背景、AlphaFold、接觸表、點樣將序列變成 graph）由 partner 講。
> **Audience 識 graph，但唔識 protein。** 所以第 8–14 頁全部用 graph 嘅講法：node、edge、graph-level regression、node-type histogram。Protein 嘅字眼只喺第一次出現時解釋一次。
> Slide 上面只留結論同少量數字，細節（CI、± sd、0.100 點解唔見咗）全部喺第 5 節 Q&A。

---

## 0. 呢個 project 用 graph 嘅語言講

### 一句講晒
**我哋將每個 protein 變成一個 graph，用 GNN 預測佢喺空間有幾散（Rg）。Graph 有用：沿住條鏈做 message passing，error 比只睇 node-type histogram 低三分一。唔得嘅係我哋另外加嘅 long-range edge，因為揀 edge 嘅公式幾乎只睇距離。**

> *We turn each protein into a graph and use a GNN to predict how spread out it is in space. The graph helps: message passing along the chain cuts the error by a third compared with a node-type histogram. Our extra long-range edges do not help, because the rule that picks them is dominated by sequence distance.*

### Project 嘅性質（俾人問「what is this project about」時用）
| 問題 | 答案 |
|---|---|
| 係咩 task？ | **Graph-level regression**：每個 graph 輸出一個數 |
| Input 係咩？ | 一條 amino acid 序列。每個 amino acid 係一個 node（20 種 type + 位置），沿住條鏈連 local edges，再加按統計揀嘅 long-range edges |
| Output 係咩？ | Rg（radius of gyration）：條鏈喺 3D 空間有幾散，單位 nm。Train 嘅時候用 ln Rg 做 MSE |
| Label 由邊度嚟？ | 28,058 個 protein 嘅 physics simulation（Human IDRome），每個有大約 1,000 幀 3D 形狀，平均出 Rg。另外有 151 個實驗室量度嘅 protein 做 out-of-distribution test |
| 點解要預測 Rg？ | Rg 話俾生物學家知一個 disordered protein 係縮埋定散開，同佢點樣同其他分子結合有關。Simulation 每個 protein 都要跑好耐，GNN 一次 forward pass 就有答案 |
| 點解唔用 3D structure 做 graph？ | 呢類 protein（IDP）冇固定 3D 形狀，成日郁緊，所以冇一個 structure graph 可以用；手上只有序列 |
| 研究問題係咩？ | (1) Graph structure 有冇幫手？即係 GNN 贏唔贏一個完全唔睇 edge 嘅 node-type histogram？(2) 我哋用 simulation 統計加嘅 long-range edges 有冇額外幫手？ |
| 答案 | (1) 有：chain-only GNN 贏晒。(2) 冇：揀 edge 嘅方法被距離主導，加咗反而蓋過 node 次序 |

### Audience 要帶走嘅三件事
1. **Graph 幫到手**：chain-only graph 喺模擬 error 低 33%，實驗低 8–9%。
2. **我哋嘅 long-range edge 係瓶頸**：模擬數據加咗反而差，實驗數據冇分別。
3. **我哋知道點解**：揀 edge 嘅公式俾距離主導，揀出嚟嘅都係最遠嘅 node，仲蓋過咗 node 次序。

### 名稱對照（slide 上用嘅名）
| Slide 上 | 實驗入面 | 意思 |
|---|---|---|
| Graph: contact edges | full | Local edges + 每個 node 按 edge score 揀 top-8 long-range edge（我哋原本嘅 model） |
| Graph: distance edges | distance_only | 對照組：long-range edge 數目一樣，但只按距離揀（唔睇 node type） |
| Graph: chain only | local_only | 冇 long-range edge，只有 \|i−j\| ≤ 2 嘅 local edges |
| Graph size only | 只睇長度 baseline | Rg ∝ N^ν，N = node 數 |
| Node-type histogram | 組成（composition）baseline | 20 種 node type 嘅比例 + 長度嘅 linear model（21 個參數）。生物學叫 composition |

---

## 1. 講得出同唔可以講

### 講得出（有數據支持）
| # | 結論 | 證據 |
|---|---|---|
| 1 | Chain-only graph 喺模擬數據贏 histogram | 0.066 vs 0.098 nm（低 33%）；3 個 seed 全部好過；bootstrap −0.036 nm [−0.038, −0.033] |
| 2 | Graph model 喺實驗數據贏 histogram | Contact edges 0.301、chain only 0.303 vs 0.331（低 9% 同 8%）；兩個 CI 都唔包 0 |
| 3 | 我哋嘅 long-range edge 冇幫手 | 模擬：加咗之後 0.111，差過 histogram；實驗：同 chain only 冇分別（+0.008 [−0.012, +0.028]） |
| 4 | 原因：edge 由距離決定 | 96.6% partner 喺最遠 band；只按距離揀 edge 嘅對照組表現差唔多 |
| 5 | 拎走 long-range edge，模型睇到短 graph 嘅 node 次序 | 6 個同 node labels、107 nodes：實驗 Rg 相差 0.73；contact edges 預測相差 0.06，chain only 0.47 |

### 唔可以講
- ❌「Contact prior 令模型更準」：而家嘅證據顯示相反。
- ❌「我哋嘅模型睇得到次序」：只係短 graph 嗰組；334 nodes 嗰組冇一個 variant 排得啱（slide 13 caption 有寫）。
- ❌「接觸資訊原則上冇用」：我哋只證明咗**呢個建法**冇用；用化學揀 edge 嘅實驗未跑。
- ❌ 用 0.100 做 full model 嘅成績：重新 train 唔到，要用 3-seed 平均。
- ❌ 同其他 GNN（GCN、GIN、graph transformer）比較：我哋冇跑。

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


---

## 3. 成個簡報點樣串連

| 頁 | 講者 | 一句重點 | 時間 |
|---|---|---|---|
| 1–7 | Partner | 背景、IDP、Rg、接觸表、序列變 graph | 約 6:00 |
| **8** | **你** | **用 graph 嘅語言重講一次個 task：一個 protein 一個 graph，預測一個數** | **1:00** |
| **9** | **你** | **Edge-aware GAT；edge feature 入 attention** | **0:45** |
| **10** | **你** | **公平測試：三個 graph 對兩個唔睇 edge 嘅 baseline** | **0:50** |
| **11** | **你** | **模擬：chain-only error 低三分一；node 次序有用；加 long-range edge 反而差** | **0:55** |
| **12** | **你** | **實驗：所有 graph model 都贏 baseline；long-range edge 冇分別** | **0:40** |
| **13** | **你** | **點解：距離揀 edge，node 次序被蓋過** | **0:55** |
| **14** | **你** | **三個 takeaway** | **0:35** |

**時間：** 你嗰半 speaker notes 共 638 字。正常語速（每分鐘約 120 字）大約 5:20，加埋喺 11–13 頁指住 chart 嘅停頓，就大約 6 分鐘。如果超時，第 9 頁最易縮：唔讀公式，只講「edge features go into the attention score」。

### 你嗰半嘅弧線
1. **重新起步（8）：** Partner 講完 biology，你用 graph 嘅語言重講一次：node 係乜、edge 係乜、預測乜。**對識 graph 嘅 audience 嚟講，呢頁係入門口**，講慢啲。
2. **模型（9）：** GAT 點讀個 graph。
3. **定規矩（10）：** 點樣先算「graph 有用」：graph model 要贏 histogram；contact edges 要贏另外兩個 graph。
4. **好消息（11）：** Graph 贏，error 低三分一，因為 histogram 掉咗 node 次序。轉折：我哋自己加嘅 long-range edge 拖後腿。
5. **再確認（12）：** 真實數據上 graph 一樣贏，edge 冇分別。
6. **偵探（13）：** 點解？距離揀 edge，次序被蓋過。
7. **收尾（14）：** Graph 有用、瓶頸喺邊、下一步做咩。

---

## 4. 逐頁講稿（同 .pptx speaker notes 一樣）

### 第 8 頁：The task in graph terms: one graph per protein（1:00）
- **指住：** 先指左邊個 table，一行一行講 protein 對應 graph 嘅乜；然後指右邊 adjacency：藍色對角線係 local edges，橙色點係 long-range edges。最後一定要講「graph-level regression」。

> Thanks. Before the results, here is our task in graph terms.
>
> Each protein is a chain of amino acids, so we turn it into one graph. Each amino acid is a node, with its type, one of twenty, and its position. Neighbours along the chain get local edges, in blue. Then each node gets eight long-range edges, in orange, to partners that our simulation statistics say are likely to touch in 3D.
>
> These proteins have no fixed 3D shape, so there is no structure graph to use. The sequence is all we have.
>
> The target is one number per graph: Rg, how spread out the chain is in space. So this is graph-level regression. About one in ten node pairs becomes an edge, so the graphs stay sparse.

### 第 9 頁：Edge-aware graph attention network（0:45）
- **指住：** 由左至右掃一次上面四步，然後指公式入面橙色嘅 a_edge·MLP(e(i,j))。唔使讀成條公式，識 GAT 嘅人一睇就明。

> The model is a graph attention network with two layers. In each layer, every node collects messages from its neighbours and uses attention to weight them.
>
> The edge features, in orange, go into the attention score, so the model can learn how much to trust each long-range edge.
>
> Then we pool all nodes with mean and max, add the graph size, and predict Rg. The whole model has under nineteen thousand parameters.
>
> Our question is simple: does this graph structure, and especially our long-range edges, help?

### 第 10 頁：The test: three graphs and two baselines（0:50）
- **指住：** 由上至下指三個細 graph；然後指右邊兩個 baseline；最後指底部嗰句規則。可以順口講「notice the first two look almost the same」，為第 13 頁埋伏筆。

> To test that, we train three versions of the same network. The first has our contact edges. The second is a control: the same number of long-range edges, picked by distance along the chain alone. The third has no long-range edges, just the chain.
>
> We compare them with two baselines that ignore edges. One uses only the graph size. The other uses a histogram of the twenty node types, plus size. Biologists call this composition.
>
> If structure matters, the graph models should beat the histogram. If our contact edges help, the first model should win.

### 第 11 頁：Simulations: the chain-only graph cuts error by a third（0:55）
- **指住：** 虛線（histogram）→ 橙色 bar 同佢上面三粒點 → 第一條藍色 bar（contact edges）。講完「a third lower」停一停。

> Here are four thousand test proteins the models never saw. Lower is better. The grey bars are the baselines, and the histogram, this dashed line, is the one to beat.
>
> The orange bar is the chain-only graph. Its error is about a third lower than the histogram, and all three training runs agree. So the order of the nodes, which a histogram throws away, really matters, and message passing captures it.
>
> But the first blue bar, with our contact edges, is worse, even behind the histogram. The graph helps, but our long-range edges hold it back.

### 第 12 頁：Lab measurements: every graph model beats the baselines（0:40）
- **指住：** 虛線，然後指三條 graph bar 全部喺虛線下面；最後指藍色同橙色差唔多高。

> Now a harder test: 151 real proteins measured in the lab, while the models only ever saw simulations.
>
> Every graph model beats both baselines, the two main ones by eight to nine percent, and those two are tied. So on real data, the long-range edges neither help nor hurt. Errors are larger here because simulations are not perfect copies of real proteins.
>
> So why do our contact edges fail?

### 第 13 頁：Why our long-range edges fail（0:55）
- **指住：** 左邊：先讀 edge score 嗰句，再指藍色線好長、橙色線好短。右邊：三條 bar，由上至下 Measured、Chain only、Contact edges（幾乎冇）。

> Our edge score is: how often these two amino-acid types touch, divided by how often any pair this far apart touches. The first part varies only two-fold across types. The second varies over a thousand-fold with distance. So distance decides, and ninety-seven percent of chosen partners are simply the farthest nodes. That is why the distance-only control behaves the same.
>
> It also hurts. Here are six graphs with the same node labels, shuffled along the chain. Their real sizes differ a lot. The chain-only model sees much of that difference. With our contact edges, the predictions barely move. The far edges seem to wash out the order.

### 第 14 頁：What we can say, and what comes next（0:35）
- **指住：** 唔使指乜，望住 audience 講。

> To wrap up. First, the graph helps: message passing along the chain beats a node-type histogram, on simulations and on real proteins.
>
> Second, our long-range edges are the bottleneck, because distance, rather than chemistry, picks them.
>
> Third, next we rebuild the edge score so that chemistry picks the edges.
>
> Thank you. We are happy to take questions.

---

## 5. Q&A 準備

### 5a. Graph 相關（audience 最大機會問）

**G1. 個 graph 實際點砌？**
> One node per amino acid. Node features: a one-hot of the 20 types, plus the position i/(N−1). Local edges link nodes up to two apart along the chain, plus self-loops. Then each node keeps its top 8 long-range partners by our edge score, and we make the edges undirected, so a node ends up with about 12 long-range neighbours. Every edge has 10 features: the contact frequency of the type pair, the sequence distance, a one-hot of six distance bands, and flags for local edges and self-loops.

**G2. Long-range edge 點揀？Edge score 係咩？**
> We counted, over 28 million simulation frames, how often each pair of amino-acid types is within 8 Å. That gives a 20 × 20 table, f(a,b). The score divides f(a,b) by p(d), the average contact frequency at that sequence distance, so it is meant to say "more contact than expected for this distance". Each node keeps its top 8.

**G3. 個 graph 要預測乜？目標係乜？**
> One number per graph: the radius of gyration, Rg, which is how spread out the chain is in 3D. We regress log Rg with an MSE loss. The readout is mean and max pooling over nodes, concatenated with log N, then a small MLP.

**G4. 點解唔直接用 3D structure 做 graph？**
> These proteins are intrinsically disordered. They have no single 3D structure, they keep changing shape, so there is no structure graph to build. The sequence is the only input we have, and Rg is an average over many shapes.

**G5. 點解唔用 fully connected graph 或者 transformer？**
> A full graph has about N squared over two node pairs, around 130,000 for 512 nodes, and we only have about 19,000 training graphs. We also wanted to test a specific idea: whether simulation statistics can pick useful sparse edges. We have not run a transformer comparison.

**G6. 點解揀 GAT，唔用 GCN 或者 GIN？**
> Attention with edge features lets the model weight each edge, so in principle it can down-weight bad edges. We did not benchmark other GNN types, so we can't say GAT is the best choice.

**G7. 兩層、只連 ±2，receptive field 得 ±4 個 node，點樣預測到成條鏈嘅大細？**
> Global information comes from the readout: mean and max over all nodes, plus log N. Length explains most of Rg, and the local patterns pooled over the chain explain much of the rest. That also fits our limitation: for long chains, no model sees node order.

**G8. Attention 點解唔自動忽略啲壞 edge？**
> Our hypothesis is dilution: softmax is normalised over about 12 far neighbours and only 2 to 4 local ones, so the local signal gets washed out. We haven't verified that with an attention analysis.

**G9. 會唔會係 over-smoothing？**
> We use only two layers with residual connections and LayerNorm, and the chain-only model with the same depth works well. So the depth is the same in both, and the difference comes from the edges.

**G10. Node 次序點樣入到 model？**
> Through the chain edges and the position feature. The readout is permutation invariant, but the graph itself changes when you shuffle labels along the chain. A histogram can't tell shuffled sequences apart; the chain-only model can, at least for short chains.

**G11. 點解 node-type histogram 已經咁勁？**
> Rg depends mostly on length and on which amino acids are present, for example charged or sticky ones. Node order is the remaining part, and that is exactly what message passing adds.

**G12. Data 有幾多？點樣 split？**
> 28,058 simulated proteins, up to 512 nodes. We split 70/15/15 by protein, keeping regions of the same protein and identical sequences in one split: 18,860 train, 4,020 validation, 4,103 test. Plus 151 lab-measured proteins as a separate test.

### 5b. 結果同數字

**Q1. 咁你哋個 contact graph 究竟有冇用？**
> The graph itself helps: message passing along the chain beats the histogram on both datasets. Our long-range contact edges, as built, don't add anything, and we traced that to the edge rule: distance, not node type, decides the edges.

**Q2. 咁點解唔直接報 chain-only，仲要講 contact prior？**
> Because the project question was whether pairwise contact information helps. Answering "not this way, and here is why" is the result. The chain-only graph is the baseline that any future contact graph has to beat.

**Q3. 「低三分一」同「8–9%」點計？**
> On simulations, 0.066 versus 0.098 nanometres mean absolute error. On lab data, 0.301 and 0.303 versus 0.331. Bootstrap intervals exclude zero in both cases.

**Q4. 三個 seed 之間差幾多？**
> Chain only: 0.066 plus or minus 0.007 on simulations, and all three runs beat the histogram. With contact edges: 0.111 plus or minus 0.015.

**Q5. 你哋之前唔係報過 0.100 咩？**
> That came from one run on a different machine. Re-evaluating that saved checkpoint still gives 0.100, but retraining with the same seed on the new machine gives 0.128. So we report the mean over three seeds, which is 0.111.

**Q6. Bootstrap CI 有冇包括 seed 嘅不確定性？**
> No. We average predictions over seeds and then resample proteins. That's why we also show every seed: all three chain-only runs beat the histogram.

**Q7. 長啲嘅鏈點？**
> For a group of seven 334-node graphs, the measured spread is 1.39 nanometres, and no variant captures it: 0.08 with contact edges, 0.17 chain only.

**Q8. 點解 band-resolved 表未做？**
> It needs contact counts per distance band, recounted from the raw simulation trajectories. That archive wasn't available on our compute server, and we didn't want to fake it from the pooled table.

**Q9. 接觸表有冇 data leakage？**
> Yes, a small one: it was counted over all proteins, including test. It's a 20 × 20 summary, and our best model, chain only, uses it only as an edge feature on local edges. A training-only rebuild needs the same trajectory archive.

**Q10. 同 ALBATROSS 或者 STARLING 比點？**
> We haven't run them on our split, so we won't quote numbers.（唔好即場講佢哋 paper 嘅數字。）

**Q11. R² 0.99 唔係好高咩？**
> Graph size alone already gives 0.97, so R² hides most of the differences. That's why we compare error against the size and histogram baselines.

---

## 6. 數字速查同出處

| 數字 | 值 | 出處 |
|---|---|---|
| 只睇長度：模擬 / 實驗 MAE | 0.124 / 0.416 | `comp5222-presentation/analysis/check_story.py` |
| 組成：模擬 / 實驗 MAE | 0.098 / 0.331 | 同上 |
| 每個 seed 嘅 MAE | 見第 2 節 | `exp/edge-ablation`：`COMP-5222/experiments/edge_ablation/seed_metrics.tsv`；用 prediction 檔重新計過，一致（`scripts/data/seed_mae.json`） |
| 33% / 8–9% | (0.098 − 0.066) / 0.098 = 33%；(0.331 − 0.301) / 0.331 = 9%，(0.331 − 0.303) / 0.331 = 8% | 由上面數字計 |
| Bootstrap 差距 | 見第 1 節 | `experiments/edge_ablation/bootstrap.tsv` |
| 排列測試 | 6×107：0.73 / 0.06 / 0.47；7×334：1.39 / 0.08 / 0.17 | `experiments/edge_ablation/permutation_sensitivity.tsv` |
| 最遠 band 比例 | 96.6%（300 條 test 鏈） | `analysis/check_story.py`；`experiments/edge_ablation/edge_audit.json` |
| f(a,b) 範圍；p(d) 範圍 | 2.1×；1,338× | `scripts/scale_fig.py` |
| 舊 checkpoint 重新評估 | 模擬 0.100、實驗 0.295 | `runs/edge_ablation/historical_checkpoint_eval/` |
| 第 11、12 頁嘅 chart | — | `scripts/build.js` 嘅 `ablationChart`（PowerPoint native chart） |
