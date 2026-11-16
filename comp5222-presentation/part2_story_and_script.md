# COMP 5222 簡報後半段：故事線同講稿（第 8–14 頁，約 6 分鐘）

> 你負責第 8–14 頁：graph 長咩樣、模型點運作、點樣公平咁測試、結果、同埋點解 long-range edge 唔得。
> 第 1–7 頁（背景、AlphaFold、接觸表、點樣將序列變成 graph）由 partner 講。
> 呢版將 slide 同講稿簡化咗：slide 上面只留結論同少量數字，細節（CI、± sd、0.100 點解唔見咗）全部搬咗去第 5 節 Q&A。

---

## 0. 一句講晒

**Graph 有用：一個細細嘅 GAT 沿住條鏈做 message passing，喺模擬數據 error 比組成模型低三分一，喺實驗數據都贏。唔得嘅係我哋揀 long-range edge 嘅方法，因為條公式幾乎只睇序列距離。**

英文版：

> *The graph helps: a tiny network passing messages along the chain beats composition on simulations and on lab data. Our long-range edges are the bottleneck, because sequence distance, rather than chemistry, decides which edges we draw.*

### Audience 要帶走嘅三件事
1. **Graph 幫到手**：chain-only graph 喺模擬 error 低 33%，實驗低 8–9%。
2. **我哋嘅 long-range edge 係瓶頸**：模擬數據加咗反而差，實驗數據冇分別。
3. **我哋知道點解**：揀 edge 嘅公式俾距離主導，揀出嚟嘅都係最遠嘅殘基，仲蓋過咗排列資訊。

### 名稱對照（slide 上用嘅名）
| Slide 上 | 實驗入面 | 意思 |
|---|---|---|
| Graph: contact edges | full | Local edge + 每個殘基按 contact prior 揀 top-8 long-range edge（我哋原本嘅 model） |
| Graph: distance edges | distance_only | 對照組：long-range edge 數目一樣，但只按距離揀（唔睇胺基酸） |
| Graph: chain only | local_only | 冇 long-range edge，只有 \|i−j\| ≤ 2 嘅 local edge |
| Composition | 組成 + 長度 baseline | 20 個胺基酸比例 + 長度嘅 linear model（21 個參數） |

---

## 1. 講得出同唔可以講

### 講得出（有數據支持）
| # | 結論 | 證據 |
|---|---|---|
| 1 | Chain-only graph 喺模擬數據贏組成模型 | 0.066 vs 0.098 nm（低 33%）；3 個 seed 全部好過組成；bootstrap −0.036 nm [−0.038, −0.033] |
| 2 | Graph model 喺實驗數據贏組成模型 | Contact edges 0.301、chain only 0.303 vs 組成 0.331（低 9% 同 8%）；兩個 CI 都唔包 0 |
| 3 | 我哋嘅 long-range edge 冇幫手 | 模擬：加咗之後 0.111，差過組成；實驗：同 chain only 冇分別（+0.008 [−0.012, +0.028]） |
| 4 | 原因：edge 由距離決定 | 96.6% partner 喺最遠 band；只按距離揀 edge 嘅對照組表現差唔多 |
| 5 | 拎走 long-range edge，模型睇到短鏈嘅排列 | 6 條同組成、107 aa：實驗 Rg 相差 0.73；contact edges 預測相差 0.06，chain only 0.47 |

### 唔可以講
- ❌「接觸先驗令模型更準」：而家嘅證據顯示相反。
- ❌「我哋嘅模型睇得到排列」：只係短鏈嗰組；334 aa 嗰組冇一個 variant 排得啱（slide 13 caption 有寫）。
- ❌「接觸資訊原則上冇用」：我哋只證明咗**呢個建法**冇用；用化學揀 edge 嘅實驗未跑。
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
| 1–7 | Partner | 背景、IDP、Rg、接觸表、序列變 graph | 約 6:00 |
| **8** | **你** | **Graph 有兩種 edge：local（藍）同 long-range（橙）** | **0:45** |
| **9** | **你** | **GAT 讀個 graph；edge feature 入 attention，model 自己學信唔信 contact prior** | **0:50** |
| **10** | **你** | **公平測試：三個 graph 對兩個冇 graph 嘅 baseline** | **0:50** |
| **11** | **你** | **模擬：chain-only error 低三分一；加 long-range edge 反而差** | **1:00** |
| **12** | **你** | **實驗：所有 graph model 都贏 baseline；long-range edge 冇分別** | **0:45** |
| **13** | **你** | **點解：距離揀 edge，排列資訊被蓋過** | **1:00** |
| **14** | **你** | **三個 takeaway** | **0:35** |

