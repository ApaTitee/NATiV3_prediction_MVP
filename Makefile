PY := .venv/Scripts/python.exe

.PHONY: run reproduce ledger test figures

# 在线路径（需网络 + .env 中的 LLM key）
run:
	$(PY) -m src.fetch.ctgov
	$(PY) -m src.fetch.pubmed
	$(PY) -m src.fetch.benchmarks
	$(PY) -m src.fetch.company_pr
	$(PY) -m src.extract.pdf_text
	$(PY) -m src.fetch.leak_scan
	$(PY) -m src.extract.ctgov_card
	$(PY) -m src.llm.pipeline
	$(PY) -m src.model.run_model
	$(PY) -m src.report.figures

# 离线路径：只用已提交快照与 artifacts，零 API 成本，确定性
reproduce:
	$(PY) -m src.fetch.leak_scan
	$(PY) -m src.model.run_model
	$(PY) -m src.report.figures
	$(PY) -m pytest tests/ -q
	$(PY) -m src.report.check_reproduce

test:
	$(PY) -m pytest tests/ -q

figures:
	$(PY) -m src.report.figures

ledger:
	$(PY) -m src.report.build_ledger
