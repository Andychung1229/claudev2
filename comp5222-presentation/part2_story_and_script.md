# COMP 5222 簡報後半段：故事線同講稿（第 8–14 頁，5–6 分鐘）

> 你負責第 8–14 頁。第 1–7 頁（背景、AlphaFold、接觸表、點樣將序列變成 graph）由 partner 講。
> **Audience 識 graph，但唔識 protein。** 所以第 8–14 頁全部用 graph 嘅講法：node、edge、graph-level regression、node-type histogram。Protein 嘅字眼只喺第一次出現時解釋一次。
> Slide 上面只留結論同少量數字，細節（CI、± sd、0.100 點解唔見咗）全部喺第 5 節 Q&A。

---

## 0. 呢個 project 用 graph 嘅語言講

### 一句講晒
**我哋將每個 protein 變成一個 graph，用細型 GAT 預測佢喺空間有幾散（Rg）。Chain-only GNN 嘅平均 error 比 linear node-type histogram 低三分一；原本額外加嘅 long-range edges 未顯示有額外益處。下一步係研究咩 long-range links 有用，同點樣同 local messages 配合。**

> *We turn each protein into a graph and use a GNN to predict how spread out it is in space. A small chain-based GNN cuts average simulation error by a third compared with a linear node-type histogram. Our current long-range edges add no clear benefit, and their selection is dominated by sequence distance.*

### Project 嘅性質（俾人問「what is this project about」時用）
| 問題 | 答案 |
|---|---|
| 係咩 task？ | **Graph-level regression**：每個 graph 輸出一個數 |
| Input 係咩？ | 一條 amino acid 序列。每個 amino acid 係一個 node（20 種 type + 位置），沿住條鏈連 local edges，再加按統計揀嘅 long-range edges |
| Output 係咩？ | Rg（radius of gyration）：條鏈喺 3D 空間有幾散，單位 nm。Train 嘅時候用 ln Rg 做 MSE |
| Label 由邊度嚟？ | 28,058 個 protein 嘅 physics simulation（Human IDRome），每個有大約 1,000 幀 3D 形狀，平均出 Rg。另外有 151 個實驗室量度嘅 protein 做 out-of-distribution test |
| 點解要預測 Rg？ | Rg 話俾生物學家知一個 disordered protein 係縮埋定散開，同佢點樣同其他分子結合有關。Simulation 每個 protein 都要跑好耐，GNN 一次 forward pass 就有答案 |
| 點解唔用 3D structure 做 graph？ | 呢類 protein（IDP）冇固定 3D 形狀，成日郁緊，所以今次用 sequence-based graph；預測時唔需要一個固定 3D structure |
| 研究問題係咩？ | (1) Graph structure 有冇幫手？即係 GNN 贏唔贏一個完全唔睇 edge 嘅 node-type histogram？(2) 我哋用 simulation 統計加嘅 long-range edges 有冇額外幫手？ |
| 答案 | (1) Chain-only GNN 贏 linear histogram baseline。(2) 呢個 long-range edge 規則喺模擬表現較差，實驗未見清楚差異；揀邊受距離主導 |

### Audience 要帶走嘅三件事
1. **Graph 幫到手**：chain-only graph 喺模擬 error 低 33%，實驗低 8–9%。
2. **我哋嘅 long-range edge 係瓶頸**：模擬數據加咗反而差，實驗數據未見清楚差異。
3. **Graph audit 提供線索**：96.6% partners 喺最遠可用 distance band；短鏈嗰組，contact graph 對次序變動較唔敏感。機制仍待驗證。

### 名稱對照（slide 上用嘅名）
| Slide 上 | 實驗入面 | 意思 |
|---|---|---|
| Graph: contact edges | full | Local edges + 每個 node 按 edge score 揀 top-8 long-range edge（我哋原本嘅 model） |
| Graph: distance edges | distance_only | 對照組：同樣 top-8 selection budget，但 ranking 唔用 node-type term；轉成 undirected 後 degree 可以唔同 |
| Graph: chain only | local_only | 冇 long-range edge，只有 \|i−j\| ≤ 2 嘅 local edges |
| Graph size only | 只睇長度 baseline | Rg ∝ N^ν，N = node 數 |
| Node-type histogram | 組成（composition）baseline | 20 種 node type 嘅比例 + 長度嘅 linear model（21 個參數）。生物學叫 composition |

**模型配色：** Contact graph 藍色、distance-only 深灰、chain-only 橙色；baselines 淺灰。Graph diagram 入面 local / long-range edge 嘅藍／橙係 edge 類型。