**時間：** 你嗰半 speaker notes 共 651 字。正常語速（每分鐘約 120 字）大約 5:25，加埋喺 11–13 頁指住 chart 嘅停頓，就大約 6 分鐘。如果超時，第 9 頁最易縮：唔讀公式，只講「edge features go into the attention score」。

### 你嗰半嘅弧線
1. **鋪墊（8–9）：** Graph 長咩樣、模型點讀佢。
2. **定規矩（10）：** 講清楚點樣先算「graph 有用」：graph model 要贏組成；contact edge 要贏另外兩個 graph。**呢頁係令 audience 睇得明之後幾頁嘅關鍵**，講慢啲。
3. **好消息（11）：** Graph 贏，error 低三分一。轉折：我哋自己加嘅 long-range edge 拖後腿。
4. **再確認（12）：** 真實數據上 graph 一樣贏，edge 冇分別。
5. **偵探（13）：** 點解？距離揀 edge，排列被蓋過。
6. **收尾（14）：** Graph 有用、瓶頸喺邊、下一步做咩。

**第 10 同 11 頁係成段最重要。** 第 10 頁講清楚遊戲規則，第 11 頁先可以自信咁講「graph 幫到手」。

---

## 4. 逐頁講稿（同 .pptx speaker notes 一樣）

### 第 8 頁：Two kinds of edges in one sparse graph（0:45）
- **指住：** 先指 adjacency matrix 嘅藍色對角線（local edges），再指散開嘅橙色點（long-range edges）。

> Thanks. So our graph has two kinds of edges. The blue ones are local: each residue links to its neighbours, up to two steps away along the chain, so messages can travel along the sequence.
>
> The orange ones are long-range: each residue also links to eight partners chosen by our contact prior. The idea is to connect residues that might touch in 3D.
>
> Each edge carries a few features, like the contact frequency and the distance along the chain. Only about one in ten pairs becomes an edge, so the graph stays small even for long chains.

### 第 9 頁：Edge-aware graph attention network（0:50）
- **指住：** 由左至右掃一次上面四步，然後指公式入面橙色嘅 `a_edge·MLP(e(i,j))`。唔使讀成條公式。

> The model is a graph attention network. It runs two rounds of message passing. In each round, every residue collects messages from its neighbours and uses attention to decide how much to listen to each one.
>
> The key detail is here, in orange: the edge features go into the attention score. So the model can learn how much to trust our contact prior, instead of us fixing it by hand.
>
> After two rounds, we pool over the whole chain, add the chain length, and predict Rg. The whole model has under nineteen thousand parameters, which is tiny by deep-learning standards.

### 第 10 頁：The test: three graphs and two baselines（0:50）
- **指住：** 由上至下指三個細 graph；然後指右邊兩個 baseline；最後指底部嗰句規則。
- **提示：** 指住頭兩個 graph 時可以順口講「notice they look almost the same」，為第 13 頁埋伏筆（唔講都得）。

> To find out whether the graph really helps, we set up a fair test. We train three versions of the same network.
>
> The first has our contact edges. The second is a control: the same number of long-range edges, but picked by distance alone. The third has no long-range edges at all, just the chain.
>
> We compare them with two simple baselines that use no graph. One uses only the chain length, and one adds the amino-acid composition.
>
> So, if the graph helps, the graph models should beat composition. And if our contact edges help, the first model should win.

### 第 11 頁：Simulations: the chain-only graph cuts error by a third（1:00）
- **指住：** 灰色 bar 同虛線（composition）→ 橙色 bar 同佢上面三粒點 → 第一條藍色 bar（contact edges）。講完「a third lower」停一停。

> Here are the results on four thousand simulated proteins that the models never saw. Lower is better.
>
> The grey bars are the baselines, and composition, this dashed line, is the one to beat.
>
> Now the orange bar: the chain-only graph. Its error is about a third lower than composition, and all three training runs, these dots, agree. So message passing along the chain clearly helps.
>
> But look at the first blue bar. When we add our contact edges, the error goes up, and the model falls behind composition. So the graph helps, but our long-range edges hold it back.

### 第 12 頁：Lab measurements: every graph model beats the baselines（0:45）
- **指住：** 虛線，然後指三條 graph bar 全部喺虛線下面；最後指藍色同橙色差唔多高。

