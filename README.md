# README — NATiV3 主终点预测 MVP

## 这是什么

对 lanifibranor 的 NATiV3 Ⅲ期试验（NCT04849728）主终点能否达到预设统计标准的可复现预测系统。
**结论：positive，P(success) = 0.753（稳健性区间 I80 = [0.57, 0.89]）** —— 概率由整试验 Monte Carlo 模拟器算出，非 LLM 自述置信度。

## 环境

```bash
uv venv --python 3.12 && uv pip install requests numpy scipy pandas matplotlib statsmodels openai pytest python-dotenv pypdf
cp .env.example .env   # 填入 LLM_API_KEY / LLM_BASE_URL（仅 make run 需要）
```

## 两条运行路径

| 命令 | 说明 | 成本 |
|---|---|---|
| `make run` | 在线全链路：抓取快照 → 泄漏扫描 → LLM 管线 → 模型 → 图 | LLM API 按量计费（硬上限 $35） |
| `make reproduce` | **离线复算**：只读已提交快照与 artifacts → 模型 → 图 → 7 项测试 → 与 `ledger/prediction.json` 对账（判据 \|ΔP\| ≤ 2·MCSE） | 零 |

## 目录

- `data/snapshots/` + `manifest.csv` — 全部原始数据快照（sha256 + retrieved_at，全部 ≤ cutoff 2026-10-08T07:00Z）
- `artifacts/evidence.csv` — 20 条证据台账（分级 A/B/C/D，verbatim 引文经程序化校验）
- `artifacts/design_card.json` — 试验设计卡（CTG 机械抽取 + 人工核对）
- `artifacts/model/` — 模型输出（verdict.json、假设矩阵、敏感性、情景表、设计反演）
- `artifacts/llm/` — LLM 调用审计（prompt/response/usage/cost）
- `src/fetch|extract|model|llm|report/` — 代码；`tests/` — 数值 QA
- `ledger/` — prediction.json（首次预测，不可回改）、cost_report.csv、timesheet.csv、leak_scan.csv、cutoff.json
- `report/` — REPORT.md（主报告）、mechanism.md、figures/
- `analysis_plan.md` — 自我 SAP（判定规则/基线假设/超参，先于任何概率计算冻结；改动只走 Amendments）

## 关键口径声明

1. **成功标准**：主队列 Week 72 复合终点（MASH 缓解 ∩ 纤维化改善≥1 期）按 SAP 检验与多重性策略统计显著。SAP 未公开的槽位（α/多重性/插补等）以假设矩阵逐格报告 P，不择优。
2. **概率依据**：混合先验（情景 S1–S4，权重冻结）× 整试验模拟（共享对照相关性、Hochberg、NRI 衰减均由模拟显式处理）；LLM 只用于证据结构化/红队/审校，不产出数值先验。
3. **成本口径**：`cost_report.csv` 记 MVP 运行期 LLM 调用；本项目的开发期 AI 助手消耗（会话型）无法精确计量，单列说明而不混入运行期账单。
4. **泄漏纪律**：cutoff 后出现的疗效信息只允许触发"作废/重记"程序，禁止回改 `prediction.json`；读出后按 `ledger/update_policy.md` 做校准复盘。
