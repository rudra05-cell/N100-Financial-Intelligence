# =============================================================
# Nifty 100 Financial Intelligence Platform — Makefile
# =============================================================

.PHONY: help load ratios test report dashboard api clean setup

help:
	@echo ""
	@echo "  Nifty 100 Financial Intelligence Platform"
	@echo "  ─────────────────────────────────────────"
	@echo "  make setup      Create venv + install dependencies"
	@echo "  make load       Run ETL: load all 12 files → nifty100.db"
	@echo "  make ratios     Compute 50+ KPIs → financial_ratios table"
	@echo "  make test       Run full pytest suite → pytest_report.html"
	@echo "  make report     Generate all PDFs (92 tearsheets + 11 sector)"
	@echo "  make dashboard  Start Streamlit dashboard on port 8501"
	@echo "  make api        Start FastAPI server on port 8000"
	@echo "  make clean      Remove .pyc, __pycache__, test artifacts"
	@echo ""

setup:
	python -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	cp config/.env.template .env
	@echo "Setup complete. Edit .env if needed, then run: make load"

load:
	python src/etl/loader.py

ratios:
	python src/analytics/ratios.py

test:
	pytest tests/ \
		--html=reports/pytest_report.html \
		--self-contained-html \
		--cov=src \
		--cov-report=html:reports/coverage \
		-v

report:
	python src/reports/portfolio_report.py

dashboard:
	streamlit run src/dashboard/app.py --server.port 8501

api:
	uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned build artifacts."
