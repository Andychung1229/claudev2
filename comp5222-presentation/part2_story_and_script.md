# COMP 5222 簡報後半段：故事線同講稿（第 8–14 頁，6 分鐘）

> 你負責第 8–14 頁：graph 長咩樣、模型點運作、結果、同埋我哋學到咩。
> 第 1–7 頁（背景、接觸表、點樣將序列變成 graph）由你 partner 講。
> 本文所有數字都由 zip 入面嘅數據同 run 結果計出嚟，出處喺最尾。

---

## 0. 一句講晒

**我哋整咗一個好細（18.7k 參數）、唔使模擬就預測到 IDP 大細嘅 graph 模型，佢喺真實實驗數據上贏一個只睇胺基酸組成嘅簡單模型；但喺模擬 test set 上兩者打和，而我哋搵到原因：揀 edge 嘅規則幾乎只睇序列距離，所以個 graph 未真正用到「邊對殘基會黐埋」呢個資訊。**

英文版（可以用嚟收尾）：

> *A small, simulation-free graph model predicts IDP size and transfers to experiment better than a composition baseline — but our edge rule is dominated by sequence distance, so the graph does not yet use pairwise contact information. Fixing that is the clear next step.*

---

## 1. 我哋份 project 有冇嘢講？

**有，但唔係「graph 贏晒」。** 有三樣嘢係講得出、又企得穩嘅，另外有兩樣嘢唔可以講。

### 講得出（有數據支持）

| # | 結論 | 證據 |
|---|---|---|
| 1 | 模型準、細、唔使模擬 | 18,721 參數；4,103 條未見過嘅蛋白：MAE 0.100 nm，R² 0.981 |
| 2 | 由模擬學到嘅嘢，搬去真實實驗都用得 | 151 條實驗 Rg：r = 0.92，MAE 0.295 nm（只睇長度：0.416） |
| 3 | 喺實驗數據上，GAT 明顯贏只睇組成嘅模型 | MAE 0.295 vs 0.331 nm；差 −0.036 nm，95% CI [−0.054, −0.018]；61% 序列 GAT 較準 |
| 4 | **（新發現）模擬 test set 上，組成 + 長度已經夠** | 21 參數線性模型：MAE 0.098 vs GAT 0.100；差距 95% CI [−0.001, +0.005]，即係打和 |
| 5 | **（新發現）點解 graph 幫唔到手：edge 幾乎只由距離決定** | 揀出嚟嘅 partner 有 96.6% 喺「最遠嗰個距離 band」；組成一樣但排列唔同嘅序列，GAT 幾乎俾同一個答案 |

### 唔可以講（冇數據支持）

- ❌ 「graph／non-local edge／接觸先驗令模型更準」：未做 ablation，而且第 4 點反而顯示喺模擬數據上冇額外幫助。
- ❌ 「模型可解釋，睇到邊對殘基推動壓縮」：attention 同刪 edge 實驗都未做。

### 點解呢個仍然係一個好故事

Proposal 第 5 節自己寫咗：

> *“The project remains informative if the graph model does not outperform simpler baselines: that outcome would identify limits of the proposed contact representation rather than justify unsupported performance claims.”*

我哋而家正正係咁：有一個 controlled baseline，有一個具體診斷（點解 graph 未發揮作用），仲有一個同 proposal 公式 (2) 一致嘅修正方法。老師通常好欣賞呢種誠實、有證據嘅分析，多過一句冇根據嘅「我哋贏晒」。

---

## 2. 三個新檢查（之前份 slides 未有）

呢三樣係我喺寫呢份文件之前做嘅，**會改變第 11–14 頁要講嘅嘢**。

### 檢查 A：只用組成 + 長度嘅線性模型

- 模型：ln Rg = w₀ + w₁·ln N + Σ wₐ·(胺基酸 a 嘅比例)，共 21 個參數；用同一個 training split（N ≤ 512）fit，ridge λ = 10⁻³。
- 呢個係 proposal Table 1 「Composition MLP」嘅簡化版（線性，唔係 MLP），所以如果用 MLP，baseline 只會更強。