---

## 1. 講得出同唔可以講

### 講得出（有數據支持）
| # | 結論 | 證據 |
|---|---|---|
| 1 | Chain-only graph 喺模擬數據贏 histogram | 0.066 vs 0.098 nm（低 33%）；3 個 seed 全部好過；bootstrap −0.036 nm [−0.038, −0.033] |
| 2 | Graph model 喺實驗數據贏 histogram | Contact edges 0.301、chain only 0.303 vs 0.331（低 9% 同 8%）；兩個 CI 都唔包 0 |
| 3 | 我哋嘅 long-range edge 冇幫手 | 模擬：加咗之後 0.111，差過 histogram；實驗：同 chain only 嘅差異未有定論（+0.008 [−0.012, +0.028]） |
| 4 | Edge selection 受距離主導 | Full 同 distance-only 都有 96.6% partners 喺最遠可用 band；呢個係 topology audit，唔代表兩個模型表現相同 |
| 5 | 拎走 long-range edge，模型睇到短 graph 嘅 node 次序 | 6 個同 node labels、107 nodes：實驗 Rg 相差 0.73；contact edges 預測相差 0.06，chain only 0.47 |

### 唔可以講
- ❌「Contact prior 令模型更準」：而家嘅證據顯示相反。
- ❌「我哋嘅模型睇得到次序」：只係短 graph 嗰組；334 nodes 嗰組冇一個 variant 排得啱（slide 13 caption 有寫）。
- ❌「接觸資訊原則上冇用」：今次測試嘅**呢個建法**未顯示額外益處；用化學揀 edge 嘅實驗未跑。
- ❌ 用 0.100 做 full model 嘅成績：重新 train 唔到，要用 3-seed 平均。
- ❌ 同其他 GNN（GCN、GIN、graph transformer）比較：我哋冇跑。

---

## 2. 新實驗（Codex，`exp/edge-ablation` branch）

**設計：** 同一個 split、模型、optimizer 同 early stopping，只改 graph 規則同 seed（42、43、44）。

| Variant | 意思 |
|---|---|
| full | 原本嘅 graph：local edge + 每個殘基 top-8 contact edge |
| local_only | 只留 \|i−j\| ≤ 2 嘅 local edge 同 self-loop（proposal Table 1 嘅「Local-chain GAT」） |
| distance_only | 同樣 top-8 selection budget，只按距離 band ranking，再用 deterministic random ties；最終 degree 唔完全匹配 |
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
- **Distance-only 唔穩定：** 3 個 seed 由 0.070 到 0.140。Seed-averaged bootstrap 喺 test 優於 full，但實驗區間跨零；唔可以講兩個模型等價。最終平均 non-local degree 亦唔同：full 12.47、distance-only 14.75。
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
| **11** | **你** | **模擬：chain-only 平均 error 低三分一；加 contact edges 反而差** | **0:50** |
| **12** | **你** | **實驗：graph models 平均贏 baseline；long-range edge 未見清楚益處** | **0:40** |
| **13** | **你** | **Audit：距離主導揀邊；短鏈嗰組對次序較唔敏感** | **1:00** |
| **14** | **你** | **結論，加兩個 graph 研究方向** | **0:45** |

**時間：** Speaker notes 共 566 個英文詞，已包括最後兩句後續方向。每分鐘 110–120 詞，加約 40 秒轉頁同指圖，約 5:23–5:49。逐頁標示預留咗較多停頓，合共約 5:50。第 8、13 頁要練指圖；第 9 頁唔讀公式。

### 你嗰半嘅弧線
1. **重新起步（8）：** Partner 講完 biology，你用 graph 嘅語言重講一次：node 係乜、edge 係乜、預測乜。**對識 graph 嘅 audience 嚟講，呢頁係入門口**，講慢啲。
2. **模型（9）：** GAT 點讀個 graph。
3. **定規矩（10）：** 點樣先算「graph 有用」：graph model 要贏 histogram；contact edges 要贏另外兩個 graph。
4. **好消息（11）：** Chain-only GNN 平均 error 低三分一，三個 seeds 全部贏 linear histogram。轉折：加咗 contact edges 反而較差。
5. **再確認（12）：** 真實數據上 graph models 平均一樣贏 baseline，contact 同 chain-only 嘅差異未有定論。
6. **偵探（13）：** Audit：距離主導揀 edge；短鏈嗰組嘅 contact graph 次序敏感度較低。
7. **收尾（14）：** Chain-based GNN 有用；下一步研究揀邊、local/global messages 同 receptive field。