> Next, 151 proteins whose size was measured in the lab. Remember, the models only ever saw simulations.
>
> Here, every graph model beats both baselines. The chain-only and the contact-edge models are tied, both eight to nine percent better than composition. So on real data, the long-range edges neither help nor hurt.
>
> The errors are larger than on simulations, because we inherit the gap between the simulations and real proteins.
>
> So why do our contact edges fail?

### 第 13 頁：Why our long-range edges fail（1:00）
- **指住：** 左邊：藍色線好長、橙色線好短。右邊：三條 bar，由上至下 Measured → Chain only → Contact edges（幾乎冇）。

> We looked at how they are chosen. Our edge score divides the contact frequency of a residue pair by the average frequency at that distance. The chemistry part varies only about two-fold. The distance part varies more than a thousand-fold.
>
> So distance wins. Ninety-seven percent of the chosen partners are simply the farthest residues, and the amino-acid type barely matters. That is why the distance-only control behaves the same.
>
> And it costs us residue order. Here are six sequences with the same amino acids in different orders. Their measured sizes differ a lot. The chain-only model picks up much of that difference. With our contact edges, the predictions barely move.

### 第 14 頁：What we can say, and what comes next（0:35）

> To wrap up. First, the graph helps: a tiny network passing messages along the chain beats composition, on simulations and on real measurements.
>
> Second, our long-range edges are the bottleneck, because sequence distance, rather than chemistry, decides which edges we draw.
>
> Third, the next step is to rebuild the contact table for each distance band, so that chemistry picks the edges.
>
> Thank you. We are happy to take questions.

---

## 5. Q&A 準備

**Q1. 咁你哋個 contact graph 究竟有冇用？**
> The graph itself helps: message passing along the chain beats composition on both datasets. Our long-range contact edges, as built, don't add anything, and we traced that to the edge rule: distance, not amino-acid type, decides the edges.

**Q2. Chain-only 點解會好過有 contact edge 嘅 model？**
> We don't know for sure. Our hypothesis is dilution: each residue has two to four local neighbours but about twelve distant ones, and attention is normalised over all of them. We haven't tested that directly yet.

**Q3. 咁點解唔直接報 chain-only，仲要講 contact prior？**
> Because the project question was whether pairwise contact information helps. Answering "not this way, and here is why" is the result. The chain-only graph is the baseline that any future contact graph has to beat.

**Q4. 「低三分一」同「8–9%」點計？**
> On simulations, 0.066 versus 0.098 nanometres mean absolute error. On lab data, 0.301 and 0.303 versus 0.331. Bootstrap intervals exclude zero in both cases.

**Q5. 三個 seed 之間差幾多？**
> Chain only: 0.066 plus or minus 0.007 on simulations, and all three runs beat composition. With contact edges: 0.111 plus or minus 0.015.

**Q6. 你哋之前唔係報過 0.100 咩？**
> That came from one run on a different machine. Re-evaluating that saved checkpoint still gives 0.100, but retraining with the same seed on the new machine gives 0.128. So we report the mean over three seeds, which is 0.111.

**Q7. Bootstrap CI 有冇包括 seed 嘅不確定性？**
> No. We average predictions over seeds and then resample sequences. That's why we also show every seed: all three chain-only runs beat composition.

**Q8. Chain-only GAT 睇到幾遠？**
> Two layers over neighbours up to two apart, so each residue sees about four residues either side, plus global mean and max pooling. So it learns local sequence patterns, which fits with it sensing order in short chains but not in long ones.

**Q9. 長啲嘅鏈點？**
> For a group of seven 334-residue sequences, the measured spread is 1.39 nanometres, and no variant captures it: 0.08 with contact edges, 0.17 chain only.

**Q10. 點解 band-resolved 表未做？**
> It needs pair counts per distance band, which must be recounted from the raw trajectories. That archive wasn't available on our compute server, and we didn't want to fake it from the pooled table.

**Q11. 接觸表有冇 data leakage？**
> Yes, a small one: it was counted over all chains, including test. It's a 20 × 20 summary, and our best model, chain only, uses it only as an edge feature on local edges. A training-only rebuild needs the same trajectory archive.

**Q12. 同 ALBATROSS 或者 STARLING 比點？**
> We haven't run them on our split, so we won't quote numbers.（唔好即場講佢哋 paper 嘅數字。）

**Q13. R² 0.99 唔係好高咩？**
> Length alone already gives 0.97, so R² hides most of the differences. That's why we compare error against length and composition baselines.

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