| | 只睇長度 | 組成 + 長度（21 參數） | ContactGAT（18,721 參數） |
|---|---|---|---|
| **模擬 test（n = 4,103）** MAE | 0.124 | **0.098** | 0.100 |
| RMSE | 0.210 | 0.177 | **0.173** |
| R² | 0.972 | 0.980 | **0.981** |
| 長度解釋唔到嘅 variance，捉到幾多 | — | 31% | **36%** |
| **實驗（n = 151）** MAE | 0.416 | 0.331 | **0.295** |
| R² | 0.744 | 0.822 | **0.846** |
| Pearson r | 0.865 | 0.908 | **0.921** |

**點讀：** 模擬數據上兩者打和；實驗數據上 GAT 贏，而且 paired bootstrap 嘅 95% CI 唔包 0。注意 GAT 只 train 咗一個 seed，所以呢個 CI 只反映「揀邊啲序列」嘅不確定性，唔包括 training 隨機性。

### 檢查 B：non-local edge 實際上點揀

規則係：分數 = f(a,b) / p(band)，每個殘基揀分數最高嘅 8 個。問題係兩個數嘅變化幅度差太遠：

| | 最細 | 最大 | 幅度 |
|---|---|---|---|
| f(a,b)：唔同胺基酸對嘅接觸頻率 | 0.0068 | 0.0145 | **約 2.1 倍** |
| p(band)：唔同距離 band 嘅平均接觸頻率 | 0.00032（> 32） | 0.42（2–4） | **約 1,300 倍** |

相鄰兩個 band 之間，最細嘅差距都有 2.8 倍（9–16 對 17–32），**大過**所有胺基酸對之間最大嘅差距（2.1 倍）。所以：

- 胺基酸種類**永遠**唔可以將一條 edge 由一個 band 推去另一個 band，佢只係喺同一個 band 入面揀邊個。
- 實測：隨機抽 300 條 test 鏈，揀出嚟嘅 partner **96.6%** 喺嗰個殘基「最遠嗰個 band」。剩低 3.4% 係因為最遠 band 唔夠 8 個殘基，要去下一個 band 補。
- 結果：graph 嘅 topology 基本上等於「每個殘基連去最遠嗰批殘基」。接觸資訊只係透過 edge feature f(a,b) 入去，而嗰個數只得 2 倍變化。

**點解會咁：** Proposal 公式 (2) 嘅 p_abd 係按 (a, b, 距離 band) 分開計，enrichment = p_abd / p_d 會喺同一個 band 入面比較，距離效應自動抵銷。我哋嘅實作冇三維計數，用咗一張 20 × 20 嘅 f(a,b) 代替，所以除以 p_d 就變咗主要喺度量距離。`contact_mpnn/graph.py` 入面 `build_sparse_graph` 個 docstring 都有寫明呢個簡化。

### 檢查 C：組成一樣、排列唔同嘅序列

151 條實驗序列入面，有 2 組係組成完全一樣、只係排列唔同（共 13 條）：

| 組 | 長度 | 實驗 Rg 範圍 | GAT 預測範圍 |
|---|---|---|---|
| 6 條 | 107 | 2.21 – 2.94 nm（差 0.73） | 3.00 – 3.08 nm（差 0.08） |
| 7 條 | 334 | 4.06 – 5.44 nm（差 1.38） | 5.27 – 5.33 nm（差 0.06） |

**點讀：** 真實世界入面，排列唔同可以令 Rg 差到 1.4 nm，但我哋個模型幾乎俾同一個答案。排序方向大致啱（rank correlation 0.54、0.68），但幅度細到冇用。呢個同檢查 B 一致：**個 graph 幾乎睇唔到排列**，而排列（例如電荷分佈）正正係 IDP 生物學最關心嘅嘢。

> 咁點解 GAT 喺實驗數據會贏組成模型？我哋唔肯定。可能係 non-linear 嘅組成效應，或者組成同長度之間嘅交互作用，線性模型捉唔到。**唔好講係因為佢識睇排列**，檢查 C 顯示唔係。

---

## 3. 成個故事點樣串連（14 頁）