---

## 4. 逐頁講稿（同 .pptx speaker notes 一樣）

### 第 8 頁：The task in graph terms: one graph per protein（1:00）
- **指住：** 先指 table，再指藍色 local edges 同橙色 long-range edges；講清楚一個 graph 預測一個數。

> Thanks. Here is our task in graph terms.
>
> Each protein becomes one graph. Each amino acid is a node, with one of twenty types and its position along the chain.
>
> We connect nearby nodes with local edges, shown in blue. Each node also selects up to eight long-range partners from our contact prior, shown in orange. We then make these edges undirected.
>
> At prediction time, we use the sequence without a 3D structure. Our target is Rg, one number describing how spread out the chain is in space.
>
> So this is graph-level regression, using sequence-based graphs.

### 第 9 頁：Edge-aware graph attention network（0:45）
- **指住：** 由左至右指四步；公式只指橙色 edge-feature term，唔使讀公式。

> We use an edge-aware graph attention network with two layers. Each node collects messages from its neighbours, and attention learns how much weight to give each message.
>
> The orange term shows where edge features enter the attention score.
>
> Then we pool all nodes with mean and max, add the log graph size, and predict Rg. The whole model has fewer than nineteen thousand parameters.
>
> Now we can ask which graph connections actually help.

### 第 10 頁：The test: three graphs and two baselines（0:50）
- **指住：** 指三個 graph，再指兩個 baselines；模型配色：contact 藍、distance 灰、chain-only 橙。

> We compare three versions of the same network.
>
> First, our contact-edge graph. Second, a distance-only control, with the same top-eight selection budget but no node-type term in the ranking. Third, a chain-only graph with no long-range edges.
>
> There are also two baselines that ignore edges. One uses graph size alone. The other uses node-type proportions plus size. Biologists call this composition.
>
> We train each graph model with three random seeds. A useful contact-edge rule should improve on the chain-only graph.

### 第 11 頁：Simulations: the chain-only graph cuts error by a third（0:50）
- **指住：** 先指 histogram 虛線，再指橙色 chain-only 同三粒 seed 點；33% 係平均改善。

> Here are the results on about four thousand unseen simulated proteins. Lower error is better. The grey bars are the baselines, and the dashed line is the histogram baseline.
>
> The orange bar is the chain-only graph. Its average error is thirty-three percent lower than the histogram, and all three runs beat that baseline.
>
> This shows that a small chain-based GNN is useful for this task.
>
> But adding our contact edges raises the error. More connections do not automatically give a better graph.

### 第 12 頁：Lab measurements: every graph model beats the baselines（0:40）
- **指住：** 指 0.301 同 0.303：平均接近，未確認有清楚差異。

> Next are 151 proteins measured in the lab. The models were trained only on simulations.
>
> All three graph models have lower average error than the baselines. The contact-edge and chain-only models improve on the histogram by about eight to nine percent.
>
> Their average errors are close, and we found no clear difference between them on this dataset.
>
> So we looked more closely at the edge rule.

### 第 13 頁：Why edge choice matters（1:00）
- **指住：** 先指兩個 variation scales，再指 0.73 / 0.47 / 0.06；次序敏感度嘅結論只限呢組。

> The rule divides the contact frequency of two node types by the average frequency in their sequence-distance band.
>
> The node-type term varies about two-fold, while the distance term varies over a thousand-fold. As a result, ninety-seven percent of selected partners lie in the farthest available distance band.
>
> On the right are six sequences with the same node-type counts but different orders. Their measured sizes vary by 0.73 nanometres. The chain-only model captures a spread of 0.47, while the contact-edge model gives only 0.06.
>
> This suggests weaker order sensitivity in this group. The mechanism still needs testing.

### 第 14 頁：What we can say, and what comes next（0:45）
- **指住：** 收結用 graph design 問題：有用嘅 long-range edges 同較大 receptive field。最後兩句係後續研究方向。

> To finish, a small chain-based GNN beats the histogram baseline, while our current long-range edge rule adds no clear benefit.
>
> The next question is which long-range links are useful, and how they should interact with local messages.
>
> We plan to test distance-calibrated edges with separate local and long-range message passing. We also want to study larger receptive fields for longer chains, where sequence order remains difficult to capture.
>
> Thank you.

---

## 5. Q&A 準備

### 5a. Graph 相關（audience 最大機會問）

