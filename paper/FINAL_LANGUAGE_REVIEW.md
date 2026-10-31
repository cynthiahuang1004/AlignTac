# AlignTac 最終稿語句審查：待作者核准的建議

審查日期：2026-10-24（America/New_York）。對象為八頁 conference manuscript `main.tex` 與 `sections/*.tex`，不是長版。

本機正文與 Overleaf `3e4890cf70f9bc7c3d944813f1abca8114d347ff` 一致。本輪只讀取遠端，沒有 pull 覆蓋本機、修改論文文字或推送。本文件是建議稿，不代表下列修改已套用。

## 審查結論與修改範圍

目前主線與章節順序已清楚：標註需求 → real-image–geometry alignment → pseudo-labels → student → session adaptation／optional refinement。建議維持結構、數字、四項貢獻、圖與表，集中處理少量長句、冗餘及比較對象不明的表達。標準技術詞如 pseudo-label、residual aligner、contact state 應保留；不能由幾個常見短語判斷作者是否使用 AI。

依作者要求，Xiaohao 修改過的內容需先核准。已查遠端提交 `34f2646`、`20a2cfb`、`e6fe7e7`、`cc27f61`。其中 `cc27f61` 直接修改消融正文；Method 多處的最後修改者也是 Xiaohao。其他段落雖然最後由共同作者更新，仍保留 Xiaohao 的文字，因此本輪所有建議都先列出，不直接改正文。下列「待確認」是依作者的明確要求，而非額外的工具或 skill 審批要求。

## 參考的原始論文