| 頁 | 講者 | 一句重點 | 時間 |
|---|---|---|---|
| 1 | Partner | 題目同兩個人 | 0:20 |
| 2 | Partner | IDP 冇固定結構，要用 ensemble 描述 | 0:55 |
| 3 | Partner | Rg 係 ensemble 嘅大細；長度定 baseline，序列定其餘 | 0:55 |
| 4 | Partner | 冇結構數據、現有模型讀 1D、數據少 | 0:50 |
| 5 | Partner | 我哋嘅想法：將殘基對資訊放入 graph | 0:40 |
| 6 | Partner | 由 2,800 萬幀模擬數出接觸表；同已知物理一致 | 1:05 |
| 7 | Partner | 序列 → graph：node、local edge、non-local edge | 1:10 |
| **8** | **你** | **graph 好稀疏；每條 edge 有 10 個 feature** | **0:50** |
| **9** | **你** | **edge-aware GAT；先驗經 attention 入去** | **1:00** |
| **10** | **你** | **按蛋白分 split；13 分鐘 train 完** | **0:30** |
| **11** | **你** | **模擬 test：準，但組成 + 長度都做到** | **1:20** |
| **12** | **你** | **實驗：GAT 贏組成模型，但誤差係模擬嘅 3 倍** | **1:00** |
| **13** | **你** | **診斷：edge 由距離決定，graph 睇唔到排列** | **0:55** |
| **14** | **你** | **三個 takeaway + 下一步** | **0:25** |

Partner 6:35，你 6:00。Partner 要再壓 30 秒左右先夠 12 分鐘，最易係第 2、3 頁各減 15 秒。

### 故事嘅弧線（你嗰半）

1. **建立期望（8–10）：** 我哋有一個好有物理意義嘅 graph 同一個細模型。
2. **好消息（11 前半、12 前半）：** 準、可以搬去實驗。
3. **轉折（11 後半）：** 但一個 21 參數嘅組成模型喺模擬數據做到一樣好。
4. **偵探（13）：** 點解？因為 edge 規則被距離主導，graph 睇唔到排列。
5. **收尾（14）：** 呢個係有價值嘅發現，同埋點樣修正。

**轉折位係成段最重要嘅地方**，唔好講得好似道歉，要講得好似「我哋做咗一個認真嘅檢查，而且搵到原因」。

---

## 4. 你嘅 6 分鐘：逐頁講稿

每頁有：目的、要指住咩、要記嘅數字、英文講稿（按每分鐘大約 140 字寫）、過場句。
✅ 第 5 節嘅修改已經做咗：.pptx 同網頁版 deck 嘅第 8–14 頁 slides 同 speaker notes 已經同下面嘅講稿一致。

### 第 8 頁：The graph is sparse, and every edge carries features（0:50）

- **目的：** 由 partner 嘅「一個殘基點揀 edge」拉闊到「成條鏈嘅 graph」，並為第 13 頁埋伏筆。
- **指住：** adjacency matrix 嘅藍色對角線（local），然後橙色點（non-local），強調橙色點全部離對角線好遠。
- **數字：** 155 個殘基；1,192 / 11,935 對 = 10%；每條 edge 10 個 feature。

> **Script:**
> Thanks. So that was one residue — here is a whole graph, for a chain of 155 residues. This is its adjacency matrix. The blue band along the diagonal is the local edges; the orange cells are the non-local edges. Only about ten percent of all residue pairs become edges, so the graph grows like N times w plus k instead of N squared, and message passing stays cheap. Every edge carries ten numbers: the contact frequency from our table, the sequence distance, a one-hot distance band, and two flags for local edges and self-loops. Keep one thing in mind: all the orange edges sit far from the diagonal. That will matter when we look at the results.

- **過場：** “Now, how does the model read this graph?”

### 第 9 頁：An edge-aware graph attention network reads the graph（1:00）

- **目的：** 解釋接觸先驗點樣影響模型，同埋模型有幾細。
- **指住：** 第一條公式嘅 `a_edge · MLP(e(i,j))`，然後右邊「18,721 parameters」。
- **數字：** 2 層 × 4 heads × 16 channels；18,721 參數；readout = mean ‖ max ‖ log N。