**G1. 個 graph 實際點砌？**
> One node per amino acid. Node features: a one-hot of the 20 types, plus the position i/(N−1). Local edges link nodes up to two apart along the chain, plus self-loops. Then each node keeps its top 8 long-range partners by our edge score, and we make the edges undirected, so a node ends up with about 12 long-range neighbours. Every edge has 10 features: the contact frequency of the type pair, the sequence distance, a one-hot of six distance bands, and flags for local edges and self-loops.

**G2. Long-range edge 點揀？Edge score 係咩？**
> We counted, over 28 million simulation frames, how often each pair of amino-acid types is within 8 Å. That gives a 20 × 20 table, f(a,b). The score divides f(a,b) by p(d), the average contact frequency at that sequence distance, so it is meant to say "more contact than expected for this distance". Each node selects up to eight partners, and we make the graph undirected. Incoming choices can make the final degree larger than eight.

**G3. 個 graph 要預測乜？目標係乜？**
> One number per graph: the radius of gyration, Rg, which is how spread out the chain is in 3D. We regress log Rg with an MSE loss. The readout is mean and max pooling over nodes, concatenated with log N, then a small MLP.

**G4. 點解唔直接用 3D structure 做 graph？**
> These proteins are intrinsically disordered. They have no single fixed 3D structure. In this project, prediction uses the sequence and a precomputed contact prior, without requiring 3D coordinates for the new protein. Rg describes an ensemble of shapes.

**G5. 點解唔用 fully connected graph 或者 transformer？**
> A full graph has about N squared over two node pairs, around 130,000 for 512 nodes, and we only have about 19,000 training graphs. We also wanted to test a specific idea: whether simulation statistics can pick useful sparse edges. We have not run a transformer comparison.

**G6. 點解揀 GAT，唔用 GCN 或者 GIN？**
> Attention with edge features lets the model weight each edge, so in principle it can down-weight bad edges. We did not benchmark other GNN types, so we can't say GAT is the best choice.

**G7. 兩層、只連 ±2，receptive field 得 ±4 個 node，點樣預測到成條鏈嘅大細？**
> Global information comes from the readout: mean and max over all nodes, plus log N. Length explains most of Rg, and the local patterns pooled over the chain explain much of the rest. In the 334-node permutation group, none of our variants ranks the sequences reliably. That motivates testing larger receptive fields.

**G8. Attention 點解唔自動忽略啲壞 edge？**
> Our hypothesis is dilution: softmax is normalised over about 12 far neighbours and only 2 to 4 local ones, so the local signal gets washed out. We haven't verified that with an attention analysis.

**G9. 會唔會係 over-smoothing？**
> We use only two layers with residual connections and LayerNorm, and the chain-only model with the same depth works well. The depth is matched, but extra edges could still change smoothing. We would need embedding or attention diagnostics to test that mechanism.

**G10. Node 次序點樣入到 model？**
> Through the chain edges and the position feature. The readout is permutation invariant, but the graph itself changes when you shuffle labels along the chain. A histogram can't tell shuffled sequences apart; the chain-only model can, at least for short chains.

**G11. 點解 node-type histogram 已經咁勁？**
> Rg depends mostly on length and on which amino acids are present, for example charged or sticky ones. The chain graph can represent local order, which the histogram discards. Our comparison does not isolate that effect from the GNN's nonlinear capacity and position feature.

**G12. Data 有幾多？點樣 split？**
> We start with 28,058 simulated sequences and group related proteins and identical sequences into a fixed 70/15/15 split. After limiting graphs to 512 nodes, we use: 18,860 train, 4,020 validation, 4,103 test. Plus 151 lab-measured proteins as a separate test.

### 5b. 結果同數字

**Q1. 咁你哋個 contact graph 究竟有冇用？**
> The graph itself helps: message passing along the chain beats the histogram on both datasets. Our current long-range edges raise simulation error and show no clear gain on lab data. The audit shows that distance dominates edge selection, and the short permutation group suggests reduced order sensitivity. The causal mechanism remains a hypothesis.

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

## 7. 後續方向（已放入第 14 頁最後兩句）

> We plan to test distance-calibrated edges with separate local and long-range message passing. We also want to study larger receptive fields for longer chains, where sequence order remains difficult to capture.

- **揀邊同 message passing：** 用 train-only、按 distance band 校準嘅 contact score，再比較分開 local / long-range messages 嘅設計；用 matched-degree control 分開 edge 質素同密度嘅影響。
- **長鏈嘅 context：** 兩層 local ±2 每個 node 嘅 receptive field 只到 ±4。以較大 receptive field 或分層 pooling 測試長鏈次序敏感度，特別係現時表現較弱嘅 334-node group。呢啲係後續假設，未聲稱已完成。
