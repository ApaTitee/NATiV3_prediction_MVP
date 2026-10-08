# 核验与更新政策（读出后如何记录）

## 读出前（当前状态）
- `prediction.json` 冻结：任何字段不得回改；只允许追加 `amendments[]`（时间戳 + 理由 + 影响）。
- 若 cutoff 后、读出前出现**泄漏**（会议摘要/PR/媒体出现疗效数据）：
  1. 在 `leak_scan.csv` 追加一行（verdict=leak，附证据快照）；
  2. 在 `prediction.json.amendments[]` 记录泄漏时点与范围；
  3. 原预测标注 "prediction predates leak"，**禁止**用泄漏信息更新 P。

## 读出后（topline 公布或 CTG resultsSection 出现）
1. **分辨记录**：在 `prediction.json.amendments[]` 追加分辨来源（URL + 快照 + 时点）、主终点 p 值、各臂应答率。
2. **校准评分**：
   - 结果编码：success=1/0（对照 `success_definition`，含多重性细节）；
   - Brier score = (P − outcome)²；同时记录假设矩阵各格的 Brier；
   - 与类内历史预测（若有）做可靠性对比。
3. **复盘报告**（`future_work.md` 第 1 条）：逐条归因——先验哪里对/错（Δ？p0？脱落？）、SAP 槽位假设与实际之差、哪条证据被错误分级。
4. **失败模式特别审查**：若实际失败，检查是否为 S4 已实现（机制失败）还是执行因素（脱落/安慰剂漂移），以修正未来 a0 与 p0 的定标。