> **Script:**
> The model is a graph attention network that also reads edge features. For each edge, every attention head scores it from three parts: the sending node, the receiving node, and the edge features. That third term is where the contact prior enters — as an input to the attention score, not a fixed weight, so the model learns how much to trust it. The scores are normalised only over each node’s neighbours, and each node takes a weighted sum of their messages, with a residual connection and LayerNorm. After two layers, we pool the whole chain — mean, max, and log of the length — and a small MLP predicts log Rg. The whole model has under nineteen thousand parameters.

- **過場：** “We trained it on a split that really tests unseen proteins.”

### 第 10 頁：Training on unseen-protein splits（0:30）

- **目的：** 證明 test set 係公平嘅（按蛋白分）。快快講過。
- **數字：** 18,860 / 4,020 / 4,103；15,331 組；13 分鐘；best epoch 31。

> **Script:**
> We split seventy–fifteen–fifteen by protein, not by sequence: all regions of the same UniProt protein stay in one split, so the test set holds proteins the model has never seen. We minimise squared error on log Rg with AdamW and early stopping. Training takes about thirteen minutes on one consumer GPU. The validation curve is noisy — a learning-rate schedule should fix that.

- **過場：** “So, how well does it do?”

### 第 11 頁：On simulations, composition and length explain most of Rg（1:20）

- **目的：** 好消息 + 轉折。呢頁係你成段最重要嘅一頁。
- **指住：** 先指 parity plot，再指 table 三欄，最後指「打和」嗰個 callout。
- **數字：** GAT 0.100 / R² 0.981；只睇長度 0.124 / 0.972；組成 + 長度 0.098 / 0.980；36% vs 31%。

> **Script:**
> On four thousand unseen proteins, the model is accurate: mean error 0.10 nanometres, R squared 0.98. But a high R squared here proves very little, because length alone already gives 0.97. So we tested two simple baselines on the same split. Against length alone, our model cuts the error by about a fifth. The harder test is a linear model on amino-acid composition plus length — just 21 parameters. And on simulated data, it ties with our graph model: 0.098 versus 0.100 nanometres, and the difference is within noise. Of the variation that length cannot explain, our model captures 36 percent, the linear model 31. So on this benchmark, composition and length explain most of what our model predicts. We think any IDP predictor should report this baseline.

- **過場：** “Simulations are one thing. What about real experiments?”

### 第 12 頁：On real experiments, the graph model does beat composition（1:00）

- **目的：** 第二個好消息，加一個誠實嘅限制。
- **指住：** parity plot（橙色菱形 = 同 training 重疊），然後 table 嘅組成模型一行。
- **數字：** GAT 0.295 / r 0.921；組成 0.331 / r 0.908；長度 0.416；差 −0.036，CI [−0.054, −0.018]；61%；22 條重疊，剔走後 0.296。

> **Script:**
> Here are 151 sequences with experimentally measured Rg. The model never saw an experimental label, yet it tracks them with a correlation of 0.92. Here the graph model does beat the composition model: 0.295 versus 0.331 nanometres, and a paired bootstrap puts that difference clearly below zero. Twenty-two of these sequences, the orange diamonds, sit inside training sequences; dropping them changes nothing. The caveat is that the error is three times larger than on simulations. Our labels come from one simulation model, so we inherit its gap to experiment.

- **過場：** “So why does the graph help so little on simulations? We looked closely at the edges.”

### 第 13 頁：Why the graph adds little: distance decides the edges（0:55）

- **目的：** 偵探時間，解釋原因。要講得自信，因為呢個係我哋自己搵到嘅結果。
- **指住：** 左邊張 log-scale 圖：藍色（距離 band）橫跨成條軸，橙色（胺基酸對）得一小段；然後右上 96.6%，最後右下排列測試嘅兩行（實驗差好遠，預測幾乎一樣）。
- **數字：** f 2.1×；p(band) 1,300×；96.6%；Rg 2.21–2.94 vs 預測 3.00–3.08。