- [DeepIM](https://arxiv.org/html/1804.00175v4)：方法段先明示輸入、初始估計與輸出的 correction；參考其具體說明方式，不複製句子或宣稱本稿有其未見物體能力。
- [Sparsh](https://arxiv.org/html/2410.24090v1)：摘要、Introduction 與 Discussion；區分 representation learning 的研究定位、下游任務與部署限制。本稿使用 frozen SITR，因此摘要可更直接以 geometry／pose prediction 作開場。
- [Tac2Pose](https://arxiv.org/html/2204.11701v3)：方法、實驗與 Discussion；對已知幾何、真實 contact observations 和 pose ambiguity 的描述具體。本稿同樣應維持已知 identity／mesh 的範圍。

這些參考支持寫作組織的取捨；下面的英文皆為針對本稿提出的建議，不是上述論文的引文。

## 優先建議

### P01 — 摘要開場：直接指出本稿要學的任務

位置：`main.tex:45`。共同編修段落，待確認。

原文：
> Vision-based tactile representation learning is a key enabler for dexterous manipulation. However, collecting accurately labeled training data remains a bottleneck.

建議：
> Learning to estimate contact geometry and pose from tactile images requires accurately labeled data, which are difficult to collect.

原因：原句並非事實錯誤，但 representation learning 容易使讀者預期本文主要貢獻是新的 encoder／pretraining。本稿固定 SITR encoder，直接指出 geometry／pose 任務更準確，也減少抽象開場。這仍以資料取得的一般問題作研究動機，不以 teacher／student 的消融結果倒推動機。

### P02 — 摘要末句：保留 release 承諾，刪除泛泛目的語

位置：`main.tex:45`。共同編修段落，待確認。

原文：
> Our code will be released to foster future research.

建議：
> Code will be released.

原因：後半句沒有提供額外資訊。是否保留整句取決於作者的 release 計畫；本建議不改成「已公開」，也不新增 URL。

### P03 — 消融：刪除重複的比較用語

位置：`sections/05_experiments.tex:69`。Xiaohao 在 `cc27f61` 直接修改，必須先核准。

原文：
> Without alignment, the resulting student underperforms compared to a real-only baseline trained under the same 50-epoch schedule (depth MSE 0.058 vs. 0.049); with alignment, it is the best student across the reported metrics.

建議：
> Without alignment, the student performs worse than the real-only baseline under the same 50-epoch schedule (depth MSE 0.058 vs. 0.049). With alignment, it performs best across the reported metrics.

原因：`underperforms compared to` 冗餘；拆成兩句更容易對照。保留相同 schedule、數字及結果範圍。

### P04 — 消融：明確說出兩個 IoU 各自與誰比較

位置：`sections/05_experiments.tex:69`。Xiaohao 在 `cc27f61` 直接修改，必須先核准。

原文：
> Adding teacher pose pseudo-labels to self-training (row 2) improves pose without appreciable change in contact reconstruction, and L1 search (row 4) improves label and student IoU but remains below that of the aligner.

建議：
> Adding teacher pose pseudo-labels to self-training (row 2) improves pose with little change in contact reconstruction. L1 search (row 4) improves both pseudo-label and student IoU, but both remain lower than with learned alignment.

原因：`remains below that of the aligner` 的主詞與比較對象不夠明確。建議只改句法，不改 teacher 差異、row 定義或因果結論。

### P05 — Related Work：修正不自然的搭配

位置：`sections/02_related.tex:10`。最後修改者為 Xiaohao，待確認。

原文：
> Pretrained encoders such as SITR, T3 and Sparsh reduce feature learning from scratch; all our predictors share a frozen SITR backbone.

建議：
> Pretrained encoders such as SITR, T3 and Sparsh reduce the need to learn tactile features from scratch. All predictors in our experiments use the same frozen SITR backbone.

原因：`reduce feature learning from scratch` 不如 `reduce the need to learn ...` 自然。改成兩句也分清前人貢獻與本稿的固定比較條件。實作時保留原有 citations。

### P06 — Conclusion 首段：縮短長列舉，減少重述方法

位置：`sections/06_conclusion.tex:3`。共同編修段落，保守列為待確認。

原文：
> AlignTac connects real tactile appearance with simulated contact geometry through learned contact-state alignment. For known objects, a small labeled set trains an aligner that turns additional real contacts into geometrically supervised examples. Across the marker-free and dot-marker variants of GelSlim 4.0, a separate session of the marker-free sensor and four additional objects, this improves contact reconstruction using real tactile images and aligned geometric supervision. Images from a new session can be pseudo-labeled by the same aligner without re-calibration, further lowering contact error. Standard student inference predicts contact geometry and pose directly, with mesh-assisted refinement available as an option.

建議：
> For known objects, AlignTac learns contact-state alignment from a small labeled set and uses the aligned mesh to supervise additional real images. Experiments on both GelSlim 4.0 variants, a second capture session, and four additional objects show improved contact reconstruction. The same aligner supports adaptation to the new session by generating pseudo-labels without recalibration. The student predicts depth, normals and planar pose from the image and object identity, with optional mesh-assisted pose refinement.

原因：目前第三句的長列舉與 `this` 讓主詞較難追蹤，並再度重述開頭的 real-image／geometry 設定。建議把評估範圍獨立成一句。後面的 alignment insight、simulation 的互補角色與 future work 維持原段落，不刪除。

## 可選的小修

### P07 — Introduction：移除不自然的指稱

位置：`sections/01_intro.tex:26`。共同編修段落，待確認。

原文片段：
> our AlignTac combines real tactile appearance with known simulated geometry ...

建議片段：
> AlignTac combines real tactile appearance with known simulated geometry ...

原因：方法名稱前不需要 `our`。其餘研究動機與已知 mesh 設定保留。

### P08 — Introduction：收準「不能直接比較」的含義

位置：`sections/01_intro.tex:26`。共同編修段落，待確認；屬措辭精確度，而非新的實驗結論。

原文片段：
> mesh depth cannot be compared with tactile RGB directly

建議片段：
> mesh depth and tactile RGB are not directly comparable as pixel intensities

原因：原句可能被理解為任何跨模態比較都不可行。建議明示 pixel intensities，不排除 geometry matching、特徵或 learned correspondence。仍可保留它作一般性的跨表示對齊困難；93% 的 renderer 實驗不拿來作此問題的起源。

### P09 — Setup：把 L1 search 的長句拆成步驟

位置：`sections/03_setup.tex:15`。共同編修段落，待確認。

原文：
> L1 search fits the mesh to teacher depth from the teacher's pose, then picks, among 567 nearby poses, the one whose learned-renderer (K) image has the lowest L1 error against the real image; mesh depth is used for the lowest-error half of each object's frames and teacher depth otherwise.

建議：
> L1 search initializes the mesh at the teacher's pose and fits it to teacher depth. It then evaluates 567 nearby poses with the learned renderer (K) and selects the pose with the lowest RGB L1 error against the real image. For each object, the lowest-error half of frames uses mesh depth; the rest uses teacher depth.

原因：保留原演算法、候選數與 half-depth gate，只降低句法負擔。實作時保留原 `\emph{L1 search}` 與數學格式。

### P10 — 新 session adaptation：讓新增資料與測試分割更直接

位置：`sections/05_experiments.tex:123`。共同編修段落，待確認。

原文：
> We take every contact frame from half of the session-2 presses (1,066 images), discard their poses, pseudo-label them with the session-1 teacher and aligner, and add them to student training.

建議：
> We add 1,066 images from one half of the session-2 presses to student training, using pseudo-labels from the session-1 teacher and aligner without their recorded poses.

原因：把資料量、用途與 supervision 放在同一條明確流程，省去容易讓人追問 raw-frame sampling 的 `every`。下一句維持在另一半 presses 上測試、三 seed 與 IoU 未改善的說明。本項不是說當前實驗分割有問題。

### P11 — Abstract：把 student prediction 與 optional refinement 分句

位置：`main.tex:45`。共同編修段落，待確認。

原文：
> The aligned geometry supplies depth, normal and planar-pose pseudo-labels for a student that predicts directly from the image and object identity; the same aligner optionally refines pose at inference.

建議：
> The aligned geometry supplies depth, normal and planar-pose pseudo-labels for a student that predicts from the image and object identity. The same aligner can optionally refine pose at inference.

原因：保留原有任務和 input 假設，將兩條 inference 路徑分開讀。原句本身並無技術錯誤。

## 一項值得補充的實驗交代

### C01 — 四個新增物體的 test-set 大小

位置：`sections/05_experiments.tex:127`。共同編修段落，待確認；這是補充 protocol，不只是 rephrase。

目前段落交代四個物體、3,156 contacts、16-object training 與 three-seed 結果，但沒有說新增物體的 held-out test set 有多大。Setup 的 530 sensor-A test frames 是原本 12-object testA，讀者需要分清兩組。

可在該段第二句前加入：
> We evaluate these objects on 489 held-out frames.

依據：`aligntac_newobj/eval_newobj_v2.json` 的 `/new` 結果，button／edge／hex key／marble 的 `n` 分別為 88／138／118／145，合計 489。這只是把已完成的 evaluation 範圍寫明，沒有新增實驗、修改模型或重算結果。

## 建議維持的部分

- 標題、四項貢獻及章節順序，這輪沒有必要再重構。
- Method 的 state／pose 區分、初始化與迭代公式、object identity、mesh-free standard inference 已清楚，不為追求「不同用詞」而更動。
- 各 teacher 的差異、三 seed／single-seed 標記、兩種 checkpoint 的選擇方式與 training-label／validation-label 的區分，繼續保留。
- 93% 的敘述目前正確限定於 tested renderer 的 RGB L1 score，沒有把它寫成 pose failure rate。
- Fig. 6 目前 caption 沒有聲稱所有例子都按 median 選取；不恢復舊的 median-frame 敘述。
- Discussion 中 contact ambiguity、simulation coverage 和 geometric alignment 的適用條件有價值，不刪成只有摘要重述。

## 驗證

- 已在原始稿上執行 `python build.py`，編譯成功，PDF 仍為 8 頁。
- `main.log` 沒有 undefined references/citations、overfull boxes、LaTeX errors 或 warnings。
- 檢視八頁 PDF，沒有看到文字或圖表被截斷／重疊；所有文字框均在頁面範圍內。
- Hash 比對：`main.tex` 與六個 short-section sources 在本輪沒有變更。沒有修改圖、table data、bibliography、長版或 `.overleaf_head`；沒有 push。

建議先考慮 P01–P06 與 C01。P07–P11 是可選的局部調整；沒有必要把每一句都改成另一種寫法。套用任何核准項目後，仍須重新編譯檢查八頁版面，尤其現有 `\FinalLine{...}` 包裹的位置。