> **Script:**
> Our edge score divides the pair’s contact frequency by the average frequency at that distance. But contact frequency varies only two-fold between amino-acid pairs, while the distance term varies over a thousand-fold. So distance always wins: 97 percent of chosen partners lie in the farthest available distance band. The amino-acid type only breaks ties inside a band. You can see the consequence in the experiments. Here are six sequences with the same composition in different orders: their measured Rg spans 0.7 nanometres, but our predictions span less than 0.1. In other words, our graph barely sees residue order — and order, like charge patterning, is exactly what matters for disordered proteins.

- **過場：** “That points directly to what we do next.”

### 第 14 頁：Takeaways（0:25）

> **Script:**
> Three takeaways. One: a tiny, simulation-free graph model predicts IDP size and transfers to experiment better than a composition baseline. Two: on simulated data, composition and length already explain most of Rg, so that baseline belongs in every comparison. Three: our edge rule was dominated by distance. The fix is the band-resolved contact table from our proposal, which compares amino-acid pairs at the same distance — then the planned ablations. Thank you.

---

## 5. Slides 改咗咩（已完成）

舊版 .pptx 係檢查 A–C **之前**整嘅，有兩句企唔住，而家已經改好（.pptx、網頁版 deck、GitHub 都係新版）：

- 第 11 頁標題「On unseen proteins, the graph beats length alone」：字面上啱，但會令人以為係 graph 嘅功勞。
- 第 14 頁標題「Putting residue pairs into the graph works」：**而家冇證據支持**，一定要改。

| 頁 | 舊版 | 新版 |
|---|---|---|
| 8 | Speaker notes 開頭冇過場 | 加「Thanks. So that was one residue…」；結尾嘅伏筆保留 |
| 11 | 2 欄 table；callout「−19%」「36%」 | 標題：*On simulations, composition and length explain most of Rg*；table 加「Composition + length (21 params)」一欄；callout 改為「Tie: 0.100 vs 0.098 nm」同「36% vs 31%」 |
| 12 | 冇組成 baseline | 標題：*On real experiments, the graph model does beat composition*；table 加組成一行（0.331 / 0.822 / 0.908）；callout：「−0.036 nm, 95% CI [−0.054, −0.018]」 |
| 13 | 4 格 limitations | 標題：*Why the graph adds little: distance decides the edges*；左邊一張新圖（`edge_scales.png`，log scale 比較兩個幅度）；右上 96.6%；右邊排列測試 table；底部一行細字列埋餘下限制（接觸表用咗全部鏈、只有一個 seed） |
| 14 | 「Putting residue pairs into the graph works」 | 標題：*What we can say, and what comes next*；三點跟第 4 節第 14 頁講稿 |

第 8–10 頁嘅 slides 內容冇改，只係 speaker notes 換成第 4 節嘅講稿（加咗過場句，第 10 頁縮到 30 秒）。

---

## 6. Q&A 準備

**Q1. 咁你哋個 graph 究竟有冇用？**
> On simulated data, not beyond composition and length — we show that directly. On experiments it does beat composition, with a confidence interval that excludes zero, though from one training seed. And we found why it helps less than we hoped: the edge rule is dominated by distance.

**Q2. R² 0.98 唔係好高咩？**
> It is, but length alone gives 0.97. That is why we report the length and composition baselines and the share of the length-residual variance.

**Q3. 點解 GAT 喺實驗贏，但喺模擬打和？**
> We don’t know yet. It is not order sensitivity — the permutation test rules that out. Likely non-linear composition effects or composition–length interactions, which a linear model can’t capture. A composition MLP, from our proposal, would test that.

**Q4. 你哋同 ALBATROSS 或者 STARLING 比點？**
> We haven’t compared on the same split, so we won’t quote numbers. That needs running them on our test proteins.
>（⚠️ 唔好即場講佢哋 paper 嘅數字，唔同數據集冇得直接比。）

**Q5. 接觸表有冇 data leakage？**
> Yes, a small one: it was counted over all 28,058 trajectories, including validation and test. It is only a 20 × 20 summary, so we expect little effect, but we will rebuild it from training chains only, as the proposal says.

**Q6. 點解唔用 proposal 講嘅 PyTorch Geometric GATConv？**
> We implemented the same edge-aware attention as dense tensors with an edge mask, which is mathematically equivalent on our graph and lets us batch chains of similar length.

**Q7. 點解 predict log Rg？**
> Rg follows a power law in length, which is linear in log space, and errors scale with size, so log makes the loss treat short and long chains fairly.

**Q8. 點解只用 ≤ 512 個殘基？**
> Our attention is stored densely, so memory grows with N squared. That drops 1,075 of 28,058 chains; a sparse implementation would remove the limit.

**Q9. 只 train 一個 seed，結果穩唔穩？**
> No, one seed is a limitation; the validation curve is noisy too. The proposal plans three seeds.

**Q10. 你哋講可解釋，有冇證據？**
> Not yet. The contact table itself is interpretable — aromatic pairs enriched, prolines with charges depleted — but we haven’t tested which edges the model relies on.

---

## 7. 如果簡報前仲有一個 GPU 小時（可選）

做到第一個實驗，第 13 頁嘅論點會強好多。

1. **先修好 `contact_mpnn/graph.py`**：第 25 行尾嘅 `"""` 刪咗（docstring 提早收咗尾，而家成個 package import 唔到，乜都 run 唔到）。
2. **Local-only GAT（proposal Table 1 嘅 “Local-chain GAT”）**：複製 `configs/sparse_gat.yaml`，將 `graph.topk` 改做 `0`，`paths.out_dir` 改做 `runs/contact_gat_local_only`，然後 `python scripts/train.py --config <新 config>`，大約 13 分鐘。
   - 如果結果同 full model 差唔多，就直接證明 non-local edge 而家冇幫手，同檢查 B 吻合。
3. **Band-resolved 接觸表**：要改 `build_contact_table.py` 按 (a, b, band) 計數，仲要有原本嗰個 trajectory zip（喺你部 server 度），唔係一個鐘做得完。放喺「下一步」就得。

---

## 8. 數字速查同出處

| 數字 | 值 | 出處 |
|---|---|---|
| GAT test MAE / RMSE / R² / r | 0.100 / 0.173 / 0.981 / 0.992 | `runs/contact_gat_idrome_sparse/plot_metrics.json` |
| GAT 實驗 MAE / RMSE / R² / r | 0.295 / 0.417 / 0.846 / 0.921 | 同上 |
| 參數數目 | 18,721 | `logs/contact_gat_sparse.out` |
| Split | 18,860 / 4,020 / 4,103（N ≤ 512） | 同上 |
| 只睇長度：ν，test MAE，實驗 MAE | 0.535，0.124，0.416 | `make_figs.py` |
| 組成 + 長度：test MAE / R²；實驗 MAE / R² / r | 0.098 / 0.980；0.331 / 0.822 / 0.908 | `check_story.py` |
| 長度殘差 variance 捉到 | GAT 36%，組成 31% | `make_figs.py`、`check_story.py` |
| GAT − 組成（實驗）MAE 差 | −0.036 nm，95% CI [−0.054, −0.018]，61% 序列 GAT 較準 | `bootstrap.py` |
| GAT − 組成（test）MAE 差 | +0.002 nm，95% CI [−0.001, +0.005] | `bootstrap.py` |
| f(a,b) 範圍 | 0.0068 – 0.0145 | `check_story.py` |
| p(band)：2–4 / 5–8 / 9–16 / 17–32 / > 32 | 0.422 / 0.0248 / 0.00847 / 0.00302 / 0.00032 | `check_story.py` |
| Partner 喺最遠 band 嘅比例 | 96.6%（300 條隨機 test 鏈） | `check_story.py` |
| 排列組 | 6 條（107 aa）：實驗 2.21–2.94，預測 3.00–3.08；7 條（334 aa）：實驗 4.06–5.44，預測 5.27–5.33 | `perm_check.py` |
| 實驗序列同 training 重疊 | 22 / 151；剔走後 MAE 0.296 | `make_figs.py` |

Script 全部喺 GitHub `comp5222-presentation/analysis/` 同 `comp5222-presentation/scripts/`，用法：`python <script> <COMP-5222 folder>`（要 numpy；畫圖嘅 script 仲要 matplotlib）。`scale_fig.py` 畫第 13 頁嗰張圖。組成 baseline 同 bootstrap 係我加嘅分析，唔係原本 project code 嘅一部分。
